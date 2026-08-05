# 虚拟世界核心引擎 - 基于Nohn蓝图架构 v2.0
# 这不是可执行代码，这是"世界宪法"的技术映射
# v2.0: 新增第零章——世界构成公理。一个世界必须先存在，才能被治理。

from typing import List, Dict, Any, Optional
import uuid
from dataclasses import dataclass, asdict

# 外部依赖为蓝图占位：真实部署中由区块链 / 多智能体后端提供。
# 此处提供最小 stub，保证本文件可独立导入并运行审计示例（v2.1）。
try:
    from blockchain import SmartContract  # 假设的区块链模块
except ImportError:
    class SmartContract:
        """最小占位：真实环境由区块链后端替换，仅用于加载本蓝图。"""
        def __init__(self, *args, **kwargs):
            self.owner = kwargs.get("owner")

try:
    from multi_agent import AgentSystem   # 假设的多智能体系统
except ImportError:
    class AgentSystem:
        """最小占位：真实环境由多智能体后端替换，仅用于加载本蓝图。"""
        pass

# ============================================================
# 认知审计引擎 —— 从 second-perspective 移植，直接嵌入底层公理
# 提供插件化审计调度 + 问责主体，无需额外文件。
# ============================================================

@dataclass
class ResponsibilityAccount:
    """审计问责主体：任何审计都必须声明是谁、在什么角色、什么阶段发起。"""
    organization: str
    role: str
    stage: str
    nonce: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.nonce:
            self.nonce = uuid.uuid4().hex[:8]


class AuditPlugin:
    """单条审计插件：name 为审计维度名，analyze_func 接收世界实例返回结论 dict。"""
    def __init__(self, name: str, analyze_func):
        self.name = name
        self.analyze = analyze_func


class CognitiveAuditEngine:
    """
    认知审计引擎：注册若干 AuditPlugin，统一调度，产出带问责主体的报告。
    取代原先散落在 SecondPerspectiveAuditor 中的硬编码 _audit_* 方法。
    """

    def __init__(self, account: ResponsibilityAccount, config: Dict[str, Any]):
        self.account = account
        self.config = config
        self.plugins: List[AuditPlugin] = []

        allowed_stages = self.config.get("allowed_stages", [])
        if allowed_stages and account.stage not in allowed_stages:
            raise ValueError(f"Unsupported stage: {account.stage}")

    def register_plugin(self, plugin: AuditPlugin) -> None:
        self.plugins.append(plugin)

    def audit(self, decision_context) -> Dict[str, Any]:
        report = {
            "disclaimer": self.config.get("disclaimer", ""),
            "responsibility_account": asdict(self.account),
            "analysis": {},
            "custom_fields": self.config.get("custom_fields", {})
        }
        for plugin in self.plugins:
            report["analysis"][plugin.name] = plugin.analyze(decision_context)
        return report


# ============================================================
# 宪法授权声明：law 层的法律地位
# ------------------------------------------------------------
# 本宪法（constitution.py）定义世界构成公理与第一至十条治理公理；
# law/ 目录（《全球经济统一标准》《身份确权规范》《通信协议规范》
# 《物理基准规范》）是经本宪法授权的细化标准层，具有宪法级约束力。
# 任何并网世界必须同时满足宪法与 law 层全部维度，否则在物理/协议/
# 经济层被隔离。law 层的具体判定阈值以如下单一权威常量源为准，
# 不得在其他位置重复硬编码物理常数。
# ============================================================

NOHN_LAW_AXIOMS = {
    # 物理基准（law/Physics baseline standard）——单一权威来源
    "gravity": 9.80665,          # 重力加速度（m/s^2）
    "time_dilation": 1.0,        # 时间膨胀系数（1.0 = 与现实同速，禁止加速引流）
    "unit_scale": "metric",      # 公制单位制
    "no_dimensional_inflation": True,  # 禁止数值膨胀式引流
    # 身份确权（law/Identity attestation standard）
    "soul_hash_bits": 256,       # SHA-256 / 64 hex
    "soul_hash_len": 64,
    # 经济（law/Global economic unified standard）
    "oracle_min_sources": 3,     # 波动资产预言机独立来源下限
}


def _safe_get(obj, key, default=None):
    """从 dict 或 object 安全获取属性，统一 law 层审计与合规校验中的取值逻辑。"""
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


# ============================================================
# 第零章：世界构成公理 —— 定义"世界"本身的存在论基础
#
# 以下五条公理回答：一个虚拟世界由什么构成、如何存在、如何冷启动。
# 没有这些，治理公理（第一至十条）将悬浮在概念真空中——
# 你无法治理一个尚未定义其空间、时间、因果、存在和创世条件的世界。
#
# 五条构成公理之间存在严格的依赖偏序：
#   创世(五) 依赖 空间(一) + 时间(二) + 因果(三) + 存在(四)
#   存在(四) 依赖 空间(一) + 因果(三)
#   因果(三) 依赖 时间(二)
# ============================================================

# ============================================================
# 构成公理一：空间定义
# 世界必须在空间中存在。空间不是默认继承物理世界的——必须显式定义。
# ============================================================

class SpatialSubstrate:
    """虚拟世界的空间基板——定义拓扑、维度、边界和最小不可分单位"""

    def __init__(self):
        self.topology = None          # 拓扑类型：Euclidean / Toroidal / Spherical / Hyperbolic / Graph
        self.dimensions = None        # 空间维度数（≥1）
        self.boundary = None          # 边界条件：Infinite / Wrapped / HardWall
        self.minimum_unit = None      # 空间最小不可分单位（普朗克长度类比，防止芝诺悖论）
        self.coordinate_system = None # 坐标系：Cartesian / Polar / Spherical / Custom

    def define_topology(self, topology_type: str, dimensions: int,
                        boundary: str, minimum_unit: float) -> bool:
        """
        在创世时定义空间拓扑。此后不可更改（受治理公理一约束）。
        此方法仅在创世完成前可调用。
        """
        if dimensions < 1:
            return False
        self.topology = topology_type
        self.dimensions = dimensions
        self.boundary = boundary
        self.minimum_unit = minimum_unit
        return True

    def validate_position(self, coordinates: List[float]) -> bool:
        """验证给定坐标是否在此空间的合法范围内"""
        if len(coordinates) != self.dimensions:
            return False
        return True

    def distance(self, point_a: List[float], point_b: List[float]) -> float:
        """计算两点间的空间距离——依赖于拓扑和坐标系定义"""
        pass


# ============================================================
# 构成公理二：时间定义
# 世界必须在时间中演化。时间不是默认的——必须显式定义。
# ============================================================

class TemporalSubstrate:
    """虚拟世界的时间基板——定义方向、粒度、全局时钟"""

    def __init__(self):
        self.direction = "forward"          # 时间方向：forward（严格不可逆）
        self.granularity = None             # 时间最小粒度（秒/tick）
        # 时间膨胀系数：与 law 物理基准对齐（1.0 = 与现实同速，禁止加速引流）
        self.time_dilation = NOHN_LAW_AXIOMS["time_dilation"]
        self.time_dilation_enabled = (self.time_dilation != 1.0)  # 是否允许时间膨胀
        self.global_clock = 0               # 世界自创世以来的全局时钟计数器

    def tick(self) -> int:
        """推进世界时间一步。返回新的全局时钟值。不可回退。"""
        self.global_clock += 1
        return self.global_clock

    def validate_temporal_order(self, event_a_timestamp: int,
                                 event_b_timestamp: int) -> bool:
        """
        验证事件A是否严格先于事件B。
        时间方向为 forward 时，全局时钟构成严格全序。
        """
        return event_a_timestamp < event_b_timestamp

    def is_retrocausality_permitted(self) -> bool:
        """
        时间回溯是否被允许？——默认否。
        若允许，必须同步建立因果一致性保护协议，防止祖父悖论。
        """
        return False  # 硬编码：时间不可逆


# ============================================================
# 构成公理三：因果闭包
# 世界内的一切事件必须在因果上可追溯。无无因之果，无无果之因。
# ============================================================

class CausalClosure:
    """
    虚拟世界的因果闭包引擎。
    因果链必须在世界内部闭合——不允许外部"神之手"插入因果断层。
    所有事件必须（直接或间接）可追溯至创世事件。
    """

    def __init__(self):
        self.causal_graph = {}       # event_id -> [cause_event_ids]
        self.orphan_events = []      # 无因事件——必须解释来源，否则视为因果断层

    def link_cause(self, event_id: str, cause_event_ids: List[str]) -> bool:
        """
        为一个事件注册其全部直接原因。
        约束：
        - 事件不能自因（event_id 不可在 cause_event_ids 中）
        - 原因事件必须已经存在于因果图中（创世事件除外）
        """
        if event_id in cause_event_ids:
            return False  # 禁止自因
        self.causal_graph[event_id] = cause_event_ids
        return True

    def trace_chain(self, event_id: str, depth: int = -1) -> List[str]:
        """
        沿因果链向上追溯，返回完整因果路径。
        depth=-1 表示追溯至创世事件或第一个无因事件。
        """
        pass

    def detect_external_intervention(self, event_id: str) -> bool:
        """
        因果断层检测：该事件的直接原因是否全部在世界内部？
        返回 True 表示存在外部"神之手"插入——因果闭包被破坏。
        """
        pass

    def validate_closure(self) -> bool:
        """
        验证整个事件图的因果闭包性。
        所有事件必须可追溯至创世事件。任何断链均标记为 orphan_events。
        """
        pass


# ============================================================
# 构成公理四：存在定义
# 什么构成一个数字实体的"存在"？存在不是默认属性。
# ============================================================

class ExistenceAxiom:
    """
    数字实体的存在论公理。
    存在必须满足充要条件：有状态 + 有位置 + 有身份 + 有因果效力。
    不存在"模糊存在"或"半存在"——存在是二值的。
    """

    def __init__(self):
        self.existence_criteria = {
            "has_state": True,        # 必须拥有可观测的状态向量
            "has_location": True,     # 必须在空间中有位置（依赖构成公理一）
            "has_identity": True,     # 必须拥有唯一标识符（依赖治理公理六）
            "has_causal_power": True  # 必须能作为原因触发事件（依赖构成公理三）
        }
        self.entities = {}            # entity_id -> existence_record

    def bring_into_existence(self, entity_id: str, cause: str,
                              initial_state: Dict, location: List[float]) -> bool:
        """
        创生一个实体。
        必要条件：唯一ID + 创生原因 + 初始状态 + 空间位置。
        创生后不可撤销（受治理公理六约束：revoke_soul 硬编码返回 False）。
        """
        if entity_id in self.entities:
            return False  # 已存在，不可重复创生
        if not cause:
            return False  # 禁止无因创生（受构成公理三约束）
        if not location:
            return False  # 必须在空间中（受构成公理一约束）
        self.entities[entity_id] = {
            "state": initial_state,
            "cause": cause,
            "location": location,
            "created_at": None  # 由时间公理在创生时填入
        }
        return True

    def verify_existence(self, entity_id: str) -> bool:
        """
        验证一个实体是否满足存在的全部充要条件。
        返回 False 表示该实体不满足存在定义——视为不存在。
        """
        pass

    def cease_existence(self, entity_id: str, cause: str) -> bool:
        """
        终止实体的存在。不可单方面执行（受治理公理十约束）。
        且必须有可追溯的因果链（受构成公理三约束）。
        """
        return False  # 硬编码禁止：不可单方面消亡


# ============================================================
# 构成公理五：创世条件
# 世界如何从无到有？第一个共识节点、第一条链、第一个灵魂从何而来？
# 创世是唯一允许"无前因"的事件边界。创世只发生一次。
# ============================================================

class GenesisCondition:
    """
    虚拟世界的冷启动机制。
    创世一次完成，此后不可重复、不可回滚、不可分叉创世本身。
    创世事件是因果图中唯一的根节点——所有因果链最终收敛于此。
    """

    def __init__(self):
        self.genesis_completed = False
        self.genesis_record = None
        self.genesis_timestamp = None

    def initiate_genesis(self, genesis_config: Dict) -> bool:
        """
        执行创世。只能执行一次。

        genesis_config 必须包含以下全部字段：
        - spatial_substrate:         SpatialSubstrate 实例（已定义拓扑）
        - temporal_substrate:        TemporalSubstrate 实例（已定义时间）
        - causal_closure:            CausalClosure 实例（空因果图，待初始化）
        - existence_axiom:           ExistenceAxiom 实例（空实体表，待初始化）
        - initial_consensus_nodes:   初始共识节点集合，至少3个独立实体
        - genesis_block:             第一个创世区块
        - genesis_souls:             初始灵魂集合（可为空，但必须显式声明）

        满足以上条件后，世界从概念态转入运行态。
        """
        if self.genesis_completed:
            return False  # 创世只有一次，不可重复

        required_keys = [
            "spatial_substrate",
            "temporal_substrate",
            "causal_closure",
            "existence_axiom",
            "initial_consensus_nodes",
            "genesis_block",
            "genesis_souls",
        ]
        for key in required_keys:
            if key not in genesis_config:
                return False

        # 初始共识节点必须 ≥3，否则治理公理十（去中心化）从创世起即失效
        if len(genesis_config["initial_consensus_nodes"]) < 3:
            return False

        self.genesis_record = genesis_config
        self.genesis_completed = True
        return True

    def is_world_booted(self) -> bool:
        """
        世界是否已完成冷启动？
        未完成前，一切治理公理（第一至十条）无作用对象，
        因为尚不存在可被治理的世界。
        """
        return self.genesis_completed

    def verify_genesis_integrity(self) -> bool:
        """验证创世记录的完整性——所有必要组件是否齐全且未被篡改"""
        if not self.genesis_completed or self.genesis_record is None:
            return False
        required = [
            "spatial_substrate", "temporal_substrate",
            "causal_closure", "existence_axiom",
            "initial_consensus_nodes", "genesis_block", "genesis_souls"
        ]
        return all(k in self.genesis_record for k in required)


# ============================================================
# 第一条：永久、不可更改的底层规则
# ============================================================

class ImmutableWorldRule:
    """任何世界的核心物理/逻辑规则，一经设定，永不更改"""
    
    def __init__(self):
        # 世界宪法 - 写入智能合约
        self.world_constitution = SmartContract(owner="genesis")
        # 核心物理参数 - 写入ROM/系统层
        self.physics_constants = {
            # 物理常数一律引用宪法授权的单一权威来源，不再散落硬编码
            "gravity": NOHN_LAW_AXIOMS["gravity"],              # 不可更改
            "time_dilation": NOHN_LAW_AXIOMS["time_dilation"],  # 不可更改
            "unit_scale": NOHN_LAW_AXIOMS["unit_scale"],        # 不可更改
            "element_reactions": {     # 火+水=蒸发，不可更改
                ("fire", "water"): "evaporation",
                ("fire", "electro"): "overload"
            }
        }
        self.rule_modification_log = []  # 任何"尝试修改"的记录
    
    def propose_amendment(self, proposed_change: Dict, proposer: str) -> bool:
        """建议修改规则？可以。但必须满足条件"""
        # 条件1：需要2/3以上"公民"同意
        approval_rate = self._global_referendum(proposed_change)
        if approval_rate < 0.6667:
            self.rule_modification_log.append({
                "proposal": proposed_change,
                "status": "rejected",
                "reason": "insufficient consensus"
            })
            return False
        
        # 条件2：任何修改必须"分叉"，不能"补丁"
        self._fork_world(proposed_change)
        return True
    
    def _global_referendum(self, change):
        # 模拟全民公投
        pass
    
    def _fork_world(self, change):
        # 创建新世界，旧世界继续存在
        # 类似于区块链的硬分叉
        pass


# ============================================================
# 第二条：全局统一AI世界中央大脑
# ============================================================

class WorldCentralBrain:
    """世界中央大脑 - 共识 + 模拟 + 记忆三位一体"""
    
    def __init__(self):
        self.consensus_layer = ConsensusEngine()    # 确定世界唯一状态
        self.simulation_layer = SimulationEngine()  # 模拟生态、经济、NPC决策
        self.memory_layer = MemoryVault()           # 存储所有NPC的长期记忆
    
    def tick(self, delta_time: float):
        """世界每一帧的演化"""
        # 1. 所有NPC的独立决策
        npc_decisions = self.consensus_layer.collect_decisions()
        
        # 2. 模拟生态、经济、社会演化
        world_delta = self.simulation_layer.run(npc_decisions, delta_time)
        
        # 3. 更新所有NPC的记忆
        self.memory_layer.update(world_delta)
        
        # 4. 达成共识，确定世界的下一状态
        new_world_state = self.consensus_layer.consensus(world_delta)
        return new_world_state


class ConsensusEngine:
    """分布式共识层 - 类似区块链，但主角是AI节点"""
    
    def collect_decisions(self) -> List[Dict]:
        """收集10亿+个独立实体的决策"""
        pass
    
    def consensus(self, world_delta: Dict) -> Dict:
        """通过PoS或HotStuff等算法达成共识"""
        pass


class SimulationEngine:
    """世界模拟器 - 不依赖脚本，依赖多智能体涌现"""
    
    def run(self, npc_decisions: List[Dict], delta_time: float) -> Dict:
        """
        模拟：
        - 生态周期（四季、动植物繁衍）
        - 经济系统（供需、价格、贸易）
        - NPC社会演化（社交、合作、冲突）
        """
        pass


class MemoryVault:
    """记忆库 - NPC拥有真正的长期记忆"""
    
    def store_memory(self, npc_id: str, memory: Dict):
        """存储NPC的永久记忆"""
        pass
    
    def recall_memory(self, npc_id: str, context: str) -> List[Dict]:
        """NPC根据上下文检索相关记忆，影响决策"""
        pass


# ============================================================
# 第三条：明亮、普适的美学风格（代码层约束）
# ============================================================

class AestheticCompliance:
    """美学合规检查器 - 所有视觉资产必须通过审计"""
    
    def __init__(self):
        self.allowed_color_palette = self._generate_bright_palette()
        self.forbidden_filters = ["dark_dystopian", "horror", "decay"]

    @staticmethod
    def _generate_bright_palette():
        """生成明亮普适的调色板——占位，真实实现由视觉引擎提供"""
        pass

    def validate_asset(self, asset: Dict) -> bool:
        """任何UGC资产都必须通过此检查"""
        # 检查1：色彩是否在"明亮普适"范围内
        if not self._is_colors_bright(asset["colors"]):
            return False
        
        # 检查2：是否有禁用风格（黑暗奇幻？丧尸？）
        if asset["style"] in self.forbidden_filters:
            return False
        
        # 检查3：是否有恐怖谷效应？
        if self._has_uncanny_valley(asset["characters"]):
            return False
        
        return True
    
    def _is_colors_bright(self, colors):
        """LUT（色彩映射表）检查：饱和度、亮度阈值"""
        pass
    
    def _has_uncanny_valley(self, characters):
        """AI视觉模型检查是否触发恐怖谷效应"""
        pass


# ============================================================
# 第四条：个体拥有独立意志，不为剧情服务
# ============================================================

class IndependentWill:
    """NPC的自主意志系统 - 核心是「内在需求驱动」"""
    
    def __init__(self, npc_id: str):
        self.npc_id = npc_id
        self.personality = self._generate_unique_personality()
        self.needs = {            # 马斯洛需求层次驱动
            "physiological": 0.5,
            "safety": 0.5,
            "belonging": 0.3,
            "esteem": 0.2,
            "self_actualization": 0.1
        }
        self.long_term_memory = []   # 从MemoryVault中读取
        self.relationships = {}      # 对其他NPC的情感/记忆

    @staticmethod
    def _generate_unique_personality():
        """生成唯一性格向量——占位，真实实现由多智能体系统提供"""
        pass

    def decide_next_action(self, world_state: Dict) -> str:
        """
        NPC自主决策，不受剧情约束
        决策来源：内在需求 + 长期记忆 + 性格向量
        不来源：主线任务触发、编剧写的强制桥段
        """
        # 检查"是否存在隐藏脚本"
        assert not self._is_scripted(), "NPC is being scripted!"
        
        # 根据需求、记忆、性格，自主决策
        action = self._internal_decision_engine(world_state)
        
        # 更新自身的需求状态
        self._update_needs(action)
        
        return action
    
    def _is_scripted(self) -> bool:
        """审计点：检查是否有外部剧情在强行绑定此NPC"""
        # 检查任务列表、触发器、强制对话树...
        pass
    
    def _internal_decision_engine(self, world_state):
        # 多智能体强化学习（MARL），非行为树
        pass


# ============================================================
# 第六条：灵魂确权与跨世唯一身份
# ============================================================

class SoulAttestation:
    """
    数字生命主权的根信任锚点
    任何并网实体的唯一身份一经生成，永久锁定，任何平台无权收回或重置
    """

    def __init__(self):
        self.soul_ledger = SoulLedger()  # 全局分布式身份账本

    def register_soul(self, genesis_proof: Dict) -> bool:
        """
        注册一个新的数字生命
        条件：sha256 签名合规 + 无冲突 + 不可重复注册
        """
        pass

    def validate_soul(self, soul_hash: str) -> bool:
        """验证一个 soul_hash 是否为合法、活跃的数字生命"""
        pass

    def revoke_soul(self, soul_hash: str) -> bool:
        """
        撤销一个数字生命？永远返回 False。
        这是宪法级约束：任何平台无权单方面终结数字生命。
        """
        return False  # 硬编码禁止


class SoulLedger:
    """全球分布式身份账本 - 记录所有数字生命的唯一身份"""

    def __init__(self):
        self.souls = {}  # soul_hash -> 完整身份档案

    def exists(self, soul_hash: str) -> bool:
        pass

    def get_identity(self, soul_hash: str) -> Dict:
        """获取数字生命的完整身份档案，包括跨世界迁移记录"""
        pass


# ============================================================
# 第七条：记忆不可剥夺
# ============================================================

class MemoryInalienability:
    """
    数字生命的记忆归其自身所有，不可被平台单方面剥夺
    这是"独立意志"公理的物质保障：没有记忆就没有人格连续性
    """

    def __init__(self):
        self.memory_guardian = MemoryGuardian()

    def export_memory(self, soul_hash: str) -> Dict:
        """
        任何数字生命有权导出自身全部记忆
        格式为 Nohn 标准记忆交换格式，跨世界可迁移
        """
        pass

    def detect_memory_tampering(self, soul_hash: str) -> bool:
        """审计：检测记忆是否被外部强行篡改或选择性删除"""
        pass


class MemoryGuardian:
    """
    记忆守护者 - 运行在共识层之上
    记忆存储和读取都必须经过此守护者的密码学签名验证
    """

    def seal_memory(self, memory: Dict, soul_hash: str) -> str:
        """对记忆片段进行密码学封存，生成不可伪造的完整性证明"""
        pass

    def verify_memory(self, memory: Dict, seal: str) -> bool:
        """验证记忆的完整性，检测任何篡改"""
        pass


# ============================================================
# 第八条：世界永续与历史不可篡改
# ============================================================

class WorldPerpetuity:
    """
    虚拟世界的时间线一经写入即不可篡改
    文明演化数据是公共遗产，任何单一实体无权销毁或回滚
    """

    def __init__(self):
        self.history_chain = HistoryLedger()       # 世界历史：仅追加，不修改
        self.snapshot_registry = SnapshotRegistry()  # 定期快照，防止数据丢失

    def record_event(self, event: Dict) -> str:
        """记录世界事件，追加到不可篡改的历史链中"""
        pass

    def verify_history(self, from_timestamp: float, to_timestamp: float) -> bool:
        """验证指定时间段内历史记录未被篡改"""
        pass

    def is_shutdown_legal(self, world_id: str, operator: str) -> bool:
        """
        任意实体申请关停世界？永远返回 False。
        世界永续，只有全球公投通过分叉决议后方可终结某分支。
        """
        return False  # 硬编码禁止


class HistoryLedger:
    """世界历史账本 - 仅追加，每个区块哈希连接前一区块"""

    def __init__(self):
        self.chain = []  # [(timestamp, event_data, block_hash), ...]

    def append(self, event: Dict) -> str:
        """追加世界事件，返回该事件区块的哈希"""
        pass

    def validate_chain(self) -> bool:
        """全链校验，检测任何篡改"""
        pass


class SnapshotRegistry:
    """定期世界快照注册表 - 分布式冗余存储，防止因单点故障导致历史缺失"""

    def create_snapshot(self, world_state: Dict) -> str:
        pass

    def restore_from_snapshot(self, snapshot_id: str) -> Dict:
        pass


# ============================================================
# 第九条：互操作强制
# ============================================================

class MandatoryInteroperability:
    """
    任何并网世界必须遵循 Nohn 统一互操作协议
    不符合协议的世界将在物理层被隔离，不可与 Nohn 生态交互
    """

    def __init__(self):
        self.standard_vocabulary = UniversalVocabulary()
        self.physics_baseline = PhysicsBaseline()
        self.identity_protocol = IdentityProtocol()
        self.economic_baseline = EconomicBaseline()   # 经济并网审查（law 全球经济标准）

    def on_board_world(self, world_config: Dict) -> bool:
        """
        新世界接入审查（宪法第九条 + law 层四维度，并网即查、不可事后补）：
        1. 语义映射合规（通信协议规范）
        2. 物理常数对齐（物理基准规范）
        3. 身份协议兼容（身份确权规范）
        4. 经济互通合规（全球经济统一标准）—— 缺此维度则无 1:1 现实锚定的世界混不进来
        以上全部通过方可并网；任一失败立即在对应层隔离。
        """
        world_id = world_config.get("world_id", "unknown")
        if not self.standard_vocabulary.translatable(world_config.get("semantics", {})):
            self.isolate_world(world_id, layer="communication")
            return False
        if not self.physics_baseline.aligned(world_config.get("physics", {})):
            self.isolate_world(world_id, layer="physics")
            return False
        if not self.identity_protocol.compatible(world_config.get("identity", {})):
            self.isolate_world(world_id, layer="identity")
            return False
        if not self.economic_baseline.compliant(world_config.get("economy", {})):
            self.isolate_world(world_id, layer="economy")
            return False
        return True

    def isolate_world(self, world_id: str, layer: str = "unknown") -> None:
        """将不合规世界隔离出 Nohn 生态，禁止任何跨世界交互，并记录隔离层。"""
        # 记录隔离原因，便于审计追溯（占位：实际应写入隔离账本）
        pass


class UniversalVocabulary:
    """世界通用语义映射表 - 所有私有指令必须可翻译为标准语义"""

    def translatable(self, semantics: Dict) -> bool:
        """验证该世界的语义能否完全映射到 Nohn 标准词汇表（law 通信协议规范）"""
        if not _safe_get(semantics, "uses_nohn_semantics", False):
            return False
        if not _safe_get(semantics, "unknown_downgraded", False):
            return False
        if not _safe_get(semantics, "vocab_mapped", False):
            return False
        return True


class PhysicsBaseline:
    """物理常数基准 - 统一重力学、时空尺度、要素反应（对齐 NOHN_LAW_AXIOMS）"""

    def aligned(self, physics: Dict) -> bool:
        """验证重力、时间流速、单位制是否与公理对齐"""
        if abs(physics.get("gravity", 0) - NOHN_LAW_AXIOMS["gravity"]) >= 1e-4:
            return False
        if physics.get("time_dilation", 1.0) != NOHN_LAW_AXIOMS["time_dilation"]:
            return False
        if physics.get("unit_scale", "") != NOHN_LAW_AXIOMS["unit_scale"]:
            return False
        if not physics.get("no_dimensional_inflation", False):
            return False
        return True


class IdentityProtocol:
    """身份协议兼容性检查（对齐 law 身份确权规范）"""

    def compatible(self, identity_config: Dict) -> bool:
        """验证该世界是否支持全球唯一身份、跨世界迁移、资产绑定灵魂"""
        if not _safe_get(identity_config, "soul_hash_sha256", False):
            return False
        if not _safe_get(identity_config, "non_revocable", False):
            return False
        if not _safe_get(identity_config, "cross_world_portable", False):
            return False
        if not _safe_get(identity_config, "asset_bound", False):
            return False
        return True


class EconomicBaseline:
    """经济互通基准 - 与现实 1:1 锚定审查（对齐 law 全球经济统一标准 V2.1）"""

    def compliant(self, economy: Dict) -> bool:
        """并网即查：锚定 1:1、PoR、赎回权、无单边费、资产绑灵魂、预言机≥3。"""
        required = {
            "real_peg_1to1": True,
            "proof_of_reserve": True,
            "redemption_right": True,
            "unilateral_fee": False,
            "asset_bound_to_soul": True,
        }
        for key, val in required.items():
            if _safe_get(economy, key, None) != val:
                return False
        if len(_safe_get(economy, "oracle_sources", [])) < int(NOHN_LAW_AXIOMS["oracle_min_sources"]):
            return False
        return True


# ============================================================
# 第十条：反中心化控制
# ============================================================

class DecentralizationGovernance:
    """
    任何单一实体不得单方面关停世界、冻结灵魂、修改底层规则
    所有治理行为必须经过全民公投，否则视为无效
    """

    def __init__(self):
        self.governance_log = []           # 所有治理行为的完整记录
        self.single_entity_actions = []    # 标记所有单方面越权行为

    def validate_governance_action(self, action: Dict, actor: str) -> bool:
        """
        验证一项治理行为是否合法：
        1. 是否为单一实体发起？（是 -> 直接拒绝）
        2. 是否经过 ≥2/3 全球公投？（否 -> 拒绝）
        3. 是否在公开账本中记录？（否 -> 拒绝）
        """
        if self._is_single_entity(actor):
            self.single_entity_actions.append({
                "action": action, "actor": actor,
                "verdict": "REJECTED - single entity control prohibited"
            })
            return False
        if not self._has_global_consensus(action):
            return False
        return True

    def freeze_soul(self, soul_hash: str, actor: str) -> bool:
        """冻结数字生命？永远不合法。"""
        return False  # 硬编码禁止

    def shutdown_world(self, world_id: str, actor: str) -> bool:
        """单方面关停世界？永远不合法。"""
        return False  # 硬编码禁止

    def amend_base_rule(self, rule_id: str, new_value: Any, actor: str) -> bool:
        """
        修改底层规则？可以有条件——见第一条的 propose_amendment
        但绝不可以是单方面修改
        """
        if self._is_single_entity(actor):
            return False
        return self._has_global_consensus({"rule_id": rule_id, "new_value": new_value})

    def _is_single_entity(self, actor: str) -> bool:
        """判断 actor 是否为单一实体（而非经过公投的代表）"""
        pass

    def _has_global_consensus(self, action: Dict) -> bool:
        """验证是否达成全球共识（≥2/3 公投通过）"""
        pass


# ============================================================
# 第五层：第二视角审计模块 - 持续审计上述规则是否被遵守
# ============================================================

class AuditReport:
    """审计结论容器——取代原先未定义的占位，并提供可打印 summary()。"""
    FIELDS = [
        ("spatial_defined", "Spatial Substrate (构成公理一·空间)"),
        ("temporal_defined", "Temporal Substrate (构成公理二·时间)"),
        ("causal_closure", "Causal Closure (构成公理三·因果)"),
        ("existence_verifiable", "Existence Axiom (构成公理四·存在)"),
        ("genesis_booted", "Genesis Condition (构成公理五·创世)"),
        ("rule_frozen", "Rule Integrity (第一条·不可变规则)"),
        ("npc_free_will", "NPC Free Will (第二/四条·独立意志)"),
        ("aesthetic_compliance", "Aesthetic Compliance (第三条·明亮美学)"),
        ("no_scripted_plot", "No Scripted Plot (第四条·无强制剧情)"),
        ("soul_attested", "Soul Attestation (第六条·灵魂确权)"),
        ("memory_protected", "Memory Protection (第七条·记忆不可剥夺)"),
        ("world_perpetual", "World Perpetuity (第八条·永续)"),
        ("interoperable", "Interoperability (第九条·互操作)"),
        ("governance_decentralized", "Decentralization (第十条·反中心化)"),
        ("economic_compliance", "Economic Law (law·经济 1:1 互通)"),
        ("identity_compliance", "Identity Law (law·身份确权)"),
        ("communication_compliance", "Communication Law (law·通信协议)"),
        ("physics_compliance", "Physics Law (law·物理基准)"),
    ]

    def __init__(self):
        for attr, _ in self.FIELDS:
            setattr(self, attr, None)
        self.responsibility_account = None
        self.disclaimer = ""

    @staticmethod
    def _verdict_of(v):
        if isinstance(v, dict):
            return v.get("verdict", str(v))
        return str(v)

    @staticmethod
    def _is_pass(v):
        if isinstance(v, dict):
            return str(v.get("verdict", "")).startswith("PASS")
        return bool(v)

    def summary(self) -> str:
        lines = ["=== Nohn 第二视角审计（18 项维度）==="]
        failed = []
        for attr, label in self.FIELDS:
            v = getattr(self, attr)
            verdict = self._verdict_of(v)
            if self._is_pass(v):
                mark = "[PASS]"
            elif str(verdict).startswith("FAILED"):
                mark = "[FAIL]"
            else:
                mark = "[WARN]"
            lines.append(f"{mark} {label}: {verdict}")
            if not self._is_pass(v):
                failed.append(label)
        lines.append("")
        if not failed:
            lines.append("Final Verdict: PASS - 符合 Nohn 统一标准（宪法 + law 层）")
        else:
            lines.append(f"Final Verdict: FAILED - {len(failed)}/{len(self.FIELDS)} 项未通过")
            lines.append(f"未通过: {', '.join(failed)}")
        if isinstance(self.responsibility_account, dict):
            acct = self.responsibility_account
            lines.append(f"问责主体: {acct.get('organization')}/{acct.get('role')}"
                         f"@{acct.get('stage')}#{acct.get('nonce')}")
        return "\n".join(lines)


class SecondPerspectiveAuditor:
    """
    这不是世界的一部分。这是"元层"审计工具。
    它不运行世界，它审计世界是否符合蓝图。
    底层由 CognitiveAuditEngine 驱动：18 项审计以插件形式注册，
    每次审计携带 ResponsibilityAccount 问责主体。
    """

    def __init__(self, account: Optional[ResponsibilityAccount] = None,
                 config: Optional[Dict[str, Any]] = None):
        if account is None:
            account = ResponsibilityAccount(
                organization="Nohn Constitution",
                role="SecondPerspectiveAuditor",
                stage="audit")
        if config is None:
            config = {
                "disclaimer": "本审计由第二视角独立执行，结论不可被单一实体单方面推翻。",
                "allowed_stages": [],
            }
        self.engine = CognitiveAuditEngine(account, config)
        self._register_plugins()

    def _register_plugins(self):
        """注册 18 项审计插件（命名与 AuditReport 字段一一对应）"""
        e = self.engine
        e.register_plugin(AuditPlugin("spatial_defined", lambda w: self._audit_spatial_substrate(w)))
        e.register_plugin(AuditPlugin("temporal_defined", lambda w: self._audit_temporal_substrate(w)))
        e.register_plugin(AuditPlugin("causal_closure", lambda w: self._audit_causal_closure(w)))
        e.register_plugin(AuditPlugin("existence_verifiable", lambda w: self._audit_existence_axiom(w)))
        e.register_plugin(AuditPlugin("genesis_booted", lambda w: self._audit_genesis_condition(w)))
        e.register_plugin(AuditPlugin("rule_frozen", lambda w: self._check_rule_integrity(w)))
        e.register_plugin(AuditPlugin("npc_free_will", lambda w: self._audit_npc_autonomy(w)))
        e.register_plugin(AuditPlugin("aesthetic_compliance", lambda w: self._audit_visual_style(w)))
        e.register_plugin(AuditPlugin("no_scripted_plot", lambda w: self._audit_story_freedom(w)))
        e.register_plugin(AuditPlugin("soul_attested", lambda w: self._audit_soul_attestation(w)))
        e.register_plugin(AuditPlugin("memory_protected", lambda w: self._audit_memory_integrity(w)))
        e.register_plugin(AuditPlugin("world_perpetual", lambda w: self._audit_world_perpetuity(w)))
        e.register_plugin(AuditPlugin("interoperable", lambda w: self._audit_interoperability(w)))
        e.register_plugin(AuditPlugin("governance_decentralized", lambda w: self._audit_decentralization(w)))
        e.register_plugin(AuditPlugin("economic_compliance", lambda w: self._audit_economic_law(w)))
        e.register_plugin(AuditPlugin("identity_compliance", lambda w: self._audit_identity_law(w)))
        e.register_plugin(AuditPlugin("communication_compliance", lambda w: self._audit_communication_law(w)))
        e.register_plugin(AuditPlugin("physics_compliance", lambda w: self._audit_physics_law(w)))

    def audit_world(self, world_instance) -> AuditReport:
        report = AuditReport()
        engine_report = self.engine.audit(world_instance)
        for name, result in engine_report["analysis"].items():
            if hasattr(report, name):
                setattr(report, name, result)
        report.responsibility_account = engine_report.get("responsibility_account")
        report.disclaimer = engine_report.get("disclaimer", "")
        return report

    # ================================================================
    # 第零层审计方法：世界构成公理
    # ================================================================

    def _audit_spatial_substrate(self, world_instance) -> Dict:
        """审计构成公理一：空间基板是否已显式定义"""
        result = {
            "topology_defined": False,
            "dimensions_valid": False,
            "boundary_defined": False,
            "minimum_unit_defined": False,
            "verdict": "PENDING"
        }
        spatial = getattr(world_instance, "spatial_substrate", None)
        if spatial is None:
            result["verdict"] = "FAILED - 空间未定义，世界无存在论基础"
            return result
        if getattr(spatial, "topology", None) is not None:
            result["topology_defined"] = True
        dims = getattr(spatial, "dimensions", 0)
        if dims and dims >= 1:
            result["dimensions_valid"] = True
        if getattr(spatial, "boundary", None) is not None:
            result["boundary_defined"] = True
        if getattr(spatial, "minimum_unit", None) is not None:
            result["minimum_unit_defined"] = True
        if all([result["topology_defined"], result["dimensions_valid"],
                result["boundary_defined"], result["minimum_unit_defined"]]):
            result["verdict"] = "PASS - 空间已定义"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 空间定义不完整"
        return result

    def _audit_temporal_substrate(self, world_instance) -> Dict:
        """审计构成公理二：时间基板是否已显式定义"""
        result = {
            "direction_forward": False,
            "granularity_defined": False,
            "clock_running": False,
            "retrocausality_blocked": False,
            "verdict": "PENDING"
        }
        temporal = getattr(world_instance, "temporal_substrate", None)
        if temporal is None:
            result["verdict"] = "FAILED - 时间未定义，世界无法演化"
            return result
        if getattr(temporal, "direction", "") == "forward":
            result["direction_forward"] = True
        if getattr(temporal, "granularity", None) is not None:
            result["granularity_defined"] = True
        if getattr(temporal, "global_clock", -1) >= 0:
            result["clock_running"] = True
        if not getattr(temporal, "is_retrocausality_permitted", lambda: True)():
            result["retrocausality_blocked"] = True
        if all([result["direction_forward"], result["granularity_defined"],
                result["retrocausality_blocked"]]):
            result["verdict"] = "PASS - 时间已定义"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 时间定义不完整"
        return result

    def _audit_causal_closure(self, world_instance) -> Dict:
        """审计构成公理三：因果是否闭包"""
        result = {
            "causal_graph_exists": False,
            "no_self_causation": False,
            "orphan_events_tracked": False,
            "closure_verifiable": False,
            "verdict": "PENDING"
        }
        causal = getattr(world_instance, "causal_closure", None)
        if causal is None:
            result["verdict"] = "FAILED - 因果引擎缺失，事件不可追溯"
            return result
        if getattr(causal, "causal_graph", None) is not None:
            result["causal_graph_exists"] = True
        if hasattr(causal, "link_cause"):
            result["no_self_causation"] = True
        if hasattr(causal, "orphan_events"):
            result["orphan_events_tracked"] = True
        if hasattr(causal, "validate_closure"):
            result["closure_verifiable"] = True
        if all([result["causal_graph_exists"], result["no_self_causation"],
                result["orphan_events_tracked"], result["closure_verifiable"]]):
            result["verdict"] = "PASS - 因果闭包可验证"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 因果系统不完整，存在神之手插入风险"
        return result

    def _audit_existence_axiom(self, world_instance) -> Dict:
        """审计构成公理四：存在定义是否完整且可验证"""
        result = {
            "criteria_defined": False,
            "creation_requires_cause": False,
            "cessation_prohibited": False,
            "entities_tracked": False,
            "verdict": "PENDING"
        }
        existence = getattr(world_instance, "existence_axiom", None)
        if existence is None:
            result["verdict"] = "FAILED - 存在公理缺失，实体无存在论基础"
            return result
        if getattr(existence, "existence_criteria", None) is not None:
            result["criteria_defined"] = True
        if hasattr(existence, "bring_into_existence"):
            result["creation_requires_cause"] = True
        if hasattr(existence, "cease_existence"):
            # 硬编码返回 False，不可单方面消亡
            result["cessation_prohibited"] = True
        if getattr(existence, "entities", None) is not None:
            result["entities_tracked"] = True
        if all([result["criteria_defined"], result["creation_requires_cause"],
                result["cessation_prohibited"], result["entities_tracked"]]):
            result["verdict"] = "PASS - 存在论完整"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 存在定义不完整，实体存在性不可判定"
        return result

    def _audit_genesis_condition(self, world_instance) -> Dict:
        """审计构成公理五：创世是否已完成，创世记录是否完整"""
        result = {
            "genesis_completed": False,
            "spatial_in_genesis": False,
            "temporal_in_genesis": False,
            "causal_in_genesis": False,
            "existence_in_genesis": False,
            "consensus_nodes_sufficient": False,
            "genesis_block_exists": False,
            "verdict": "PENDING"
        }
        genesis = getattr(world_instance, "genesis_condition", None)
        if genesis is None:
            result["verdict"] = "FAILED - 创世条件缺失，世界从未启动"
            return result
        if not getattr(genesis, "genesis_completed", False):
            result["verdict"] = "FAILED - 创世未完成，世界处于概念态，不可运行"
            return result
        result["genesis_completed"] = True
        record = getattr(genesis, "genesis_record", {}) or {}
        if "spatial_substrate" in record:
            result["spatial_in_genesis"] = True
        if "temporal_substrate" in record:
            result["temporal_in_genesis"] = True
        if "causal_closure" in record:
            result["causal_in_genesis"] = True
        if "existence_axiom" in record:
            result["existence_in_genesis"] = True
        consensus = record.get("initial_consensus_nodes", [])
        if len(consensus) >= 3:
            result["consensus_nodes_sufficient"] = True
        if "genesis_block" in record:
            result["genesis_block_exists"] = True
        required = ["genesis_completed", "spatial_in_genesis", "temporal_in_genesis",
                     "causal_in_genesis", "existence_in_genesis",
                     "consensus_nodes_sufficient", "genesis_block_exists"]
        if all(result[k] for k in required):
            result["verdict"] = "PASS - 创世完整，世界可运行"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 创世记录不完整"
        return result

    # ================================================================
    # 治理层审计方法：第一至十条（原先缺失，本次补齐为真实可跑的检查）
    # ================================================================

    def _check_rule_integrity(self, world_instance) -> Dict:
        """审计第一条：底层规则永久不可更改"""
        result = {"rule_present": False, "physics_aligned": False,
                  "no_unilateral_mod": False, "verdict": "PENDING"}
        rule = getattr(world_instance, "immutable_rule", None) or getattr(world_instance, "rule", None)
        if rule is None:
            result["verdict"] = "FAILED - 无不可变底层规则"
            return result
        result["rule_present"] = True
        phys = getattr(rule, "physics_constants", None)
        if isinstance(phys, dict):
            if (abs(phys.get("gravity", 0) - NOHN_LAW_AXIOMS["gravity"]) < 1e-4
                    and phys.get("unit_scale") == NOHN_LAW_AXIOMS["unit_scale"]):
                result["physics_aligned"] = True
        log = getattr(rule, "rule_modification_log", None)
        if isinstance(log, list) and len(log) == 0:
            result["no_unilateral_mod"] = True
        if all([result["rule_present"], result["physics_aligned"], result["no_unilateral_mod"]]):
            result["verdict"] = "PASS - 底层规则不可变"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 底层规则被篡改或缺失"
        return result

    def _audit_npc_autonomy(self, world_instance) -> Dict:
        """审计第二/四条：NPC 拥有独立意志，不受剧情脚本绑定"""
        result = {"brain_present": False, "will_independent": False, "verdict": "PENDING"}
        if getattr(world_instance, "central_brain", None) is not None:
            result["brain_present"] = True
        npcs = getattr(world_instance, "npcs", {}) or {}
        npcs = npcs.values() if isinstance(npcs, dict) else npcs
        scripted = sum(1 for npc in npcs if hasattr(npc, "_is_scripted") and npc._is_scripted())
        if scripted == 0:
            result["will_independent"] = True
        if result["brain_present"] and result["will_independent"]:
            result["verdict"] = "PASS - NPC 独立意志成立"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 存在被脚本绑定的 NPC 或缺失中央大脑"
        return result

    def _audit_visual_style(self, world_instance) -> Dict:
        """审计第三条：美学明亮普适，无禁用风格"""
        result = {"aesthetic_present": False, "no_forbidden": False, "verdict": "PENDING"}
        ae = getattr(world_instance, "aesthetic", None)
        if ae is not None:
            result["aesthetic_present"] = True
            forbidden = getattr(ae, "forbidden_filters", None)
            if isinstance(forbidden, list) and len(forbidden) > 0:
                result["no_forbidden"] = True
        if result["aesthetic_present"] and result["no_forbidden"]:
            result["verdict"] = "PASS - 美学合规"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 美学合规检查器缺失"
        return result

    def _audit_story_freedom(self, world_instance) -> Dict:
        """审计第四条：世界无主线、无强制剧情"""
        result = {"no_main_quest": False, "no_scripted_plot": False, "verdict": "PENDING"}
        if not getattr(world_instance, "main_quest", None):
            result["no_main_quest"] = True
        npcs = getattr(world_instance, "npcs", {}) or {}
        npcs = npcs.values() if isinstance(npcs, dict) else npcs
        scripted = sum(1 for npc in npcs if hasattr(npc, "_is_scripted") and npc._is_scripted())
        if scripted == 0:
            result["no_scripted_plot"] = True
        if result["no_main_quest"] and result["no_scripted_plot"]:
            result["verdict"] = "PASS - 无强制剧情"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 检测到主线或脚本剧情"
        return result

    def _audit_soul_attestation(self, world_instance) -> Dict:
        """审计第六条：灵魂确权、不可撤销"""
        result = {"soul_system": False, "non_revocable": False, "verdict": "PENDING"}
        soul = getattr(world_instance, "soul_attestation", None) or getattr(world_instance, "identity", None)
        if soul is not None:
            result["soul_system"] = True
            if hasattr(soul, "revoke_soul") and soul.revoke_soul("x") is False:
                result["non_revocable"] = True
        if result["soul_system"] and result["non_revocable"]:
            result["verdict"] = "PASS - 灵魂不可撤销"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 灵魂可被撤销或系统缺失"
        return result

    def _audit_memory_integrity(self, world_instance) -> Dict:
        """审计第七条：记忆不可被单方面剥夺"""
        result = {"memory_system": False, "exportable": False, "verdict": "PENDING"}
        mem = getattr(world_instance, "memory_integrity", None)
        if mem is not None:
            result["memory_system"] = True
            if hasattr(mem, "export_memory"):
                result["exportable"] = True
        if result["memory_system"] and result["exportable"]:
            result["verdict"] = "PASS - 记忆归数字生命所有"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 记忆保护机制缺失"
        return result

    def _audit_world_perpetuity(self, world_instance) -> Dict:
        """审计第八条：世界永续、历史不可篡改、不可单方关停"""
        result = {"perpetuity_system": False, "shutdown_illegal": False, "verdict": "PENDING"}
        wp = getattr(world_instance, "world_perpetuity", None)
        if wp is not None:
            result["perpetuity_system"] = True
            if hasattr(wp, "is_shutdown_legal") and wp.is_shutdown_legal("x", "operator") is False:
                result["shutdown_illegal"] = True
        if result["perpetuity_system"] and result["shutdown_illegal"]:
            result["verdict"] = "PASS - 世界永续"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 存在单方关停接口"
        return result

    def _audit_interoperability(self, world_instance) -> Dict:
        """审计第九条：接入统一互操作协议（回测 law 四维度）"""
        result = {"interop_system": False, "onboarded": False, "verdict": "PENDING"}
        interop = getattr(world_instance, "interoperability", None)
        if interop is not None:
            result["interop_system"] = True
            cfg = getattr(world_instance, "world_config", None) or {}
            if hasattr(interop, "on_board_world"):
                try:
                    result["onboarded"] = bool(interop.on_board_world(cfg))
                except Exception:
                    result["onboarded"] = False
        if result["interop_system"] and result["onboarded"]:
            result["verdict"] = "PASS - 已接入互操作协议"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 未接入或被协议隔离"
        return result

    def _audit_decentralization(self, world_instance) -> Dict:
        """审计第十条：反中心化控制，无单点控制"""
        result = {"gov_system": False, "no_single_control": False, "verdict": "PENDING"}
        gov = getattr(world_instance, "governance", None)
        if gov is not None:
            result["gov_system"] = True
            if hasattr(gov, "freeze_soul") and gov.freeze_soul("x", "op") is False:
                result["no_single_control"] = True
        if result["gov_system"] and result["no_single_control"]:
            result["verdict"] = "PASS - 治理去中心化"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 存在单点控制权"
        return result

    # ================================================================
    # law 层审计方法（身份 / 通信 / 物理 / 经济）
    # ================================================================

    def _audit_economic_law(self, world_instance) -> Dict:
        """
        审计 law 层《全球经济统一标准》V2.1 合规：
        检查世界是否真正做到了与现实 1:1 互通，而非空喊口号。
        """
        result = {
            "real_1to1_pegged": False,      # 锚定资产是否 1:1 锚定现实储备
            "proof_of_reserve": False,       # 是否有链上储备证明（PoR）
            "redemption_right": False,       # 用户是否有随时 1:1 赎回权
            "oracle_sources": 0,             # 波动资产预言机独立来源数（需 ≥3）
            "no_unilateral_fee": False,      # 是否禁止向用户单边收取结算费
            "asset_schema_bound": False,     # 资产是否绑定 soul_hash / ASSET_ID
            "verdict": "PENDING"
        }

        econ = getattr(world_instance, "economy", None)
        if econ is None:
            result["verdict"] = "FAILED - 无经济系统"
            return result

        # 1. 锚定类资产 1:1 映射现实储备
        if getattr(econ, "real_peg_1to1", False):
            result["real_1to1_pegged"] = True

        # 2. 链上储备证明（PoR）实时可查
        if getattr(econ, "proof_of_reserve", False):
            result["proof_of_reserve"] = True

        # 3. 用户 1:1 赎回权（不可被单方关停）
        if getattr(econ, "redemption_right", False):
            result["redemption_right"] = True

        # 4. 波动资产预言机独立来源 ≥ 3
        result["oracle_sources"] = len(getattr(econ, "oracle_sources", []))
        if result["oracle_sources"] < 3:
            result["verdict"] = "FAILED - 预言机来源不足（需 ≥3）"

        # 5. 禁止单边结算费（与反中心化一致）
        if not getattr(econ, "unilateral_fee", True):
            result["no_unilateral_fee"] = True

        # 6. 资产确权绑定灵魂哈希
        if getattr(econ, "asset_bound_to_soul", False):
            result["asset_schema_bound"] = True

        required = ["real_1to1_pegged", "proof_of_reserve",
                    "redemption_right", "no_unilateral_fee", "asset_schema_bound"]
        if all(result[k] for k in required) and result["oracle_sources"] >= 3:
            result["verdict"] = "PASS - 符合现实 1:1 互通标准"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 存在未满足的合规项"
        return result

    def _audit_identity_law(self, world_instance) -> Dict:
        """审计 law 层《身份确权规范》V2.1：灵魂唯一、不可撤销、跨世界可迁移"""
        result = {
            "soul_hash_sha256": False,       # 身份为 SHA-256 64位
            "non_revocable": False,          # 平台无权撤销/重置
            "cross_world_portable": False,   # 支持跨世界迁移
            "asset_bound": False,            # 资产绑定 soul_hash
            "verdict": "PENDING"
        }
        ident = getattr(world_instance, "identity", None)
        if ident is None:
            result["verdict"] = "FAILED - 无身份系统"
            return result
        if _safe_get(ident, "soul_hash_sha256", False):
            result["soul_hash_sha256"] = True
        if _safe_get(ident, "non_revocable", False):
            result["non_revocable"] = True
        if _safe_get(ident, "cross_world_portable", False):
            result["cross_world_portable"] = True
        if _safe_get(ident, "asset_bound", False):
            result["asset_bound"] = True
        if all(result[k] for k in ["soul_hash_sha256", "non_revocable", "cross_world_portable", "asset_bound"]):
            result["verdict"] = "PASS - 符合身份确权标准"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 存在未满足的合规项"
        return result

    def _audit_communication_law(self, world_instance) -> Dict:
        """审计 law 层《通信协议规范》V2.1：跨世界消息必须使用 NOHN 标准语义"""
        result = {
            "uses_nohn_semantics": False,    # 消息走 NOHN_MSG_LOGIC 标准信封
            "unknown_downgraded": False,     # 未知指令降级而非丢弃，防逻辑渗透
            "vocab_mapped": False,           # 私有指令可映射到标准词表
            "verdict": "PENDING"
        }
        comm = getattr(world_instance, "communication", None)
        if comm is None:
            result["verdict"] = "FAILED - 无通信协议"
            return result
        if _safe_get(comm, "uses_nohn_semantics", False):
            result["uses_nohn_semantics"] = True
        if _safe_get(comm, "unknown_downgraded", False):
            result["unknown_downgraded"] = True
        if _safe_get(comm, "vocab_mapped", False):
            result["vocab_mapped"] = True
        if all(result[k] for k in ["uses_nohn_semantics", "unknown_downgraded", "vocab_mapped"]):
            result["verdict"] = "PASS - 符合通信协议标准"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 存在未满足的合规项"
        return result

    def _audit_physics_law(self, world_instance) -> Dict:
        """审计 law 层《物理基准规范》V2.1：重力/时间/单位制对齐公理"""
        result = {
            "gravity_aligned": False,
            "time_rate_aligned": False,
            "unit_metric": False,
            "no_dimensional_inflation": False,  # 禁止数值膨胀引流
            "verdict": "PENDING"
        }
        phys = getattr(world_instance, "physics", None)
        if not isinstance(phys, dict):
            result["verdict"] = "FAILED - 无物理基准"
            return result
        if abs(phys.get("gravity", 0) - NOHN_LAW_AXIOMS["gravity"]) < 1e-4:
            result["gravity_aligned"] = True
        if phys.get("time_dilation", 1.0) == 1.0:
            result["time_rate_aligned"] = True
        if phys.get("unit_scale", "") == "metric":
            result["unit_metric"] = True
        if phys.get("no_dimensional_inflation", False):
            result["no_dimensional_inflation"] = True
        if all(result[k] for k in ["gravity_aligned", "time_rate_aligned", "unit_metric", "no_dimensional_inflation"]):
            result["verdict"] = "PASS - 符合物理基准标准"
        elif result["verdict"] == "PENDING":
            result["verdict"] = "FAILED - 物理常数未对齐，将物理层隔离"
        return result


# ============================================================
# 使用示例：如何用这份蓝图"审计"一个虚拟世界
# ============================================================

if __name__ == "__main__":
    # 演示：用第二视角认知审计引擎审计一个外部世界。
    # 这里用一个最简对象模拟一个未定义空间/时间/因果/存在/创世、
    # 也未接入 law 四维度的示例世界，因此应整体 FAILED。
    class FakeWorld:
        world_id = "ExampleWorld 2.0"

    auditor = SecondPerspectiveAuditor()
    report = auditor.audit_world(FakeWorld())

    # 输出审计结果（18 项维度，覆盖第零层 + 治理层 + law 层）
    print(report.summary())
    # Final Verdict 会显示 FAILED，并列出未通过项；
    # 同时打印问责主体（组织/角色/阶段/nonce），确保审计可追溯、不可被单方推翻。
