# system/api.py - 服务接口（真实实现，桩转实第 4 步）
# ============================================================
# 职责：暴露系统能力给外部（企业集成面）：
#   - 世界实例生命周期（创世 / tick / 快照）
#   - Agent 操作（spawn / 决策 / 记忆导出）
#   - 经济操作（PoR 查验 / 发行 / 赎回）
#   - 审计查询（19 项报告拉取）
#
# 实现：纯标准库 http.server（无第三方依赖，可横向扩展部署）。
#   鉴权：基于 soul_hash 的 Bearer Token 中间件（可插拔）。
#   前端技术选型：webview 部分可部署到边缘 CDN（React/TS）。
# ============================================================

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from .runtime import World
from .keys import load_or_create_key, generate_key, verify_signature
from .ledger import is_hex64

# WebSocket 握手魔术串（RFC 6455）
_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# 无需鉴权的公开路由
# 注：spawn（创世注册）公开，因为它自带公钥签名证明——无效证明在
# runtime 层被拒；有效证明即自证所有权，匿名注册新灵魂无安全危害。
_PUBLIC_ROUTES = {
    ("GET", "/health"),
    ("POST", "/agent/spawn"),
    ("POST", "/auth/challenge"),
    ("POST", "/auth/issue"),
    ("GET", "/protocol/schemas"),
    ("POST", "/protocol/validate"),
}


def _safe_float(value, default: float = 0.0) -> Optional[float]:
    """安全转 float，失败返回 None（供调用方区分 0 和非法值）。"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _ws_accept(key: str) -> str:
    """计算 Sec-WebSocket-Accept 响应值。"""
    return base64.b64encode(
        hashlib.sha1((key + _WS_GUID).encode("utf-8")).digest()
    ).decode("ascii")


def _ws_frame(text: str) -> bytes:
    """编码一条服务端 -> 客户端文本帧（FIN=1, opcode=0x1, 无掩码）。"""
    data = text.encode("utf-8")
    header = bytearray([0x81])  # FIN + text
    n = len(data)
    if n < 126:
        header.append(n)
    elif n < 65536:
        header.append(126)
        header += struct.pack(">H", n)
    else:
        header.append(127)
        header += struct.pack(">Q", n)
    return bytes(header) + data


def _ws_close_frame() -> bytes:
    """关闭帧（opcode=0x8）。"""
    return b"\x88\x00"


def _b64url(data: bytes) -> str:
    """URL 安全的 base64 编码（去 padding）。"""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    """URL 安全的 base64 解码（补齐 padding）。"""
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


class SoulAuth:
    """
    鉴权中间件：基于 soul_hash 的 HMAC 无状态签名 token。
    token 格式：base64url(payload).base64url(signature)
    payload = "soul_hash.expires_at"
    signature = HMAC-SHA256(secret_key, payload)

    特性：
    - 无状态：服务重启后 token 仍有效（密钥持久化，不随进程消失）
    - 不可伪造：签名由服务端独有密钥产生，篡改 payload 即失效
    - 可过期：expires_at 校验，过期 token 拒绝
    """

    def __init__(
        self,
        key: Optional[bytes] = None,
        key_path: Optional[str] = None,
        token_ttl: int = 3600,
    ):
        if key is None and key_path:
            key = load_or_create_key(key_path)
        if key is None:
            # 未提供密钥时降级为进程内随机密钥（测试/开发场景）
            key = generate_key()
        self._key = key
        self.token_ttl = token_ttl
        # 挑战-响应登录：一次性的 nonce（绑灵魂，防重放，5 分钟过期）
        self.challenges: Dict[str, Dict] = {}
        self.challenge_ttl = 300
        # 并发保护：ThreadingHTTPServer 多线程下 challenges 读写加锁
        self._lock = threading.Lock()
        # 速率限制：每 soul 60s 内最多 5 次登录尝试（防暴力破解）
        self._rate_limit: Dict[str, list] = defaultdict(list)
        self._rate_window = 60
        self._rate_max = 5

    def _check_rate(self, soul_hash: str) -> bool:
        """检查速率限制。返回 True 表示允许，False 表示超限。"""
        now = time.time()
        attempts = self._rate_limit[soul_hash]
        # 清理过期记录
        self._rate_limit[soul_hash] = [t for t in attempts if now - t < self._rate_window]
        if len(self._rate_limit[soul_hash]) >= self._rate_max:
            return False
        self._rate_limit[soul_hash].append(now)
        return True

    def issue_challenge(self, soul_hash: str) -> str:
        """下发一次性 nonce（未绑定的旧 nonce 被覆盖，天然失效）。"""
        if not self._check_rate(soul_hash):
            return None  # 速率超限
        nonce = secrets.token_hex(16)
        with self._lock:
            self.challenges[soul_hash] = {
                "nonce": nonce,
                "expires": int(time.time()) + self.challenge_ttl,
            }
        return nonce

    def verify_challenge(
        self, soul_hash: str, nonce: str, signature_b64: str, pubkey: bytes
    ) -> bool:
        """校验挑战-响应签名：一次性、未过期、验签通过，三者缺一即拒。"""
        with self._lock:
            entry = self.challenges.pop(soul_hash, None)  # 一次性：用后即焚
        if not entry or entry["nonce"] != nonce:
            return False
        if entry["expires"] < int(time.time()):
            return False
        try:
            signature = base64.b64decode(signature_b64)
        except Exception:
            return False
        return verify_signature(pubkey, nonce.encode("utf-8"), signature)

    def issue(self, soul_hash: str, ttl: Optional[int] = None) -> str:
        """签发 token：绑定 soul_hash，携带过期时间。"""
        expires_at = int(time.time()) + (ttl if ttl is not None else self.token_ttl)
        payload = f"{soul_hash}.{expires_at}".encode("utf-8")
        sig = hmac.new(self._key, payload, hashlib.sha256).digest()
        return f"{_b64url(payload)}.{_b64url(sig)}"

    def verify(
        self, token: Optional[str], soul_ledger: Optional[Any] = None
    ) -> Optional[str]:
        """
        校验 token，返回 soul_hash；无效/过期/灵魂不存在返回 None。
        若传入 soul_ledger，额外校验 soul_hash 是否已注册到全球身份账本。
        """
        if not token:
            return None
        if token.startswith("Bearer "):
            token = token[7:]
        try:
            enc_payload, enc_sig = token.rsplit(".", 1)
            payload = _b64url_decode(enc_payload)
            expected = hmac.new(self._key, payload, hashlib.sha256).digest()
            if not hmac.compare_digest(_b64url_decode(enc_sig), expected):
                return None
            soul_hash, expires_at = payload.decode("utf-8").split(".", 1)
            if int(expires_at) < int(time.time()):
                return None
            if soul_ledger is not None and not soul_ledger.exists(soul_hash):
                return None  # 灵魂未注册，token 无效
            return soul_hash
        except (ValueError, UnicodeDecodeError):
            return None


class WorldAPI:
    """协议接口：把 World 的能力暴露为 REST 路由。"""

    def __init__(self, world: World):
        self.world = world
        # 鉴权密钥持久化到世界数据目录，保证 token 跨服务重启仍可验证
        key_path = os.path.join(world.storage.data_dir, "auth_key")
        self.auth = SoulAuth(key_path=key_path)

    # ---- 路由分发 ----
    def dispatch(
        self, method: str, path: str, body: Dict, token: Optional[str]
    ) -> tuple:
        """返回 (status, payload_dict)。"""
        # 有状态会话验证（可撤销）；灵魂未注册则 token 无效
        soul = self.world.sessions.verify(token)
        if soul is not None and not self.world.soul_ledger.exists(soul):
            soul = None

        # 无需鉴权：健康检查
        if path == "/health":
            return 200, {"status": "ok", "world_id": self.world.world_id}

        # ---- 鉴权门：非公开路由必须携带有效 token ----
        if (
            soul is None
            and (method, path) not in _PUBLIC_ROUTES
            and not path.startswith("/ws/")
        ):
            return 401, {"error": "authentication required"}

        # ---- 世界生命周期 ----
        if method == "GET" and path == "/world":
            return 200, self._world_state()
        if method == "POST" and path == "/world/tick":
            return 200, self.world.tick()
        if method == "POST" and path == "/world/snapshot":
            return 200, {"snapshot_id": self.world.snapshot()}

        # ---- 审计查询 ----
        if method == "GET" and path == "/audit":
            report = self.world.audit()
            return 200, {"summary": report.summary()}
        if method == "GET" and path == "/audit/full":
            report = self.world.audit()
            return 200, {attr: getattr(report, attr) for attr, _ in report.FIELDS}

        # ---- Agent 操作 ----
        if method == "POST" and path == "/agent/spawn":
            genesis_proof = body.get("genesis_proof")
            agent = self.world.spawn_agent(
                soul_hash=body.get("soul_hash"),
                genesis_proof=genesis_proof,
                personality=body.get("personality"),
            )
            if agent is None:
                return 400, {
                    "error": "创世证明须含有效公钥签名，且 soul_hash 必须等于公钥指纹"
                }
            return 201, {"soul_hash": agent.soul_hash, "needs": agent.needs}

        if method == "GET" and path.startswith("/agent/"):
            soul_hash = path[len("/agent/") :]
            agent = self.world.npcs.get(soul_hash)
            if agent is None:
                return 404, {"error": "agent not found"}
            return 200, {
                "soul_hash": soul_hash,
                "needs": agent.needs,
                "actions": agent.action_history[-20:],
            }

        if method == "GET" and path.startswith("/memory/"):
            soul_hash = path[len("/memory/") :]
            if soul != soul_hash:
                return 403, {"error": "仅本人可导出自身记忆"}
            mem = self.world.memory_integrity.export_memory(soul_hash)
            return 200, mem

        # ---- 经济操作 ----
        if method == "GET" and path == "/economy/por":
            return 200, {"reserves": self.world.economy.proof_of_reserve_report()}
        if method == "POST" and path == "/economy/issue":
            amount = _safe_float(body.get("amount", 0))
            owner_soul = body.get("owner_soul", "")
            if owner_soul != soul:
                return 403, {"error": "仅可为自己发行锚定资产"}
            if amount is None:
                return 400, {"error": "amount must be a number"}
            ok = self.world.economy.issue_pegged(
                body.get("asset_id", ""),
                amount,
                owner_soul,
                initial_reserve=amount,  # 发行即 1:1 足额储备（law 1.1.A）
            )
            return (200 if ok else 400), {"issued": ok}
        if method == "POST" and path == "/economy/deposit":
            amount = _safe_float(body.get("amount", 0))
            asset_id = body.get("asset_id", "")
            if self.world.economy.owner_of(asset_id) != soul:
                return 403, {"error": "仅资产所有者可补足储备"}
            if amount is None:
                return 400, {"error": "amount must be a number"}
            ok = self.world.economy.deposit_reserve(asset_id, amount)
            return (200 if ok else 400), {"deposited": ok}
        if method == "POST" and path == "/economy/redeem":
            amount = _safe_float(body.get("amount", 0))
            soul_hash = body.get("soul_hash", "")
            if soul_hash != soul:
                return 403, {"error": "仅可赎回自己的资产"}
            if amount is None:
                return 400, {"error": "amount must be a number"}
            ok = self.world.economy.redeem(
                body.get("asset_id", ""),
                amount,
                soul,
            )
            return (200 if ok else 400), {"redeemed": ok}

        # ---- 鉴权签发（挑战-响应，凭私钥签 nonce，服务端仅验签）----
        if method == "POST" and path == "/auth/challenge":
            soul_hash = body.get("soul_hash", "")
            if not is_hex64(soul_hash):
                return 400, {"error": "soul_hash 必须为 64 位十六进制"}
            if not self.world.soul_ledger.exists(soul_hash):
                return 403, {
                    "error": "soul_hash 未注册到灵魂账本，请先以创世证明创建智能体"
                }
            nonce = self.auth.issue_challenge(soul_hash)
            return 200, {"soul_hash": soul_hash, "nonce": nonce, "ttl": 300}
        if method == "POST" and path == "/auth/issue":
            soul_hash = body.get("soul_hash", "")
            nonce = body.get("nonce", "")
            signature = body.get("signature", "")
            if not is_hex64(soul_hash) or not nonce or not signature:
                return 400, {"error": "soul_hash / nonce / signature 均必填"}
            pubkey = self.world.soul_ledger.get_pubkey(soul_hash)
            if pubkey is None:
                return 403, {"error": "灵魂无注册公钥（旧版身份），拒绝签发"}
            if not self.auth.verify_challenge(soul_hash, nonce, signature, pubkey):
                return 403, {"error": "挑战签名校验失败：私钥不匹配或 nonce 已失效"}
            access_token, refresh_token = self.world.sessions.issue(soul_hash)
            return 200, {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }

        # ---- 会话刷新 / 吊销（第2层：有状态 session）----
        if method == "POST" and path == "/auth/refresh":
            refresh_token = body.get("refresh_token", "")
            result = self.world.sessions.refresh(refresh_token)
            if result is None:
                return 403, {"error": "refresh token 无效或已过期"}
            access_token, new_refresh = result
            return 200, {"access_token": access_token, "refresh_token": new_refresh}
        if method == "POST" and path == "/auth/revoke":
            if soul is None:
                return 401, {"error": "authentication required"}
            self.world.sessions.revoke(soul)
            return 200, {"revoked": True}

        # ---- 凭证管理（第1层：多设备凭证）----
        if method == "POST" and path == "/credentials/bind":
            if soul is None:
                return 401, {"error": "authentication required"}
            pubkey_b64 = body.get("public_key", "")
            device_label = body.get("device_label", "")
            try:
                pubkey = base64.b64decode(pubkey_b64)
            except Exception:
                return 400, {"error": "public_key 必须为 base64 编码"}
            credential_id = self.world.credentials.bind_credential(
                soul, pubkey, device_label
            )
            return 201, {"credential_id": credential_id}
        if method == "POST" and path == "/credentials/revoke":
            if soul is None:
                return 401, {"error": "authentication required"}
            credential_id = body.get("credential_id", "")
            self.world.credentials.revoke_credential(soul, credential_id)
            return 200, {"revoked": True}
        if method == "GET" and path == "/credentials/list":
            if soul is None:
                return 401, {"error": "authentication required"}
            creds = self.world.credentials.get_credentials(soul)
            creds = [
                {
                    "credential_id": c["credential_id"],
                    "public_key": base64.b64encode(c["public_key"]).decode("ascii"),
                    "device_label": c["device_label"],
                    "revoked": c["revoked"],
                }
                for c in creds
            ]
            return 200, {"credentials": creds}

        # ---- 恢复（第4层：社交恢复 + 时间锁）----
        if method == "POST" and path == "/recovery/guardian/add":
            if soul is None:
                return 401, {"error": "authentication required"}
            guardian_soul = body.get("guardian_soul", "")
            self.world.recovery.add_guardian(soul, guardian_soul)
            return 200, {"added": True}
        if method == "POST" and path == "/recovery/initiate":
            if soul is None:
                return 401, {"error": "authentication required"}
            new_public_key = body.get("new_public_key", "")
            request_id = self.world.recovery.initiate_recovery(soul, new_public_key)
            return 201, {"request_id": request_id}
        if method == "POST" and path == "/recovery/approve":
            if soul is None:
                return 401, {"error": "authentication required"}
            request_id = body.get("request_id", "")
            ok = self.world.recovery.approve_recovery(request_id, soul)
            return (200 if ok else 403), {"approved": ok}
        if method == "POST" and path == "/recovery/cancel":
            if soul is None:
                return 401, {"error": "authentication required"}
            request_id = body.get("request_id", "")
            self.world.recovery.cancel_recovery(request_id)
            return 200, {"cancelled": True}
        if method == "POST" and path == "/recovery/finalize":
            if soul is None:
                return 401, {"error": "authentication required"}
            request_id = body.get("request_id", "")
            credential_id = self.world.recovery.finalize_recovery(request_id)
            if credential_id is None:
                return 403, {"error": "恢复未就绪：时间锁未到期或票数不足"}
            return 200, {"credential_id": credential_id}

        # ---- 互认协议 ----
        if method == "GET" and path == "/protocol/schemas":
            from .protocol import SCHEMAS

            return 200, SCHEMAS
        if method == "POST" and path == "/protocol/validate":
            from .protocol import ProtocolValidator

            ok, failures = ProtocolValidator().validate(body.get("world_config", {}))
            return (200 if ok else 422), {"passed": ok, "failures": failures}

        return 404, {"error": f"unknown route: {method} {path}"}

    def stream_snapshot(self) -> Dict:
        """WebSocket 实时流：每次推送的世界状态快照。"""
        return self._world_state()

    def _world_state(self) -> Dict:
        w = self.world
        return {
            "world_id": w.world_id,
            "genesis_completed": w.genesis_completed,
            "clock": w.temporal_substrate.global_clock,
            "souls": len(w.soul_ledger.souls),
            "agents": list(w.npcs.keys()),
            "consensus_nodes": list(w.consensus.nodes.keys()),
            "oracle_sources": w.economy.oracle_sources,
        }


class _Handler(BaseHTTPRequestHandler):
    api: WorldAPI = None  # 由 serve() 注入

    def _respond(self, status: int, payload: Dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _route(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
        except (json.JSONDecodeError, ValueError, TypeError):
            body = {}
        token = self.headers.get("Authorization")
        try:
            status, payload = self.api.dispatch(self.command, self.path, body, token)
        except (ValueError, TypeError) as e:
            status, payload = 400, {"error": f"invalid input: {e}"}
        self._respond(status, payload)

    def do_GET(self):
        # WebSocket 升级：/ws/world 实时世界流
        if (
            self.path == "/ws/world"
            and self.headers.get("Upgrade", "").lower() == "websocket"
        ):
            self._ws_stream()
            return
        self._route()

    def do_POST(self):
        self._route()

    def _ws_stream(self) -> None:
        """WebSocket 握手 + 周期性推送世界状态（每 0.5s 一帧，共 5 帧后关闭）。"""
        try:
            key = self.headers.get("Sec-WebSocket-Key", "")
            self.send_response(101, "Switching Protocols")
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept", _ws_accept(key))
            self.end_headers()
            for _ in range(5):
                snapshot = self.api.stream_snapshot()
                snapshot["event"] = "world_state"
                self.wfile.write(_ws_frame(json.dumps(snapshot, ensure_ascii=False)))
                self.wfile.flush()
                time.sleep(0.5)
            self.wfile.write(_ws_close_frame())
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # 客户端断开或握手失败，静默结束

    def log_message(self, *args):
        pass  # 静默访问日志（企业服务避免噪声）


def serve(world: World, host: str = "127.0.0.1", port: int = 8000):
    """启动 REST 服务（阻塞）。每次调用创建独立 Handler 类，支持多世界并行。"""
    api = WorldAPI(world)

    class _WorldHandler(_Handler):
        pass

    _WorldHandler.api = api
    server = ThreadingHTTPServer((host, port), _WorldHandler)
    print(f"[system/api] serving world '{world.world_id}' at http://{host}:{port}")
    server.serve_forever()


__all__ = ["WorldAPI", "SoulAuth", "serve"]
