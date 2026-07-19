# Nohn™ Core — 虚拟世界的灵魂

> "A virtual world must first be a world"

**Nohn™ Core** 是未来虚拟世界的底层核心框架，由**宪法（Constitution）**、**法律（Law）**和**桥梁（Bridge）**三部分组成。它不为任何平台服务，不发布任何产品，不托管任何数据，也不运营任何服务——它只定义规则、提供灵魂、守护秩序。

---

## 项目架构

```
SPL-virtual-world-core/
├── constitution.py          # 虚拟世界宪法核心
│   ├── SpatialSubstrate     # 空间基底
│   ├── TemporalSubstrate    # 时间基底
│   ├── CausalClosure        # 因果闭环
│   ├── ExistenceAxiom       # 存在公理
│   ├── GenesisCondition     # 创世条件
│   └── ...                  # 更多宪法级组件
├── compatibility_bridge.py  # 跨世界兼容桥接协议
├── virtual_world.py         # 虚拟世界运行实例
│   ├── NohnWorld            # 世界容器
│   ├── NohnAgent            # 智能体
│   ├── EconomySystem        # 经济系统
│   └── NohnVisualApp        # 可视化应用
└── law/                     # 行业标准规范
    ├── Identity attestation standard
    ├── Physics baseline standard
    ├── Communication protocol standard
    └── Global economic unified standard
```

---

## 核心特性

### 宪法层（Constitution）
- **空间基底**：定义世界拓扑结构、维度、边界和最小单位
- **时间基底**：时间流逝机制，确保事件时序性
- **因果闭环**：事件因果链追踪与外部干预检测
- **存在公理**：实体的创生、验证与消亡
- **创世条件**：世界初始化与完整性验证
- **不可变规则**：世界宪法的修改需经全局公投

### 灵魂层（Soul）
- **SoulAttestation**：灵魂注册与验证
- **SoulLedger**：身份账本
- **MemoryInalienability**：记忆不可剥夺性
- **MemoryGuardian**：记忆密封与篡改检测
- **IndependentWill**：自主意志（非行为树的 MARL 决策）

### 审计与合规
- **CognitiveAuditEngine**：认知审计引擎（插件化设计）
- **SecondPerspectiveAuditor**：全方位合规审查
- **DecentralizationGovernance**：去中心化治理

### 永恒性保障
- **WorldPerpetuity**：世界永恒运行记录
- **HistoryLedger**：历史账本
- **SnapshotRegistry**：快照注册与恢复

### 互操作性（Bridge）
- **MandatoryInteroperability**：强制互操作协议
- **UniversalVocabulary**：通用语义词汇
- **PhysicsBaseline**：物理基准对齐
- **IdentityProtocol**：身份协议兼容
- **EconomicBaseline**：经济标准合规

---

## 快速开始

```python
from constitution import GenesisCondition, SpatialSubstrate, TemporalSubstrate
from virtual_world import NohnWorld, NohnAgent, NohnVisualApp
from compatibility_bridge import NohnCompatibilityBridge

# 1. 创建世界
world = NohnWorld()

# 2. 定义空间拓扑
space = SpatialSubstrate()
space.define_topology("continuous", 3, "infinite", 0.001)

# 3. 初始化时间
time = TemporalSubstrate()

# 4. 生成创世块
genesis = GenesisCondition()
genesis.initiate_genesis({
    "world_id": "nohn_world_001",
    "initial_agents": [],
    "physics_constants": {...}
})

# 5. 孕育智能体
agent = world.spawn("Explorer_001", soul_hash="...")

# 6. 运行世界
visual = NohnVisualApp(world)
while world.running:
    world.step()
    visual.step()
```

---

## 法律与许可

⚠️ **重要声明**

本项目**并非开源软件**，不适用任何开源许可证。在《著作权法》和《计算机软件保护条例》下，采用**"默认保留权利 + 商业授权"**双轨模式：

| 用户类型 | 用途 | 许可要求 |
|---------|------|---------|
| 个人（自然人） | 非商业学术研究/学习/个人实验 | 免费（参见 LICENSE 中的"个人研究自由许可"） |
| 政府机构/公共机构/企业 | 任何用途（包括内部部署、产品开发、服务提供）| **需事先签署商业授权协议并支付费用** |

- **个人研究者**可免费使用本作品进行非商业研究，但不得用于任何商业目的，也不得向任何企业或政府组织提供服务
- **政府/企业用户**在签署商业授权协议并支付约定费用之前，不得复制、部署、运行、集成或分发本作品

**申请授权**：
- 国际/全球：ai@nohnlins.com
- 中国：lin@secondai.top

完整的许可条款请参见 [LICENSE](./LICENSE) 文件。

## Architecture — Constitution · Law · Bridge

Nohn™ Core is composed of three parts that together define the foundational axioms of the next-generation internet civilization:

- **Constitution** (`constitution.py`) — the primordial, immutable axioms of the virtual world, serving as the permanent root trust anchor. It embeds a ported cognitive-audit engine (`ResponsibilityAccount` + pluggable `AuditPlugin`s) so every governance action carries a named, accountable node.
- **Law** (`law/`) — four standard layers that iterate annually:
  - *Communication protocol standard*
  - *Global economic unified standard* — currency, 1:1 asset peg, proof-of-reserve, redemption rights
  - *Identity attestation standard* — soul-hash bound identity
  - *Physics baseline standard* — gravity / time / scale constants
- **Bridge** (`compatibility_bridge.py`) — the sole "customs checkpoint" between old and new worlds:
  - `translate_intent()` — semantic wash that maps vendor-private instructions to the Nohn standard vocabulary, removing hidden interpretation rights.
  - `check_physics_constants()` — rejects worlds whose physics diverge from `NOHN_LAW_AXIOMS`.
  - `verify_soul_hash()` — verifies identity against the soul-hash anchor.

The runtime (`virtual_world.py`) integrates these with an economy, task generation, and agents.

## Modules

| Module | File | Responsibility |
|---|---|---|
| Constitution & audit | `constitution.py` | World axioms + embedded cognitive-audit engine |
| Compatibility bridge | `compatibility_bridge.py` | Legacy-world onboarding: semantic wash + physics/soul checks |
| Virtual world runtime | `virtual_world.py` | Economy, tasks, agents |
| Law standards | `law/` | Communication / Economic / Identity / Physics standards |

## Quick Start

```bash
# Pure Python ≥3.8 — standard library only
python virtual_world.py --init demo
```

## Project Structure

```
SPL-virtual-world-core/
├── constitution.py              # world axioms + embedded cognitive-audit engine
├── compatibility_bridge.py      # legacy-world "customs": semantic wash + physics/soul checks
├── virtual_world.py             # runtime: economy, tasks, agents
├── law/                         # Communication / Economic / Identity / Physics standards
└── LICENSE
```

---

## 商标声明

**"Nohn™"** 和 **"Second Perspective™"** 是虚拟世界领域的未注册商标，受反不正当竞争法和普通法仿冒制度保护。任何未经授权的商业使用均构成侵权。

---

## 商业合作

如需商业授权、定制合规评估或加入 Nohn™ 生态系统，请联系：**ai@nohnlins.com**

---

*人类需要秩序。虚拟世界需要灵魂。我们提供答案。*

© 2026 Nohn™. All Rights Reserved.