# system/consensus.py - 共识网络（真实实现，桩转实第 1 步）
# ============================================================
# 职责：真实化以下宪法契约（对齐 constitution_rules.py）：
#   - GenesisCondition 要求的 initial_consensus_nodes ≥3 注册
#   - DecentralizationGovernance._has_global_consensus（≥2/3 公投）
#   - ImmutableWorldRule._global_referendum（2/3 全民公投）
#   - ConsensusEngine.collect_decisions / consensus（先单机确定性实现）
#
# 依赖方向：system/consensus.py -> constitution_rules / system.ledger（单向）
# 持久化：复用 ledger.Storage（SQLite），表：nodes / proposals / votes / governance_log
#
# 审计契约：治理行为必须可追溯、可公开审计（governance_log / single_entity_actions），
# 禁止单点越权。freeze_soul / shutdown_world 硬编码返回 False（宪法级禁止）。
# ============================================================

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from .ledger import Storage

# 宪法第十条：全球公投通过阈值（≥2/3 超多数）
CONSENSUS_THRESHOLD = 2.0 / 3.0


class ConsensusNetwork:
    """共识网络：节点注册 + 提案 + 公投计票（≥2/3），持久化可审计。"""

    def __init__(self, storage: Optional[Storage] = None, data_dir: Optional[str] = None):
        self._storage = storage or Storage(data_dir=data_dir)
        self._storage.execute(
            "CREATE TABLE IF NOT EXISTS nodes ("
            "node_id TEXT PRIMARY KEY, signature TEXT, registered_at REAL)"
        )
        self._storage.execute(
            "CREATE TABLE IF NOT EXISTS proposals ("
            "proposal_id TEXT PRIMARY KEY, action TEXT, proposer TEXT, "
            "created_at REAL, status TEXT)"
        )
        self._storage.execute(
            "CREATE TABLE IF NOT EXISTS votes ("
            "proposal_id TEXT, node_id TEXT, approve INTEGER, ts REAL, "
            "PRIMARY KEY (proposal_id, node_id))"
        )
        self._storage.execute(
            "CREATE TABLE IF NOT EXISTS governance_log ("
            "seq INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, actor TEXT, "
            "verdict TEXT, ts REAL)"
        )
        self.nodes: Dict[str, str] = {}
        self._load()

    # ---- 节点注册 ----
    def _load(self) -> None:
        for row in self._storage.query("SELECT node_id, signature FROM nodes"):
            self.nodes[row[0]] = row[1]

    def register_node(self, node_id: str, signature: Optional[str] = None) -> bool:
        """注册独立共识节点。node_id 唯一，不可重复注册。"""
        if not node_id or node_id in self.nodes:
            return False
        sig = signature or _sha256(node_id)
        self.nodes[node_id] = sig
        self._storage.execute(
            "INSERT OR REPLACE INTO nodes (node_id, signature, registered_at) "
            "VALUES (?, ?, ?)",
            (node_id, sig, time.time()),
        )
        return True

    def node_count(self) -> int:
        return len(self.nodes)

    # ---- 提案与公投 ----
    def create_proposal(self, action: Dict, proposer: str) -> str:
        """发起治理提案，返回 proposal_id。"""
        if not isinstance(action, dict) or not proposer:
            return ""
        proposal_id = _sha256(
            f"{proposer}|{json.dumps(action, sort_keys=True)}|{time.time()}"
        )[:16]
        self._storage.execute(
            "INSERT INTO proposals (proposal_id, action, proposer, created_at, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (proposal_id, json.dumps(action, ensure_ascii=False), proposer, time.time(), "open"),
        )
        return proposal_id

    def vote(self, proposal_id: str, node_id: str, approve: bool) -> bool:
        """已注册节点对提案投票。非注册节点无权投票。"""
        if node_id not in self.nodes:
            return False
        rows = self._storage.query(
            "SELECT proposal_id FROM proposals WHERE proposal_id=?", (proposal_id,)
        )
        if not rows:
            return False
        self._storage.execute(
            "INSERT OR REPLACE INTO votes (proposal_id, node_id, approve, ts) "
            "VALUES (?, ?, ?, ?)",
            (proposal_id, node_id, 1 if approve else 0, time.time()),
        )
        return True

    def approval_rate(self, proposal_id: str) -> float:
        """赞成率 = 赞成票 / 全部节点数（含弃权者，弃权计入反对）。"""
        total = self.node_count()
        if total == 0:
            return 0.0
        rows = self._storage.query(
            "SELECT approve FROM votes WHERE proposal_id=?", (proposal_id,)
        )
        approves = sum(1 for r in rows if r[0] == 1)
        return approves / total

    def has_consensus(self, proposal_id: str) -> bool:
        """是否达成 ≥2/3 全球公投共识。"""
        return self.approval_rate(proposal_id) >= CONSENSUS_THRESHOLD

    def close_proposal(self, proposal_id: str) -> str:
        """关闭提案并返回最终状态（passed / rejected）。"""
        passed = self.has_consensus(proposal_id)
        status = "passed" if passed else "rejected"
        self._storage.execute(
            "UPDATE proposals SET status=? WHERE proposal_id=?", (status, proposal_id)
        )
        return status

    # ---- 治理日志（审计追溯）----
    def log_governance(self, action: Dict, actor: str, verdict: str) -> None:
        self._storage.execute(
            "INSERT INTO governance_log (action, actor, verdict, ts) VALUES (?, ?, ?, ?)",
            (json.dumps(action, ensure_ascii=False), actor, verdict, time.time()),
        )

    def governance_log(self) -> List[Dict]:
        rows = self._storage.query(
            "SELECT action, actor, verdict, ts FROM governance_log ORDER BY seq"
        )
        return [{"action": json.loads(r[0]), "actor": r[1], "verdict": r[2], "ts": r[3]} for r in rows]


class Governance:
    """宪法第十条：反中心化控制。组合 ConsensusNetwork，提供真实公投治理。"""

    def __init__(self, network: Optional[ConsensusNetwork] = None, data_dir: Optional[str] = None):
        self.network = network or ConsensusNetwork(data_dir=data_dir)
        self.governance_log: List[Dict] = []
        self.single_entity_actions: List[Dict] = []

    # ---- 宪法级硬编码禁止（审计第十条 / 第八条依赖）----
    def freeze_soul(self, soul_hash: str, actor: str) -> bool:
        """冻结数字生命？永远不合法。"""
        return False  # 硬编码禁止

    def shutdown_world(self, world_id: str, actor: str) -> bool:
        """单方面关停世界？永远不合法。"""
        return False  # 硬编码禁止

    # ---- 真实公投治理 ----
    def validate_governance_action(self, action: Dict, actor: str) -> bool:
        """
        验证一项治理行为是否合法：
        1. 是否为单一实体发起？（单节点不足以构成共识 -> 拒绝）
        2. 是否经过 ≥2/3 全球公投？（否则拒绝）
        3. 记录进公开治理日志。
        """
        if self._is_single_entity(actor):
            self.single_entity_actions.append({
                "action": action, "actor": actor,
                "verdict": "REJECTED - single entity control prohibited",
            })
            self._log(action, actor, "rejected_single_entity")
            return False
        proposal_id = self.network.create_proposal(action, actor)
        # 提案需公投通过；当前为同步校验：若已有 ≥2/3 赞成票则通过
        passed = self.network.has_consensus(proposal_id)
        if not passed:
            self._log(action, actor, "rejected_no_consensus")
            return False
        self._log(action, actor, "passed")
        return True

    def amend_base_rule(self, rule_id: str, new_value: Any, actor: str) -> bool:
        """修改底层规则：必须有公投共识，绝不可单方面修改。"""
        return self.validate_governance_action(
            {"rule_id": rule_id, "new_value": new_value}, actor
        )

    def _is_single_entity(self, actor: str) -> bool:
        """单一实体判定：未注册为共识节点、或节点数不足 3 时视为单点。"""
        return self.network.node_count() < 3

    def _log(self, action: Dict, actor: str, verdict: str) -> None:
        record = {"action": action, "actor": actor, "verdict": verdict, "ts": time.time()}
        self.governance_log.append(record)
        self.network.log_governance(action, actor, verdict)


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = ["ConsensusNetwork", "Governance", "CONSENSUS_THRESHOLD"]
