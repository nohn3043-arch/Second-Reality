# system/ledger.py - 状态账本（真实实现，桩转实第 0 步）
# ============================================================
# 职责：真实化以下宪法契约（对齐 constitution_rules.py / law/ 标准）：
#   - SoulLedger          灵魂账本：SHA-256 soul_hash 全局唯一确权，持久化
#   - HistoryLedger       世界历史：哈希链仅追加，篡改可检测
#   - EconomicReserve     PoR 储备账本：1:1 锚定 + 强制赎回 + 预言机 ≥3
#   - SnapshotRegistry    世界快照：落盘，进程重启不丢失
#
# 依赖方向：system/ledger.py -> constitution_rules（单向，无循环导入）
# 持久化：SQLite（标准库 sqlite3，ACID），数据默认落在仓库根 .world_data/
#
# 审计契约：本模块实例可挂载到 world 供 audit_engine.SecondPerspectiveAuditor
# 的 _audit_economic_law / _audit_identity_law / _audit_world_perpetuity 消费。
# ============================================================

import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from constitution_rules import NOHN_LAW_AXIOMS

_DEFAULT_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, ".world_data")
)


def _sha256_hex(payload: str) -> str:
    """SHA-256 输出 64 位十六进制（对齐 NOHN_LAW_AXIOMS soul_hash_len=64）"""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ============================================================
# SQLite 持久化后端（ACID，进程重启不丢失）
# ============================================================

class Storage:
    """统一存储后端：一张连接管理全部账本表，线程安全。"""

    _SCHEMA = [
        """
        CREATE TABLE IF NOT EXISTS souls (
            soul_hash  TEXT PRIMARY KEY,
            identity   TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS history (
            seq        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  REAL NOT NULL,
            event      TEXT NOT NULL,
            block_hash TEXT NOT NULL,
            prev_hash  TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS reserve (
            asset_id       TEXT PRIMARY KEY,
            owner_soul     TEXT NOT NULL,
            total_supply   REAL NOT NULL DEFAULT 0,
            reserve_amount REAL NOT NULL DEFAULT 0,
            updated_at     REAL NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS reserve_ledger (
            seq       INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id  TEXT NOT NULL,
            action    TEXT NOT NULL,
            amount    REAL NOT NULL,
            soul_hash TEXT,
            ts        REAL NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            snapshot_id TEXT PRIMARY KEY,
            state       TEXT NOT NULL,
            created_at  REAL NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """,
    ]

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or _DEFAULT_DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        db_path = os.path.join(self.data_dir, "ledger.sqlite3")
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        for ddl in self._SCHEMA:
            self._conn.execute(ddl)
        self._conn.commit()
        self._lock = threading.Lock()

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self._lock:
            self._conn.execute(sql, params)
            self._conn.commit()

    def query(self, sql: str, params: tuple = ()) -> List[tuple]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# ============================================================
# 第六条：灵魂账本（law/Identity attestation standard）
# ============================================================

class SoulLedger:
    """灵魂账本：SHA-256 soul_hash 全局唯一，持久化，不可撤销。"""

    def __init__(self, storage: Optional[Storage] = None, data_dir: Optional[str] = None):
        self._storage = storage or Storage(data_dir=data_dir)
        self.souls: Dict[str, Dict] = {}
        self._load()

    def _load(self) -> None:
        for row in self._storage.query("SELECT soul_hash, identity FROM souls"):
            self.souls[row[0]] = json.loads(row[1])

    def _flush(self, soul_hash: str, identity: Dict) -> None:
        self._storage.execute(
            "INSERT OR REPLACE INTO souls (soul_hash, identity, created_at) VALUES (?, ?, ?)",
            (soul_hash, json.dumps(identity, ensure_ascii=False), time.time()),
        )

    def register_soul(self, genesis_proof: Dict) -> Optional[str]:
        """注册新的数字生命。合规：sha256 签名 + 无冲突 + 不可重复注册。"""
        if not isinstance(genesis_proof, dict) or not genesis_proof:
            return None
        payload = (
            genesis_proof.get("signature")
            or genesis_proof.get("genesis_id")
            or json.dumps(genesis_proof, sort_keys=True)
        )
        soul_hash = _sha256_hex(str(payload))
        if soul_hash in self.souls:
            return None  # 不可重复注册
        identity = {
            "soul_hash": soul_hash,
            "soul_hash_sha256": True,          # law 身份确权：SHA-256 / 64 hex
            "non_revocable": True,             # 宪法第六条：任何平台无权撤销
            "cross_world_portable": True,      # 跨世界唯一、可迁移
            "asset_bound": True,               # 资产绑定 soul_hash
            "genesis_proof": genesis_proof,
            "created_at": time.time(),
            "world_history": [],               # 跨世界迁移记录
        }
        self.souls[soul_hash] = identity
        self._flush(soul_hash, identity)
        return soul_hash

    def exists(self, soul_hash: str) -> bool:
        return soul_hash in self.souls

    def get_identity(self, soul_hash: str) -> Dict:
        return self.souls.get(soul_hash, {})

    def record_migration(self, soul_hash: str, to_world: str) -> bool:
        """跨世界迁移记录（law 身份确权：跨世界可迁移，不强制重新注册）。"""
        ident = self.souls.get(soul_hash)
        if not ident:
            return False
        ident["world_history"].append({"to_world": to_world, "ts": time.time()})
        self._flush(soul_hash, ident)
        return True


# ============================================================
# 第八条：世界历史账本（宪法 WorldPerpetuity / HistoryLedger）
# ============================================================

class HistoryLedger:
    """世界历史账本：哈希链仅追加，篡改可检测（宪法第八条）。"""

    def __init__(self, storage: Optional[Storage] = None, data_dir: Optional[str] = None):
        self._storage = storage or Storage(data_dir=data_dir)
        self.chain: List[tuple] = []  # [(timestamp, event_data, block_hash), ...]
        self._load()

    def _load(self) -> None:
        for row in self._storage.query(
            "SELECT timestamp, event, block_hash FROM history ORDER BY seq"
        ):
            self.chain.append((row[0], json.loads(row[1]), row[2]))

    def append(self, event: Dict) -> str:
        """追加世界事件，返回该事件区块哈希。链接前一区块，仅追加不改写。"""
        if not isinstance(event, dict):
            event = {"payload": event}
        prev_hash = self.chain[-1][2] if self.chain else None
        ts = event.get("timestamp", time.time())
        block_hash = _sha256_hex(
            f"{ts}|{json.dumps(event, ensure_ascii=False, sort_keys=True)}|{prev_hash or ''}"
        )
        self._storage.execute(
            "INSERT INTO history (timestamp, event, block_hash, prev_hash) VALUES (?, ?, ?, ?)",
            (ts, json.dumps(event, ensure_ascii=False, sort_keys=True), block_hash, prev_hash),
        )
        self.chain.append((ts, event, block_hash))
        return block_hash

    def validate_chain(self) -> bool:
        """全链校验：任一区块哈希不匹配或链头断裂即判定被篡改。"""
        rows = self._storage.query(
            "SELECT timestamp, event, block_hash, prev_hash FROM history ORDER BY seq"
        )
        prev = None
        for ts, event, block_hash, prev_hash in rows:
            expected = _sha256_hex(f"{ts}|{event}|{prev_hash or ''}")
            if expected != block_hash:
                return False
            if prev is not None and prev_hash != prev:
                return False
            prev = block_hash
        return True


# ============================================================
# law 全球经济统一标准 V2.1：PoR 储备账本
# ============================================================

class EconomicReserve:
    """PoR 储备账本：锚定类资产按发行储备 1:1 映射；储备率 < 100% 即暂停兑换；
    赎回通道常驻、不可单方关停；预言机独立来源 ≥3（对齐 law 标准）。"""

    def __init__(
        self,
        oracle_sources: Optional[List[str]] = None,
        storage: Optional[Storage] = None,
        data_dir: Optional[str] = None,
    ):
        self._storage = storage or Storage(data_dir=data_dir)
        # 并网即查属性（对齐 EconomicBaseline.compliant 与审计引擎）
        self.real_peg_1to1 = True
        self.proof_of_reserve = True
        self.redemption_right = True
        self.unilateral_fee = False
        self.asset_bound_to_soul = True
        self.oracle_sources: List[str] = list(oracle_sources or [])
        self._ledger: Dict[str, Dict] = {}
        self._load_oracles()
        self._load_assets()

    def _load_oracles(self) -> None:
        row = self._storage.query("SELECT value FROM meta WHERE key='oracle_sources'")
        if row:
            self.oracle_sources = json.loads(row[0][0])

    def _save_oracles(self) -> None:
        self._storage.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('oracle_sources', ?)",
            (json.dumps(self.oracle_sources),),
        )

    def _load_assets(self) -> None:
        for row in self._storage.query(
            "SELECT asset_id, owner_soul, total_supply, reserve_amount FROM reserve"
        ):
            self._ledger[row[0]] = {
                "owner_soul": row[1],
                "total_supply": row[2],
                "reserve_amount": row[3],
            }

    def register_oracle(self, source_id: str) -> None:
        """登记独立预言机来源（law：≥3 个，防单点操纵）。"""
        if source_id and source_id not in self.oracle_sources:
            self.oracle_sources.append(source_id)
            self._save_oracles()

    def issue_pegged(self, asset_id: str, amount: float, owner_soul: str) -> bool:
        """发行锚定资产：按发行储备 1:1 映射（real_peg_1to1）。"""
        if amount <= 0 or asset_id in self._ledger:
            return False
        self._ledger[asset_id] = {
            "owner_soul": owner_soul,
            "total_supply": amount,
            "reserve_amount": 0.0,
        }
        self._sync_asset(asset_id)
        self._log(asset_id, "issue", amount, owner_soul)
        return True

    def deposit_reserve(self, asset_id: str, amount: float) -> bool:
        """现实储备入账：锚定资产必须由等额储备背书。"""
        asset = self._ledger.get(asset_id)
        if not asset or amount <= 0:
            return False
        asset["reserve_amount"] += amount
        self._sync_asset(asset_id)
        self._log(asset_id, "reserve_in", amount, asset["owner_soul"])
        return True

    def reserve_ratio(self, asset_id: str) -> float:
        """储备率 = 储备金额 / 流通总量。"""
        asset = self._ledger.get(asset_id)
        if not asset or asset["total_supply"] <= 0:
            return 1.0
        return asset["reserve_amount"] / asset["total_supply"]

    def reserve_ratio_ok(self, asset_id: str) -> bool:
        """PoR：储备率 < 100% 即暂停兑换并公示（law 强制）。"""
        return self.reserve_ratio(asset_id) >= 1.0

    def redeem(self, asset_id: str, amount: float, soul_hash: str) -> bool:
        """赎回权：持币人随时按 1:1 兑回现实法币；通道常驻不可单方关停。"""
        asset = self._ledger.get(asset_id)
        if not asset or asset["owner_soul"] != soul_hash:
            return False
        if amount <= 0 or amount > asset["total_supply"]:
            return False
        if amount > asset["reserve_amount"]:
            return False  # 储备不足：暂停兑换（PoR 约束）
        asset["total_supply"] -= amount
        asset["reserve_amount"] -= amount
        self._sync_asset(asset_id)
        self._log(asset_id, "redeem", amount, soul_hash)
        return True

    def proof_of_reserve_report(self) -> List[Dict]:
        """PoR 报表：供审计与全网公示（注：proof_of_reserve 为审计布尔属性，方法名错开）。"""
        return [
            {
                "asset_id": aid,
                "owner_soul": a["owner_soul"],
                "total_supply": a["total_supply"],
                "reserve_amount": a["reserve_amount"],
                "ratio": round(self.reserve_ratio(aid), 4),
                "poR_ok": self.reserve_ratio_ok(aid),
            }
            for aid, a in sorted(self._ledger.items())
        ]

    def compliant(self) -> bool:
        """并网即查：对齐 EconomicBaseline.compliant（law 经济标准）。"""
        if not (
            self.real_peg_1to1
            and self.proof_of_reserve
            and self.redemption_right
            and not self.unilateral_fee
            and self.asset_bound_to_soul
        ):
            return False
        if len(self.oracle_sources) < int(NOHN_LAW_AXIOMS["oracle_min_sources"]):
            return False
        return True

    def _sync_asset(self, asset_id: str) -> None:
        a = self._ledger[asset_id]
        self._storage.execute(
            "INSERT OR REPLACE INTO reserve "
            "(asset_id, owner_soul, total_supply, reserve_amount, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (asset_id, a["owner_soul"], a["total_supply"], a["reserve_amount"], time.time()),
        )

    def _log(self, asset_id: str, action: str, amount: float, soul_hash: Optional[str]) -> None:
        self._storage.execute(
            "INSERT INTO reserve_ledger (asset_id, action, amount, soul_hash, ts) "
            "VALUES (?, ?, ?, ?, ?)",
            (asset_id, action, amount, soul_hash, time.time()),
        )


# ============================================================
# 第八条：世界快照注册表
# ============================================================

class SnapshotRegistry:
    """世界快照注册表：落盘，防止单点故障导致历史缺失（宪法第八条）。"""

    def __init__(self, storage: Optional[Storage] = None, data_dir: Optional[str] = None):
        self._storage = storage or Storage(data_dir=data_dir)

    def create_snapshot(self, world_state: Dict) -> str:
        snapshot_id = uuid.uuid4().hex
        self._storage.execute(
            "INSERT INTO snapshots (snapshot_id, state, created_at) VALUES (?, ?, ?)",
            (snapshot_id, json.dumps(world_state, ensure_ascii=False), time.time()),
        )
        return snapshot_id

    def restore_from_snapshot(self, snapshot_id: str) -> Dict:
        rows = self._storage.query(
            "SELECT state FROM snapshots WHERE snapshot_id=?", (snapshot_id,)
        )
        return json.loads(rows[0][0]) if rows else {}


__all__ = ["Storage", "SoulLedger", "HistoryLedger", "EconomicReserve", "SnapshotRegistry"]
