<div align="center">
  <img src="assets/banner.png" alt="SPL-Virtual-World-Base 横幅" width="100%" />
</div>

<p align="center">
  <img src="https://img.shields.io/badge/metaverse-D4AF37?style=flat-square" alt="metaverse" />
  <img src="https://img.shields.io/badge/infrastructure-D4AF37?style=flat-square" alt="infrastructure" />
  <img src="https://img.shields.io/badge/constitution-D4AF37?style=flat-square" alt="constitution" />
  <img src="https://img.shields.io/badge/second--perspective-D4AF37?style=flat-square" alt="second-perspective" />
</p>

<p align="center">
  <em>虚拟世界与元宇宙基础设施底座</em>
</p>

<p align="center">
[English](README.md) | 简体中文
</p>

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px; font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #2b2b2b; line-height: 1.8;">

## ✦ 关于

<p style="font-size: 16px; line-height: 1.9; color: #2F2F2F; margin: 0 0 24px;">
  <strong>SPL-VIRTUAL-WORLD-BASE</strong> 是一套可运行的虚拟世界与元宇宙基础设施底座，以「宪法—法律—桥梁」三层架构组织，底层为真实实现层（<code>system/</code>）。它提供：
</p>

<ul>
  <li><strong>端到端账户与世界运行时</strong> — 持久化哈希链账本、≥2/3 公投共识、需求驱动型智能体、无头 tick 循环、REST + WebSocket API，以及多层账户体系（凭证→会话→分级授权→社交恢复），全部真实打通。</li>
  <li><strong>第二视角认知审计引擎</strong> 作为中立裁判 — 19 维合规审查（含功能执行式认证安全维度），可按需对任意世界实例运行审计。</li>
  <li><strong>地理分布式就绪</strong> — 混合逻辑时钟、带切换协议的空间分片、AOI 增量同步、带 Merkle 差分合并的分区防护，以及分层共识（数据中心内快速环 + 跨数据中心 epoch），全部走真实 TCP，并由 3 节点本地集群冒烟测试验证。</li>
  <li><strong>AR / 边缘接入</strong> — 边缘 SDK，支持设备凭证登录、AOI 视口同步、跨数据中心迁移，以及漫游、账户抽象与密钥轮换模块。</li>
</ul>

<div align="center">
  <img src="assets/overview.png" alt="SPL-Virtual-World-Base 总览" width="100%" />
</div>

</div>

<p align="center">— ✦ —</p>

## ✦ 快速开始

```bash
# 主仓库：GitHub（仓库名：Second-Reality）
git clone https://github.com/nohn3043-arch/Second-Reality.git

# 镜像：Gitee
# git clone https://gitee.com/nohn-ecosystem/SPL-virtual-world-core.git

cd Second-Reality

# Python ≥3.8；核心运行时仅需 cryptography（Ed25519 签名）
# pip install cryptography   # GUI 演示额外需要 pygame
# 无 GPU 依赖，无数据库服务依赖 —— 可在任意硬件上运行

# 1. 社会仿真演示（独立内存模式；pygame GUI，60×60 网格，30 个智能体）
python virtual_world.py

# 2. 基础设施验证（无需 GUI）
python smoke_test.py            # 账户/会话/恢复安全路径 —— 约 1 秒
python tools/cluster_smoke.py   # 3 节点本地地理分布式集群 —— 约 14 秒
python tools/edge_smoke.py      # AR 边缘接入路径 —— 小于 1 秒
```

### 编程式启动（参考世界）

```python
from system.runtime import World
from system.keys import generate_user_keypair, build_genesis_proof
from system.ledger import derive_soul_hash

world = World("my-world", data_dir="./my_data")
device = generate_user_keypair()   # 私钥留在设备端，永不上传
genesis_proof = build_genesis_proof(device["secret"], {"genesis_id": "my-first-soul"})
soul_hash = derive_soul_hash(genesis_proof)
world.spawn_agent(soul_hash=soul_hash, genesis_proof=genesis_proof)
world.tick()
print(world.audit_summary())       # 19 维第二视角审计
```

### API 服务

```python
from system.api import serve
serve(world, host="0.0.0.0", port=8000)
```

<p align="center">— ✦ —</p>

## ✦ 架构

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px; font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #2b2b2b; line-height: 1.8;">

架构将规则（只读）、审计器（中立裁判）、实现与演示严格分离：

- <strong>宪法规则</strong>（`constitution_rules.py`）：原始公理与十条治理法则，锁定为根信任锚。`NOHN_LAW_AXIOMS` 是共享常量的唯一权威来源（重力、时间膨胀、单位尺度、灵魂哈希长度、预言机最少源数）。
- <strong>审计引擎</strong>（`audit_engine.py`）：第二视角认知审计器 —— `ResponsibilityAccount` + 可插拔 `AuditPlugin` + `CognitiveAuditEngine`（反事实 `reconstruct()`）+ `SecondPerspectiveAuditor`。运行 19 维合规审查；认证安全维度在隔离的内存世界中功能执行式地验证账户体系，而非仅检查属性。
- <strong>法律</strong>（`law/`）：四份人类可读标准 —— 通信协议 · 统一全球经济（货币、锚定、储备证明、赎回）· 身份认证（绑定灵魂哈希，含 V2.2 凭证恢复条款）· 物理基线。其机器可读 JSON-Schema 对应物位于 `system/protocol.py`，驱动入网校验。
- <strong>系统</strong>（`system/`，23 个模块）：真实实现层 —— 账本、共识、智能体引擎、无头运行时、REST/WS API、协议 Schema、账户体系各层、地理分布子系统、边缘接入。详见下方模块表。
- <strong>桥梁</strong>（`compatibility_bridge.py`）：旧世界进入 Nohn 领地的海关关卡 —— `translate_intent()` 语义清洗、`check_physics_constants()` 验证、`verify_soul_hash()` 身份核验。

### 系统模块（23 个）

**核心运行时**：

| 模块 | 职能 | 备注 |
|---|---|---|
| `runtime.py` | 世界创世组装 + tick 循环 + 因果链 + 快照 | STORAGE 后端选择 |
| `ledger.py` | 持久化账本：灵魂 / 历史哈希链 / 经济 / 快照 + ShardRouter | SQLite（默认）、内存、PostgreSQL |
| `consensus.py` | 提案公投（≥2/3 绝对多数）、治理、创世豁免 | 真实 TCP 传输 |
| `agent_engine.py` | 需求驱动型智能体决策 + HMAC 内存密封 + gas 计量 | 内存不可剥夺保证 |
| `api.py` | REST + WebSocket 服务、质询-响应认证、限流 | 纯标准库 |
| `protocol.py` | 四份法律标准的机器可读 JSON Schema + 入网校验器 | — |
| `keys.py` | Ed25519 密钥、Shamir 秘密共享、KMS 抽象（文件 / 云） | — |

**账户体系**：

| 模块 | 层级 | 职能 |
|---|---|---|
| `credentials.py` | 凭证（L1） | 一灵魂多设备凭证（服务端仅存公钥） |
| `session.py` | 认证（L2） | 有状态访问/刷新令牌，可撤销；存储可插拔（SQLite / 内存 / Redis） |
| `authorization.py` | 授权（L3） | 分级授权（即时 / 延迟 / 多签 / 人工）+ 风险评分 |
| `recovery.py` | 恢复（L4） | 社交恢复（3/5 监护人投票）+ 7 天可撤销时间锁 |
| `identity_root.py` | 身份根（L0） | 主密钥对 + Shamir(3,5) 分片；瘦客户端服务端辅助（`POST /identity/root/generate`，零密钥持久化） |
| `account_abstraction.py` | 会话密钥（ERC-4337 风格） | 带支出限额 / 过期 / 动作范围约束的会话密钥；日常操作用会话密钥通过质询-响应签名 —— 主密钥保持离线（`/aa/*`） |
| `key_rotation.py` | 密钥生命周期 | 服务器签名密钥按计划轮换；令牌嵌入密钥 ID —— 退役密钥继续验证旧令牌，吊销密钥即时失效（`/keys/*`，接入会话签名） |

**地理分布**（作为 horizon-2 子系统接入运行时）：

| 模块 | 职能 |
|---|---|
| `hlc.py` | 混合逻辑时钟 —— 跨节点事件一致排序 |
| `spatial_sharding.py` | 地理分片 + `ShardRouter` + 迁移切换协议 |
| `aoi_sync.py` | 兴趣区增量同步（`AoiTracker` / `DeltaSync` / `SyncScheduler`） |
| `partition_guard.py` | 分区检测、本地自治降级、Merkle 差分树合并 |
| `hierarchical_consensus.py` | 数据中心内快速环 + 跨数据中心 epoch 慢环（最终一致性） |
| `cluster.py` | 集群连线、心跳循环、入站白名单、传输分发器 |

**边缘与漫游**：

| 模块 | 职能 |
|---|---|
| `edge_sdk.py` | AR 眼镜接入：设备凭证注册、质询登录、AOI 视口同步、最近数据中心路由、跨数据中心迁移 |
| `soul_roaming.py` | 跨世界身份漫游：由源世界签发证书，目标世界验证（签名 + 过期 + 灵魂哈希派生 + 可选用户质询-响应），并本地映射灵魂（`/roaming/*`；记忆传输通道待实现） |

**多后端部署（同一代码库，四种后端）**

运行前通过 `STORAGE` 环境变量选择存储后端；默认 `sqlite`：

| STORAGE | 账本 | 会话 | 适用场景 |
|---|---|---|---|
| `sqlite`（默认） | 磁盘 SQLite（`.world_data/`） | 与账本同库 | 单机 / 演示 |
| `memory` | 进程内 `:memory:`（不落盘） | 内存字典 | 测试 / 无状态演示 |
| `redis` | 本地 SQLite | Redis（需 `pip install redis`；缺失则回退到 SQLite） | 多实例共享会话 |
| `postgres` | 通过 psycopg2 连接 PostgreSQL（DSN 来自 `DATABASE_URL` 或 `pg_dsn`） | SQLite | 大规模账本 —— 需要驱动，不静默回退 |

```bash
STORAGE=redis REDIS_URL=redis://cache:6379/0 python -m system.api            # 横向扩展
STORAGE=postgres DATABASE_URL=postgresql://user:pass@db:5432/world python -m system.api
```

部署级抽象支持：`ShardRouter`（按 `soul_hash` 路由，默认单分片）、`SessionStore`（外置会话状态）、`CloudKmsProvider`（云 KMS 信封加密；未注入云客户端时回退文件后端）。多数据中心部署意味着布局分片单元 —— 无需代码改动。

**硬件需求与部署拓扑**

负载为纯 CPU 逻辑仿真（需求状态机 + SHA-256 哈希链 + Ed25519 签名）：无矩阵运算、无本地 LLM 推理、无 GPU 依赖。从树莓派到多数据中心集群均可运行。

| 等级 | 场景 | 参考硬件 | 存储后端 |
|---|---|---|---|
| 最低 | 演示 / 冒烟测试 / 审计追踪 | 1 CPU 核 · 256MB–1GB 内存 | `memory` / `sqlite` |
| 标准 | 百级智能体 + 完整 19 维审计 | 2–4 核 · 2–4GB · SSD | `sqlite` |
| 规模化 | 千级智能体 / 生产多实例 | 4–8 核 · 8–16GB · SSD · Redis/PG | `redis` / `postgres` |

- 单智能体决策为常数时间；世界 tick 为 O(N)（N = 智能体数）。规模化成本在于账本 I/O 与磁盘增长，而非计算。
- 唯一引入外部计算的路径是 LLM 增强（通过外部 API）；本地核心保持低配置。

</div>

<p align="center">— ✦ —</p>

## ✦ 演示与验证

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px;">

<strong>社会仿真演示</strong>（`virtual_world.py`）—— 一个独立内存模式的社会仿真，展示本架构的智能体与经济动力学。它独立于 `system/` 运行（无需基础设施）：

- 60×60 网格世界、30 个初始智能体、80 个资源节点、8 座建筑
- 需求驱动智能体（五级需求模型），含感知 → 思考 → 行动循环与 STM→LTM 记忆巩固
- 经济系统含定期 UBI（每 10 tick）、财富税（每 30）、通胀（每 50）与财富上限规则
- `run_gui()` 用 pygame 渲染实时世界（暂停 / 速度控制 / 智能体检视）；`run_headless(n)` 运行 n 个 tick 并打印统计与合规分数

**验证脚本**（当前全部通过）：

| 脚本 | 范围 | 运行时间 |
|---|---|---|
| `smoke_test.py` | 创世证明 → 灵魂哈希、质询-响应签名、会话签发、单设备吊销、认证安全审计、分片路由器、恢复污染检查 | 约 1 秒 |
| `tools/cluster_smoke.py` | 3 节点本地集群：心跳、epoch 广播、AOI 复制、HLC 收敛、迁移切换、分区降级与恢复 | 约 14 秒 |
| `tools/edge_smoke.py` | 边缘设备：凭证注册、质询登录、AOI 视口增量、最近数据中心路由、跨数据中心迁移、吊销 | 小于 1 秒 |
| `tools/wiring_smoke.py` | 账户抽象（会话密钥签发 → 质询 → 执行 → 约束 → 吊销）、密钥轮换（退役验证 / 吊销失效）、身份根（Shamir 3-of-5 恢复）、灵魂漫游（签发 → 篡改拒绝 → 验证 → 映射） | 约 2 秒 |

<strong>专家评审报告</strong>（`expert_report.py`）—— 将审计器的机器可读裁决与账本哈希锚点导出为本地可复现的 Markdown 报告（见 `reports/`）。报告本身是展示层；每个锚点（哈希 / 裁决）都指向可重新运行的原语，评审者无需信任报告。

</div>

<p align="center">— ✦ —</p>

## ✦ 企业集成

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px;">

本底座是 <strong>协议守护者 + 参考实现</strong>，而非单一运营平台。三种集成路径：

### A. 协议参与者（自托管，数据本地留存）

运行符合四项标准的自研实现。入网前校验：

```python
from system.protocol import ProtocolValidator
ok, failures = ProtocolValidator().validate(world_config)
# ok=True  -> 加入 Nohn 网络
# ok=False -> 隔离在失败层
```

<strong>硬性约束</strong>：原始数据（灵魂、资产、记忆、世界状态）永不离开数据中心。协议层仅交换可验证的证明 —— 哈希、签名、Merkle 根、储备证明。

### B. 参考实现（嵌入式）

直接使用已审计的参考世界 —— 见上方「编程式启动」。私钥保留在设备内存中；账本仅存公钥与哈希。

### C. API 集成（REST + WebSocket）

主要端点：`GET /health`、`GET /world`、`POST /world/tick`、`GET /world/snapshot`、`GET /audit`、`GET /audit/full`、`POST /agent/spawn`、`POST /protocol/validate`、`/auth/*`（质询 → 签发 → 刷新 → 吊销、延迟操作批准/取消/执行）、`/credentials/*`（绑定 / 列表 / 吊销）、`/aa/*`（账户抽象：会话密钥签发 / 列表 / 吊销 / 质询 / 执行）、`/keys/*`（签名密钥列表 / 轮换 / 吊销）、`POST /identity/root/generate`、`/roaming/*`（世界注册 / 证书签发 / 验证 / 映射 / 映射查询）、`/recovery/*`（发起 / 监护人/添加 / 批准 / 取消 / 完成）、`/economy/*`（储备证明 / 发行 / 存入 / 赎回），以及持久化 WebSocket 流 `/ws/world`。

<strong>⚠ 生产加固须知</strong> —— 这是参考实现，而非开箱即用的生产部署。暴露任何实例前，运营方必须自行加固。集成方需补齐的已知缺口：

<ul>
  <li><strong>特权端点的管理闸门</strong>：<code>/keys/rotate</code> 与 <code>/keys/revoke</code> 当前仅要求已认证灵魂 —— 尚无角色模型。请在反向代理处设闸（IP 白名单 / mTLS）或扩展授权层增加管理员角色。若未设闸，恶意认证灵魂可轮换服务器密钥（中断服务）或吊销活跃密钥（大规模会话失效）。</li>
  <li><strong>集群传输安全</strong>：节点间 TCP 传输无 TLS、无节点认证 —— 能连通集群端口的节点可注入投票。请将集群端口限制在私有网段或用 VPN/mesh 前置。</li>
  <li><strong>密钥存储后端</strong>：默认 KMS 是纯文件后端（且 <code>key_rotation</code> 将密钥材料存在账本数据库中）。生产环境请向 <code>CloudKmsProvider</code> 注入真实 KMS 客户端，并以此支撑 <code>KeyRotationManager</code>。</li>
  <li><strong>代理信任</strong>：API 信任 <code>X-Forwarded-For</code> 做限流 —— 仅在可信代理后运行，否则客户端可伪造源 IP。</li>
</ul>

</div>

<p align="center">— ✦ —</p>

## ✦ 项目结构

```text
Second-Reality/
├── constitution_rules.py        # 宪法：公理 + 十条治理法则 + NOHN_LAW_AXIOMS
├── audit_engine.py              # 第二视角审计器：19 维合规审查
├── constitution.py              # 聚合层（向后兼容的再导出）
├── compatibility_bridge.py      # 旧世界"海关"：语义 / 物理 / 灵魂验证
├── virtual_world.py             # 社会仿真演示（独立，pygame GUI / 无头）
├── smoke_test.py                # 账户与会话安全验证
├── expert_report.py             # 专家评审报告导出（审计裁决 + 哈希锚点）
├── system/                      # 真实实现层（23 个模块）
│   ├── runtime.py               #   创世组装 + tick 循环 + STORAGE 选择
│   ├── ledger.py                #   持久化账本 + ShardRouter + PG/内存后端
│   ├── consensus.py             #   ≥2/3 公投共识 + 治理
│   ├── agent_engine.py          #   需求驱动智能体 + 内存密封
│   ├── api.py                   #   REST + WS + 质询-响应认证 + 限流
│   ├── protocol.py              #   机器可读法律 Schema + 校验器
│   ├── keys.py                  #   Ed25519 + Shamir + KMS 抽象
│   ├── credentials.py           #   账户 L1：多设备凭证
│   ├── session.py               #   账户 L2：有状态可撤销会话
│   ├── authorization.py         #   账户 L3：分级授权 + 风险引擎
│   ├── recovery.py              #   账户 L4：社交恢复 + 时间锁
│   ├── identity_root.py         #   账户 L0：主密钥 + Shamir（服务端瘦客户端辅助）
│   ├── account_abstraction.py   #   带支出/过期/范围约束的会话密钥（/aa/*）
│   ├── key_rotation.py          #   服务器签名密钥轮换，接入会话令牌（/keys/*）
│   ├── hlc.py                   #   混合逻辑时钟
│   ├── spatial_sharding.py      #   地理分片 + 迁移切换
│   ├── aoi_sync.py              #   AOI 增量同步
│   ├── partition_guard.py       #   分区检测 + Merkle 差分合并
│   ├── hierarchical_consensus.py#  数据中心内快速环 + 跨数据中心 epoch
│   ├── cluster.py               #   集群连线 + 心跳 + 分发器
│   ├── edge_sdk.py              #   AR / 边缘设备接入 SDK
│   └── soul_roaming.py          #   跨世界漫游证书 + 灵魂映射（/roaming/*）
├── law/                         # 通信 / 经济 / 身份 / 物理标准（文本）
├── tools/                       # cluster_smoke / edge_smoke / 文档生成工具
├── reports/                     # 已导出的专家评审报告
├── assets/                      # banner.svg/png, overview.svg/png
├── .gitignore
├── LICENSE
└── README.md
```

<p align="center">— ✦ —</p>

## ✦ 生态

SPL-VIRTUAL-WORLD-BASE 是 NOHN AI 生态的一员 —— 围绕第二视角因果审计与确定性执行构建的项目家族：

| 项目 | 仓库 | 定位 |
|---|---|---|
| **Second-Perspective (GCAE)** | [nohn3043-arch/second-perspective](https://github.com/nohn3043-arch/second-perspective) | 全球认知审计引擎 —— 五算子因果审计核心（IMDA 95/100） |
| **NOMOS** | [nohn3043-arch/second-perspective](https://github.com/nohn3043-arch/second-perspective)（`Intelligent-Decision-Hub--Nomos` 分支） | 可审计确定性决策中心（IMDA 95/100） |
| **SPL-G1** | [nohn3043-arch/SPL-G1](https://github.com/nohn3043-arch/SPL-G1) | 硬件因果审计可信计算单元（TCU） |
| **SPL-Virtual-World-Base** | [nohn3043-arch/Second-Reality](https://github.com/nohn3043-arch/Second-Reality) | 虚拟世界与元宇宙基础设施（宪法 / 法律 / 桥梁） |
| **Story-Engine** | [nohn3043-arch/story-engine](https://github.com/nohn3043-arch/story-engine) | 长篇叙事一致性引擎 |
| **Antares** | [nohn3043-arch/Antares](https://github.com/nohn3043-arch/Antares) | GFSIP v1.0 —— 带因果审计的联邦稳定互操作协议 |
| **Anthropomorphic-Agent-Engine** | [nohn3043-arch/Anthropomorphic-Agent-Engine](https://github.com/nohn3043-arch/Anthropomorphic-Agent-Engine) | 确定性拟人心理学引擎（SPL Pure Core V8.0） |
| **PAGES** | [nohn3043-arch/pages](https://github.com/nohn3043-arch/pages) | NOHN AI 生态官方落地页 |

<p align="center">— ✦ —</p>

## ✦ 许可与授权

本仓库 <strong>不是开源软件</strong>。双轨模式：个人非商业研究免费；政府 / 企业使用需付费商业许可。参见 [LICENSE](./LICENSE)。

<strong>商标声明</strong>：「Nohn™」与「Second Perspective™」为虚拟世界领域的未注册商标，受反不正当竞争法与普通法假冒原则保护。任何未经授权的商业使用均构成侵权。

<strong>许可咨询</strong>：国际 / 全球 — [ai@nohnlins.com](mailto:ai@nohnlins.com) · 中国 — [lin@secondai.top](mailto:lin@secondai.top)

<p align="center">
  <a href="https://github.com/nohn3043-arch">GitHub</a>
  &nbsp;·&nbsp;
  <a href="https://www.nohnlins.com/">nohnlins.com</a>
  &nbsp;·&nbsp;
  <a href="mailto:ai@nohnlins.com">ai@nohnlins.com</a>
</p>
<p align="center"><sub>NOHN AI · SPL-VIRTUAL-WORLD-BASE</sub></p>
