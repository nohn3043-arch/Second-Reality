# -*- coding: utf-8 -*-
"""Second Reality · 真栈世界（第一个 25/25 全过的真实虚拟世界）
====================================================================

定位
----
本文件是 demo/virtual_world.py（教学演示，22/25 + 三项如实失败）的「真栈版」：
继承同一套规则层驱动的社会仿真，但把三个 FAILED 维度用 system/ 的真实实现补齐——
不改判定、不放宽标准：

  1) 身份法：每个灵魂铸造真实 Ed25519 密钥对（system/keys.py 链路），
     soul_hash = SHA-256(公钥)，登记 public_key / key_fingerprint / genesis_proof，
     审计器逐灵魂重算指纹 + 验签。
  2) 经济法：挂接 system/ledger.EconomicReserve（PoR 储备账本），
     预言机 ≥3、发行即 1:1 足额储备、赎回通道真实走通一次（不是声明）。
  3) 互操作：world_config["economy"] 如实同步真实储备账本 →
     宪法层 EconomicBaseline 并网审查通过。

与 virtual_world.py 的关系：纯增量子类化，不改其任何一行——教学版原样保留作对照。

诚实边界（本文件与真实生产链路的两处差异，如实声明，不得隐去）
----------------------------------------------------------------
  A. 密钥驻留：真实系统私钥仅驻留用户设备安全区、世界侧永不知晓（见 system/keys.py
     头注）。本演示为了「同 seed 逐字节可复现」，私钥种子由 (world_seed, aid) 确定
     性派生——世界侧可复算私钥。这是可复现性与密钥隔离之间的演示取舍；
     生产部署必须换成设备端生成 + 创世证明上链。
  B. 储备背书语义：1:1 的账目结构是真实执行的（储备率可复算、赎回真实走通），
     但演示中每笔增发的「储备」由世界劳动产出/国库记账背书；真实系统的储备
     应为现实法币存款（预言机信源也应换成现实数据源）。形式与账目为真，
     储备的现实性是演示边界。

依赖：cryptography（system/keys.py 同源依赖）。缺失即 ImportError，不做静默降级。

用法：
  python demo/real_virtual_world.py --headless --ticks 100 --audit
  python demo/real_virtual_world.py --gui            # pygame 渲染，进去看
"""

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from types import SimpleNamespace

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# 真实实现层（本文件的存在意义：把 system/ 真栈接入 demo 世界）
from system.keys import (
    build_genesis_proof,
    verify_genesis_proof,
    derive_soul_hash_from_pubkey,
)
from system.ledger import EconomicReserve, Storage
from system.soul_roaming import SoulRoamingProtocol
from system.memory_transfer import MemoryTransferChannel
from system.agent_engine import MemoryVault, MemoryInalienability
from system.session import SessionManager
from system.credentials import CredentialVault
from system.api import WorldAPI, serve as serve_http
from system.keys import FileKmsProvider, public_from_private
from constitution_rules import NOHN_LAW_AXIOMS

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# 教学演示层（被继承，不被修改）
import virtual_world as vw
from virtual_world import NohnWorld, WorldConfig, build_demo_config, _print_demo_note

# 《红尘泪》世界层（大央帝朝武道体系）
from hongchenlei import HongchenleiRealm, rank_name, RANK_JIDAO

COIN_ID = "NR-COIN"
# 三个独立预言机来源（law：≥3，防单点操纵）。
# 演示信源：真实部署应替换为现实汇率/储备证明数据源（诚实边界 B 的一部分）。
ORACLE_SOURCES = [
    "oracle://nohn.layer-one.example",
    "oracle://independent-rate-feed.example",
    "oracle://reserve-proof-notary.example",
]


def _derive_device_seed(world_seed: int, subject: str) -> bytes:
    """确定性派生 32 字节私钥种子：SHA-256(world_seed | subject)。

    同一 (seed, aid) 必得同一密钥对 => 世界逐字节可复现（诚实边界 A）。
    不消耗 world._rng：随机流与教学版完全一致，社会轨迹不变。
    """
    return hashlib.sha256(
        ("real-world-device-key|%d|%s" % (world_seed, subject)).encode("utf-8")
    ).digest()


def _mint_keypair(world_seed: int, subject: str):
    """铸造真实 Ed25519 密钥对。返回 (secret32, pubkey32, soul_hash)。"""
    priv = Ed25519PrivateKey.from_private_bytes(_derive_device_seed(world_seed, subject))
    secret = priv.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    pubkey = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return secret, pubkey, derive_soul_hash_from_pubkey(pubkey)


class RealIdentity:
    """身份侧视图（law·身份确权规范）——真栈版。

    与教学版 DemoIdentity 的唯一差别：真实密钥链路已接入（Ed25519，
    soul_hash = SHA-256(公钥)，见 _register_soul 覆盖），公钥绑定审计可过。
    """

    def __init__(self):
        self.soul_hash_sha256 = True
        self.non_revocable = True
        self.cross_world_portable = True
        self.asset_bound = True

    def revoke_soul(self, soul_hash):
        return False  # 第六条：灵魂不可撤销（宪法层 SoulAttestation 承担）


class RealEconomyView:
    """经济宪法侧视图——真栈版：转发 system/ledger.EconomicReserve。

    审计探测面（_audit_economic_law 逐项消费）全部来自真实储备账本，
    无一处硬编码 True。demo 记账式守恒口径（教学版遗留）继续成立，
    与 PoR 守恒口径并行可复算——两个口径都真，才叫真栈。
    """

    def __init__(self, world, book_reserve, peg: EconomicReserve):
        self.world = world
        self._book = book_reserve   # demo 记账式货币（virtual_world.EconomicReserve）
        self.peg = peg              # 真实 PoR 储备账本（system/ledger.EconomicReserve）

    # ---- 审计探测面：转发真实储备账本（不硬编码） ----
    @property
    def real_peg_1to1(self):
        return self.peg.real_peg_1to1

    @property
    def redemption_right(self):
        return self.peg.redemption_right

    @property
    def unilateral_fee(self):
        return self.peg.unilateral_fee

    @property
    def asset_bound_to_soul(self):
        return self.peg.asset_bound_to_soul

    @property
    def oracle_sources(self):
        return self.peg.oracle_sources

    @property
    def _ledger(self):
        return self.peg._ledger

    def reserve_ratio_ok(self, asset_id):
        return self.peg.reserve_ratio_ok(asset_id)

    @property
    def proof_of_reserve(self):
        return all(self.peg.reserve_ratio_ok(aid) for aid in self.peg._ledger)

    def proof_of_reserve_report(self):
        return self.peg.proof_of_reserve_report()

    # ---- 双守恒口径 ----
    def conservation_residual(self):
        """记账式守恒残差（demo 口径）：Σwealth+treasury+inflation+unallocated==supply。
        居民化（无主角）：玩家账户与其他居民一同纳入求和——玩家同领 UBI、同缴税，
        这些流都真实入账，漏掉玩家反而会得出假残差。"""
        accts = self.world.agents + ([self.world.player] if self.world.player else [])
        return self._book.invariant_residual(accts)

    def conservation_holds(self):
        return abs(self.conservation_residual()) <= NOHN_LAW_AXIOMS["conservation_tolerance"]

    def por_conservation_holds(self):
        """PoR 守恒口径：流通量不得超过储备背书（账目侧单一权威实现）。"""
        return self.peg.conservation_holds()

    def total_supply(self):
        return self._book.money_supply

    def compliant(self):
        return self.peg.compliant() and self.conservation_holds() and self.por_conservation_holds()


class RealWorld(NohnWorld):
    """真栈世界：真实密钥链路 + 真实 PoR 储备账本，其余继承教学版。

    装配时序（关键）：
      NohnWorld.__init__ -> _init_constitution（建宪法外壳，economy 暂为教学侧视图）
                          -> _init_world（spawn 30 agents -> _register_soul 覆盖生效）
                          -> _complete_genesis（创世锁定）
      之后本类 _init_real_economy：挂接 EconomicReserve、替换侧视图、
      同步 world_config、赎回通道自检。
    """

    def __init__(self, config=None, storage_backend="memory", data_dir=None,
                 world_id=None):
        self._storage_backend = storage_backend
        self._data_dir = data_dir
        self._world_id_override = world_id
        self._soul_pubkeys = {}       # soul_hash -> 32B 公钥（漫游证书签发要用）
        self._agent_soul = {}         # aid -> soul_hash（记忆按灵魂归档要用）
        super().__init__(config)
        if world_id:
            self.world_id = world_id
        self._init_real_economy()
        self._init_transport()
        self._init_realm()
        self._init_api_compat()

    # ------------------------------------------------------------
    # 身份真实化（覆盖教学版「public_key 留空」的实现）
    # ------------------------------------------------------------
    def _register_soul(self, agent):
        """真实密钥链路：Ed25519 确定性铸造 + 创世证明验签 + 公钥指纹登记。

        私钥不入账本（no_plaintext_credential）；确定性派生的边界见诚实边界 A。

        两条路径（必须区分，否则会造出「世界替用户保管私钥」的假身份）：
          · 内部居民：私钥种子由 (world_seed, aid) 确定性派生 —— 可复现，演示需要；
          · 外部调用方（HTTP /agent/spawn）：公钥由**调用方**提供，世界只验签存证，
            私钥永不进入本世界 —— 这才是真实链路的形态。
        """
        provided = getattr(self, "_pending_proof", None)
        if provided:
            sh, proof = provided
            pubkey = base64.b64decode(proof["pubkey"])
            if derive_soul_hash_from_pubkey(pubkey) != sh or not verify_genesis_proof(proof):
                raise RuntimeError("external genesis proof failed verification")
        else:
            secret, pubkey, sh = _mint_keypair(self.config.seed, agent.aid)
            if sh in self._soul_index:
                return sh
            declaration = {
                "world": self.world_id,
                "aid": agent.aid,
                "world_seed": self.config.seed,
                "born_tick": self._tick,
            }
            proof = build_genesis_proof(secret, declaration)
            if proof is None or not verify_genesis_proof(proof):
                # 真实链路自检失败即拒绝登记：绝不把未经验签的记录写进灵魂账本
                raise RuntimeError("genesis proof self-check failed for %s" % agent.aid)

        self._soul_index[sh] = agent
        self.soul_attestation.register_soul({
            "soul_hash": sh, "timestamp": self._tick,
            "identity": {"aid": agent.aid, "world_id": self.world_id},
        })
        rec = self.soul_ledger.souls.setdefault(sh, {
            "soul_hash": sh, "created_at": self._tick, "cross_world_records": [],
        })
        rec["public_key"] = base64.b64encode(pubkey).decode("ascii")
        rec["key_fingerprint"] = sh
        rec["genesis_proof"] = proof   # 公开证明（pubkey/declaration/sig，无私钥材料）
        self._soul_pubkeys[sh] = pubkey
        self._agent_soul[agent.aid] = sh
        # API 契约：agent 必须能报出自己的 soul_hash（POST /agent/spawn 的响应要用）
        agent.soul_hash = sh
        # API 的 /agent/<soul_hash> 与 npcs 查询按 soul_hash 取，双键登记
        self.npcs[sh] = agent
        if provided:
            self._persist_external_soul(sh, rec)
        return sh

    def _persist_external_soul(self, soul_hash, rec):
        """外部灵魂落库：世界重启后仍能认出对方（否则每次重启都要重新注册）。"""
        try:
            self.storage.execute(
                "INSERT OR REPLACE INTO souls (soul_hash, identity, created_at) "
                "VALUES (?, ?, ?)",
                (soul_hash, json.dumps({
                    "public_key": rec.get("public_key", ""),
                    "key_fingerprint": rec.get("key_fingerprint", soul_hash),
                    "genesis_proof": rec.get("genesis_proof"),
                }, ensure_ascii=False), time.time()),
            )
        except Exception as exc:                      # 落库失败不得静默
            print("[warn] 外部灵魂落库失败 %s: %s" % (soul_hash[:12], exc))

    def spawn_agent(self, soul_hash=None, genesis_proof=None, personality=None, pos=None):
        """兼容 system.api 的签名。教学版只有 `spawn_agent(pos=None)`。

        外部调用方必须自带创世证明（soul_hash = SHA-256(公钥)），世界只验签，不代持私钥。
        """
        if genesis_proof:
            if not verify_genesis_proof(genesis_proof):
                return None
            try:
                pubkey = base64.b64decode(genesis_proof.get("pubkey", ""))
            except Exception:
                return None
            sh = derive_soul_hash_from_pubkey(pubkey)
            if soul_hash and soul_hash != sh:
                return None
            if sh in self._soul_index:
                return self._soul_index[sh]          # 幂等
            self._pending_proof = (sh, genesis_proof)
            try:
                return self._spawn_agent(pos=pos)
            finally:
                self._pending_proof = None
        return self._spawn_agent(pos=pos)

    # ------------------------------------------------------------
    # 经济真实化
    # ------------------------------------------------------------
    def _init_real_economy(self):
        # 统一账本：储备 / 漫游 / 记忆库共用一份，避免多账本分叉
        if self._storage_backend == "memory":
            self.storage = Storage(backend="memory")
        else:
            d = self._data_dir or os.path.join(
                _REPO_ROOT, ".world_data", "real_demo")
            self.storage = Storage(data_dir=d, backend="sqlite")
        storage = self.storage
        self.peg = EconomicReserve(oracle_sources=list(ORACLE_SOURCES), storage=storage)

        # 国库灵魂：真实密钥对，与本世界任何个体同一链路、同一审计标准
        secret, pubkey, tsh = _mint_keypair(self.config.seed, "TREASURY")
        tproof = build_genesis_proof(secret, {
            "world": self.world_id, "aid": "TREASURY",
            "world_seed": self.config.seed, "born_tick": self._tick,
        })
        if tproof is None or not verify_genesis_proof(tproof):
            raise RuntimeError("treasury genesis proof self-check failed")
        trec = self.soul_ledger.souls.setdefault(tsh, {
            "soul_hash": tsh, "created_at": self._tick, "cross_world_records": [],
        })
        trec["public_key"] = base64.b64encode(pubkey).decode("ascii")
        trec["key_fingerprint"] = tsh
        trec["genesis_proof"] = tproof
        self.treasury_soul = tsh

        # 创世发行：发行即 1:1 足额储备（law 强制），资产绑定国库灵魂。
        # 幂等：创世只发生一次。世界自落盘账本恢复时，资产已存在——
        # 此时不得重复发行（否则每次启动都撞 issue_pegged 的重复校验而崩溃）。
        if COIN_ID in self.peg._ledger:
            self._peg_mirrored = self.peg._ledger[COIN_ID]["total_supply"]
            already = self.storage.query(
                "SELECT 1 FROM reserve_ledger WHERE asset_id=? AND action='redeem' LIMIT 1",
                (COIN_ID,))
            self.redemption_selfcheck = bool(already)
        else:
            if not self.peg.issue_pegged(
                COIN_ID, self.config.initial_money_supply, tsh,
                initial_reserve=self.config.initial_money_supply,
            ):
                raise RuntimeError("pegged issuance failed at genesis")
            self._peg_mirrored = self.config.initial_money_supply
            # 赎回通道自检：真实执行一次小额赎回——通道常驻是走出来的，不是声明的
            self.redemption_selfcheck = self.peg.redeem(COIN_ID, 1.0, tsh)
            if not self.redemption_selfcheck:
                raise RuntimeError("redemption channel self-check failed")

        # 替换侧视图与身份视图；world_config 如实同步真实账本状态
        self.economy = RealEconomyView(self, self.reserve, self.peg)
        self.identity = RealIdentity()
        self.world_config["economy"] = self._economy_config()
        self.world_config["treasury_soul"] = tsh
        self.world_config["coin_id"] = COIN_ID

    def _economy_config(self):
        """world_config 经济段：逐项取自真实储备账本（并网审查消费的就是这份）。"""
        peg = self.peg
        return {
            "real_peg_1to1": peg.real_peg_1to1,
            "proof_of_reserve": all(peg.reserve_ratio_ok(a) for a in peg._ledger),
            "redemption_right": peg.redemption_right,
            "unilateral_fee": peg.unilateral_fee,
            "asset_bound_to_soul": peg.asset_bound_to_soul,
            "oracle_sources": list(peg.oracle_sources),
        }

    # ------------------------------------------------------------
    # 跨世界接入：世界级身份 + 漫游协议 + 记忆传输通道
    # ------------------------------------------------------------
    def _init_transport(self):
        """补齐跨世界记忆过境所需的五个注入点。

        世界级密钥经 KMS 托管（真随机，落盘），**不进 export_state**——
        因此同 seed 的仿真仍逐字节可复现，同时跨世界保密性成立。
        """
        key_dir = self._data_dir or os.path.join(_REPO_ROOT, ".world_data", "real_demo")
        self.kms = FileKmsProvider(key_dir)
        # 世界签名密钥（Ed25519）：名片与漫游证书由它自签
        self._world_secret = self.kms.get_or_create_key("world_signing_key")
        self._world_pubkey = public_from_private(self._world_secret)
        # 世界传输密钥（X25519 通道密钥）：与签名密钥分离，不做曲线硬转
        channel_secret = self.kms.get_or_create_key("world_transport_key")

        self.roaming = SoulRoamingProtocol(
            world_id=self.world_id,
            world_private_key=self._world_secret,
            world_public_key=self._world_pubkey,
            storage=self.storage,
        )
        # 真实记忆库：按 soul_hash 归档，HMAC 封存 —— 记忆可过境的前提。
        # 注意命名：demo 侧 NohnWorld 已有 self.memory_vault（DemoMemoryVault，
        # tick 内要调 seal_all()），故此处另起一名，不得覆盖。
        self.soul_memory_vault = MemoryVault(storage=self.storage)
        self.memory_channel = MemoryTransferChannel(
            world_id=self.world_id,
            channel_secret=channel_secret,
            storage=self.storage,
            vault=self.soul_memory_vault,
            roaming=self.roaming,
            signing_secret=self._world_secret,
            identity_pubkey=self._world_pubkey,
            soul_ledger=self.soul_ledger,
        )

    def mirror_memories(self, soul_hash=None) -> int:
        """把智能体的长期记忆归档进真实记忆库（按灵魂），供跨世界导出。

        demo 侧的智能体记忆原本只在进程内存里（MemoryVault on agent），
        不经这一步就无记忆可过境 —— 通道接了但没有货物。
        """
        written = 0
        for agent in self.agents:
            sh = self._agent_soul.get(agent.aid)
            if sh is None or (soul_hash and sh != soul_hash):
                continue
            vault = getattr(agent, "memory", None)
            if vault is None:
                continue
            memories = list(getattr(vault, "ltm", [])) + list(getattr(vault, "stm", []))
            for m in memories:
                self.soul_memory_vault.store_memory(sh, {
                    "content": getattr(m, "content", str(m)),
                    "importance": getattr(m, "importance", 0.5),
                    "emotion": getattr(m, "emotion", "neutral"),
                    "tags": list(getattr(m, "tags", [])),
                    "tick": self._tick,
                    "world": self.world_id,
                })
                written += 1
        return written

    # ------------------------------------------------------------
    # HTTP 服务化：让 system.api.WorldAPI 能驱动这个 demo 世界
    # ------------------------------------------------------------
    def _init_api_compat(self):
        """补齐 system.api 依赖、但教学版 demo 没有的组件。

        API 的路由会访问 world.sessions / credentials / memory_integrity /
        audit() / soul_ledger.get_pubkey() / npcs-by-soul_hash —— 少一项，
        鉴权门（sessions.verify）或对应路由就会抛异常。
        """
        # 会话签名密钥必须经 KMS 托管（否则 SessionManager 的 _kms 为 None，
        # /auth/issue 会在 _signing_key() 处抛异常、连接被直接掐断）
        self.sessions = SessionManager(storage=self.storage, kms_provider=self.kms)
        self.credentials = CredentialVault(self.storage)
        self.memory_integrity = MemoryInalienability(vault=self.soul_memory_vault)
        # /audit 端点调用 world.audit()
        self.audit = self.run_constitutional_audit
        # /world 端点消费的两个字段：demo 世界的创世与共识是内嵌实现，无同名属性
        self.genesis_completed = bool(getattr(self, "genesis_block_hash", None))
        self.consensus = SimpleNamespace(nodes={self.world_id: "local"})
        # 宪法层 SoulLedger 有 exists()、没有 get_pubkey()
        ledger = self.soul_ledger
        if not hasattr(ledger, "get_pubkey"):
            def _get_pubkey(sh):
                rec = ledger.souls.get(sh) or {}
                pk = rec.get("public_key") or ""
                return base64.b64decode(pk) if pk else None
            ledger.get_pubkey = _get_pubkey
        self._hydrate_persisted_souls()

    def _hydrate_persisted_souls(self):
        """从账本库恢复外部灵魂（对方世界的人），使之在重启后仍可认证。

        只恢复能通过公钥指纹校验的记录：不合格的一律跳过并如实打印，
        绝不把坏档案塞进灵魂账本（那会让身份法审计假通过或假失败）。
        """
        try:
            rows = self.storage.query("SELECT soul_hash, identity FROM souls")
        except Exception as exc:
            print("[warn] 读取持久化灵魂失败: %s" % exc)
            return
        restored, skipped = 0, 0
        for sh, identity in rows:
            if sh in self.soul_ledger.souls:
                continue
            try:
                ident = json.loads(identity) if isinstance(identity, str) else dict(identity)
            except Exception:
                skipped += 1
                continue
            pk_b64 = ident.get("public_key") or ""
            try:
                pubkey = base64.b64decode(pk_b64)
            except Exception:
                pubkey = b""
            if len(pubkey) != 32 or derive_soul_hash_from_pubkey(pubkey) != sh:
                skipped += 1
                continue
            rec = {
                "soul_hash": sh, "created_at": self._tick, "cross_world_records": [],
                "public_key": pk_b64, "key_fingerprint": sh,
            }
            if ident.get("genesis_proof"):
                rec["genesis_proof"] = ident["genesis_proof"]
            self.soul_ledger.souls[sh] = rec
            self._soul_pubkeys[sh] = pubkey
            restored += 1
        if restored or skipped:
            print("[api] 已恢复外部灵魂 %d 个（跳过不合格 %d 个）" % (restored, skipped))

    # ------------------------------------------------------------
    # 《红尘泪》世界层装配
    # ------------------------------------------------------------
    def _init_realm(self):
        self.realm = HongchenleiRealm(self, genesis_qi=self.config.initial_money_supply * 10.0)
        # 凌化尘裁决：太子按极道算（已成就领域，剑圣级）
        self.ling_huachen_rank = RANK_JIDAO

    def tick(self):
        supply_before = self.reserve.money_supply
        events = super().tick()
        delta = self.reserve.money_supply - supply_before
        if delta > 0:
            self._mirror_expansion(delta)
        elif delta < 0:
            # 记账式货币没有销毁路径；出现负增量说明账目被外力破坏，如实报警
            print("[warn] money_supply 负增量 %.4f —— 守恒被外力破坏？" % delta)
        # 《红尘泪》武道推进（确定性，独立 rng，不消耗 world._rng）
        self._realm_step = self.realm.tick()
        return events

    def _mirror_expansion(self, delta):
        """每笔增发镜像同额储备入账：流通量永不超储备（ratio 恒 ≥ 1.0）。

        采用**绝对值同步**而非增量累加：锚定资产的流通量始终等于世界的
        货币供应量，储备只增不减且恒 ≥ 流通量。这样世界重启（自落盘账本
        恢复、货币供应量回到创世值）时不会把储备重复累加成超额抵押。

        背书语义见诚实边界 B：演示中储备由世界劳动产出/国库记账背书。
        """
        asset = self.peg._ledger[COIN_ID]
        target = float(self.reserve.money_supply)
        changed = False
        if abs(asset["total_supply"] - target) > 1e-9:
            asset["total_supply"] = target
            changed = True
        if asset["reserve_amount"] < target:
            gap = target - asset["reserve_amount"]
            asset["reserve_amount"] = target
            self.peg._log(COIN_ID, "reserve_in", gap, self.treasury_soul)
            changed = True
        if changed:
            self.peg._sync_asset(COIN_ID)
        self._peg_mirrored = asset["total_supply"]


class RealStoryWorld(RealWorld):
    """真栈世界全栈装配（M2.6/M2.7）：RealWorld + 涌现目标层 + 剧情层。

    纯增量，三项纪律与 demo/goal_system.py、demo/factions.py 同一口径：
      1) 零世界 RNG：NPC 身份化用 (seed, aid) 派生流；两层引擎全确定性排序；
      2) 零账本写入：目标/剧情均为派生态（不入 export_state/state_hash）；
      3) 25 维宪法审计不变（tools/goal_system_smoke.py 断言）。
    注意：goal_system / factions 以顶层名导入——与本文件 `import virtual_world`
    同一模块族，EventType 等枚举比对保持同一身份（模块身份纪律）。"""

    def __init__(self, config=None, goal_config=None, **kw):
        super().__init__(config, **kw)
        self.goal_config = goal_config
        self.goal_generator = None
        self.last_goal_transitions = []
        self.story_engine = None
        self.last_story_transitions = []
        import factions as _story_mod
        for _a in self.agents:
            _story_mod.assign_npc_identity(_a, self.config.seed)

    def add_player(self, pid: str = "PLAYER", route: str = "magic"):
        import goal_system as _goal_mod
        import factions as _story_mod
        _p = super().add_player(pid, route=route)
        self.goal_generator = _goal_mod.GoalGenerator(_p, self, self.goal_config)
        self.story_engine = _story_mod.StoryEngine(_p, self)
        return _p

    def tick(self):
        _te = super().tick()
        if self.goal_generator is not None and self.player is not None:
            self.last_goal_transitions = self.goal_generator.step(self)
        if self.story_engine is not None and self.player is not None:
            self.last_story_transitions = self.story_engine.step(self)
        return _te


class _ApiFacade:
    """供 HTTP 层使用的世界门面。

    唯一差异：`tick()` 返回 JSON 安全的结果（demo 的 tick 返回 Event 对象列表，
    直接 json.dumps 会抛异常）。GUI / 无头路径仍然直接用 RealWorld.tick()，
    因此这里只影响服务端，不影响任何仿真语义。
    """

    def __init__(self, world):
        self._w = world

    def __getattr__(self, name):
        return getattr(self._w, name)

    def tick(self):
        events = self._w.tick()
        realm = getattr(self._w, "_realm_step", None) or {}
        return {
            "tick": self._w._tick,
            "events": len(events),
            "realm": {k: v for k, v in realm.items() if k in ("promoted", "residual")},
            "population": sum(1 for a in self._w.agents if getattr(a, "alive", True)),
        }


# ============================================================
# 运行与验证
# ============================================================

def _reverify_identities(world) -> bool:
    """独立复算（不信审计器、不信本文件）：逐灵魂重算公钥指纹 + 验签创世证明。"""
    souls = world.soul_ledger.souls
    if not souls:
        return False
    for sh, rec in souls.items():
        try:
            pk = base64.b64decode(rec.get("public_key", ""))
        except Exception:
            return False
        if len(pk) != 32 or derive_soul_hash_from_pubkey(pk) != sh:
            return False
        if rec.get("key_fingerprint") != sh:
            return False
        proof = rec.get("genesis_proof")
        if not isinstance(proof, dict) or not verify_genesis_proof(proof):
            return False
    return True


def run_real_headless(ticks=100, seed=0, config=None, verbose=False,
                      storage_backend="memory", world_id=None, data_dir=None):
    config = config or build_demo_config(seed=seed)
    world = RealWorld(config, storage_backend=storage_backend, world_id=world_id,
                      data_dir=data_dir)
    t0 = time.time()
    for i in range(ticks):
        world.tick()
        if verbose and (i + 1) % 50 == 0:
            s = world.get_stats()
            print("Tick %d: Pop=%d AvgW=%.1f supply=%.0f" % (
                i + 1, s["alive"], s["avg_wealth"], s["money_supply"]))
    el = time.time() - t0
    s = world.get_stats()
    print("\n=== Real-Stack World Run (%d ticks, %.1fs, seed=%d) ===" % (ticks, el, seed))
    print("State hash (sha256): %s" % world.state_hash())
    print("Population: %d alive / %d dead" % (s["alive"], s["dead"]))
    print("Souls in ledger: %d (all Ed25519, soul_hash=SHA-256(pubkey))" %
          len(world.soul_ledger.souls))
    print("Money: supply=%.0f treasury=%.0f" % (s["money_supply"], s["treasury"]))
    print("Book conservation residual: %.3e  PoR ratio: %.4f  (both must hold)" % (
        world.economy.conservation_residual(),
        world.peg.reserve_ratio(COIN_ID)))
    print("\n--- 《红尘泪》世界层（大央帝朝武道）---")
    rs = world.realm.summary()
    print("Genesis qi=%.0f  unallocated=%.2f  dissipated=%.2f  absorbed=%.2f" % (
        rs["genesis_qi"], rs["unallocated"], rs["dissipated"], rs["absorbed_total"]))
    print("Qi conservation residual: %.3e  holds=%s" % (
        rs["conservation_residual"], rs["conservation_holds"]))
    print("Promotions: %d   Shattered dantian: %d" % (rs["promotions"], rs["shattered"]))
    print("Rank distribution: %s" % json.dumps(rs["rank_distribution"], ensure_ascii=False))
    for name, board in world.realm.boards().items():
        if board:
            top = board[0]
            print("  %s 榜首: %s（%s，真气 %.0f）" % (
                name, getattr(top, "name", "?"),
                rank_name(getattr(top, "rank_idx", 0)), getattr(top, "qi", 0.0)))
    return world


def run_audit_gate(world) -> bool:
    """25 维宪法审计 + 独立复算门禁。全过返回 True（退出码 0）。"""
    from audit_engine import AuditReport

    report = world.run_constitutional_audit()
    print("\n" + report.summary())

    all_pass = all(
        AuditReport._is_pass(getattr(report, attr))
        for attr, _ in AuditReport.FIELDS
    )

    print("\n--- PoR 储备报表（可第三方复算）---")
    for row in world.peg.proof_of_reserve_report():
        print("  %s owner=%s supply=%.1f reserve=%.1f ratio=%.4f ok=%s" % (
            row["asset_id"], row["owner_soul"][:16] + "...",
            row["total_supply"], row["reserve_amount"],
            row["ratio"], row["poR_ok"]))

    print("\n--- 独立复算门禁（不信任 report 本身，逐项重跑）---")
    checks = {
        "audit_25_dims": all_pass,
        "identity_reverify": _reverify_identities(world),
        "economy_compliant": world.peg.compliant(),
        "onboarding_pass": bool(world.interoperability.on_board_world(world.world_config)),
        "book_conservation": world.economy.conservation_holds(),
        "por_conservation": world.peg.conservation_holds(),
        "redemption_selfcheck": bool(world.redemption_selfcheck),
    }
    ok = True
    for name, passed in checks.items():
        print("  [%s] %s" % ("PASS" if passed else "FAIL", name))
        ok = ok and passed
    print("\nGATE VERDICT: %s" % ("PASS - 25/25 + 独立复算全过" if ok else "FAILED"))
    return ok


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(
        description="Second Reality - Real-Stack Virtual World (25/25 audit)")
    ap.add_argument("--headless", action="store_true", help="run without GUI")
    ap.add_argument("--gui", action="store_true", help="pygame GUI（真栈世界，可进去看）")
    ap.add_argument("--ticks", type=int, default=100, help="ticks to simulate")
    ap.add_argument("--seed", type=int, default=0, help="world RNG seed (reproducible)")
    ap.add_argument("--audit", action="store_true",
                    help="25 维宪法审计 + 独立复算门禁；全过退出码 0")
    ap.add_argument("--agents", type=int, default=None)
    ap.add_argument("--world-size", type=int, default=None)
    ap.add_argument("--resources", type=int, default=None)
    ap.add_argument("--buildings", type=int, default=None)
    ap.add_argument("--tps", type=int, default=10, help="GUI ticks per second")
    ap.add_argument("--storage", choices=["memory", "sqlite"], default="memory",
                    help="储备账本后端：memory=进程内可复现（默认）；sqlite=落盘")
    ap.add_argument("--world-id", default=None, help="世界 ID（跨世界互通时需要唯一）")
    ap.add_argument("--data", default=None,
                    help="世界数据目录（含世界私钥与账本；默认仓库 .world_data/real_demo）")
    # ---- HTTP 服务化（红尘泪世界直接对外提供 REST/WS）----
    ap.add_argument("--serve", action="store_true",
                    help="以 HTTP 服务方式运行本世界（替代 system.World 的角色）")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    # ---- 跨世界记忆过境 ----
    # --card 写文件而非打 stdout：运行日志会混进输出，重定向出的文件不是合法 JSON，
    # 跨机器流程会在"注册对端名片"这一步卡住。
    ap.add_argument("--card", nargs="?", const="world_card.json", default=None,
                    metavar="PATH", help="导出本世界名片到文件（默认 world_card.json）")
    ap.add_argument("--register-card", metavar="PATH",
                    help="注册对端世界名片（JSON 文件）")
    ap.add_argument("--export-memory", metavar="PEER_WORLD_ID",
                    help="向已注册的对端世界打包记忆信封")
    ap.add_argument("--soul", default=None, help="指定灵魂哈希（默认取首个居民灵魂）")
    ap.add_argument("--out", default="memory_bundle.json", help="信封输出路径")
    ap.add_argument("--import-memory", metavar="PATH", help="导入对端记忆信封")
    args = ap.parse_args()

    demo_cfg = build_demo_config(agents=args.agents, world_size=args.world_size,
                                 resources=args.resources, buildings=args.buildings,
                                 seed=args.seed)
    _print_demo_note(demo_cfg)

    if args.gui:
        # run_gui 内部硬编码实例化 NohnWorld；此处把模块名替换为 RealWorld
        # （进程内一次性替换，不改 virtual_world.py 一行——教学版保持原样）。
        vw.NohnWorld = RealWorld
        world = vw.run_gui(tps=args.tps, seed=args.seed, max_ticks=args.ticks,
                           config=demo_cfg)
    elif args.serve:
        # 服务模式：不预跑 tick，世界由 /world/tick 驱动（与 system.World 行为一致）
        world = RealWorld(demo_cfg, storage_backend=args.storage,
                          data_dir=args.data, world_id=args.world_id)
    else:
        world = run_real_headless(ticks=args.ticks, seed=args.seed, config=demo_cfg,
                                  verbose=True, storage_backend=args.storage,
                                  world_id=args.world_id, data_dir=args.data)

    # ---- 跨世界操作（在仿真之后执行）----
    if args.card:
        card = world.memory_channel.export_world_card()
        with open(args.card, "w", encoding="utf-8") as f:
            json.dump(card, f, ensure_ascii=False, indent=2)
        print("[card] 名片已写出: %s (world=%s)" % (
            args.card, card.get("card", {}).get("world_id", "?")))
    if args.register_card:
        with open(args.register_card, "r", encoding="utf-8") as f:
            peer_card = json.load(f)
        res = world.memory_channel.register_world_card(peer_card)
        print("[register-card] %s" % res)
    if args.export_memory:
        soul = args.soul or next(iter(world._soul_pubkeys), None)
        if not soul:
            raise SystemExit("[export-memory] 本世界无灵魂可导出")
        n = world.mirror_memories(soul)
        print("[export-memory] 归档 %d 条记忆 -> 真实记忆库" % n)
        bundle = world.memory_channel.export_bundle(
            target_world_id=args.export_memory,
            soul_hash=soul,
            user_pubkey=world._soul_pubkeys.get(soul),
        )
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=2)
        print("[export-memory] 信封已写出: %s (transfer=%s)" % (
            args.out, bundle.get("transfer_id")))
    if args.import_memory:
        with open(args.import_memory, "r", encoding="utf-8") as f:
            bundle = json.load(f)
        res = world.memory_channel.import_bundle(bundle)
        print("[import-memory] %s" % json.dumps(res, ensure_ascii=False))

    if args.serve:
        rs = world.realm.summary()
        print("\n=== 红尘泪世界 · HTTP 服务 ===")
        print("world_id   : %s" % world.world_id)
        print("数据目录   : %s" % (args.data or "（默认 .world_data/real_demo）"))
        print("监听       : %s:%d （明文 HTTP，仅限可信局域网）" % (args.host, args.port))
        print("灵魂数     : %d   真气守恒: %s" % (
            len(world.soul_ledger.souls), rs["conservation_holds"]))
        print("世界名片   : 可 POST /roaming/memory/card 取（需 token）")
        print("推进世界   : POST /world/tick")
        serve_http(_ApiFacade(world), host=args.host, port=args.port)
        return

    if args.audit:
        ok = run_audit_gate(world)
        raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
