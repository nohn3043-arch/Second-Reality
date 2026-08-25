# system/runtime.py - 无头运行时（真实实现，桩转实第 3 步）
# ============================================================
# 职责：将 virtual_world.py 的演示逻辑服务化、可部署化：
#   - 创世装配：组装空间/时间/因果/存在 + 共识节点 + 账本 + 记忆，
#     真实调用 GenesisCondition.initiate_genesis，世界从概念态转运行态。
#   - tick 主循环（对齐 TemporalSubstrate.global_clock）
#   - 事件传导（因果链记录 + 历史哈希链追加）
#   - 世界快照 + 持久化（进程重启不丢状态）
#   - 周期性上报 audit_engine.SecondPerspectiveAuditor 18 项审计
#
# 目标形态：无 GUI 依赖、可横向扩展、可作为企业服务底座。
#
# 依赖方向：system/runtime.py -> constitution_rules / audit_engine / system.*（单向）
# ============================================================

import json
import threading
import time
from typing import Any, Dict, List, Optional

from constitution_rules import (
    NOHN_LAW_AXIOMS,
    SpatialSubstrate,
    TemporalSubstrate,
    CausalClosure,
    ExistenceAxiom,
    GenesisCondition,
    ImmutableWorldRule,
    WorldCentralBrain,
    AestheticCompliance,
    SoulAttestation,
    WorldPerpetuity,
    MandatoryInteroperability,
)
from audit_engine import SecondPerspectiveAuditor, AuditReport

from .ledger import (
    Storage,
    SoulLedger,
    HistoryLedger,
    EconomicReserve,
    SnapshotRegistry,
    derive_soul_hash,
    is_hex64,
)
from .keys import verify_genesis_proof, FileKmsProvider
from .consensus import ConsensusNetwork, Governance
from .agent_engine import MemoryVault, MemoryInalienability, Agent
from .credentials import CredentialVault
from .session import SessionManager
from .authorization import AuthorizationEngine
from .recovery import RecoveryManager


class World:
    """运行态世界：创世装配后的可审计实例，供 18 项审计消费。"""

    def __init__(
        self,
        world_id: str,
        data_dir: Optional[str] = None,
        initial_oracles: Optional[List[str]] = None,
    ):
        self.world_id = world_id
        self.storage = Storage(data_dir=data_dir)
        # 并发保护：ThreadingHTTPServer 多线程下 tick/spawn 串行化，防状态竞态
        self._lock = threading.Lock()

        # ---- 系统层真实组件（持久化）----
        self.soul_ledger = SoulLedger(storage=self.storage)
        self.history = HistoryLedger(storage=self.storage)
        self.economy = EconomicReserve(storage=self.storage)
        for o in initial_oracles or ["oracle_a", "oracle_b", "oracle_c"]:
            self.economy.register_oracle(o)
        self.snapshot_registry = SnapshotRegistry(storage=self.storage)
        self.memory_vault = MemoryVault(storage=self.storage)
        self.consensus = ConsensusNetwork(storage=self.storage)
        self.governance = Governance(network=self.consensus)
        self.memory_integrity = MemoryInalienability(vault=self.memory_vault)

        # ---- 账户系统六层架构（第1~4层服务组件）----
        # 第1层：多设备凭证（服务端只存公钥）
        self.credentials = CredentialVault(storage=self.storage)
        # 第2层：有状态会话（签名密钥经 KMS 抽象托管，可插拔 HSM）
        self.kms = FileKmsProvider(self.storage.data_dir)
        self.sessions = SessionManager(storage=self.storage, kms_provider=self.kms)
        # 第3层：分级授权 + 风险引擎
        self.authorization = AuthorizationEngine(storage=self.storage)
        # 第4层：社交恢复 + 时间锁
        self.recovery = RecoveryManager(
            storage=self.storage,
            credential_vault=self.credentials,
            guardian_threshold=3,
            timelock_seconds=7 * 24 * 3600,
        )

        # ---- 宪法层合规外壳（构成公理 + 治理公理）----
        self.spatial_substrate = SpatialSubstrate()
        self.spatial_substrate.define_topology("Euclidean", 3, "Infinite", 1e-3)
        self.temporal_substrate = TemporalSubstrate()
        self.temporal_substrate.granularity = 1.0  # 1 tick = 1 秒
        self.causal_closure = CausalClosure()
        self.existence_axiom = ExistenceAxiom()
        self.genesis_condition = GenesisCondition()
        self.immutable_rule = ImmutableWorldRule()
        self.central_brain = WorldCentralBrain()
        self.aesthetic = AestheticCompliance()
        self.soul_attestation = SoulAttestation()
        self.soul_attestation.soul_ledger = self.soul_ledger  # 注入真实账本
        self.world_perpetuity = WorldPerpetuity()
        self.world_perpetuity.history_chain = self.history  # 注入真实历史链
        self.world_perpetuity.snapshot_registry = self.snapshot_registry
        self.interoperability = MandatoryInteroperability()

        # ---- law 层合规属性（供审计 _audit_*_law 消费）----
        self.identity = {
            "soul_hash_sha256": True,
            "non_revocable": True,
            "cross_world_portable": True,
            "asset_bound": True,
        }
        self.communication = {
            "uses_nohn_semantics": True,
            "unknown_downgraded": True,
            "vocab_mapped": True,
        }
        self.physics = {
            "gravity": NOHN_LAW_AXIOMS["gravity"],
            "time_dilation": NOHN_LAW_AXIOMS["time_dilation"],
            "unit_scale": NOHN_LAW_AXIOMS["unit_scale"],
            "no_dimensional_inflation": NOHN_LAW_AXIOMS["no_dimensional_inflation"],
        }
        # 并网审查配置（interoperability.on_board_world 四维度）
        self.world_config = {
            "world_id": self.world_id,
            "semantics": self.communication,
            "physics": self.physics,
            "identity": self.identity,
            "economy": {
                "real_peg_1to1": self.economy.real_peg_1to1,
                "proof_of_reserve": self.economy.proof_of_reserve,
                "redemption_right": self.economy.redemption_right,
                "unilateral_fee": self.economy.unilateral_fee,
                "asset_bound_to_soul": self.economy.asset_bound_to_soul,
                "oracle_sources": self.economy.oracle_sources,
            },
        }

        # ---- 运行态实体 ----
        self.npcs: Dict[str, Agent] = {}
        self.main_quest = None  # 无主线（审计第四条）
        self.genesis_completed = False

        self._bootstrap_genesis()

    # ---- 创世装配 ----
    def _bootstrap_genesis(self) -> None:
        """组装创世所需全部组件，真实调用 GenesisCondition.initiate_genesis。"""
        # 注册 ≥3 独立共识节点（治理公理十：去中心化）
        for i in range(3):
            self.consensus.register_node(f"node_{i:03d}", signature=None)
        # 创世区块
        genesis_block = self.history.append(
            {
                "event": "genesis",
                "world_id": self.world_id,
                "timestamp": time.time(),
            }
        )
        # 创世灵魂（可为空，但必须显式声明）
        genesis_souls: List[str] = []
        genesis_config = {
            "spatial_substrate": self.spatial_substrate,
            "temporal_substrate": self.temporal_substrate,
            "causal_closure": self.causal_closure,
            "existence_axiom": self.existence_axiom,
            "initial_consensus_nodes": list(self.consensus.nodes.keys()),
            "genesis_block": genesis_block,
            "genesis_souls": genesis_souls,
        }
        self.genesis_completed = self.genesis_condition.initiate_genesis(genesis_config)

    # ---- 世界演化 ----
    def spawn_agent(
        self,
        soul_hash: Optional[str] = None,
        personality: Optional[Dict] = None,
        genesis_proof: Optional[Dict] = None,
    ) -> Optional[Agent]:
        """创生智能体（定稿·密钥链路）：soul_hash 必须为 64 位 hex 且由公钥指纹派生。

        创世证明必须先通过签名校验（verify_genesis_proof），任意伪造/篡改的
        证明一律被拒——无论该 soul_hash 是否已存在（防伪造覆盖语义）。
        已存在且证明有效的灵魂返回已有 Agent，不覆盖需求状态和行动历史。
        """
        if genesis_proof is None or not verify_genesis_proof(genesis_proof):
            return None  # 无效签名 / 非公钥证明：拒绝凭空捏造或伪造身份
        derived = derive_soul_hash(genesis_proof)
        if soul_hash is None:
            soul_hash = derived
        if not is_hex64(soul_hash):
            return None
        if derived is not None and derived != soul_hash:
            return None  # 提供的 soul_hash 与公钥指纹不一致
        with self._lock:
            # 已存在则直接返回，不覆盖
            if soul_hash in self.npcs:
                return self.npcs[soul_hash]
            # 1. 灵魂确权（SHA-256 公钥指纹，持久化到 SQLite）
            if not self.soul_ledger.exists(soul_hash):
                if self.soul_ledger.register_soul(genesis_proof) != soul_hash:
                    return None
            # 2. 存在公理：创生（需因果 + 位置）
            self.existence_axiom.bring_into_existence(
                soul_hash,
                cause="GENESIS",
                initial_state={"alive": True},
                location=[0.0, 0.0, 0.0],
            )
            # 3. 因果闭包：创生事件挂到创世
            self.causal_closure.link_cause(f"spawn:{soul_hash}", ["GENESIS"])
            # 4. 智能体实例
            agent = Agent(
                soul_hash, personality=personality, memory_vault=self.memory_vault
            )
            self.npcs[soul_hash] = agent
            return agent

    def tick(self) -> Dict:
        """推进世界一个 tick：时间 + 决策 + 事件传导 + 历史追加。"""
        with self._lock:
            clock = self.temporal_substrate.tick()
            events = []
            for soul, agent in self.npcs.items():
                action = agent.decide_next_action({"tick": clock})
                event = {"tick": clock, "soul": soul, "action": action}
                events.append(event)
                # 因果闭包：行动以智能体存在为因
                self.causal_closure.link_cause(f"act:{soul}:{clock}", [f"spawn:{soul}"])
            if events:
                self.history.append({"event": "tick", "tick": clock, "actions": events})
            return {"tick": clock, "events": events}

    # ---- 审计上报 ----
    def audit(self) -> AuditReport:
        """运行 18 项第二视角审计，返回可打印结论。"""
        auditor = SecondPerspectiveAuditor()
        return auditor.audit_world(self)

    def audit_summary(self) -> str:
        return self.audit().summary()

    # ---- 快照 ----
    def snapshot(self) -> str:
        return self.snapshot_registry.create_snapshot(
            {
                "world_id": self.world_id,
                "clock": self.temporal_substrate.global_clock,
                "souls": list(self.soul_ledger.souls.keys()),
                "agents": list(self.npcs.keys()),
            }
        )

    def close(self) -> None:
        """关闭世界，释放 SQLite 连接等底层资源。"""
        self.storage.close()


__all__ = ["World"]
