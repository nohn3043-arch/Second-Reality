<p align="center">
  <img src="assets/banner.png" alt="SPL-Virtual-World-Core banner" style="width:100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/metaverse--D4AF37?style=flat-square" alt="metaverse">  <img src="https://img.shields.io/badge/infrastructure--D4AF37?style=flat-square" alt="infrastructure">  <img src="https://img.shields.io/badge/constitution--D4AF37?style=flat-square" alt="constitution">
</p>

<blockquote align="center">
  <em>虚拟世界与元宇宙基础设施基座</em>
</blockquote>

<div style="max-width:880px;margin:0 auto;padding:0 16px">

## ✦ 关于

<p style="font-size:15px;line-height:1.8;color:#2C2C2C">SPL-VIRTUAL-WORLD-CORE 是面向虚拟世界与元宇宙的基础设施框架，基于三层架构——宪法（Constitution）、法律（Law）、桥接（Bridge）——为虚拟空间提供可治理、可互操作、可演进的运行基座。它使资产、规则与智能体在不同世界之间能够稳定桥接与协作。</p>

<p align="center">
  <img src="assets/overview.png" alt="SPL-Virtual-World-Core overview" style="width:100%">
</p>

</div>

<p align="center">— ✦ —</p>

## ✦ 快速开始

```bash
git clone git@github.com:NOHN-AI/SPL-virtual-world-base.git
cd SPL-virtual-world-base
# 纯 Python ≥3.8 —— 仅标准库，无需安装任何依赖
# 启动 GUI 演示（需图形环境；会生成两个内置智能体）
python virtual_world.py
```

编程式启动：

```python
from virtual_world import NohnWorld, NohnVisualApp
nexus = NohnWorld()
nexus.spawn("Explorer_01", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
NohnVisualApp(nexus).root.mainloop()
```

<p align="center">— ✦ —</p>

## ✦ 三层架构

<div style="max-width:880px;margin:0 auto;padding:0 16px">

- **宪法（Constitution）**（`constitution.py`）—— 虚拟世界的本原公理，永久锁定为根信任锚。内嵌移植版**认知审计引擎**（`ResponsibilityAccount` + 可插拔 `AuditPlugin`），使每一项治理行为都可追责。
- **法律（Law）**（`law/`）—— 四层标准：
  - *通信协议标准*
  - *全球经济统一标准* —— 货币、锚定、储备证明、兑付
  - *身份 attestation 标准* —— 灵魂哈希绑定的身份
  - *物理基线标准* —— 重力 / 时间 / 尺度常量
- **桥接（Bridge）**（`compatibility_bridge.py`）—— 旧世界接入 Nohn 领地的唯一“海关”：
  - `translate_intent()` —— 语义清洗：将厂商私有指令映射为 Nohn 标准词表，剥离隐藏的解释权。
  - `check_physics_constants()` —— 拒绝物理常量偏离 `NOHN_LAW_AXIOMS` 的世界。
  - `verify_soul_hash()` —— 依据灵魂哈希锚验证身份。

运行时（`virtual_world.py`）将以上与 `EconomySystem`、`TaskGenerator`、`NohnAgent` 串联起来。

</div>

## ✦ 架构模块

下表每个类均对照当前源码核验。按 Nohn™ 世界栈的六层分组：

| 层 | 模块（类） | 职责 |
|---|---|---|
| **宪法 Constitution** | `SpatialSubstrate` | 世界拓扑、维度、边界、最小单元 |
| | `TemporalSubstrate` | 时间流与事件排序 |
| | `CausalClosure` | 因果链追踪、外部干预检测 |
| | `ExistenceAxiom` | 实体创建、验证与销毁 |
| | `GenesisCondition` | 世界初始化与完整性校验 |
| | `ImmutableWorldRule` | 需全球公投方可修改的规则 |
| | `WorldCentralBrain` | 世界子系统的中央协调 |
| **灵魂 Soul** | `SoulAttestation` | 灵魂注册与验证 |
| | `SoulLedger` | 身份账本 |
| | `MemoryInalienability` | 记忆不可扣押性 |
| | `MemoryGuardian` | 记忆封存与篡改检测 |
| | `IndependentWill` | 自主意志（基于 MARL，而非行为树） |
| | `MemoryVault` | 安全记忆存储 |
| **审计 Audit** | `ResponsibilityAccount` | 每项治理行为的具名问责 |
| | `AuditPlugin` | 可插拔审计检查 |
| | `CognitiveAuditEngine` | 认知审计引擎核心 |
| | `SecondPerspectiveAuditor` | 综合合规审查 |
| | `DecentralizationGovernance` | 去中心化治理 |
| | `AestheticCompliance` | 美学 / 渲染合规 |
| | `AuditReport` | 结构化审计报告 |
| **永续 Perpetuity** | `WorldPerpetuity` | 永恒的世界运行记录 |
| | `HistoryLedger` | 历史账本 |
| | `SnapshotRegistry` | 快照注册与恢复 |
| **互操作 Interoperability** | `NohnCompatibilityBridge` | 跨世界桥接协议 |
| | `MandatoryInteroperability` | 强制互操作协议 |
| | `UniversalVocabulary` | 通用语义词表 |
| | `PhysicsBaseline` | 物理基线对齐 |
| | `IdentityProtocol` | 身份协议兼容 |
| | `EconomicBaseline` | 经济标准合规 |
| **运行时 Runtime** | `NohnWorld` | 世界容器 |
| | `NohnAgent` | 智能体 |
| | `EconomySystem` | 经济系统 |
| | `TaskGenerator` | 任务生成 |
| | `NohnVisualApp` | 可视化应用 |
| | `ConsensusEngine` | 世界参与者间的共识 |
| | `SimulationEngine` | 世界模拟循环 |

## ✦ 项目结构

```
SPL-Virtual-world-base/
├── constitution.py              # 世界公理 + 六层类体系（见上表）
├── compatibility_bridge.py      # 旧世界“海关”：语义清洗 + 物理/灵魂检查
├── virtual_world.py             # 运行时：世界、智能体、经济、任务、可视化
├── law/                         # 通信 / 经济 / 身份 / 物理 标准
├── assets/                      # banner.svg/png, overview.svg/png
└── LICENSE
```

## ✦ 许可与授权

本仓库**非开源**。采用双轨模式：个人非商业研究免费；政府 / 企业需事先取得书面商业授权。详见 [LICENSE](./LICENSE)。

**商标声明**： “Nohn™” 与 “Second Perspective™” 为虚拟世界领域内的未注册商标，受反不正当竞争法及普通法仿冒原则保护。任何未经授权的商业使用均构成侵权。

**授权咨询**：
- 国际 / 全球：ai@nohnlins.com
- 中国：lin@secondai.top

<p align="center">
  <a href="https://github.com/NOHN-AI">NOHN-AI</a>
  &nbsp;·&nbsp;
  <a href="https://www.nohnlins.com/">nohnlins.com</a>
  &nbsp;·&nbsp;
  <a href="mailto:ai@nohnlins.com">ai@nohnlins.com</a>
</p>
<p align="center"><sub>NOHN AI · SPL-VIRTUAL-WORLD-CORE</sub></p>
