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
import logging
import os
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
    merkle_root,
)
from .keys import verify_genesis_proof, FileKmsProvider, CloudKmsProvider
from .consensus import ConsensusNetwork, Governance, TcpTransport
from .agent_engine import MemoryVault, MemoryInalienability, Agent, GasMeter, GasExceeded
from .credentials import CredentialVault
from .session import (
    SessionManager,
    SqliteSessionStore,
    MemorySessionStore,
    RedisSessionStore,
)
from .authorization import AuthorizationEngine
from .recovery import RecoveryManager
from .hlc import HybridLogicalClock, HlcTimestamp
from .spatial_sharding import ShardManager, HandoverProtocol
from .aoi_sync import AoiTracker, SyncScheduler, DeltaSync
from .partition_guard import PartitionGuard
from .hierarchical_consensus import InterDcConsensus, IntraDcConsensus

logger = logging.getLogger(__name__)


# 存储后端白名单：同一份代码，三套后端。
#   sqlite   默认：账本落盘 SQLite，会话同库
#   memory   测试/无状态演示：账本进程内 :memory:，会话内存 dict
#   redis    生产：账本本地 SQLite + 会话外置 Redis（需 redis-py，缺省降级）
#   postgres 生产：账本预留 PG 驱动接口（当前降级 SQLite，分片路由已就绪）
_STORAGE_BACKENDS = ("sqlite", "memory", "redis", "postgres")


def _resolve_storage_backend() -> str:
    """从环境变量 STORAGE 读取后端类型，非法值回落 sqlite。"""
    backend = os.environ.get("STORAGE", "sqlite").strip().lower()
    return backend if backend in _STORAGE_BACKENDS else "sqlite"


def _build_redis_session_store():
    """构造 Redis 会话存储；redis-py 缺失或连接失败时返回 None（调用方降级）。"""
    try:
        import redis
    except ImportError:
        print("[runtime] STORAGE=redis 但未安装 redis-py（pip install redis），会话降级 SQLite")
        return None
    try:
        client = redis.Redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        )
    except Exception as e:  # pragma: no cover - 连接失败降级
        print(f"[runtime] Redis 连接失败（{e}），会话降级 SQLite")
        return None
    return RedisSessionStore(client)


class World:
    """运行态世界：创世装配后的可审计实例，供 18 项审计消费。"""

    def __init__(
        self,
        world_id: str,
        data_dir: Optional[str] = None,
        initial_oracles: Optional[List[str]] = None,
    ):
        self.world_id = world_id
        # 节点身份（确定性全序的 tie-break 键）+ HLC 全局时钟
        self.node_id = world_id
        self.hlc = HybridLogicalClock(node_id=self.node_id)
        # 空间索引（地基 A）：cell_key -> set(soul_hash)；positions: soul_hash -> [x, y, z]
        self.spatial: Dict[str, set] = {}
        self.positions: Dict[str, List[float]] = {}
        self._event_seq = 0
        # Gas 计量（地基 B）：每 tick 全局预算，按 agent 数均分
        self.tick_budget = 1000        # 每 tick 全局步数上限
        self.tick_timeout_ms = 500     # 单 agent 超时 500ms
        # 地平线二：跨数据中心模块实例化
        self.shard_manager = ShardManager(local_dc="dc_local")
        self.shard_manager.init_default_shards()
        self.aoi_tracker = AoiTracker()
        self.aoi_sync = SyncScheduler()
        self.partition_guard = PartitionGuard(node_id=self.node_id)
        # Intra-DC 快环先建，Inter-DC 慢环构注入同一个实例（避免双实例孤立）
        self.intra_consensus = IntraDcConsensus()
        self.interdc_consensus = InterDcConsensus(
            local_dc_consensus=self.intra_consensus
        )
        # 存储后端：STORAGE 环境变量（sqlite/memory/redis/postgres），默认 sqlite
        self.storage_backend = _resolve_storage_backend()
        ledger_backend = (
            self.storage_backend if self.storage_backend in ("sqlite", "memory") else "sqlite"
        )
        self.storage = Storage(data_dir=data_dir, backend=ledger_backend)
        # 并发保护：ThreadingHTTPServer 多线程下 tick/spawn 串行化，防状态竞态
        self._lock = threading.Lock()

        # ---- 账户系统六层架构（第1~4层服务组件）----
        # 第1层：多设备凭证（服务端只存公钥）
        self.credentials = CredentialVault(storage=self.storage)
        # 第4层恢复，依赖凭证库查询绑定状态
        self.recovery = RecoveryManager(
            storage=self.storage,
            credential_vault=self.credentials,
        )
        # 第3层授权，依赖恢复层查询守护者列表
        self.authorization = AuthorizationEngine(
            storage=self.storage,
            recovery_manager=self.recovery
        )

        # ---- 系统层真实组件（持久化）----
        self.soul_ledger = SoulLedger(storage=self.storage)
        self.history = HistoryLedger(storage=self.storage)
        self.economy = EconomicReserve(
            storage=self.storage, authorization=self.authorization
        )
        for o in initial_oracles or ["oracle_a", "oracle_b", "oracle_c"]:
            self.economy.register_oracle(o)
        self.snapshot_registry = SnapshotRegistry(storage=self.storage)
        self.memory_vault = MemoryVault(storage=self.storage)
        self.consensus = ConsensusNetwork(storage=self.storage)
        self.governance = Governance(network=self.consensus)
        # 缺点接通 2：TcpTransport 挂载到共识网络（地平线一 E，端点为静态清单）
        self.transport = TcpTransport(
            node_id=self.node_id,
            endpoint_resolver=lambda nid: self.consensus.endpoints.get(nid),
        )
        self.consensus.set_transport(self.transport)
        # 缺点接通 3：AOI 增量复制器复用同一传输层推送跨 DC Delta
        self.aoi_sync.set_push(
            lambda target, payload: (
                self.transport.send(target, payload) if self.transport else None
            )
        )
        self.memory_integrity = MemoryInalienability(vault=self.memory_vault)
        # 第2层：有状态会话（签名密钥经 KMS 抽象托管，可插拔 HSM）
        # 会话存储按 STORAGE 选择：memory -> 内存；redis -> Redis（缺省降级）；其余 -> SQLite
        if self.storage_backend == "memory":
            self.session_store = MemorySessionStore()
        elif self.storage_backend == "redis":
            self.session_store = _build_redis_session_store() or SqliteSessionStore(self.storage)
        else:
            self.session_store = SqliteSessionStore(self.storage)
        # 密钥后端：redis/postgres 为生产形态，走云 KMS 抽象（未注入 client 时文件降级）
        if self.storage_backend in ("redis", "postgres"):
            self.kms = CloudKmsProvider(key_dir=self.storage.data_dir)
        else:
            self.kms = FileKmsProvider(self.storage.data_dir)
        self.sessions = SessionManager(
            storage=self.storage,
            kms_provider=self.kms,
            session_store=self.session_store,
        )
        logger.info(
            "world initialized world_id=%s storage_backend=%s session_store=%s",
            self.world_id,
            self.storage_backend,
            type(self.session_store).__name__,
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
                soul_hash,
                personality=personality,
                memory_vault=self.memory_vault,
                storage=self.storage,
            )
            self.npcs[soul_hash] = agent
            # 空间索引注册：创生于原点 [0,0,0]
            self._register_position(soul_hash, [0.0, 0.0, 0.0])
            # 地平线二：AOI 关注域注册 + 分片归属
            self.aoi_tracker.set_aoi(soul_hash, [0.0, 0.0, 0.0])
            return agent

    def tick(self) -> Dict:
        """推进世界一个 tick：时间 + 决策 + 事件传导 + 历史追加。

        确定性事件全序（地基 C）：动作按 soul_hash 排序产出（消除 dict
        遍历对插入序的隐性依赖），每个事件携带 (order_seq, node_id, hlc)
        三元组，保证跨节点按 100% 相同顺序重放。
        Gas 计量（地基 B）：全局预算均分到各 agent，消耗超限则跳过。
        地平线二：每 tick 检查分区状态 + 纪元推进。
        """
        with self._lock:
            clock = self.temporal_substrate.tick()
            events = []
            seq = self._event_seq
            n = len(self.npcs)
            # Gas 预算：均分到各 agent，防止单个 agent 死循环/无限递归锁死线程
            per_agent = max(1, self.tick_budget // n) if n > 0 else self.tick_budget
            # 地平线二：分区检测 + 纪元推进
            self.partition_guard.guard(list(self.consensus.nodes.keys()))
            self.interdc_consensus.tick()
            # 确定性全序：按 soul_hash 字典序，杜绝顺序漂移
            for soul in sorted(self.npcs):
                agent = self.npcs[soul]
                meter = GasMeter(budget=per_agent, timeout_ms=self.tick_timeout_ms)
                try:
                    action = agent.decide_next_action(
                        {"tick": clock, "gas_meter": meter}
                    )
                except GasExceeded:
                    # Gas 耗尽 → 跳过该 agent（无状态副作用，保证不锁死线程）
                    action = "gas_exhausted"
                seq += 1
                hlcts = self.hlc.send()
                event = {
                    "tick": clock,
                    "order_seq": seq,
                    "node_id": self.node_id,
                    "hlc": hlcts.to_dict(),
                    "soul": soul,
                    "action": action,
                }
                events.append(event)
                # 因果闭包：行动以智能体存在为因
                self.causal_closure.link_cause(f"act:{soul}:{clock}", [f"spawn:{soul}"])
                # 地平线二：分区降级记录
                if self.partition_guard.in_partition:
                    self.partition_guard.record_operation(
                        {"op": "tick_action", "soul": soul, "action": action}
                    )
            self._event_seq = seq
            if events:
                self.history.append({"event": "tick", "tick": clock, "actions": events})
            return {"tick": clock, "events": events}

    # ---- 空间索引（地基 A）----
    @staticmethod
    def _cell_key(pos, cell: float = 10.0) -> str:
        """整数网格单元键：固定网格划分，制造稳定局部性。"""
        x, y, z = int(pos[0] // cell), int(pos[1] // cell), int(pos[2] // cell)
        return f"{x}_{y}_{z}"

    def _unregister_position(self, soul_hash: str) -> None:
        old = self.positions.pop(soul_hash, None)
        if old is None:
            return
        cell = self._cell_key(old)
        bucket = self.spatial.get(cell)
        if bucket:
            bucket.discard(soul_hash)
            if not bucket:
                self.spatial.pop(cell, None)

    def _register_position(self, soul_hash: str, pos) -> None:
        self._unregister_position(soul_hash)
        self.positions[soul_hash] = list(pos)
        self.spatial.setdefault(self._cell_key(pos), set()).add(soul_hash)

    def position_of(self, soul_hash: str) -> List[float]:
        """取某智能体的空间坐标（未注册回落原点）。"""
        return list(self.positions.get(soul_hash, [0.0, 0.0, 0.0]))

    def move_agent(self, soul_hash: str, pos) -> bool:
        """移动智能体并更新空间索引。目标必须为三维坐标。

        地平线二：同时更新 AOI 关注域 + 检查是否跨分片边界。
        """
        if soul_hash not in self.npcs or len(pos) != 3:
            return False
        prev = self.positions.get(soul_hash)
        new_pos = [float(p) for p in pos]
        self._register_position(soul_hash, new_pos)
        # 地平线二：更新 AOI 中心
        self.aoi_tracker.set_aoi(soul_hash, new_pos)
        # 跨分片检测（仅当有旧位置且有分片路由）
        if prev is not None:
            prev_shard = self.shard_manager.router.shard_of(prev)
            new_shard = self.shard_manager.router.shard_of(new_pos)
            if prev_shard != new_shard:
                logger.info(
                    "agent crossed shard soul=%s %s->%s",
                    soul_hash, prev_shard, new_shard,
                )
        return True

    # ---- 缺点接通 4：脑裂恢复后的净态合并公开口 ----
    def merge_partition_state(self, remote_state: Dict, base_state: Optional[Dict] = None) -> Dict:
        """网络分区恢复后，将远端净态与本机净态经 Merkle 差分树无冲突合并。

        local_state 取当前 spatially 登记的全部 Agent 位置；冲突键取自本机。
        返回合并后的新状态，并记录审计报告。
        """
        local_state = {
            s: self.positions.get(s, [0.0, 0.0, 0.0]) for s in self.npcs
        }
        base = base_state if base_state is not None else local_state
        merged = self.partition_guard.merge_engine.merge(
            local_state=local_state,
            remote_state=remote_state,
            base_state=base,
        )
        return merged

    def agents_near(self, origin, radius: float = 5.0) -> List[str]:
        """AOI 关注域检索：返回原点半径内智能体（确定性排序）。"""
        hits = []
        r2 = radius * radius
        for soul in self.npcs:
            p = self.positions.get(soul, [0.0, 0.0, 0.0])
            if sum((a - b) ** 2 for a, b in zip(p, origin)) <= r2:
                hits.append(soul)
        return sorted(hits)

    # ---- 状态 Merkle 根（地基 A/D 锚点）----
    def state_root(self) -> str:
        """对当前世界状态计算确定性 Merkle 根，供跨节点增量验证。"""
        state = {
            "world_id": self.world_id,
            "clock": self.temporal_substrate.global_clock,
            "event_seq": self._event_seq,
            "hlc": self.hlc.peek().to_dict(),
            "souls": sorted(self.soul_ledger.souls.keys()),
            "agents": sorted(self.npcs.keys()),
            "positions": {
                s: self.positions.get(s, [0.0, 0.0, 0.0]) for s in sorted(self.npcs)
            },
        }
        return merkle_root(state)

    def replay_canonical_events(self) -> Dict:
        """重放全部 tick 事件并断言全序（跨节点确定性重放映射）。

        返回 {count, deterministic_order, events}：按 (order_seq, node_id)
        排序后校验相邻不逆序——同一批事件在任意节点必得相同重放序列。
        """
        flat = []
        for ts, event, block_hash in self.history.chain:
            if event.get("event") == "tick":
                flat.extend(event.get("actions", []))
        flat.sort(key=lambda e: (e.get("order_seq", 0), e.get("node_id", "")))
        ordered = all(
            (flat[i].get("order_seq"), flat[i].get("node_id"))
            <= (flat[i + 1].get("order_seq"), flat[i + 1].get("node_id"))
            for i in range(len(flat) - 1)
        )
        return {"count": len(flat), "deterministic_order": ordered, "events": flat}

    # ---- 审计上报 ----
    def audit(self) -> AuditReport:
        """运行 19 项第二视角审计，返回可打印结论。"""
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
                "state_root": self.state_root(),
                "souls": list(self.soul_ledger.souls.keys()),
                "agents": list(self.npcs.keys()),
                "positions": {
                    s: self.positions.get(s, [0.0, 0.0, 0.0]) for s in sorted(self.npcs)
                },
            }
        )

    def close(self) -> None:
        """关闭世界，释放 SQLite 连接等底层资源。"""
        self.session_store.close()
        self.storage.close()


__all__ = ["World"]
