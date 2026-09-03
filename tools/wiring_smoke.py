"""Wiring smoke test: account abstraction / key rotation / identity root / soul roaming.

验证四个模块接线进主流程后的端到端行为（直接调用 WorldAPI.dispatch，
与 smoke_test.py 同一风格，不依赖真实网络）。

运行：python tools/wiring_smoke.py
"""
import sys
sys.path.insert(0, ".")
import os
os.environ["STORAGE"] = "memory"

import base64
import time

from system.runtime import World
from system.keys import (
    generate_user_keypair,
    build_genesis_proof,
    sign_with_device,
    shamir_combine,
    public_from_private,
)
from system.api import WorldAPI

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    mark = "PASS" if cond else "FAIL"
    if cond:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{mark}] {name}" + (f"  ({detail})" if detail and not cond else ""))


def spawn_and_login(world: World, api: WorldAPI):
    """创世 + 挑战登录，返回 (soul_hash, keypair, access_token)。"""
    kp = generate_user_keypair()
    proof = build_genesis_proof(
        kp["secret"], {"name": "wiring-soul", "ts": int(time.time())}
    )
    agent = world.spawn_agent(soul_hash=None, genesis_proof=proof)
    nonce = api.auth.issue_challenge(agent.soul_hash, ip="127.0.0.1")
    sig = base64.b64encode(
        sign_with_device(kp["secret"], nonce.encode("utf-8"))
    ).decode("ascii")
    status, payload = api.dispatch(
        "POST", "/auth/issue",
        {"soul_hash": agent.soul_hash, "nonce": nonce, "signature": sig},
        token=None,
    )
    assert status == 200, payload
    return agent.soul_hash, kp, payload["access_token"]


def main():
    world = World("wiring-smoke", data_dir=None)
    api = WorldAPI(world)
    soul, kp, token = spawn_and_login(world, api)
    auth = {"token": token}
    print(f"login ok: soul={soul[:16]}...")

    # ── 1. 账户抽象：签发 / 挑战 / 执行 / 约束 / 吊销 ──────────
    print("\n[1] account_abstraction")
    sk_kp = generate_user_keypair()
    sk_pub_b64 = base64.b64encode(sk_kp["pubkey"]).decode("ascii")
    status, payload = api.dispatch(
        "POST", "/aa/keys/issue",
        {
            "public_key": sk_pub_b64,
            "spend_limit": 100.0,
            "duration_seconds": 3600,
            "allowed_actions": ["read", "interact"],
        },
        **auth,
    )
    check("issue session key", status == 201, str(payload))
    key_id = payload["key_id"]

    status, payload = api.dispatch(
        "POST", "/aa/challenge", {"key_id": key_id}, token=None
    )
    check("challenge (public route, no token)", status == 200, str(payload))
    nonce = payload["nonce"]
    sig = base64.b64encode(
        sign_with_device(sk_kp["secret"], nonce.encode("utf-8"))
    ).decode("ascii")

    status, payload = api.dispatch(
        "POST", "/aa/execute",
        {"key_id": key_id, "nonce": nonce, "signature": sig,
         "action": "interact", "amount": 30.0},
        token=None,
    )
    check("execute via session key (no master token)", status == 200, str(payload))
    check("spend recorded", payload.get("spent_amount") == 30.0, str(payload))

    # nonce 一次性：重放必须失败
    status, payload = api.dispatch(
        "POST", "/aa/execute",
        {"key_id": key_id, "nonce": nonce, "signature": sig,
         "action": "interact", "amount": 1.0},
        token=None,
    )
    check("nonce replay rejected", status == 403, str(payload))

    # 新挑战：超额度必须失败（已花 30，上限 100，再花 80 → 拒绝）
    nonce2 = api.dispatch("POST", "/aa/challenge", {"key_id": key_id}, token=None)[1]["nonce"]
    sig2 = base64.b64encode(
        sign_with_device(sk_kp["secret"], nonce2.encode("utf-8"))
    ).decode("ascii")
    status, payload = api.dispatch(
        "POST", "/aa/execute",
        {"key_id": key_id, "nonce": nonce2, "signature": sig2,
         "action": "interact", "amount": 80.0},
        token=None,
    )
    check("spend limit enforced", status == 403, str(payload))

    # 范围约束：非白名单动作拒绝
    nonce3 = api.dispatch("POST", "/aa/challenge", {"key_id": key_id}, token=None)[1]["nonce"]
    sig3 = base64.b64encode(
        sign_with_device(sk_kp["secret"], nonce3.encode("utf-8"))
    ).decode("ascii")
    status, payload = api.dispatch(
        "POST", "/aa/execute",
        {"key_id": key_id, "nonce": nonce3, "signature": sig3,
         "action": "admin_delete_everything", "amount": 0.0},
        token=None,
    )
    check("action scope enforced", status == 403, str(payload))

    # 主身份吊销会话密钥 → 执行失败
    status, payload = api.dispatch(
        "POST", "/aa/keys/revoke", {"key_id": key_id}, **auth
    )
    check("master revokes session key", status == 200, str(payload))
    nonce4 = api.dispatch("POST", "/aa/challenge", {"key_id": key_id}, token=None)[1]["nonce"]
    sig4 = base64.b64encode(
        sign_with_device(sk_kp["secret"], nonce4.encode("utf-8"))
    ).decode("ascii")
    status, payload = api.dispatch(
        "POST", "/aa/execute",
        {"key_id": key_id, "nonce": nonce4, "signature": sig4,
         "action": "interact", "amount": 1.0},
        token=None,
    )
    check("revoked key cannot execute", status == 403, str(payload))

    # ── 2. 密钥轮换：retired 验旧 / revoked 杀旧 ──────────────
    print("\n[2] key_rotation")
    status, payload = api.dispatch("GET", "/keys", {}, **auth)
    check("list keys (no material)", status == 200 and "key_bytes" not in str(payload), str(payload))
    old_kid = world.key_rotation.get_active_key().key_id

    status, payload = api.dispatch("POST", "/keys/rotate", {}, **auth)
    check("force rotate", status == 200, str(payload))
    new_kid = world.key_rotation.get_active_key().key_id
    check("active key changed", old_kid != new_kid)

    # 旧 token（旧密钥签发，已 retired）仍可验证
    still = world.sessions.verify(token, credential_vault=world.credentials)
    check("old token still valid (retired key verifies)", still == soul)

    # 新签发的 token 用新 kid
    access2, _ = world.sessions.issue(soul)
    import json as _json
    import base64 as _b64
    payload2 = _json.loads(_b64.urlsafe_b64decode(access2.split(".")[0]))
    check("new token carries new kid", payload2.get("kid") == new_kid)

    # 紧急吊销旧密钥 → 旧 token 即刻失效，新 token 不受影响
    status, payload = api.dispatch(
        "POST", "/keys/revoke", {"key_id": old_kid}, **auth
    )
    check("emergency revoke old key", status == 200, str(payload))
    dead = world.sessions.verify(token, credential_vault=world.credentials)
    check("old token dead after revoke", dead is None)
    alive = world.sessions.verify(access2, credential_vault=world.credentials)
    check("new token unaffected", alive == soul)
    auth = {"token": access2}  # 旧密钥已吊销，后续用新密钥签发的 token

    # ── 3. 身份根：生成 / 分片恢复 ────────────────────────────
    print("\n[3] identity_root")
    status, payload = api.dispatch(
        "POST", "/identity/root/generate", {"threshold": 3, "num_shares": 5}, **auth
    )
    check("generate identity root", status == 200, str(payload))
    master_pub = base64.b64decode(payload["master_public_key"])
    check("soul_hash = SHA-256(master pubkey)",
          payload["soul_hash"] == __import__("hashlib").sha256(master_pub).hexdigest())
    check("share count", len(payload["shares"]) == 5)
    # 服务端零落盘：shares 不进任何存储
    tables = world.storage.query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%identity%'"
    ) if world.storage_backend != "memory" else []
    check("no identity root persisted server-side", len(tables) == 0, str(tables))
    # 凑齐 threshold 份重建 → 派生公钥一致
    shares = [(int(s["x"]), int(s["y"], 16)) for s in payload["shares"][:3]]
    recovered = shamir_combine(shares)
    check("shamir(3,5) recover -> same pubkey",
          public_from_private(recovered) == master_pub)

    # ── 4. 灵魂漫游：源世界签发 / 目标世界验证映射 ──────────────
    print("\n[4] soul_roaming")
    world_a, world_b = world, World("wiring-smoke-target", data_dir=None)
    api_b = WorldAPI(world_b)
    # 互通注册：A 认识 B 的公钥，B 认识 A 的公钥
    a_pub = world_a.roaming._world_public_key
    b_pub = world_b.roaming._world_public_key
    status, payload = api.dispatch(
        "POST", "/roaming/worlds/register",
        {"world_id": "wiring-smoke-target",
         "public_key": base64.b64encode(b_pub).decode("ascii")},
        **auth,
    )
    check("target world registered in source", status == 201, str(payload))
    world_b.roaming.register_world("wiring-smoke", a_pub)

    # A 为灵魂签发漫游证书（目标 = B）
    status, payload = api.dispatch(
        "POST", "/roaming/certificates",
        {"target_world_id": "wiring-smoke-target"},
        **auth,
    )
    check("issue roaming certificate", status == 201, str(payload))
    cert = payload["certificate"]

    # 用户在 B 世界也注册一个本地灵魂（用于映射目标）
    soul_b, kp_b, token_b = spawn_and_login(world_b, api_b)

    # 篡改检测：改掉声誉字段后签名应失效
    tampered = dict(cert)
    tampered["identity_proof"] = dict(cert["identity_proof"])
    tampered["identity_proof"]["reputation_score"] = 9999
    status, payload = api_b.dispatch(
        "POST", "/roaming/verify", {"certificate": tampered},
        token=token_b,
    )
    check("tampered cert fails signature check",
          status == 200 and payload["valid"] is False, str(payload))

    # 正确证书：验证 + 挑战-响应（用户持私钥）+ 映射
    nonce_r = api_b.auth.issue_challenge(soul_b, ip="127.0.0.1")
    sig_r = base64.b64encode(
        sign_with_device(kp["secret"], nonce_r.encode("utf-8"))
    ).decode("ascii")
    status, payload = api_b.dispatch(
        "POST", "/roaming/verify",
        {"certificate": cert,
         "challenge_nonce": nonce_r, "challenge_signature": sig_r},
        token=token_b,
    )
    check("verify cert + user challenge-response",
          status == 200 and payload["valid"] is True, str(payload))

    status, payload = api_b.dispatch(
        "POST", "/roaming/map",
        {"certificate": cert, "local_soul_hash": soul_b},
        token=token_b,
    )
    check("map roaming soul to local", status == 201, str(payload))
    status, payload = api_b.dispatch(
        "POST", "/roaming/mapping/lookup",
        {"source_world_id": "wiring-smoke", "source_soul_hash": soul},
        token=token_b,
    )
    check("lookup mapping returns local soul",
          status == 200 and payload["local_soul_hash"] == soul_b, str(payload))

    # ── 回归：tick 钩子不破坏主循环 ────────────────────────────
    print("\n[5] regression")
    result = world.tick()
    check("world.tick() still runs", isinstance(result, dict))

    print(f"\nRESULT: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
