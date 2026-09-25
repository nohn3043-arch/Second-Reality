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
  <em>虚拟世界与元宇宙基础设施基座</em>
</p>

<p align="center">
[English](README.md) | 简体中文
</p>

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px; font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #2b2b2b; line-height: 1.8;">

## ✦ 关于

<p style="font-size: 16px; line-height: 1.9; color: #2F2F2F; margin: 0 0 24px;">
  <strong>SPL-VIRTUAL-WORLD-BASE</strong> 是一个可运行的虚拟世界与元宇宙基础设施基座，以"宪法 — 法律 — 桥"三级栈组织，并在其下配有真实实现层（<code>system/</code>）。它交付：
</p>

<ul>
  <li><strong>端到端的账户与世界运行时</strong> —— 持久化哈希链账本、≥2/3 公投共识、需求驱动智能体、无头 tick 循环、REST + WebSocket API，以及多层账户系统（凭据 → 会话 → 分级授权 → 社交恢复）已被真正打通。</li>
  <li><strong>第二视角认知审计器</strong>作为中立裁判 —— 一套 19 维合规审查（含一个功能性执行的认证安全维度），可按需对任意世界实例运行。</li>
  <li><strong>地理分布式就绪</strong> —— 混合逻辑时钟、带迁移交接的空间分片、AOI 增量同步、带 Merkle 差异合并的分区守护，以及分层共识（数据中心内快环 + 跨数据中心 epoch），全部走真实 TCP，并经 3 节点本地集群冒烟测试验证。</li>
  <li><strong>AR / 边缘接入</strong> —— 用于设备凭据登录、AOI 视口同步与跨数据中心迁移的 Edge SDK，另有漫游、账户抽象与密钥轮换模块。</li>
</ul>

<div align="center">
  <img src="assets/overview.png" alt="SPL-Virtual-World-Base 概览" width="100%" />
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
python smoke_test.py            # 账户/会话/恢复 安全路径 —— 约 1 秒
python tools/cluster_smoke.py   # 3 节点本地地理分布式集群 —— 约 14 秒
python tools/edge_smoke.py      # AR 边缘接入路径 —— <1 秒
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

本栈将规则（只读）、审计器（中立裁判）、实现与演示严格分离：

- <strong>宪法规则</strong>（`constitution_rules.py`）：原始公理与十条治理法，锁定为根信任锚。`NOHN_LAW_AXIOMS` 是共享常量的唯一权威来源（重力、时间膨胀、单位尺度、灵魂哈希长度、预言机最小信源数）。
- <strong>审计引擎</strong>（`audit_engine.py`）：第二视角认知审计器 —— `ResponsibilityAccount` + 可插拔 `AuditPlugin` + `CognitiveAuditEngine`（反事实 `reconstruct()`）+ `SecondPerspectiveAuditor`。运行 19 维合规审查；其中认证安全维度是在隔离的内存世界中功能性执行账户栈，而非探测属性。
- <strong>法律</strong>（`law/`）：四份人类可读标准 —— 通信协议 · 全球统一经济（货币、锚定、储备证明、兑付） · 身份认证（绑定灵魂哈希，含 V2.2 凭据恢复条款） · 物理基线。其机器可读的 JSON-Schema 对应物位于 `system/protocol.py`，驱动入驻校验。
- <strong>系统</strong>（`system/`，23 个模块）：真实实现层 —— 账本、共识、智能体引擎、无头运行时、REST/WS API、协议 schema、账户系统各层、地理分布子系统与边缘接入。见下方模块表。
- <strong>桥</strong>（`compatibility_bridge.py`）：遗留世界进入 Nohn 领地的海关检查站 —— `translate_intent()` 语义清洗、`check_physics_constants()` 物理校验、`verify_soul_hash()` 身份核验。

### 系统模块（23 个）

核心运行时：

| 模块 | 职责 | 备注 |
|---|---|---|
| `runtime.py` | 世界创世装配 + tick 循环 + 因果链 + 快照 | STORAGE 后端选择 |
| `ledger.py` | 持久化账本：灵魂 / 历史哈希链 / 经济 / 快照 + ShardRouter | SQLite（默认）、内存、PostgreSQL |
| `consensus.py` | 提案公投（≥2/3 超级多数）、治理、创世引导豁免 | 真实 TCP 传输 |
| `agent_engine.py` | 需求驱动智能体决策 + HMAC 记忆密封 + gas 计量 | 记忆不可剥夺保证 |
| `api.py` | REST + WebSocket 服务、挑战-应答认证、限流 | 纯标准库 |
| `protocol.py` | 四份法律标准的机器可读 JSON Schema + 入驻校验器 | — |
| `keys.py` | Ed25519 密钥、Shamir 秘密共享、KMS 抽象（文件 / 云） | — |

账户系统：

| 模块 | 层 | 职责 |
|---|---|---|
| `credentials.py` | 凭据（L1） | 一灵魂、多设备凭据（服务端仅存公钥） |
| `session.py` | 认证（L2） | 有状态访问/刷新令牌，可撤销；存储可插拔（SQLite / Memory / Redis） |
| `authorization.py` | 授权（L3） | 分级授权（即时 / 延迟 / 多签 / 人工）+ 风险评分 |
| `recovery.py` | 恢复（L4） | 社交恢复（3/5 守护人投票）+ 7 天可取消时间锁 |
| `identity_root.py` | 身份根（L0） | 主密钥对 + Shamir(3,5) 分享；面向瘦客户端的服务端助手（`POST /identity/root/generate`，零密钥材料留存） |
| `account_abstraction.py` | 会话密钥（ERC-4337 风格） | 带花费上限 / 有效期 / 动作范围约束的会话密钥；日常操作通过会话密钥以挑战-应答签名 —— 主密钥保持离线（`/aa/*`） |
| `key_rotation.py` | 密钥生命周期 | 服务端签名密钥按计划轮换；令牌内嵌密钥 ID —— 退役密钥仍可验证旧令牌，撤销密钥立即失效（`/keys/*`，并接入会话签名） |

地理分布式（作为 horizon-2 子系统接入运行时）：

| 模块 | 职责 |
|---|---|
| `hlc.py` | 混合逻辑时钟 —— 一致的跨节点事件排序 |
| `spatial_sharding.py` | 地理分片 + `ShardRouter` + 迁移交接协议 |
| `aoi_sync.py` | 兴趣区域增量同步（`AoiTracker` / `DeltaSync` / `SyncScheduler`） |
| `partition_guard.py` | 分区检测、本地自治降级、Merkle 差异树合并 |
| `hierarchical_consensus.py` | 数据中心内快环 + 跨数据中心 epoch 慢环（最终一致） |
| `cluster.py` | 集群接线、心跳循环、入站白名单、传输分发器 |

边缘与漫游：

| 模块 | 职责 |
|---|---|
| `edge_sdk.py` | AR 眼镜接入：设备凭据登记、挑战登录、AOI 视口同步、最近数据中心路由、跨数据中心迁移 |
| `soul_roaming.py` | 跨世界身份漫游：由源世界签发的证书，由目标世界验证（签名 + 有效期 + 灵魂哈希派生 + 可选用户挑战-应答），含本地灵魂映射（`/roaming/*`；记忆传输通道尚在建设中） |

**多后端部署（同一套代码，四种后端）**

运行前通过 `STORAGE` 环境变量选择存储后端；默认 `sqlite`：

| STORAGE | 账本 | 会话 | 适用场景 |
|---|---|---|---|
| `sqlite`（默认） | 磁盘 SQLite（`.world_data/`） | 与账本同一数据库 | 单机 / 演示 |
| `memory` | 进程内 `:memory:`（无磁盘） | 内存字典 | 测试 / 无状态演示 |
| `redis` | 本地 SQLite | Redis（需 `pip install redis`；缺失时回退 SQLite） | 多实例共享会话 |
| `postgres` | 经 psycopg2 的 PostgreSQL（DSN 来自 `DATABASE_URL` 或 `pg_dsn`） | SQLite | 大规模账本 —— 需驱动，不会静默回退 |

```bash
STORAGE=redis REDIS_URL=redis://cache:6379/0 python -m system.api            # 横向扩展
STORAGE=postgres DATABASE_URL=postgresql://user:pass@db:5432/world python -m system.api
```

支撑性部署抽象：`ShardRouter`（按 `soul_hash` 路由，默认单分片）、`SessionStore`（会话状态外置）、`CloudKmsProvider`（云 KMS 信封加密；未注入云客户端时回退文件后端）。多数据中心部署即铺排分片单元 —— 而非改代码。

**硬件要求与部署拓扑**

工作负载为纯 CPU 逻辑仿真（需求状态机 + SHA-256 哈希链 + Ed25519 签名）：无矩阵运算、无本地 LLM 推理、无 GPU 依赖。从树莓派到多数据中心集群皆可运行。

| 档位 | 场景 | 参考硬件 | 存储后端 |
|---|---|---|---|
| 最低 | 演示 / 冒烟测试 / 审计留痕 | 1 核 · 256MB–1GB RAM | `memory` / `sqlite` |
| 标准 | 百级智能体 + 完整 19 维审计 | 2–4 核 · 2–4GB · SSD | `sqlite` |
| 规模 | 千级智能体 / 生产多实例 | 4–8 核 · 8–16GB · SSD · Redis/PG | `redis` / `postgres` |

- 单智能体决策为常数时间；世界 tick 为 O(N)（N 为智能体数）。规模的成本在账本 I/O 与磁盘增长，而非算力。
- 唯一引入外部算力的路径是 LLM 增强（经外部 API）；本地核心保持低配置。

</div>

<p align="center">— ✦ —</p>

## ✦ 演示与验证

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px;">

**社会仿真演示**（`virtual_world.py`）—— 一个独立的内存社会仿真，演示本栈的智能体与经济动态。它独立于 `system/` 运行（无需基础设施）：

- 60×60 网格世界，30 个初始智能体，80 个资源节点，8 座建筑
- 需求驱动智能体（五级需求模型），含 感知 → 思考 → 行动 循环与 STM→LTM 记忆固化
- 经济含周期性 UBI（每 10 tick）、财富税（每 30）、通胀（每 50），以及财富硬顶规则
- `run_gui()` 用 pygame 渲染实时世界（暂停 / 调速 / 智能体检视）；`run_headless(n)` 运行 n 个 tick 并打印统计与合规得分

**验证脚本**（当前全部通过）：

| 脚本 | 范围 | 运行时长 |
|---|---|---|
| `smoke_test.py` | 创世证明 → 灵魂哈希、挑战-应答签名、会话签发、逐设备撤销、认证安全审计、分片路由、恢复污染检查 | 约 1 秒 |
| `tools/cluster_smoke.py` | 3 节点本地集群：心跳、epoch 广播、AOI 复制、HLC 收敛、迁移交接、分区降级与恢复 | 约 14 秒 |
| `tools/edge_smoke.py` | 边缘设备：凭据登记、挑战登录、AOI 视口增量、最近数据中心路由、跨数据中心迁移、撤销 | <1 秒 |
| `tools/wiring_smoke.py` | 账户抽象（会话密钥签发 → 挑战 → 执行 → 约束 → 撤销）、密钥轮换（退役可验证 / 撤销即失效）、身份根（Shamir 3-of-5 恢复）、灵魂漫游（签发 → 篡改拒绝 → 验证 → 映射） | 约 2 秒 |

**专家评审报告**（`expert_report.py`）—— 将审计器的机器可读裁定连同账本哈希锚点导出为本地可复现的 Markdown 报告（见 `reports/`）。报告本身只是展示层；每个锚点（哈希 / 裁定）都指向可重跑的原始操作，因此评审者永远无需信任报告本身。

</div>

<p align="center">— ✦ —</p>

## ✦ 企业集成

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px;">

本基座是<strong>协议守护者 + 参考实现</strong>，而非单一运营方平台。三条集成路径：

### A. 协议参与者（自托管，数据本地留存）

运行一套符合四项标准的自研实现。入驻前先校验：

```python
from system.protocol import ProtocolValidator
ok, failures = ProtocolValidator().validate(world_config)
# ok=True  -> 加入 Nohn 网络
# ok=False -> 隔离在失败层
```

<strong>硬约束</strong>：原始数据（灵魂、资产、记忆、世界状态）永不离开数据中心。协议层仅交换可验证证明 —— 哈希、签名、Merkle 根、储备证明。

### B. 参考实现（嵌入式）

直接使用已审计的参考世界 —— 见上文"编程式启动"。私钥留在设备内存中；账本只存公钥与哈希。

### C. API 集成（REST + WebSocket）

关键端点：`GET /health`、`GET /world`、`POST /world/tick`、`GET /world/snapshot`、`GET /audit`、`GET /audit/full`、`POST /agent/spawn`、`POST /protocol/validate`、`/auth/*`（挑战 → 签发 → 刷新 → 撤销，延迟操作 批准/取消/处理）、`/credentials/*`（绑定 / 列出 / 撤销）、`/aa/*`（账户抽象：会话密钥 签发 / 列出 / 撤销 / 挑战 / 执行）、`/keys/*`（签名密钥 列出 / 轮换 / 撤销）、`POST /identity/root/generate`、`/roaming/*`（世界注册 / 证书签发 / 验证 / 映射 / 映射查询）、`/recovery/*`（发起 / 添加守护人 / 批准 / 取消 / 完成）、`/economy/*`（por / 发行 / 存入 / 兑付），以及持久化 WebSocket 流 `/ws/world`。

<strong>⚠ 生产加固提示</strong> —— 这是参考实现，不是开箱即用的生产部署。在暴露任何实例前，运营方必须自行加固。集成方应补齐的已知缺口：

<ul>
  <li><strong>特权端点的管理员管控</strong>：<code>/keys/rotate</code> 与 <code>/keys/revoke</code> 当前仅需一个已认证灵魂 —— 尚无角色模型。请在反向代理层加以管控（IP 白名单 / mTLS），或扩展授权层加入管理员角色。若不加管控，一个恶意的已认证灵魂即可轮换服务端密钥（造成中断）或撤销在用密钥（导致大规模会话失效）。</li>
  <li><strong>集群传输安全</strong>：节点间 TCP 传输无 TLS、无节点认证 —— 能连到集群端口的节点即可注入投票。请将集群端口限制在私有网段，或以 VPN/mesh 前置。</li>
  <li><strong>密钥存储后端</strong>：默认 KMS 为纯文件后端（且 <code>key_rotation</code> 将密钥材料存于账本数据库）。生产环境应向 <code>CloudKmsProvider</code> 注入真实 KMS 客户端，并以之支撑 <code>KeyRotationManager</code>。</li>
  <li><strong>代理信任</strong>：API 信任 <code>X-Forwarded-For</code> 用于限流 —— 只应运行在受信代理之后，否则客户端可伪造源 IP。</li>
</ul>

</div>

<p align="center">— ✦ —</p>

## ✦ 项目结构

```text
Second-Reality/
├── constitution_rules.py        # 宪法：公理 + 十条治理法 + NOHN_LAW_AXIOMS
├── audit_engine.py              # 第二视角审计器：19 维合规审查
├── constitution.py              # 聚合层（向后兼容的再导出）
├── compatibility_bridge.py      # 遗留世界"海关"：语义 / 物理 / 灵魂 校验
├── virtual_world.py             # 社会仿真演示（独立，pygame GUI / 无头）
├── smoke_test.py                # 账户与会话安全验证
├── expert_report.py             # 专家评审报告导出（审计器裁定 + 哈希锚点）
├── system/                      # 真实实现层（23 个模块）
│   ├── runtime.py               #   创世装配 + tick 循环 + STORAGE 选择
│   ├── ledger.py                #   持久化账本 + ShardRouter + PG/内存后端
│   ├── consensus.py             #   ≥2/3 公投共识 + 治理
│   ├── agent_engine.py          #   需求驱动智能体 + 记忆密封
│   ├── api.py                   #   REST + WS + 挑战-应答认证 + 限流
│   ├── protocol.py              #   机器可读法律 schema + 校验器
│   ├── keys.py                  #   Ed25519 + Shamir + KMS 抽象
│   ├── credentials.py           #   账户 L1：多设备凭据
│   ├── session.py               #   账户 L2：有状态可撤销会话
│   ├── authorization.py         #   账户 L3：分级授权 + 风险引擎
│   ├── recovery.py              #   账户 L4：社交恢复 + 时间锁
│   ├── identity_root.py         #   账户 L0：主密钥 + Shamir（服务端瘦客户端助手）
│   ├── account_abstraction.py   #   带花费/有效期/范围约束的会话密钥（/aa/*）
│   ├── key_rotation.py          #   服务端签名密钥轮换，接入会话令牌（/keys/*）
│   ├── hlc.py                   #   混合逻辑时钟
│   ├── spatial_sharding.py      #   地理分片 + 迁移交接
│   ├── aoi_sync.py              #   AOI 增量同步
│   ├── partition_guard.py       #   分区检测 + Merkle 差异合并
│   ├── hierarchical_consensus.py#   数据中心内快环 + 跨数据中心 epoch
│   ├── cluster.py               #   集群接线 + 心跳 + 分发器
│   ├── edge_sdk.py              #   AR / 边缘设备接入 SDK
│   └── soul_roaming.py          #   跨世界漫游证书 + 灵魂映射（/roaming/*）
├── law/                         # 通信 / 经济 / 身份 / 物理 标准（文本）
├── tools/                       # cluster_smoke / edge_smoke / 文档生成工具
├── reports/                     # 导出的专家评审报告
├── assets/                      # banner.svg/png、overview.svg/png
├── .gitignore
├── LICENSE
└── README.md
```

<p align="center">— ✦ —</p>

## ✦ 生态

SPL-VIRTUAL-WORLD-BASE 是 NOHN AI 生态的一员 —— 一个围绕第二视角因果审计与确定性执行构建的项目家族：

| 项目 | 仓库 | 角色 |
|---|---|---|
| **Second-Perspective (GCAE)** | [nohn3043-arch/second-perspective](https://github.com/nohn3043-arch/second-perspective) | 全局认知审计引擎 —— 五算子因果审计内核（IMDA 95/100） |
| **NOMOS** | [nohn3043-arch/second-perspective](https://github.com/nohn3043-arch/second-perspective)（`Intelligent-Decision-Hub--Nomos` 分支） | 可审计的确定性决策中枢（IMDA 95/100） |
| **SPL-G1** | [nohn3043-arch/SPL-G1](https://github.com/nohn3043-arch/SPL-G1) | 硬件因果审计可信计算单元（TCU） |
| **SPL-Virtual-World-Base** | [nohn3043-arch/Second-Reality](https://github.com/nohn3043-arch/Second-Reality) | 虚拟世界与元宇宙基础设施（宪法 / 法律 / 桥） |
| **Story-Engine** | [nohn3043-arch/story-engine](https://github.com/nohn3043-arch/story-engine) | 长篇叙事一致性引擎 |
| **Antares** | [nohn3043-arch/Antares](https://github.com/nohn3043-arch/Antares) | GFSIP v1.0 —— 带因果审计的联邦稳定互操作协议 |
| **Anthropomorphic-Agent-Engine** | [nohn3043-arch/Anthropomorphic-Agent-Engine](https://github.com/nohn3043-arch/Anthropomorphic-Agent-Engine) | 确定性拟人心理引擎（SPL Pure Core V8.0） |
| **PAGES** | [nohn3043-arch/pages](https://github.com/nohn3043-arch/pages) | NOHN AI 生态官方落地页 |

<p align="center">— ✦ —</p>

## ✦ 许可与授权

本仓库<strong>并非开源</strong>。双轨模式：个人非商业研究免费；政府 / 企业使用需付费商业许可。详见 [LICENSE](./LICENSE)。

<strong>商标声明</strong>："Nohn™" 与 "Second Perspective™" 是虚拟世界领域的未注册商标，受反不正当竞争法与普通法假冒（passing-off）原则保护。任何未经授权的商业使用均构成侵权。

<strong>许可咨询</strong>：国际 / 全球 —— [ai@nohnlins.com](mailto:ai@nohnlins.com) · 中国 —— [lin@secondai.top](mailto:lin@secondai.top)

<p align="center">
  <a href="https://github.com/nohn3043-arch">GitHub</a>
  &nbsp;·&nbsp;
  <a href="https://www.nohnlins.com/">nohnlins.com</a>
  &nbsp;·&nbsp;
  <a href="mailto:ai@nohnlins.com">ai@nohnlins.com</a>
</p>
<p align="center"><sub>NOHN AI · SPL-VIRTUAL-WORLD-BASE</sub></p>
