<p align="center">
  <img src="assets/banner.png" alt="SPL-Virtual-World-Base banner" style="width:100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/metaverse--D4AF37?style=flat-square" alt="metaverse">  <img src="https://img.shields.io/badge/infrastructure--D4AF37?style=flat-square" alt="infrastructure">  <img src="https://img.shields.io/badge/constitution--D4AF37?style=flat-square" alt="constitution">
</p>

<blockquote align="center">
  <em>虚拟世界与元宇宙基础设施底座</em>
</blockquote>

<div style="max-width:880px;margin:0 auto;padding:0 16px">

## ✦ 关于

<p style="font-size:15px;line-height:1.8;color:#2C2C2C">SPL-VIRTUAL-WORLD-BASE 是虚拟世界与元宇宙的基础设施框架，构建于「宪法 / 法律 / 审计 / 系统」四层架构之上，为虚拟空间提供可治理、可互操作、可演进的运行时底座。它支持不同世界之间资产、规则与智能体的稳定桥接与协作。</p>

<p align="center">
  <img src="assets/overview.png" alt="SPL-Virtual-World-Base overview" style="width:100%">
</p>

</div>

<p align="center">— ✦ —</p>

## ✦ 快速开始

```bash
git clone git@github.com:NOHN-AI/SPL-virtual-world-base.git
cd SPL-virtual-world-base
# 纯 Python ≥3.8，仅标准库，无需安装任何依赖
# 启动 GUI 演示（需要图形环境；默认生成两个内置智能体）
python virtual_world.py
```

程序化启动：

```python
from virtual_world import NohnWorld, NohnVisualApp
nexus = NohnWorld()
nexus.spawn("Explorer_01", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
NohnVisualApp(nexus).root.mainloop()
```

<p align="center">— ✦ —</p>

## ✦ 架构

<div style="max-width:880px;margin:0 auto;padding:0 16px">

系统按四层分离组织，确保规则（只读）、审计员（中立裁判）、系统（实现）、演示客户端互不混层：

- **宪法规则**（`constitution_rules.py`）—— 世界的原始公理与十条治理法则，永久锁定为根信任锚点。`NOHN_LAW_AXIOMS` 是所有常量的唯一权威来源。
- **审计引擎**（`audit_engine.py`）—— 第二视角认知审计器（`ResponsibilityAccount` + 可插拔 `AuditPlugin` + `SecondPerspectiveAuditor` 18 项合规审查）。它是裁判，不是世界本体。
- **法律**（`law/`）—— 四大标准层：
  - 通信协议规范
  - 全球经济统一标准 —— 货币、锚定、储备证明、赎回
  - 身份确权规范 —— 灵魂哈希绑定身份
  - 物理基准规范 —— 重力 / 时间 / 尺度常数
- **系统**（`system/`）—— 真实实现层：持久化账本、≥2/3 公投共识、智能体引擎、无头运行时、REST/WS API、机器可读协议 Schema、生产级安全。
- **桥接**（`compatibility_bridge.py`）—— 旧世界进入 Nohn 领地的唯一「海关」：
  - `translate_intent()` —— 语义洗白：将厂商私有指令映射到 Nohn 标准词汇表，剥夺隐藏解释权。
  - `check_physics_constants()` —— 拒绝物理常数偏离 `NOHN_LAW_AXIOMS` 的世界。
  - `verify_soul_hash()` —— 依据灵魂哈希锚点校验身份。

演示运行时（`virtual_world.py`）将这些组件与 `EconomySystem`、`TaskGenerator`、`NohnAgent` 串联，并挂载在真实的 `system.World` 之上。

</div>

## ✦ 企业使用

本底座是「协议监护人 + 参考实现」，不是单一运营方平台。企业可通过以下三种方式接入：

### A. 协议参与者（自托管，数据留在本地）

在自己的数据中心运行自有实现，遵循 `law/` 四大标准，并在并网前通过审查：

```python
from system.protocol import ProtocolValidator

ok, failures = ProtocolValidator().validate(world_config)
# ok=True  -> 并网加入 Nohn 网络
# ok=False -> 在失败层被隔离
```

**硬约束**：你的原始数据（灵魂、资产、记忆、世界状态）永不离开你的数据中心。协议层只交换可验证证明 —— 哈希、签名、Merkle 根、储备证明 —— 绝不交换原始数据。

### B. 参考实现（嵌入式）

直接使用已审计的参考世界：

```python
from system.runtime import World

world = World("my-world", data_dir="./my_data")
world.spawn_agent("ab" * 32)
world.tick()
print(world.audit_summary())   # 18 项第二视角审计
```

### C. API 集成（REST + WebSocket）

启动服务并通过 HTTP 集成：

```python
from system.api import serve
serve(world, host="0.0.0.0", port=8000)
```

关键端点：`GET /health`、`GET /world`、`GET /audit`、`POST /protocol/validate`、`POST /agent/spawn`、`POST /auth/issue`、`GET/POST /economy/*`、`WS /ws/world`。

### 定制边界

企业特有差异落在「配置层」（行业参数、司法辖区、部署拓扑）—— 绝不触碰核心宪法、审计、共识规则，这些对所有企业保持完全一致。

<p align="center">— ✦ —</p>

## ✦ 项目结构

```
SPL-Virtual-world-base/
├── constitution_rules.py        # 宪法规则：公理 + 十条治理法则 + NOHN_LAW_AXIOMS
├── audit_engine.py              # 第二视角审计器：18 项合规审查
├── constitution.py              # 薄聚合层（向后兼容 re-export）
├── compatibility_bridge.py      # 旧世界「海关」：语义洗白 + 物理/灵魂校验
├── virtual_world.py             # 演示运行时（GUI/headless），挂载于 system.World
├── system/                      # 真实实现层
│   ├── ledger.py                #   持久化灵魂/历史/经济账本（SQLite）
│   ├── consensus.py             #   ≥2/3 公投共识 + 治理
│   ├── agent_engine.py          #   需求驱动智能体 + 记忆封存
│   ├── runtime.py               #   创世装配 + tick 循环 + 审计上报
│   ├── api.py                   #   REST + WebSocket + HMAC 鉴权
│   ├── protocol.py              #   机器可读法律 Schema + 验证器
│   └── keys.py                  #   签名密钥管理
├── law/                         # 通信 / 经济 / 身份 / 物理标准
├── assets/                      # banner.svg/png, overview.svg/png
└── LICENSE
```

## ✦ 许可与授权

本仓库**非开源**。双轨制：个人非商业研究免费；政府/企业需付费商业授权。详见 [LICENSE](./LICENSE)。

**商标声明**：「Nohn™」与「Second Perspective™」是虚拟世界领域的未注册商标，受反不正当竞争法与普通法仿冒原则保护。任何未经授权的商业使用均构成侵权。

**授权咨询**：
- 国际/全球：ai@nohnlins.com
- 中国：lin@secondai.top

<p align="center">
  <a href="https://github.com/NOHN-AI">NOHN-AI</a>
  &nbsp;·&nbsp;
  <a href="https://www.nohnlins.com/">nohnlins.com</a>
  &nbsp;·&nbsp;
  <a href="mailto:ai@nohnlins.com">ai@nohnlins.com</a>
</p>
<p align="center"><sub>NOHN AI · SPL-VIRTUAL-WORLD-BASE</sub></p>
