<p align="center">
  <img src="assets/banner.png" alt="SPL-Virtual-World-Base banner" style="width:100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/metaverse-D4AF37?style=flat-square" alt="metaverse">
  <img src="https://img.shields.io/badge/infrastructure-D4AF37?style=flat-square" alt="infrastructure">
  <img src="https://img.shields.io/badge/constitution-D4AF37?style=flat-square" alt="constitution">
  <img src="https://img.shields.io/badge/second--perspective-D4AF37?style=flat-square" alt="second-perspective">
</p>

<blockquote align="center">
  <em>虚拟世界与元宇宙基础设施基座</em>
</blockquote>

<div style="max-width:880px;margin:0 auto;padding:0 16px">

## ✦ 关于

<p style="font-size:15px;line-height:1.8;color:#2C2C2C">SPL-VIRTUAL-WORLD-BASE 是虚拟世界与元宇宙的基础设施框架，基于「宪法—法律—桥梁」三层架构，为虚拟空间提供可治理、可互操作、可演进的运行时基座，实现跨世界的资产、规则与智能体稳定衔接与协作。第二视角认知审计官作为整套栈的中立裁判。</p>

<p align="center">
  <img src="assets/overview.png" alt="SPL-Virtual-World-Base overview" style="width:100%">
</p>

</div>

<p align="center">— ✦ —</p>

## ✦ 快速开始

```bash
# 主源：GitHub（仓库名 Second-Reality）
git clone https://github.com/nohn3043-arch/Second-Reality.git
# 镜像：Gitee（本仓库）
# git clone https://gitee.com/nohn-ecosystem/SPL-virtual-world-core.git
cd SPL-virtual-world-base
# 纯 Python ≥3.8——仅标准库，无需安装
# 启动 GUI 演示（需要图形环境；内置两个智能体）
python virtual_world.py
```

编程方式启动：

```python
from virtual_world import NohnWorld, NohnVisualApp
nexus = NohnWorld()
nexus.spawn("Explorer_01", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
NohnVisualApp(nexus).root.mainloop()
```

<p align="center">— ✦ —</p>

## ✦ 架构

<div style="max-width:880px;margin:0 auto;padding:0 16px">

整套栈分为四个可分离层次，使规则（只读）、审计官（中立裁判）、系统（实现）与演示客户端互不混淆：

- **宪法规则**（`constitution_rules.py`）——原初公理与十条治理律法，永久锁定为根信任锚。`NOHN_LAW_AXIOMS` 是所有常量的唯一权威来源。
- **审计引擎**（`audit_engine.py`）——第二视角认知审计官（`ResponsibilityAccount` + 可插拔 `AuditPlugin` + `SecondPerspectiveAuditor`，含 18 维合规审查）。它是裁判，不是世界的一部分。
- **法律**（`law/`）——四个标准层：通信协议标准 · 全球经济统一标准（货币、锚定、储备证明、赎回）· 身份证明标准（灵魂哈希绑定身份）· 物理基线标准（重力 / 时间 / 尺度常数）。
- **系统**（`system/`）——真实实现层：持久化账本、≥2/3 公投共识、智能体引擎、无头运行时、REST/WS API、机器可读协议模式、生产安全。
- **桥梁**（`compatibility_bridge.py`）——遗留世界加入 Nohn 领地的唯一「海关」：`translate_intent()` 语义清洗（去隐式解释权）、`check_physics_constants()` 物理常数校验、`verify_soul_hash()` 灵魂哈希身份核验。

演示运行时（`virtual_world.py`）以 `EconomySystem`、`TaskGenerator`、`NohnAgent` 装配以上各层，挂载在真实 `system.World` 上。

</div>

<p align="center">— ✦ —</p>

## ✦ 核心模块

<div style="max-width:880px;margin:0 auto;padding:0 16px">

按 Nohn™ 世界栈的六个层次分组（全部类均与当前源码核对）：

| 层次 | 模块（类） | 职责 |
|---|---|---|
| **宪法** | `SpatialSubstrate` | 世界拓扑、维度、边界、最小单元 |
| | `TemporalSubstrate` | 时间流与事件排序 |
| | `CausalClosure` | 因果链追踪、外部干预检测 |
| | `ExistenceAxiom` | 实体创建、校验与销毁 |
| | `GenesisCondition` | 世界初始化与完整性校验 |
| | `ImmutableWorldRule` | 需全球公投方可修改的规则 |
| | `WorldCentralBrain` | 世界子系统的中央协调 |
| **灵魂** | `SoulAttestation` | 灵魂注册与核验 |
| | `SoulLedger` | 身份账本 |
| | `MemoryInalienability` | 记忆不可侵占 |
| | `MemoryGuardian` | 记忆封印与篡改检测 |
| | `IndependentWill` | 自主意志（MARL 基，非行为树） |
| | `MemoryVault` | 安全记忆存储 |
| **审计** | `ResponsibilityAccount` | 每个治理行为的具名问责 |
| | `AuditPlugin` | 可插拔审计检查 |
| | `CognitiveAuditEngine` | 认知审计引擎核心 |
| | `SecondPerspectiveAuditor` | 综合合规审查 |
| | `DecentralizationGovernance` | 去中心化治理 |
| | `AestheticCompliance` | 美学 / 渲染合规 |
| | `AuditReport` | 结构化审计报告 |
| **永续** | `WorldPerpetuity` | 永恒世界运行记录 |
| | `HistoryLedger` | 历史账本 |
| | `SnapshotRegistry` | 快照注册与恢复 |
| **互操作** | `NohnCompatibilityBridge` | 跨世界桥接协议 |
| | `MandatoryInteroperability` | 强制互操作协议 |
| | `UniversalVocabulary` | 通用语义词汇表 |
| | `PhysicsBaseline` | 物理基线对齐 |
| | `IdentityProtocol` | 身份协议兼容 |
| | `EconomicBaseline` | 经济标准合规 |
| **运行时** | `NohnWorld` | 世界容器 |
| | `NohnAgent` | 智能体 |
| | `EconomySystem` | 经济系统 |
| | `TaskGenerator` | 任务生成 |
| | `NohnVisualApp` | 可视化应用 |
| | `ConsensusEngine` | 世界参与者共识 |
| | `SimulationEngine` | 世界仿真循环 |
| **系统** | `World`（`system/runtime.py`） | 创世装配 + 滴答循环 + 18 维审计 + 快照 |
| | `Storage` · `SoulLedger` · `HistoryLedger` · `EconomicReserve` · `SnapshotRegistry`（`system/ledger.py`） | 持久化 SQLite 账本（灵魂 / 历史 / 经济 / 快照） |
| | `ConsensusNetwork` · `Governance`（`system/consensus.py`） | ≥2/3 公投共识 + 治理 |
| | `Agent`（`system/agent_engine.py`） | 需求驱动智能体 + 记忆封印 |
| | `ProtocolValidator`（`system/protocol.py`） | 机器可读法律校验 + 入网 |
| | `SoulAuth` · `WorldAPI` · `serve()`（`system/api.py`） | REST + WebSocket + HMAC 认证 |

</div>

<p align="center">— ✦ —</p>

## ✦ 企业接入

<div style="max-width:880px;margin:0 auto;padding:0 16px">

本基座是**协议守护者 + 参考实现**，而非单运营方平台。企业可按三种方式接入：

### A. 协议参与方（自托管，数据留在本地）

在自有数据中心运行符合 `law/` 四项标准的自研实现，入网前先校验：

```python
from system.protocol import ProtocolValidator
ok, failures = ProtocolValidator().validate(world_config)
# ok=True  -> 接入 Nohn 网络
# ok=False -> 在被判失败层次隔离
```

**硬约束**：原始数据（灵魂、资产、记忆、世界状态）永不离开数据中心。协议层只交换可验证证明——哈希、签名、Merkle 根、储备证明——绝不交换原始数据。

### B. 参考实现（嵌入式）

直接使用经过审计的参考世界：

```python
from system.runtime import World
world = World("my-world", data_dir="./my_data")
world.spawn_agent("ab" * 32)
world.tick()
print(world.audit_summary())   # 18 维第二视角审计
```

### C. API 集成（REST + WebSocket）

```python
from system.api import serve
serve(world, host="0.0.0.0", port=8000)
```

关键端点：`GET /health`、`GET /world`、`GET /audit`、`POST /protocol/validate`、`POST /agent/spawn`、`POST /auth/issue`、`GET/POST /economy/*`、`WS /ws/world`。

### 定制边界

企业差异只存在于**配置层**（行业参数、司法辖区、部署拓扑），绝不进入核心宪法、审计与共识规则——这些对所有企业保持一致。

</div>

<p align="center">— ✦ —</p>

## ✦ 项目结构

```
SPL-Virtual-world-base/
├── constitution_rules.py        # 宪法规则：公理 + 十条治理律法 + NOHN_LAW_AXIOMS
├── audit_engine.py              # 第二视角审计官：18 维合规审查
├── constitution.py              # 聚合层（向后兼容再导出）
├── compatibility_bridge.py      # 遗留世界「海关」：语义清洗 + 物理 / 灵魂校验
├── virtual_world.py             # 演示运行时（GUI / 无头），挂载于 system.World
├── system/                      # 真实实现层
│   ├── ledger.py                #   持久化 Soul/History/Economic 账本（SQLite）
│   ├── consensus.py             #   ≥2/3 公投共识 + 治理
│   ├── agent_engine.py          #   需求驱动智能体 + 记忆封印
│   ├── runtime.py               #   创世装配 + 滴答循环 + 审计报告
│   ├── api.py                   #   REST + WebSocket + HMAC 认证
│   ├── protocol.py              #   机器可读法律模式 + 校验器
│   └── keys.py                  #   签名密钥管理
├── law/                         # 通信 / 经济 / 身份 / 物理标准
├── assets/                      # banner.svg/png, overview.svg/png
└── LICENSE
```

<p align="center">— ✦ —</p>

## ✦ 生态

SPL-VIRTUAL-WORLD-BASE 是 NOHN AI 生态的一员——围绕第二视角因果审计与确定性执行构建的项目家族：

| 项目 | 仓库 | 定位 |
|---|---|---|
| **Second-Perspective (GCAE)** | [nohn3043-arch/second-perspective](https://github.com/nohn3043-arch/second-perspective) | 全局认知审计引擎——五算子因果审计内核（IMDA 95/100） |
| **NOMOS** | [nohn3043-arch/second-perspective](https://github.com/nohn3043-arch/second-perspective)（`Intelligent-Decision-Hub--Nomos` 分支） | 可审计确定性决策中心（IMDA 95/100） |
| **SPL-G1** | [nohn3043-arch/SPL-G1](https://github.com/nohn3043-arch/SPL-G1) | 硬件因果审计可信计算单元（TCU） |
| **SPL-Virtual-World-Base** | [nohn3043-arch/Second-Reality](https://github.com/nohn3043-arch/Second-Reality) | 虚拟世界与元宇宙基础设施（宪法 / 法律 / 桥梁） |
| **Story-Engine** | [nohn3043-arch/story-engine](https://github.com/nohn3043-arch/story-engine) | 长篇叙事一致性引擎 |
| **Antares** | [nohn3043-arch/Antares](https://github.com/nohn3043-arch/Antares) | GFSIP v1.0——带因果审计的联邦稳定互操作协议 |
| **Anthropomorphic-Agent-Engine** | [nohn3043-arch/Anthropomorphic-Agent-Engine](https://github.com/nohn3043-arch/Anthropomorphic-Agent-Engine) | 确定性拟人心理引擎（SPL Pure Core V8.0） |
| **PAGES** | [nohn3043-arch/pages](https://github.com/nohn3043-arch/pages) | NOHN AI 生态官方落地页 |

<p align="center">— ✦ —</p>

## ✦ 许可与授权

本仓库**非开源**。双轨模式：个人非商业研究免费；政府 / 企业需付费商业授权。详见 [LICENSE](./LICENSE)。

**商标声明**：「Nohn™」与「Second Perspective™」是虚拟世界领域的未注册商标，受反不正当竞争法与普通法仿冒原则保护。任何未经授权的商业使用均构成侵权。

**授权咨询**：国际 / 全球 — [ai@nohnlins.com](mailto:ai@nohnlins.com) · 中国 — [lin@secondai.top](mailto:lin@secondai.top)

<p align="center">
  <a href="https://github.com/nohn3043-arch">GitHub</a>
  &nbsp;·&nbsp;
  <a href="https://www.nohnlins.com/">nohnlins.com</a>
  &nbsp;·&nbsp;
  <a href="mailto:ai@nohnlins.com">ai@nohnlins.com</a>
</p>
<p align="center"><sub>NOHN AI · SPL-VIRTUAL-WORLD-BASE</sub></p>
