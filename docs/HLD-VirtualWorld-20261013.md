# HLD — 拟真虚拟世界架构设计

> **文档类型**：High-Level Design  
> **版本**：v0.2（涌现式目标 + 3D路径）  
> **日期**：2026-10-13  
> **基座仓库**：second-reality  
> **状态**：草案

---

## 1. 设计目标

### 1.1 核心命题

构建一个**拟真开放世界**，玩家不跟随剧本，而是在约束系统中自主行动，事件由 agent 间交互自发涌现。玩家目标由世界状态和需求驱动**动态涌现**，非预设任务树。

### 1.2 设计原则

| 原则    | 含义                                      | 来源                                  |
| ----- | --------------------------------------- | ----------------------------------- |
| 拟真性   | 世界运行遵循内禀物理/经济/社会规则，非脚本驱动                | second-reality 仿真引擎                 |
| 确定性   | 同 seed + 同 config → 同世界，逐字节可复现          | second-reality `verify_determinism` |
| 资产永续  | 玩境可毁，资产不灭；玩家离线后世界继续运行                   | 内容寻址存储 + 链上锚定                       |
| 世界唯一性 | 每个玩家拥有独立 seed，世界拓扑/资源/人口各不相同            | seed 分叉机制                           |
| 无剧本   | 无任务树、无主线、无 NPC 对白脚本；事件由 agent 需求驱动自发触发  | 五层需求模型                              |
| 涌现式目标 | 玩家目标由 `(玩家状态, 世界状态, NPC状态)` 三元组动态生成，非预设 | GoalGenerator                       |
| 软约束   | 约束存在但可违反，违反有代价（违规计数/声誉下降），非硬墙           | constitution_rules                  |
| 可暂停   | 玩家可随时暂停/退出，世界状态冻结，再次进入从冻结点恢复            | `save_state` / `export_state`       |

### 1.3 非目标

- **不做魂类难度**：无精确弹反/体力条/死亡惩罚循环
- **不做MMO统一世界**：每个玩家世界独立，不做跨世界同步
- **不做预设任务系统**：无任务面板/无目标指引/无奖励队列；目标由世界状态涌现

---

## 2. 系统架构

### 2.1 分层架构

```
┌─────────────────────────────────────────────────┐
│                 渲染层 (Render)                   │
│  PC: pygame / OpenGL     Mobile: WebGL / Canvas  │
├─────────────────────────────────────────────────┤
│               交互层 (Interaction)                │
│  输入映射 / 摄像机 / 选择 / UI 面板               │
├─────────────────────────────────────────────────┤
│              仿真层 (Simulation)                  │
│  World Engine (tick) / Agent AI / Economy /       │
│  Constitution / Event System                     │
├─────────────────────────────────────────────────┤
│             持久化层 (Persistence)                │
│  本地存档 / 内容寻址存储 / 链上锚定               │
├─────────────────────────────────────────────────┤
│             基础层 (Foundation)                   │
│  确定性 RNG / 数据模型 / 序列化 / 哈希链          │
└─────────────────────────────────────────────────┘
```

### 2.2 模块映射（second-reality → 虚拟世界）

| second-reality 模块    | 虚拟世界复用                     | 改动                            |
| -------------------- | -------------------------- | ----------------------------- |
| `NohnWorld`          | `GameWorld`                | 增加玩家 agent、摄像机、区块加载           |
| `Agent`              | `NpcAgent` + `PlayerAgent` | Player 增加输入控制、视角、背包           |
| `EconomicReserve`    | `Economy`                  | 不变，直接复用                       |
| `constitution_rules` | `ConstraintSystem`         | 19 维审计 → 约束违反有视觉反馈            |
| `Memory` (STM/LTM)   | `AgentMemory`              | 不变，直接复用                       |
| `WorldConfig`        | `WorldConfig`              | 增加 `player_seed`、`chunk_size` |
| `state_hash`         | `WorldFingerprint`         | 不变，用于资产锚定                     |
| `verify_determinism` | `ReproducibilityCheck`     | 不变                            |

---

## 3. 核心机制

### 3.1 世界生成

**种子分叉**：玩家进入时生成唯一 seed，世界从该 seed 确定性展开。

```
world_seed = SHA256(player_id || player_seed || genesis_time)
config = WorldConfig(world_size, initial_agents, initial_resources, ...)
world = GameWorld(config, seed=world_seed)
```

- 世界拓扑（地形/资源分布/建筑位置）由 seed 完全确定
- 不同玩家 seed 不同 → 世界各不相同
- 同一玩家同一 seed → 世界逐字节可复现

### 3.2 Agent 模型

**NPC Agent**（复用 second-reality `Agent`）：

| 属性                           | 说明                                                         | 来源                    |
| ---------------------------- | ---------------------------------------------------------- | --------------------- |
| needs                        | 五层需求 (生理/安全/归属/尊重/自我实现)                                    | Maslow 层级             |
| state                        | idle/working/socializing/resting/trading/learning/creating | 行为状态机                 |
| memory                       | STM → LTM 巩固 + 衰减                                          | second-reality Memory |
| wealth                       | 财富（劳动铸币，非无限刷）                                              | EconomicReserve       |
| knowledge / creativity       | 知识与创造力，随学习/创造行为增长                                          | Agent 属性              |
| friends / partner / children | 社会关系网络                                                     | Agent 属性              |
| violations                   | 约束违反计数                                                     | constitution_rules    |

**Player Agent**（已实现）：

| 属性              | 说明                      | 状态    |
| --------------- | ----------------------- | ----- |
| fx / fy         | 浮点坐标（自由移动，非网格跳跃）        | ✅     |
| speed           | 移动速度                    | ✅     |
| inventory       | 背包（物品堆叠）                | ✅     |
| owned_buildings | 拥有的建筑列表                 | ✅     |
| action_mode     | observe / build / trade | ✅     |
| needs           | 五层需求（衰减 + 采集恢复）         | ✅     |
| wealth / energy | 财富与精力                   | ✅     |
| active_goals    | 涌现式目标列表                 | ⏳ 待开发 |

### 3.3 事件系统（无剧本）

**核心：事件不预设，由 agent 需求驱动自发涌现。**

事件触发链：

```
agent.needs[某层] < 阈值
  → agent 决策（基于记忆/知识/当前状态）
    → agent 执行行为（采集/交易/社交/建造/创造）
      → 行为产生事件（produce/trade/interact/build/create）
        → 事件影响世界状态（资源减少/财富转移/关系变化）
          → 其他 agent 感知变化 → 触发新决策
```

- 无任务树，无触发器脚本
- 玩家行为也是事件源，NPC 会感知并反应
- 事件链可级联：A 采集 → B 发现资源减少 → B 迁移 → C 发现 B 离开 → C 调整社交

### 3.4 涌现式目标系统

**核心：目标不预设，由 `(玩家状态, 世界状态, NPC状态)` 三元组动态生成。**

目标生成器（`GoalGenerator`）每 tick 检查触发条件，自动加入/移除玩家活跃目标列表。

| 触发条件                              | 涌现的目标    | 完成条件                     | 来源   |
| --------------------------------- | -------- | ------------------------ | ---- |
| `player.needs["physiology"] < 30` | "寻找食物/水" | needs["physiology"] > 70 | 需求驱动 |
| 附近 NPC `needs < 20`               | "帮助NPC"  | NPC needs > 60           | 社会感知 |
| 所在区域资源枯竭                          | "迁移到新区域" | 到达资源丰富区域                 | 环境压力 |
| NPC 主动提出交易请求                      | "完成交易"   | 交易成交                     | 经济交互 |
| `player.wealth > 200` 且无房产        | "建造住所"   | 建造完成                     | 财富驱动 |
| `player.knowledge > 阈值`           | "创造作品"   | 创造物生成                    | 自我实现 |
| NPC 死亡                            | "处理遗产"   | 遗产分配完成                   | 社会事件 |
| 关系网络中好友需求危机                       | "援助好友"   | 好友需求恢复                   | 归属驱动 |
| 触发冷却 300 tick 且世界内有居民             | "切磋一场"   | 对指定 NPC 切磋获胜（DUEL 事件）   | 战斗驱动（战斗 v1） |
| 「元素」魔力特性且法阶≥5，时间窗一生一次        | "元素共鸣"   | 活跃期内任一场切磋获胜              | 稀有机缘（极低频，bug 级） |

**目标生命周期**：

```
GoalGenerator.check(player, world)  # 每 tick 检查
  → 触发条件满足 → 创建 Goal(type, condition, context)
    → 加入 player.active_goals
      → 玩家行为推进 → 检查完成条件
        → 完成：移出 active_goals，记录到 player.goal_history
        → 失败：移出 active_goals，记录失败原因
        → 过期：超时自动移出
```

**"无限分支"的实现**：

- 目标类型有限（~8 种），但目标参数（哪个 NPC、哪个区域、什么资源）由世界状态决定
- 同一时刻可有多个活跃目标
- 目标完成/失败会产生新目标（级联）
- 不同玩家世界状态不同 → 涌现的目标序列不同 → 体验唯一

### 3.5 约束系统

**复用 second-reality `constitution_rules` 的 19 维约束。**

约束不是硬墙，而是有代价的软约束：

| 约束类型 | 违反代价      | 视觉反馈            |
| ---- | --------- | --------------- |
| 经济守恒 | 货币残差 ≠ 0  | UI 显示红色残差警告     |
| 财富硬顶 | 超额财富被税收回收 | 超额部分渐隐          |
| 债务下限 | 债务不可无限累积  | 债务条变红           |
| 通胀目标 | 偏离 2% 目标  | 通胀条偏移           |
| 行为合法 | 违规计数增加    | agent 头顶 `!` 标记 |

### 3.6 经济系统

**直接复用 second-reality `EconomicReserve`：**

- UBI（每 10 tick 分发基础收入）
- 税收（每 30 tick 征收）
- 通胀（每 50 tick 调整，目标 2%）
- 劳动铸币（劳动创造财富，非无限刷）
- 货币守恒不变量：Σwealth + treasury + inflation_created + genesis_unallocated == money_supply

**玩家与经济的关系：**

- 玩家可参与交易（与 NPC agent 买卖）
- 玩家可拥有资产（建筑/土地）
- 玩家劳动也铸币（采集/建造产生财富）
- 玩家不受 UBI（UBI 仅给 NPC）

---

## 4. 资产永续机制

### 4.1 威胁模型

| 威胁               | 对策                          |
| ---------------- | --------------------------- |
| 本地存档损坏           | 内容寻址存储（CAS），每份存档有 SHA256 指纹 |
| 玩境毁灭（火灾/水灾/硬件故障） | 链上锚定：资产指纹定期上链               |
| 服务器关闭            | 玩境可灭，链上资产指纹永存；可从链上恢复到任意新环境  |
| 作弊篡改             | 链上指纹与本地存档比对，不匹配则标记为"非原始"    |

### 4.2 资产锚定流程

```
1. 玩家获得资产（建造/采集/创造）
2. 资产写入本地 CAS：content_hash = SHA256(asset_data)
3. 每 N tick 将资产指纹打包：batch_hash = SHA256(Σ content_hash)
4. batch_hash 提交到链上（可选：用 second-perspective 的 GCAE 审计证书作为锚定凭证）
5. 玩家离线/退出 → 存档冻结 → 最终指纹上链
6. 玩家重新进入 → 从链上验证指纹 → 从 CAS 恢复资产
```

### 4.3 资产类型

| 类型    | 永续方式       | 示例          |
| ----- | ---------- | ----------- |
| 建筑    | CAS + 链上指纹 | 玩家建造的房屋/工坊  |
| 创造物   | CAS + 链上指纹 | 玩家创造的艺术品/工具 |
| 土地所有权 | 链上直接登记     | 玩家拥有的地块     |
| 货币    | 链上余额       | 玩家财富        |
| 记忆/经历 | CAS（可选上链）  | 玩家在世界中的经历记录 |

---

## 5. 平台架构

### 5.1 PC 版（优先）

| 组件  | 选型             | 理由                                |
| --- | -------------- | --------------------------------- |
| 渲染  | pygame（已验证）    | second-reality 已用，零迁移成本           |
| 窗口  | pygame.display | 原生                                |
| 输入  | pygame.event   | 键鼠                                |
| 分辨率 | 1920×1080+     | CELL=32，WORLD_SIZE=60 → 1920×2160 |

### 5.2 手机版（后续）

| 组件  | 选型                     | 理由                    |
| --- | ---------------------- | --------------------- |
| 渲染  | WebGL / Canvas         | 跨平台                   |
| 框架  | React Native / Flutter | 二选一，[TBD: 需评估]        |
| 输入  | 触摸 + 虚拟摇杆              | 需设计触控 UI              |
| 分辨率 | 自适应                    | CELL 缩放，WORLD_SIZE 不变 |

### 5.3 跨平台策略

- **仿真层完全共享**：Python 仿真引擎不依赖渲染
- **渲染层分平台**：PC 用 pygame，手机用 WebGL
- **持久化层共享**：CAS + 链上锚定与平台无关
- **通信**：仿真层输出世界状态 → 渲染层消费（生产者/消费者解耦）

---

## 6. 世界运行循环

### 6.1 主循环

```
while running:
    # 1. 输入处理
    handle_input()          # 玩家输入 → PlayerAgent 行为

    # 2. 仿真步进
    if not paused:
        events = world.tick()   # 所有 agent 决策 + 行为 + 事件
        process_events(events)  # 事件 → 视觉特效 / UI 更新

    # 3. 资产锚定（每 N tick）
    if world.tick_count % ANCHOR_INTERVAL == 0:
        anchor_assets(world)    # 资产指纹上链

    # 4. 渲染
    draw_world()             # 网格 + 热力 + 资源 + 建筑 + agent
    draw_ui()                # 面板 + 需求条 + 曲线 + 事件流
    draw_fx()                # 浮动文字 + 粒子特效

    # 5. 帧率控制
    clock.tick(tps)
```

### 6.2 暂停与恢复

- `SPACE` 暂停：仿真冻结，渲染继续（可观察世界）
- `S` 存档：`world.save_state()` → 本地 JSON + CAS
- `R` 重置：同 seed 重新生成（世界完全相同）
- 退出：自动存档 + 最终指纹上链

---

## 7. 数据模型

### 7.1 世界状态

复用 second-reality `export_state()`，扩展：

```
WorldState = {
    tick: int,
    config: WorldConfig,
    seed: int,                    # 世界种子
    player: PlayerState,          # 玩家状态（新增）
    agents: [AgentState],         # NPC agents
    resources: [ResourceState],
    buildings: [BuildingState],
    economy: EconomicState,
    constitution: ConstraintState,
    asset_registry: [AssetRef],   # 资产注册表（新增）
    world_hash: str               # 世界指纹
}
```

### 7.2 资产注册表

```
AssetRef = {
    asset_id: str,           # UUID
    owner: str,              # player_id 或 agent_id
    type: str,               # building / land / item / currency
    content_hash: str,       # SHA256(asset_data)
    chain_anchor: str,       # 链上锚定哈希（可为空）
    created_tick: int,
    last_modified_tick: int
}
```

---

## 8. 约束清单

### 8.1 世界级约束

| 约束   | 说明                                                           | 来源              |
| ---- | ------------------------------------------------------------ | --------------- |
| 货币守恒 | Σwealth + treasury + inflation + unallocated == money_supply | EconomicReserve |
| 人口上限 | alive_agents <= max_agents                                   | WorldConfig     |
| 资源再生 | 资源按再生率恢复，不无限消耗                                               | Resource 机制     |
| 通胀目标 | inflation_rate → 0.02                                        | EconomicReserve |

### 8.2 Agent 级约束

| 约束   | 说明                   | 违反代价                 |
| ---- | -------------------- | -------------------- |
| 需求衰减 | 需求随时间下降，需主动满足        | 不满足 → state 恶化 → 死亡  |
| 财富硬顶 | wealth <= wealth_cap | 超额被税收回收              |
| 债务下限 | debt >= debt_floor   | 不可无限负债               |
| 行为合法 | 行为在合法行为集内            | violations += 1，声誉下降 |

### 8.3 玩家级约束

| 约束    | 说明                      |
| ----- | ----------------------- |
| 移动范围  | 玩家不可移出世界边界              |
| 背包容量  | 物品堆叠有上限                 |
| 建造规则  | 不可在 NPC 建筑上建造，不可在资源点上建造 |
| 资产所有权 | 仅可操作自己拥有的资产             |

---

## 9. 渲染设计

### 9.1 像素风格（已实现）

- CELL = 32px
- Agent：12×12 像素方块 + 代际边框
- 资源：8×8 像素方块
- 建筑：28×28 像素方块 + 像素细节
- 热力图：32×32 像素块
- UI：粗边框、像素字体

### 9.2 3D 精美渲染（目标形态）

**架构路径**：仿真层与渲染层解耦，通过协议通信。

```
Python 仿真层 (second-reality)
    ↓ gRPC / WebSocket (世界状态 JSON)
3D 渲染层 (Unity / Godot)
    → 精美人物模型 (骨骼动画)
    → 地形系统 (高度图 + 纹理)
    → 光照 (PBR 材质 + 动态光影)
    → 粒子特效
```

| 组件 | 选型                      | 理由                              |
| -- | ----------------------- | ------------------------------- |
| 引擎 | Godot 4 / Unity         | Godot 开源免费；Unity 生态成熟           |
| 人物 | 骨骼绑定 + 动画状态机            | 对接 AgentState（idle/working/...） |
| 地形 | 高度图 + 程序化生成             | 由 seed 确定性生成                    |
| 通信 | gRPC（PC）/ WebSocket（手机） | 仿真层输出状态，渲染层消费                   |
| 帧率 | 仿真 10 tps，渲染 60 fps     | 解耦后各自独立帧率                       |

**迁移策略**：

1. 仿真层不变，加 gRPC 服务端输出世界状态
2. 3D 渲染层作为客户端，订阅世界状态
3. 像素版保留为"轻量模式"，3D 版为"完整模式"

### 9.3 摄像机

- PC：跟随玩家，WASD/方向键移动，鼠标滚轮缩放


- 手机：跟随玩家，虚拟摇杆移动，双指缩放
- 世界大于屏幕 → 摄像机只渲染可见区域（视锥剔除）

### 9.3 信息层

| 层 | 内容 | 开关 |
|----|------|------|
| 网格 | 世界网格线 | 默认开 |
| 热力 | 财富热力底图 | `W` |
| 关系 | 社会关系网络 | `F` |
| 事件 | 事件特效（浮字/粒子） | `E` |
| 昼夜 | 昼夜/季节色调 | `N` |
| 面板 | 统计/需求/曲线/事件流 | 默认开 |

---

## 10. 部署与运行

### 10.1 PC 版

```
# 安装
pip install pygame

# 运行
python virtual_world.py                    # GUI 模式
python virtual_world.py --headless         # 无头模式
python virtual_world.py --seed 42          # 指定种子
python virtual_world.py --verify-determinism  # 确定性验证
```

### 10.2 手机版

[TBD: 待选型后补充]

### 10.3 资产链上锚定

[TBD: 待选定链（Ethereum / Polygon / 自建链）后补充]

---

## 11. 风险与待决项

| 项 | 风险 | 状态 |
|----|------|------|
| 3D 引擎选型 | Godot vs Unity，影响生态/成本/性能 | [TBD] |
| 手机版框架选型 | React Native vs Flutter | [TBD] |
| 链上锚定方案 | 公链 gas 费用 vs 自建链维护成本 | [TBD] |
| 世界规模 | 60×60 网格是否够大，需玩家测试反馈 | [TBD] |
| NPC 数量 | 30 个 NPC 是否够丰富，需性能/体验平衡 | [TBD] |
| 玩家与世界交互深度 | 当前采集/建造/交易，是否允许改变地形 | [TBD] |
| 多人模式 | 邀请制 vs 开放世界，影响架构复杂度 | [TBD] |
| 目标系统可玩性 | 涌现式目标是否足够有趣，需原型验证 | [TBD] |

---

## 12. 里程碑

| 阶段 | 内容 | 依赖 | 状态 |
|------|------|------|------|
| M1 | PC 版像素世界可运行 | second-reality + 像素渲染 | ✅ 已达成 |
| M2 | 玩家 Agent 接入（移动/采集/建造/交易） | M1 | ✅ 已达成 |
| M2.5 | 资产永续（CAS + 本地存档） | M2 | ✅ 已达成 |
| M2.6 | 涌现式目标系统（GoalGenerator） | M2 | ⏳ 待开发 |
| M3 | 3D 渲染层（Godot/Unity + gRPC） | M2 | ⏳ 待开发 |
| M4 | 资产链上锚定 | M2.5 + 链选型 | ⏳ 待开发 |
| M5 | 手机版渲染层 | M3 + 框架选型 | ⏳ 待开发 |
| M6 | 多人模式（邀请制） | M2.6 + M3 | ⏳ 待开发 |
| M7 | 发布 | M4 + M5 + M6 | ⏳ 待开发 |

---

## 附录 A：second-reality 可复用资产

| 文件 | 行数 | 可复用内容 |
|------|------|-----------|
| `virtual_world.py` | 1081 | World/Agent/Economy/Event/Memory/渲染 |
| `audit_engine.py` | — | 19 维宪法审计（约束系统） |
| `constitution_rules.py` | — | 约束规则定义 |
| `compatibility_bridge.py` | — | 兼容层 |
| `verify.py` | — | 确定性验证套件 |

## 附录 B：术语表

| 术语 | 含义 |
|------|------|
| tick | 仿真步进单位，1 tick = 1 次世界状态更新 |
| seed | 世界随机种子，同 seed + 同 config → 同世界 |
| CAS | Content-Addressable Storage，内容寻址存储 |
| 链上锚定 | 将资产指纹（哈希）写入区块链，实现永续 |
| 五层需求 | 生理/安全/归属/尊重/自我实现（Maslow） |
| 货币守恒 | Σwealth + treasury + inflation + unallocated == money_supply |
| 确定性 | 同输入同输出，逐字节可复现 |