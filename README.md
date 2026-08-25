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
cd Second-Reality
# 纯 Python ≥3.8——仅标准库，无需安装
# 启动 GUI 演示（需要图形环境；内置两个智能体）
python virtual_world.py
```

编程方式启动：

```python
from virtual_world import NohnWorld, run_gui, run_headless

nexus = NohnWorld()          # 内置初始资源与两个智能体
nexus.spawn_agent()          # 可选：再追加一个智能体
run_headless(200, verbose=True)  # 无头仿真 200 tick；有图形环境可用 run_gui()
```

<p align="center">— ✦ —</p>

## ✦ 架构

<div style="max-width:880px;margin:0 auto;padding:0 16px">

整套栈分为四个可分离层次，使规则（只读）、审计官（中立裁判）、系统（实现）与演示客户端互不混淆：

- **宪法规则**（`constitution_rules.py`）——原初公理与十条治理律法，永久锁定为根信任锚。`NOHN_LAW_AXIOMS` 是所有常量的唯一权威来源。
- **审计引擎**（`audit_engine.py`）——第二视角认知审计官（`ResponsibilityAccount` + 可插拔 `AuditPlugin` + `SecondPerspectiveAuditor`，含 19 维合规审查，含鉴权安全维度）。它是裁判，不是世界的一部分。
- **法律**（`law/`）——四个标准层：通信协议标准 · 全球经济统一标准（货币、锚定、储备证明、赎回）· 身份证明标准（灵魂哈希绑定身份，含 V2.2 凭证可恢复条款）· 物理基线标准（重力 / 时间 / 尺度常数）。
- **系统**（`system/`）——真实实现层：持久化账本、≥2/3 公投共识、智能体引擎、无头运行时、REST/WS API、机器可读协议模式、账户系统六层架构（身份根/凭证/会话/授权/恢复/审计）。所有暴露状态必须通过第二视角审计官的 19 项合规审查。
- **桥梁**（`compatibility_bridge.py`）——遗留世界加入 Nohn 领地的唯一「海关」：`translate_intent()` 语义清洗（去隐式解释权）、`check_physics_constants()` 物理常数校验、`verify_soul_hash()` 灵魂哈希身份核验。

### system 模块详细说明
`system/` 是整套栈的可运行实现载体，采用渐进式"桩转实"策略落地所有宪法契约，零第三方依赖，生产级安全。

| 模块 | 定位 | 核心能力 | 持久化 |
|---|---|---|---|
| `__init__.py` | 模块入口 | 定义 system 层整体边界、约束与模块规划 | - |
| `ledger.py` | 状态账本 | 灵魂哈希确权（惰性加载+分页）、世界历史哈希链、储备证明账本、世界快照 | SQLite（默认 `.world_data/` 目录） |
| `consensus.py` | 共识网络 | 节点注册（真实签名验签）、提案公投（≥2/3 超多数通过）、去中心化治理、创世引导期豁免 | 复用 ledger 存储 |
| `agent_engine.py` | 智能体引擎 | 需求驱动智能体决策、记忆封存/校验（KMS 密钥）、记忆不可侵占保障、状态持久化 | 复用 ledger 存储 |
| `runtime.py` | 无头运行时 | 世界创世装配、tick 主循环、因果链记录、快照持久化、19 项审计上报 | 复用 ledger 存储 |
| `protocol.py` | 互认协议 | 四份法律标准机器可读化 JSON Schema、第三方实现并网校验 | - |
| `api.py` | 服务接口 | REST 服务、有状态会话鉴权（可撤销）、账户系统路由、并发锁+速率限制 | 会话状态持久化 |
| `keys.py` | 密钥管理 | Ed25519 密钥、Shamir 分片、KMS 抽象（文件/云 KMS 可插拔）、签名密钥加载 | 密钥文件落盘 / 云 KMS 托管 |
| `identity_root.py` | 身份根（第0层） | 主身份密钥对 + Shamir(3,5) 分片托管，明文主私钥生成后立即清除 | - |
| `credentials.py` | 凭证层（第1层） | 一个灵魂绑定多设备凭证（服务端只存公钥），绑定/吊销/验签 | SQLite |
| `session.py` | 认证层（第2层） | 有状态会话：access token(15min) + refresh token(可轮换可撤销)；会话存储可插拔（SQLite/Memory/Redis） | SessionStore 可插拔 |
| `authorization.py` | 授权层（第3层） | 分级授权（小额即时/中额延迟/大额多签/超大额人工）+ 风险评分 | - |
| `recovery.py` | 恢复层（第4层） | 社交恢复（3/5 守护者投票）+ 时间锁（7天可取消） | SQLite |

**多后端部署（同一份代码，三套后端）：**
运行前用环境变量 `STORAGE` 选择存储后端，默认 `sqlite`：

| STORAGE | 账本（ledger） | 会话（session） | 适用 |
|---|---|---|---|
| `sqlite`（默认） | 落盘 SQLite（`.world_data/`） | 与账本同库 | 单机 / 演示 |
| `memory` | 进程内 `:memory:`（不落盘） | 内存 dict | 测试 / 无状态演示 |
| `redis` | 本地 SQLite | Redis（需 `pip install redis`，缺省降级 SQLite） | 生产横向扩展，多实例共享会话 |
| `postgres` | 预留 PG 驱动（当前降级 SQLite） | SQLite | 生产大规模账本 |

```
STORAGE=redis REDIS_URL=redis://cache:6379/0 python -m system.api   # 生产示例
```

配套的部署级抽象：`ShardRouter`（按 `soul_hash` 分片路由，默认 `SingleShardRouter` 单分片）、`SessionStore`（会话状态可外置）、`CloudKmsProvider`（云 KMS 信封加密，未注入云客户端时自动降级文件后端）。多数据中心部署只需按 soul 分片把单元铺开，代码不变。

**核心特性：**
1. 零额外依赖：全部使用 Python 标准库实现，无需安装第三方包（`redis` 后端除外）
2. 全链路可审计：所有操作均可追溯、可验证，完全符合第二视角审计引擎的 19 维合规要求
3. 多实现互认：提供机器可读协议标准，支持第三方企业自研实现并网
4. 生产级安全：账户系统六层架构（身份根/凭证/会话/授权/恢复/审计），Shamir 分片托管、KMS 密钥托管、有状态可撤销会话、社交恢复机制
5. 可水平扩展：存储后端可插拔（SQLite/Memory/Redis/PG），分片路由接口就绪，状态可外置——多数据中心部署只是配置，不改代码

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
| **系统** | `World`（`system/runtime.py`） | 创世装配 + 滴答循环 + 19 维审计 + 快照 + 账户系统六层装配 |
| | `Storage` · `SoulLedger` · `HistoryLedger` · `EconomicReserve` · `SnapshotRegistry`（`system/ledger.py`） | 持久化 SQLite 账本（灵魂 / 历史 / 经济 / 快照 / 凭证 / 会话 / 恢复） |
| | `ConsensusNetwork` · `Governance`（`system/consensus.py`） | ≥2/3 公投共识 + 治理 + 创世引导期豁免 |
| | `Agent`（`system/agent_engine.py`） | 需求驱动智能体 + 记忆封印 + 状态持久化 |
| | `IdentityRoot`（`system/identity_root.py`） | 身份根 + Shamir 分片托管 |
| | `CredentialVault`（`system/credentials.py`） | 多设备凭证管理 |
| | `SessionManager`（`system/session.py`） | 有状态可撤销会话 |
| | `AuthorizationEngine`（`system/authorization.py`） | 分级授权 + 风险引擎 |
| | `RecoveryManager`（`system/recovery.py`） | 社交恢复 + 时间锁 |
| | `ProtocolValidator`（`system/protocol.py`） | 机器可读法律校验 + 入网 |
| | `SoulAuth` · `WorldAPI`（`system/api.py`） | REST + 有状态会话鉴权 + 账户系统路由 |

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
from system.keys import generate_user_keypair, build_genesis_proof
from system.ledger import derive_soul_hash

world = World("my-world", data_dir="./my_data")
device = generate_user_keypair()   # 私钥仅驻设备安全区（内存态），永不上传
genesis_proof = build_genesis_proof(device["secret"], {"genesis_id": "my-first-soul"})
soul_hash = derive_soul_hash(genesis_proof)   # = SHA-256(公钥)
world.spawn_agent(soul_hash=soul_hash, genesis_proof=genesis_proof)
world.tick()
print(world.audit_summary())   # 19 维第二视角审计
```

### C. API 集成（REST + WebSocket）

```python
from system.api import serve
serve(world, host="0.0.0.0", port=8000)
```

关键端点：`GET /health`、`GET /world`、`GET /audit`、`POST /protocol/validate`、`POST /agent/spawn`、`POST /auth/issue`、`POST /auth/refresh`、`POST /auth/revoke`、`GET/POST /credentials/*`、`POST /recovery/*`、`GET/POST /economy/*`。

### 定制边界

企业差异只存在于**配置层**（行业参数、司法辖区、部署拓扑），绝不进入核心宪法、审计与共识规则——这些对所有企业保持一致。

</div>

<p align="center">— ✦ —</p>

## ✦ 项目结构

```
Second-Reality/
├── constitution_rules.py        # 宪法规则：公理 + 十条治理律法 + NOHN_LAW_AXIOMS
├── audit_engine.py              # 第二视角审计官：19 维合规审查（含鉴权安全）
├── constitution.py              # 聚合层（向后兼容再导出）
├── compatibility_bridge.py      # 遗留世界「海关」：语义清洗 + 物理 / 灵魂校验
├── virtual_world.py             # 演示运行时（GUI / 无头），挂载于 system.World
├── _build_vw*.py                # 虚拟世界构建脚本系列
├── _gen*.py                     # 内容生成脚本系列
├── _write_vw.py                 # 世界写入工具
├── package.json                 # Node.js 依赖（文档生成工具）
├── system/                      # 真实实现层
│   ├── __init__.py
│   ├── ledger.py                #   持久化账本（Soul/History/Economic/凭证/会话/恢复）+ ShardRouter 分片路由 + memory 后端
│   ├── consensus.py             #   ≥2/3 公投共识 + 治理 + 创世引导期豁免
│   ├── agent_engine.py          #   需求驱动智能体 + 记忆封印 + 状态持久化
│   ├── runtime.py               #   创世装配 + 滴答循环 + 19 项审计报告 + 账户系统装配（STORAGE 后端选择）
│   ├── api.py                   #   REST + 有状态会话鉴权 + 账户系统路由 + 速率限制
│   ├── protocol.py              #   机器可读法律模式 + 校验器
│   ├── keys.py                  #   签名密钥管理 + Shamir 分片 + KMS 抽象（文件 / CloudKmsProvider）
│   ├── identity_root.py         #   身份根（第0层）：主密钥 + Shamir 分片托管
│   ├── credentials.py           #   凭证层（第1层）：多设备凭证管理
│   ├── session.py               #   认证层（第2层）：有状态可撤销会话（SessionStore 可插拔）
│   ├── authorization.py         #   授权层（第3层）：分级授权 + 风险引擎
│   └── recovery.py              #   恢复层（第4层）：社交恢复 + 时间锁
├── law/                         # 通信 / 经济 / 身份 / 物理标准
├── tools/                       # 工具脚本
│   ├── gen_gcae_doc.js          #   GCAE 文档生成器
│   ├── md2pdf.py                #   Markdown 转 PDF 工具
│   └── updated_rules.md         #   规则更新记录
├── docs/                        # 技术文档
│   ├── audit_engine_vs_safety_benchmarks.md  # 审计引擎安全基准测试报告
│   └── audit_engine_vs_safety_benchmarks.pdf # PDF 版报告
├── assets/                      # banner.svg/png, overview.svg/png
├── .gitignore
├── LICENSE
└── README.md
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
