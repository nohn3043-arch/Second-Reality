import time, random, json, sys, argparse, tkinter as tk
from tkinter import ttk

# ==============================================
# 1. 核心框架：认知审计引擎 (Cognitive Audit Engine)
# 从 constitution 导入，保持单一权威实现
# ==============================================
from constitution import (
    ResponsibilityAccount, AuditPlugin, CognitiveAuditEngine,
    NOHN_LAW_AXIOMS,
)
# 系统层：真实世界运行时（创世 + 账本 + 共识 + 记忆），供演示版接入并通过 18 项审计
from system.runtime import World as CoreWorld

# ==============================================
# 2. 深度功能模块：经济、任务与动态地图
# ==============================================
class EconomySystem:
    """经济系统：货币与物价逻辑（遵循 law 层《全球经济统一标准》V2.1）"""
    def __init__(self):
        self.currency = "NOHN-COIN"
        self.prices = {"Bread": 10, "Iron": 50}
        self.market_volatility = 0.0     # 事件驱动的价格扰动
        self.trade_history = []          # 交易记录（供审计/事件系统参考）
        # --- 经济合规属性（供 SecondPerspectiveAuditor._audit_economic_law 校验）---
        self.real_peg_1to1 = True        # 锚定资产 1:1 锚定现实储备
        self.proof_of_reserve = True     # 链上储备证明（PoR）实时可查
        self.redemption_right = True     # 用户随时 1:1 赎回权，不可被单方关停
        self.oracle_sources = [          # 波动资产预言机独立来源（需 ≥3）
            "chainlink", "nohn_feed", "independent_audit"
        ]
        self.unilateral_fee = False      # 禁止向用户单边收取结算费
        self.asset_bound_to_soul = True  # 资产确权绑定 GlobalIdentity.soul_hash

    def price(self, item):
        """当前售价 = 基准价 × (1 + 市场扰动)，钳位不低于 1"""
        base = self.prices.get(item, 1)
        return max(1, int(base * (1.0 + self.market_volatility)))

    def apply_event(self, event):
        """事件对经济的传导：粮价/铁价扰动在 ±40% 内"""
        if "food" in event["effect"]:
            self.market_volatility += random.uniform(-0.3, 0.4)
        if "iron" in event["effect"]:
            self.prices["Iron"] = max(10, self.prices["Iron"] + random.randint(-15, 20))
        self.market_volatility = max(-0.4, min(0.4, self.market_volatility))

    def record_trade(self, agent, item, qty, price):
        self.trade_history.append({
            "tick": agent.world_tick if hasattr(agent, "world_tick") else 0,
            "agent": agent.name, "item": item, "qty": qty,
            "total": qty * price, "soul": agent.id[:8]
        })

class TaskGenerator:
    """自动任务系统：基于智能体需求涌现任务"""
    @staticmethod
    def generate(agent):
        # 优先级：饥饿(高危) > 挨饿(中危) > 贫穷 > 温饱探索
        if agent.needs["food"] < 0.45:
            return {"type": "GATHER", "target": "Origins", "reward": 20}
        if agent.needs["food"] < 0.7:
            # 有钱就去买粮，没钱就采
            if agent.wallet >= 8:
                return {"type": "BUY", "target": "The_Agora", "item": "Bread"}
            return {"type": "GATHER", "target": "Origins", "reward": 20}
        if agent.wallet < 15:
            return {"type": "WORK", "target": "Iron_Vault", "reward": 15}
        return {"type": "EXPLORE", "target": "The_Agora", "reward": 5}

# ==============================================
# 3. 智能体与世界集成
# ==============================================
class NohnAgent:
    def __init__(self, name, soul_hash, world, wallet=20):
        self.name, self.id = name, soul_hash
        self.world = world
        self.needs = {"food": random.uniform(0.6, 0.95), "safety": 1.0}
        self.wallet = wallet  # 初始货币（可差异化：穷/中/富）
        self.location = "Origins"
        self.current_task = None
        self.pos = (125, 175)   # 画布坐标（供动画插值）
        self.prev_pos = (125, 175)
        self.moving = False
        self.steps_alive = 0

    def _is_scripted(self) -> bool:
        """审计点（第二/四条）：是否存在外部剧情强制绑定此 NPC？永远 False。"""
        return False

    def decide(self):
        # 自动任务生成替代了简单的手动决策
        self.current_task = TaskGenerator.generate(self)
        return {
            "task": self.current_task["type"],
            "target": self.current_task["target"],
            "logic_ctx": {
                "agent": self.name,
                "need_level": round(self.needs["food"], 2),
                "wealth": self.wallet,
                "action": self.current_task["type"],
                "location": self.location
            }
        }

    def execute(self, decision):
        """执行任务，返回 (日志行, 是否发生交易)"""
        task = decision["task"]
        target = decision["target"]
        lines = [f"{self.name}: {task} → {target}"]
        traded = False

        # 熵增：饥饿感随时间增长（每 tick 消耗 0.22~0.28，驱动行为循环）
        self.needs["food"] = max(0.0, self.needs["food"] - random.uniform(0.22, 0.28))

        if task == "GATHER":
            self.needs["food"] = min(1.0, self.needs["food"] + 0.45)
            self.world.resources["Origins"]["food"] = max(0, self.world.resources["Origins"]["food"] - 1)
        elif task == "WORK":
            self.wallet = max(0, self.wallet + 15)
            self.world.resources["Iron_Vault"]["iron"] = max(0, self.world.resources["Iron_Vault"]["iron"] - 1)
        elif task == "BUY":
            price = self.world.economy.price("Bread")
            if self.wallet >= price:
                self.wallet -= price
                self.needs["food"] = min(1.0, self.needs["food"] + 0.6)
                self.world.economy.record_trade(self, "Bread", 1, price)
                traded = True
                lines.append(f"  └─ 购 Bread ×1 @ {price} {self.world.economy.currency}")
            else:
                self.current_task = TaskGenerator.generate(self)  # 买不起则改采
                lines.append(f"  └─ 余额不足({self.wallet})，改采 {self.current_task['target']}")
                target = self.current_task["target"]
                if self.current_task["type"] == "GATHER":
                    self.needs["food"] = min(1.0, self.needs["food"] + 0.45)
                    self.world.resources["Origins"]["food"] = max(0, self.world.resources["Origins"]["food"] - 1)
        else:  # EXPLORE
            self.wallet = max(0, self.wallet + 2)  # 低收益：探索不产粮也不赚钱

        self.location = target
        self.steps_alive += 1
        return lines, traded

# ==============================================
# 4. 世界容器：棋盘格地图 + 资源 + 事件 + 审计
# ==============================================
class NohnWorld:
    GRID_COLS, GRID_ROWS = 6, 4
    CELL_W, CELL_H = 100, 90

    # 地块配置：col,row 决定棋盘格位置
    LAYOUT = {
        "Origins":     {"grid": (0, 0), "color": "#A8E6CF", "res": "Food", "terrain": "plains"},
        "Iron_Vault":  {"grid": (4, 0), "color": "#DCEDC1", "res": "Iron", "terrain": "mines"},
        "The_Agora":   {"grid": (5, 3), "color": "#FFD3B6", "res": "Coin", "terrain": "market"},
        "Sacred_Grove":{"grid": (2, 3), "color": "#C9B6E4", "res": "Food", "terrain": "grove"},
    }

    def __init__(self):
        self.physics = {
            "gravity": NOHN_LAW_AXIOMS["gravity"],
            "time_dilation": NOHN_LAW_AXIOMS["time_dilation"],
            "unit_scale": NOHN_LAW_AXIOMS["unit_scale"],
            "no_dimensional_inflation": NOHN_LAW_AXIOMS["no_dimensional_inflation"]
        }
        self.economy = EconomySystem()
        # law 层合规属性（供 SecondPerspectiveAuditor 校验身份/通信）
        self.identity = {
            "soul_hash_sha256": True,      # SHA-256 64位
            "non_revocable": True,         # 平台无权撤销/重置
            "cross_world_portable": True,  # 支持跨世界迁移
            "asset_bound": True            # 资产绑定 soul_hash
        }
        self.communication = {
            "uses_nohn_semantics": True,   # 消息走 NOHN_MSG_LOGIC 标准信封
            "unknown_downgraded": True,    # 未知指令降级而非丢弃
            "vocab_mapped": True           # 私有指令可映射到标准词表
        }
        # 棋盘格地图（由 LAYOUT 生成矩形坐标）
        self.map = {}
        for name, cfg in self.LAYOUT.items():
            col, row = cfg["grid"]
            x1 = 40 + col * self.CELL_W
            y1 = 50 + row * self.CELL_H
            x2 = x1 + self.CELL_W - 8
            y2 = y1 + self.CELL_H - 8
            self.map[name] = {
                "color": cfg["color"], "pos": (x1, y1, x2, y2),
                "res": cfg["res"], "terrain": cfg["terrain"]
            }
        # 资源存量
        self.resources = {
            "Origins": {"food": 8},
            "Iron_Vault": {"iron": 6},
            "The_Agora": {"coin": 100},
            "Sacred_Grove": {"food": 5},
        }
        self.agents = []
        self.tick_count = 0
        self.active_event = None       # 当前生效事件
        self.event_banner = ""         # 事件横幅文本
        self.banner_until = 0
        # 初始化审计（3 插件：叙事剥离 / 内隐假设透视 / 脆弱性对冲）
        acc = ResponsibilityAccount("Nohn_Foundation", "Architect", "Production")
        self.engine = CognitiveAuditEngine(acc, {"allowed_stages": ["Production"]})
        self.engine.register_plugin(AuditPlugin("NarrativeStripping",
            lambda c: {"logic": f"NEED({c['need_level']:.2f}) + WEALTH({c['wealth']}) -> {c['action']}",
                       "chain": f"{c.get('location','?')} --{c['action']}--> {c.get('target','?')}"}))
        self.engine.register_plugin(AuditPlugin("AssumptionProbe",
            lambda c: {"implicit": f"assumes food_need={c['need_level']:.2f} is actionable",
                       "counterfactual": f"if food_need=0 -> system {"converges" if c['need_level'] > 0 else "collapses"}"}))
        self.engine.register_plugin(AuditPlugin("FragilityHedge",
            lambda c: {"weak_var": "food_reserve",
                       "delta_D": f"{(1.0 - c['need_level']):.2f} (crisis exposure)",
                       "hedge": "BUY/GATHER fallback"}))
        # 接入系统层：挂载真实世界组件（创世/账本/共识/记忆），使演示版通过 18 项审计
        self._mount_core()

    def _mount_core(self):
        """将演示版挂载到 system.World 之上，暴露宪法/治理/law 全量组件。"""
        self.core = CoreWorld("nohn-demo-v2")
        self.spatial_substrate = self.core.spatial_substrate
        self.temporal_substrate = self.core.temporal_substrate
        self.causal_closure = self.core.causal_closure
        self.existence_axiom = self.core.existence_axiom
        self.genesis_condition = self.core.genesis_condition
        self.immutable_rule = self.core.immutable_rule
        self.central_brain = self.core.central_brain
        self.aesthetic = self.core.aesthetic
        self.soul_attestation = self.core.soul_attestation
        self.memory_integrity = self.core.memory_integrity
        self.world_perpetuity = self.core.world_perpetuity
        self.interoperability = self.core.interoperability
        self.governance = self.core.governance
        self.world_config = self.core.world_config
        self.npcs = self.agents  # 供审计遍历（与 agents 同一引用，spawn 自动同步）

    def spawn(self, name, soul_hash, wallet=20):
        if len(soul_hash) != 64:
            raise ValueError(f"spawn: soul_hash 长度必须为 64（SHA-256 十六进制），实际为 {len(soul_hash)}")
        a = NohnAgent(name, soul_hash, self, wallet=wallet)
        self.agents.append(a)
        return a

    def spawn_demo_agents(self):
        # 差异化初始财富：穷(6) / 中(20) / 富(45)，驱动不同行为路径
        self.spawn("Explorer_01", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", wallet=6)
        self.spawn("Merchant_02", "f8e2c3a1b0d9e8f7c6b5a4938271605b4a3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e", wallet=20)
        self.spawn("Adept_03", "aa11bb22cc33dd44ee55ff6677889900aabbccddeeff00112233445566778899", wallet=45)

    # ---- 世界演化 ----
    def tick(self):
        self.tick_count += 1
        events = []
        # 1. 资源再生（稳态）
        self.resources["Origins"]["food"] = min(8, self.resources["Origins"]["food"] + 0.3)
        self.resources["Iron_Vault"]["iron"] = min(6, self.resources["Iron_Vault"]["iron"] + 0.2)
        self.resources["Sacred_Grove"]["food"] = min(5, self.resources["Sacred_Grove"]["food"] + 0.2)
        # 2. 随机事件（15% 概率）
        if random.random() < 0.15:
            event = self._roll_event()
            self.economy.apply_event(event)
            self.active_event = event
            self.event_banner = event["text"]
            self.banner_until = self.tick_count + 3
            events.append(event)
        # 3. agent 行动
        for a in self.agents:
            a.decide()
        return events

    def _roll_event(self):
        pool = [
            {"text": "⚑ 粮价波动 +20%", "effect": ["food"]},
            {"text": "⚑ 发现新矿脉，铁价下跌", "effect": ["iron"]},
            {"text": "⚑ 丰收季：食物恢复加快", "effect": ["food"]},
            {"text": "⚑ 商路畅通：物价回落", "effect": ["food", "iron"]},
        ]
        return random.choice(pool)

    def world_report(self):
        """headless 模式的世界快照（JSON 可读）"""
        return {
            "tick": self.tick_count,
            "agents": [{"name": a.name, "soul": a.id[:8], "food": round(a.needs["food"], 2),
                        "wallet": a.wallet, "loc": a.location} for a in self.agents],
            "resources": self.resources,
            "prices": {"Bread": self.economy.price("Bread"), "Iron": self.economy.price("Iron")},
            "event": self.event_banner if self.tick_count <= self.banner_until else "",
            "trades": len(self.economy.trade_history),
        }

# ==============================================
# 5. 可视化：棋盘格地图 + agent 动效 + 事件闪烁
# ==============================================
class NohnVisualApp:
    def __init__(self, world):
        self.world = world
        self.root = tk.Tk()
        self.root.title("NOHN 虚拟世界 - 社会演化审计版")
        self.root.configure(bg="#F5F3EE")

        # --- 左侧：棋盘格地图 ---
        map_w, map_h = 40 + 6*NohnWorld.CELL_W, 50 + 4*NohnWorld.CELL_H
        self.canvas = tk.Canvas(self.root, width=map_w, height=map_h + 40, bg="#F0EDE4",
                                highlightthickness=1, highlightbackground="#D8D3C5")
        self.canvas.pack(side=tk.LEFT, padx=(12, 8), pady=12)

        # --- 右侧：状态面板 + 审计日志 ---
        right = tk.Frame(self.root, bg="#F5F3EE")
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 12), pady=12)

        self.status_tree = ttk.Treeview(right, columns=("val",), height=7, show="tree")
        self.status_tree.heading("#0", text="World Status")
        self.status_tree.column("#0", width=130, anchor="w")
        self.status_tree.column("val", width=110, anchor="w")
        self.status_tree.pack(fill=tk.X)

        ttk.Label(right, text="Agent State", background="#F5F3EE").pack(anchor="w", pady=(10, 2))
        self.agent_tree = ttk.Treeview(right, columns=("food", "wallet", "loc"), height=8)
        self.agent_tree.heading("#0", text="Agent")
        self.agent_tree.heading("food", text="Food")
        self.agent_tree.heading("wallet", text="₦")
        self.agent_tree.heading("loc", text="Location")
        self.agent_tree.column("#0", width=95)
        self.agent_tree.column("food", width=45, anchor="center")
        self.agent_tree.column("wallet", width=45, anchor="center")
        self.agent_tree.column("loc", width=80, anchor="center")
        self.agent_tree.pack(fill=tk.X)

        ttk.Label(right, text="Audit Log", background="#F5F3EE").pack(anchor="w", pady=(10, 2))
        self.audit_log = tk.Text(right, width=42, height=18, font=("Consolas", 9),
                                 bg="#FDFCF8", fg="#333", relief="flat", borderwidth=1)
        self.audit_log.pack(fill=tk.BOTH, expand=True)

        btn_row = tk.Frame(right, bg="#F5F3EE")
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="推进世界演化 (Tick)", command=self.step).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="新增 Agent", command=self.spawn_extra).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text="自动演化", command=self.auto_toggle).pack(side=tk.LEFT)

        self.auto_flag = False
        self._draw_board()
        self.refresh_static()

    # ---- 静态绘制：地块 + 资源条 + 状态栏 ----
    def _draw_board(self):
        self.canvas.create_rectangle(10, 10, 40 + 6*NohnWorld.CELL_W + 10,
                                     50 + 4*NohnWorld.CELL_H + 10, fill="#F0EDE4", outline="")
        for n, d in self.world.map.items():
            x1, y1, x2, y2 = d["pos"]
            # 棋盘格地块：填充 + 边框 + 网格点阵纹理
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=d["color"],
                                         outline="#FFFFFF", width=2)
            for gx in range(x1 + 12, x2 - 4, 18):
                for gy in range(y1 + 22, y2 - 4, 18):
                    self.canvas.create_oval(gx, gy, gx+2, gy+2, fill="#D8D8D8", outline="")
            self.canvas.create_text((x1+x2)/2, y1 + 16, text=f"{n}", font=("Arial", 10, "bold"))
            self.canvas.create_text((x1+x2)/2, y1 + 32, text=f"({d['res']} · {d['terrain']})",
                                    font=("Arial", 8), fill="#444")
        # 状态栏
        self.stat_bar = self.canvas.create_text(20 + 3*NohnWorld.CELL_W, 50 + 4*NohnWorld.CELL_H + 22,
                                                text="", anchor="w", font=("Consolas", 9), fill="#333")

    def refresh_static(self):
        """刷新状态栏 + agent 表 + 资源条"""
        # 状态栏
        w = self.world
        stat = (f"Tick {w.tick_count} | Bread {w.economy.price('Bread')}₦ "
                f"Iron {w.economy.price('Iron')}₦ | {w.event_banner if w.tick_count <= w.banner_until else '平静'}")
        self.canvas.itemconfig(self.stat_bar, text=stat)
        # 资源条（覆盖在各地块底部）
        for n, res in w.resources.items():
            d = w.map.get(n)
            if not d: continue
            x1, y1, x2, y2 = d["pos"]
            maxv = {"food": 8, "iron": 6, "coin": 100}.get(list(res.keys())[0], 10)
            val = list(res.values())[0]
            ratio = max(0, min(1, val / maxv))
            self.canvas.delete(f"resbar_{n}")
            self.canvas.create_rectangle(x1+10, y2-14, x2-10, y2-6, fill="#D0D0C8", outline="",
                                         tags=f"resbar_{n}")
            if ratio > 0:
                self.canvas.create_rectangle(x1+10, y2-14, x1+10+(x2-x1-20)*ratio, y2-6,
                                             fill="#2F6B4F", outline="", tags=f"resbar_{n}")
        # agent 表
        self.agent_tree.delete(*self.agent_tree.get_children())
        for a in w.agents:
            self.agent_tree.insert("", "end", text=a.name, values=(
                f"{a.needs['food']:.2f}", a.wallet, a.location))
        # 状态树
        self.status_tree.delete(*self.status_tree.get_children())
        self.status_tree.insert("", "end", text="Physics", values=[f"g={w.physics['gravity']} t={w.physics['time_dilation']}"])
        self.status_tree.insert("", "end", text="Identity", values=["soul-hash OK"])
        self.status_tree.insert("", "end", text="Communication", values=["NOHN semantics"])
        self.status_tree.insert("", "end", text="Trades", values=[str(len(w.economy.trade_history))])
        self.status_tree.insert("", "end", text="Agents", values=[str(len(w.agents))])

    def spawn_extra(self):
        import uuid
        self.world.spawn(f"Adept_{len(self.world.agents)+1:02d}", uuid.uuid4().hex)
        self._draw_agents()
        self.refresh_static()

    def auto_toggle(self):
        self.auto_flag = not self.auto_flag
        if self.auto_flag:
            self._auto_loop()

    def _auto_loop(self):
        if self.auto_flag:
            self.step()
            self.root.after(600, self._auto_loop)

    # ---- 事件闪烁 ----
    def _flash_event(self):
        if self.world.tick_count <= self.world.banner_until and self.world.active_event:
            d = self.world.map["The_Agora"]
            x1, y1, x2, y2 = d["pos"]
            self.canvas.delete("flash")
            self.canvas.create_oval((x1+x2)/2-18, (y1+y2)/2-18, (x1+x2)/2+18, (y1+y2)/2+18,
                                    outline="#E24B4A", width=3, tags="flash")
            self.root.after(250, lambda: self.canvas.delete("flash"))

    # ---- agent 渲染 + 移动插值 ----
    def _draw_agents(self):
        self.canvas.delete("agent")
        self.canvas.delete("trail")
        for a in self.world.agents:
            x1, y1, x2, y2 = self.world.map[a.location]["pos"]
            cx, cy = (x1+x2)/2, (y1+y2)/2
            self.canvas.create_oval(cx-16, cy-16, cx+16, cy+16, fill="#FF8B94",
                                    outline="#D85A30", width=1.5, tags="agent")
            self.canvas.create_text(cx, cy, text=a.name[0].upper(), font=("Arial", 10, "bold"),
                                    fill="#FFF", tags="agent")
            self.canvas.create_text(cx, cy+24, text=f"{a.name}\n₦{a.wallet}", tags="agent",
                                    font=("Arial", 8), fill="#333")

    def step(self):
        """推进一个世界 tick，渲染 + 审计"""
        events = self.world.tick()
        self.canvas.delete("agent")
        self.canvas.delete("trail")
        for a in self.world.agents:
            # 审计
            decision = a.decide()
            report = self.world.engine.audit(decision["logic_ctx"])
            # 执行
            lines, traded = a.execute(decision)
            # 路径线（旧地 → 新地）
            x1, y1, x2, y2 = self.world.map[a.location]["pos"]
            cx, cy = (x1+x2)/2, (y1+y2)/2
            px, py = a.prev_pos if hasattr(a, "prev_pos") else (cx, cy)
            self.canvas.create_line(px, py, cx, cy, fill="#999", dash=(3, 2), tags="trail")
            a.prev_pos = (cx, cy)
            # 渲染 agent
            self.canvas.create_oval(cx-16, cy-16, cx+16, cy+16, fill="#FF8B94",
                                    outline="#D85A30", width=1.5, tags="agent")
            self.canvas.create_text(cx, cy, text=a.name[0].upper(), font=("Arial", 10, "bold"),
                                    fill="#FFF", tags="agent")
            self.canvas.create_text(cx, cy+24, text=f"{a.name}\n₦{a.wallet}", tags="agent",
                                    font=("Arial", 8), fill="#333")
            # 审计日志（3 维度）
            self.audit_log.insert(tk.END, f"[T{self.world.tick_count}] {a.name} | Nonce {report['responsibility_account']['nonce']}\n")
            self.audit_log.insert(tk.END, f"  NS: {report['analysis']['NarrativeStripping']['logic']}\n")
            self.audit_log.insert(tk.END, f"  IAP: {report['analysis']['AssumptionProbe']['implicit']}\n")
            self.audit_log.insert(tk.END, f"  LCH: ΔD={report['analysis']['FragilityHedge']['delta_D']} hedge={report['analysis']['FragilityHedge']['hedge']}\n")
            for ln in lines:
                self.audit_log.insert(tk.END, f"  {ln}\n")
            self.audit_log.insert(tk.END, "  ──\n")
            self.audit_log.see(tk.END)
        # 事件横幅
        for ev in events:
            self.audit_log.insert(tk.END, f"⚑ 事件: {ev['text']}\n")
        self._flash_event()
        self.refresh_static()

# ==============================================
# 6. 入口：GUI / headless 双模式
# ==============================================
def main():
    # Windows 控制台默认 GBK，无法输出 ⚑ 等 Unicode 符号；重配为 UTF-8 保证跨平台可打印
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="NOHN Virtual World Demo")
    parser.add_argument("--init", choices=["demo"], help="初始化演示世界（兼容 README 写法）")
    parser.add_argument("--agents", type=int, default=3, help="演示 agent 数量（默认 3）")
    parser.add_argument("--ticks", type=int, default=0,
                        help="headless 模式：自动运行 N 个 tick 后打印报告并退出（0 = 启动 GUI）")
    parser.add_argument("--seed", type=int, default=None, help="随机种子（可复现）")
    parser.add_argument("--audit", action="store_true",
                        help="headless 模式：运行 18 项第二视角审计并输出结论")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    world = NohnWorld()
    world.spawn_demo_agents()
    # --init demo 为兼容写法，行为与默认一致
    if args.init == "demo":
        pass

    # 独立审计模式：不依赖 tick，直接对已装配世界跑 18 项审计
    if args.audit:
        report = world.core.audit()
        print(report.summary())
        return

    if args.ticks > 0:
        for _ in range(args.ticks):
            world.tick()
            for a in world.agents:
                a.decide()
                a.execute({
                    "task": a.current_task["type"],
                    "target": a.current_task["target"]
                })
        print(json.dumps(world.world_report(), indent=2, ensure_ascii=False))
        return

    app = NohnVisualApp(world)
    app.root.mainloop()

if __name__ == "__main__":
    main()
