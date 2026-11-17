# -*- coding: utf-8 -*-
"""涌现式目标系统（GoalGenerator）—— M2.6：玩家任务模块
====================================================================

定位
----
HLD §3.4 的落地实现：目标不预设，由 (玩家状态, 世界状态, NPC状态) 三元组
动态生成。目标类型有限（8 种），目标参数（哪个 NPC、哪个区域、什么资源）
完全由世界状态决定——这就是"无限分支"的实现方式。

M1 入章纪律（与 demo/hongchenlei.py 同一标准）：每条机制必须同时具备
    statement  陈述（下文触发表）
    producer   执行点（GoalGenerator.check/update；以及为让目标"可完成"
               在 virtual_world.py 纯增量补上的 PlayerAgent.create_work
               与本文件的 settle_legacy）
    consumer   tools/goal_system_smoke.py 逐项验收
    recompute  全部判据只读公开世界状态（agents / resources / buildings /
               event_log / assets），第三方可在任一 tick 独立重算

八种目标类型（HLD §3.4 触发表，一字不改）
------------------------------------------------------------------
  类型              触发                                   完成
  seek_sustenance   player.needs["physiology"] < 30        needs["physiology"] > 70
  help_npc          视距内 NPC 最低需求 < 20                该 NPC 最低需求 > 60
  relocate          玩家周边区域资源枯竭                    周边重新出现资源
  complete_trade    近旁有持货 NPC 且玩家带钱               事件流出现与该 NPC 的成交
  build_home        wealth > 200 且名下无房产               owned_buildings 非空
  create_work       needs["self_actualization"] >= 70      事件流出现玩家 PRODUCE
  handle_legacy     存在带未结算遗产的死者                  该死者 wealth 归零
  aid_friend        交易结识的好友需求危机                  该好友最低需求 > 60

目标生命周期（HLD §3.4，逐条对应）
------------------------------------------------------------------
  check(world)   触发条件满足 → 创建 Goal(type, context) → 加入活跃列表
  update(world)  完成：移出活跃列表，记入 history
                 失败：移出活跃列表，记录失败原因
                 过期：超时自动移出
  级联：完成/失败/过期后经冷却期，同型目标可在后续 tick 重新涌现；
        同一时刻允许多种类型并存，但同型不重复。

确定性三纪律（违反任一即破坏世界可复现性，冒烟测试逐条断言）
------------------------------------------------------------------
  1) 本模块绝不消耗 world._rng —— 所有"选谁"的决策用确定性排序
     （数值优先 → 距离 → aid/坐标字典序），世界随机流逐字节不动；
  2) 目标层是纯观察者：check/update 不写 world 任何账本态，不入
     export_state()/state_hash()（与 persona 层同一豁免口径：派生态）；
  3) 目标列表经共享引用镜像到 player.active_goals / player.goal_history
     （运行时属性，不改 PlayerAgent 类定义，to_dict() 因此不变）。

诚实边界（如实声明，不得隐去）
------------------------------------------------------------------
  A. create_work（virtual_world.py 增量方法）与 settle_legacy（本文件）
     是为让两类目标"真的可完成"补的两个玩家动作；除此之外本模块不引入
     任何新行为——公示即执行，不留只触发达不成的假目标；
  B. 玩家没有 knowledge 字段，create_work 的触发以 self_actualization
     为代理变量；字段级成长系统属后续版本；
  C. help_npc / aid_friend 的"帮助手段"不由本模块规定（交易/赠予/护送
     均可），完成判据只看结果（对方需求回升）——判据属于世界，不属于
     目标；玩家"好友"的操作性定义 = 与玩家成交过的 NPC（经济纽带，
     事件源可复算）；
  D. 完成判据扫描 world.event_log 尾部（上限 3000 条）；目标期限
     （≤400 tick）远短于该窗口，不受日志裁剪影响。

用法
------------------------------------------------------------------
  from goal_system import GoalGenerator          # 或 demo.goal_system
  gen = GoalGenerator(player, world)
  while running:
      world.tick()
      gen.step(world)        # 先结算旧目标（完成/失败/过期），再触发新目标
"""

import math
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))            # demo/
_REPO_ROOT = os.path.dirname(_HERE)
for _p in (_REPO_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 模块身份纪律：本模块与消费方必须共享同一个 virtual_world 模块对象——
# 若 goal_system 以顶层名导入而消费方以 demo.virtual_world 导入，Python 会
# 执行两份模块，产生两套 EventType/NohnWorld 类，事件枚举比对将恒为 False
# （冒烟测试 aid_friend/complete_trade/create_work 曾因此误报）。
# 故：包内消费（demo.goal_system）走相对导入；脚本直跑回退顶层名。
import zlib  # noqa: E402  （元素共鸣时间窗：确定性哈希，不占世界 RNG）
try:                                                          # noqa: E402
    from .virtual_world import (                              # noqa: E402,F401
        Event, EventType, FIVE_LAYER_NEEDS, VISION, NohnWorld,
    )
except ImportError:                                           # pragma: no cover
    from virtual_world import (                                # noqa: E402,F401
        Event, EventType, FIVE_LAYER_NEEDS, VISION, NohnWorld,
    )

FOOD_TYPES = ("food", "water", "fruit")


class GoalStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


GOAL_TITLES_CN = {
    "seek_sustenance": "寻找食物/水",
    "help_npc": "帮助NPC",
    "relocate": "迁移到新区域",
    "complete_trade": "完成交易",
    "build_home": "建造住所",
    "create_work": "创造作品",
    "handle_legacy": "处理遗产",
    "aid_friend": "援助好友",
    "sparring_duel": "切磋一场",
    "element_resonance": "元素共鸣",
}


def _min_need(agent) -> float:
    """NPC 的最低需求（危机程度的全局口径，触发与完成共用同一把尺）。"""
    return min(agent.needs.get(n, 100.0) for n in FIVE_LAYER_NEEDS)


@dataclass
class GoalConfig:
    """全部阈值/半径/周期集中于此：调参不改逻辑，世界轨迹不受影响
    （目标层不消费随机流）。"""
    # —— 触发阈值 ——
    sustenance_trigger: float = 30.0     # 生理 < 30 触发
    sustenance_target: float = 70.0      # 生理 > 70 完成
    crisis_need: float = 20.0            # NPC 最低需求 < 20 = 危机
    recovery_need: float = 60.0          # NPC 最低需求 > 60 = 恢复
    create_trigger: float = 70.0         # 自我实现 >= 70 触发创造
    home_wealth: float = 200.0           # 财富 > 200 且无房 触发置业
    trade_min_wealth: float = 10.0       # 买得起最便宜的东西才触发交易目标
    # —— 半径 ——
    social_radius: float = float(VISION)     # help_npc 视距（与 NPC 感知同口径）
    trade_radius: float = 3.0                # 交易对象近旁
    area_scan_radius: float = 8.0            # relocate：区域枯竭判定半径
    area_rich_radius: float = 5.0            # relocate：抵达资源丰富判定半径
    # —— 生命周期（tick） ——
    cooldowns: Dict[str, int] = field(default_factory=lambda: {
        "seek_sustenance": 20, "help_npc": 40, "relocate": 60,
        "complete_trade": 30, "build_home": 200, "create_work": 100,
        "handle_legacy": 40, "aid_friend": 40,
        "sparring_duel": 300, "element_resonance": 999999})
    deadlines: Dict[str, int] = field(default_factory=lambda: {
        "seek_sustenance": 150, "help_npc": 200, "relocate": 300,
        "complete_trade": 120, "build_home": 400, "create_work": 300,
        "handle_legacy": 200, "aid_friend": 200,
        "sparring_duel": 240, "element_resonance": 600})


@dataclass
class Goal:
    """单个涌现目标：类型有限，context（哪个 NPC/哪片区域/什么资源）由
    世界状态填充——同一类型在不同世界状态下的参数不同，即"无限分支"。"""
    gid: str
    gtype: str
    created_tick: int
    deadline_tick: int
    context: Dict[str, Any] = field(default_factory=dict)
    status: GoalStatus = GoalStatus.ACTIVE
    finished_tick: Optional[int] = None
    fail_reason: str = ""

    @property
    def title(self) -> str:
        return GOAL_TITLES_CN.get(self.gtype, self.gtype)

    def describe(self) -> str:
        """人话描述（GUI 目标面板/浮.toast 直接可用）。"""
        c = self.context
        if self.gtype == "seek_sustenance":
            if c.get("nearest_food"):
                return "最近的食物（%s）在 %.1f 格外 %s" % (
                    c["nearest_food_type"], c["nearest_food_dist"], c["nearest_food"])
            return "附近没有食物——去更远的地方找"
        if self.gtype == "help_npc":
            return "%s 陷入需求危机（最低 %.0f）——帮他恢复" % (
                c.get("npc_name"), c.get("crisis_need", 0))
        if self.gtype == "relocate":
            return "周边 %s 格资源枯竭——迁移到新区域" % c.get("scan_radius")
        if self.gtype == "complete_trade":
            return "%s 想做买卖（有 %s）" % (
                c.get("npc_name"), "/".join(c.get("offered", [])))
        if self.gtype == "build_home":
            return "你攒下了 %.0f——置办一处住所" % c.get("budget", 0)
        if self.gtype == "create_work":
            return "自我实现涌动（%.0f）——创造一件作品" % c.get("self_actualization", 0)
        if self.gtype == "handle_legacy":
            return "%s 去世了，留有待结算遗产 %.0f" % (
                c.get("dead_name"), c.get("estate", 0))
        if self.gtype == "aid_friend":
            return "好友 %s 陷入需求危机（%d 次交往情分）" % (
                c.get("friend_name"), c.get("bond_trades", 0))
        if self.gtype == "sparring_duel":
            return "与 %s 切磋一场（%.1f 格外）——胜一场算数（R 键切磋）" % (
                c.get("npc_name"), c.get("dist", 0))
        if self.gtype == "element_resonance":
            return "元素共鸣：以「元素」特性引动一场切磋胜利（法阶 %d，bug 级机缘）" % (
                c.get("magic_rank", 0))
        return self.gtype

    def to_dict(self) -> dict:
        return {"gid": self.gid, "gtype": self.gtype, "title": self.title,
                "created_tick": self.created_tick, "deadline_tick": self.deadline_tick,
                "context": self.context, "status": self.status.value,
                "finished_tick": self.finished_tick, "fail_reason": self.fail_reason,
                "describe": self.describe()}


class GoalGenerator:
    """涌现式目标生成器：纯观察者，每 tick step(world) 一次。

    纪律：不消耗 world._rng；不写世界账本态；判据全部可由公开状态复算。
    """

    # 固定触发顺序（确定性的一部分：同 tick 多目标可触发时，先来先得 gid）
    RULES = ("seek_sustenance", "help_npc", "relocate", "complete_trade",
             "build_home", "create_work", "handle_legacy", "aid_friend",
             "sparring_duel", "element_resonance")

    def __init__(self, player, world=None, config: Optional[GoalConfig] = None):
        self.player = player
        self.config = config or GoalConfig()
        self.active: List[Goal] = []
        self.history: List[Goal] = []
        self._cooldown_until: Dict[str, int] = {}
        self._gid = 0
        # HLD：目标加入 player.active_goals；完成移入 player.goal_history。
        # 共享引用镜像（运行时属性）：不改 PlayerAgent 类定义，
        # to_dict()/state_hash() 不变（纪律 3）。
        player.active_goals = self.active
        player.goal_history = self.history

    # ---------------- 事件源工具（只读 event_log） ----------------

    def _events_since(self, world, etype, actor, since_tick) -> List[Event]:
        # 同 tick 边界用 >=：目标创建（check）发生在 world.tick 之后、玩家动作
        # 之前，同 tick 内玩家随后的动作（tick 值相同）必须计入完成判据；
        # 同 tick 的 NPC 事件因 actor 过滤天然排除，不会误判。
        out = []
        for e in world.event_log:
            if e.etype == etype and e.actor == actor and e.tick >= since_tick:
                out.append(e)
        return out

    def _traded_partners(self, world) -> List[str]:
        """玩家的"好友"操作定义：与玩家成交过的 NPC（按首次成交顺序）。"""
        pid = self.player.pid
        ids: List[str] = []
        for e in world.event_log:
            if e.etype == EventType.TRADE and e.actor == pid and e.target not in ids:
                ids.append(e.target)
        return ids

    # ---------------- 触发器（纯读；排序确定性：数值→距离→id） ----------------

    def _trig_seek_sustenance(self, world) -> Optional[dict]:
        p = self.player
        if p.needs["physiology"] >= self.config.sustenance_trigger:
            return None
        px, py = p.pos.x, p.pos.y
        best = None
        for r in world.resources:
            if r["amount"] <= 0 or r["type"] not in FOOD_TYPES:
                continue
            d = math.hypot(r["pos"][0] - px, r["pos"][1] - py)
            k = (round(d, 6), r["pos"])
            if best is None or k < best[0]:
                best = (k, r)
        return {"nearest_food": best[1]["pos"] if best else None,
                "nearest_food_type": best[1]["type"] if best else None,
                "nearest_food_dist": round(best[0][0], 2) if best else None}

    def _trig_help_npc(self, world) -> Optional[dict]:
        p = self.player
        px, py = p.pos.x, p.pos.y
        best = None
        for a in world.agents:
            if not a.alive:
                continue
            d = math.hypot(a.pos.x - px, a.pos.y - py)
            if d > self.config.social_radius:
                continue
            mn = _min_need(a)
            if mn >= self.config.crisis_need:
                continue
            k = (round(mn, 4), round(d, 6), a.aid)     # 最紧急 → 最近 → id
            if best is None or k < best[0]:
                best = (k, a)
        if best is None:
            return None
        a = best[1]
        return {"npc_aid": a.aid, "npc_name": a.name,
                "crisis_need": round(_min_need(a), 2),
                "dist": round(math.hypot(a.pos.x - px, a.pos.y - py), 2)}

    def _trig_relocate(self, world) -> Optional[dict]:
        p = self.player
        px, py = p.pos.x, p.pos.y
        for r in world.resources:
            if r["amount"] > 0 and math.hypot(
                    r["pos"][0] - px, r["pos"][1] - py) <= self.config.area_scan_radius:
                return None
        return {"from_region": (px, py), "scan_radius": self.config.area_scan_radius}

    def _trig_complete_trade(self, world) -> Optional[dict]:
        p = self.player
        if p.wealth < self.config.trade_min_wealth:
            return None
        px, py = p.pos.x, p.pos.y
        best = None
        for a in world.agents:
            if not a.alive or not a.inventory:
                continue
            d = math.hypot(a.pos.x - px, a.pos.y - py)
            if d > self.config.trade_radius:
                continue
            k = (round(d, 6), a.aid)
            if best is None or k < best[0]:
                best = (k, a)
        if best is None:
            return None
        a = best[1]
        return {"npc_aid": a.aid, "npc_name": a.name,
                "offered": sorted(a.inventory.keys())}

    def _trig_build_home(self, world) -> Optional[dict]:
        p = self.player
        if p.wealth <= self.config.home_wealth:      # HLD：wealth > 200（严格大于）
            return None
        if p.owned_buildings:
            return None
        return {"at": (p.pos.x, p.pos.y), "budget": round(p.wealth, 1)}

    def _trig_create_work(self, world) -> Optional[dict]:
        p = self.player
        if p.needs["self_actualization"] < self.config.create_trigger:
            return None
        return {"self_actualization": round(p.needs["self_actualization"], 1),
                "how": "调用 PlayerAgent.create_work(world, title) 创作作品"}

    def _trig_handle_legacy(self, world) -> Optional[dict]:
        best = None
        for a in world.agents:
            if a.alive or a.wealth <= 0:
                continue
            k = (-round(a.wealth, 4), a.aid)         # 遗产最多 → id
            if best is None or k < best[0]:
                best = (k, a)
        if best is None:
            return None
        a = best[1]
        return {"dead_aid": a.aid, "dead_name": a.name, "estate": round(a.wealth, 2),
                "how": "调用 goal_system.settle_legacy(world, dead_aid) 结算遗产"}

    def _trig_aid_friend(self, world) -> Optional[dict]:
        p = self.player
        partners = self._traded_partners(world)
        if not partners:
            return None
        helping = {g.context.get("npc_aid") for g in self.active
                   if g.gtype == "help_npc"}        # 已被 help_npc 盯上的不重复结目标
        best = None
        for fid in partners:                        # 首次成交顺序（事件源，确定性）
            a = world.find_agent(fid)
            if a is None or not a.alive or fid in helping:
                continue
            mn = _min_need(a)
            if mn >= self.config.crisis_need:
                continue
            bond = sum(1 for e in world.event_log
                       if e.etype == EventType.TRADE and e.actor == p.pid
                       and e.target == fid)
            k = (round(mn, 4), -bond, fid)           # 最紧急 → 情分最深 → id
            if best is None or k < best[0]:
                best = (k, a, bond)
        if best is None:
            return None
        a = best[1]
        return {"friend_aid": a.aid, "friend_name": a.name, "bond_trades": best[2],
                "crisis_need": round(_min_need(a), 2)}

    # ---- 战斗 v1 触发（切磋 / 元素共鸣；零 RNG，判据全部可复算）----
    def _trig_sparring_duel(self, world) -> Optional[dict]:
        """切磋目标：指定一名最近居民（距离→aid 字典序确定性），胜一场即成。"""
        px, py = self.player.fx, self.player.fy
        cands = [a for a in world.agents
                 if a.alive and a.aid != self.player.pid]
        if not cands:
            return None
        t = min(cands, key=lambda a: (round(
            math.hypot(a.pos.x - px, a.pos.y - py), 4), a.aid))
        d = math.hypot(t.pos.x - px, t.pos.y - py)
        return {"npc_aid": t.aid, "npc_name": getattr(t, "name", t.aid),
                "dist": round(d, 1)}

    def _trig_element_resonance(self, world) -> Optional[dict]:
        """元素共鸣（极稀有，bug 级）：仅「元素」魔力特性持有者且法阶≥5。
        时间窗 (tick+crc32(pid))%3000==7，一生一次（history 查重）——
        兑现世界观「能直接操控元素力者极少，玩家很难触发」。"""
        if self.player.affinity != "元素":
            return None
        if self.player.magic_rank < 5:
            return None
        if any(g.gtype == "element_resonance" for g in self.history):
            return None
        _w = (world._tick + zlib.crc32(
            str(self.player.pid).encode("utf-8"))) % 3000
        if _w != 7:
            return None
        return {"element": self.player.element,
                "magic_rank": self.player.magic_rank}

    # 类级触发器注册表（类体内在函数定义之后构建）
    _TRIGGERS = {
        "seek_sustenance": _trig_seek_sustenance,
        "help_npc": _trig_help_npc,
        "relocate": _trig_relocate,
        "complete_trade": _trig_complete_trade,
        "build_home": _trig_build_home,
        "create_work": _trig_create_work,
        "handle_legacy": _trig_handle_legacy,
        "aid_friend": _trig_aid_friend,
        "sparring_duel": _trig_sparring_duel,
        "element_resonance": _trig_element_resonance,
    }

    # ---------------- 生命周期 ----------------

    def check(self, world) -> List[Goal]:
        """触发相位：按 RULES 固定顺序扫描，满足条件且无同型活跃目标、
        冷却已过 → 创建目标。返回本 tick 新建的目标列表。"""
        created: List[Goal] = []
        if self.player is None:
            return created
        now = world._tick
        active_types = {g.gtype for g in self.active}
        for gtype in self.RULES:
            if gtype in active_types:
                continue
            if self._cooldown_until.get(gtype, -1) >= now:
                continue
            ctx = type(self)._TRIGGERS[gtype](self, world)
            if ctx is None:
                continue
            _dlb = (getattr(self.player, "vocation_effects", None) or {}).get("deadline_bonus", 0.0)
            g = Goal(gid="G%04d" % self._gid, gtype=gtype, created_tick=now,
                     deadline_tick=now + int(round(self.config.deadlines.get(gtype, 200) * (1.0 + _dlb))),
                     context=ctx)
            self._gid += 1
            self.active.append(g)
            active_types.add(gtype)
            created.append(g)
        return created

    def _settle(self, world, g: Goal) -> Optional[Tuple[GoalStatus, str]]:
        """完成/失败判据（纯读）。返回 None = 仍活跃。"""
        ctx = g.context
        t = g.gtype
        if t == "seek_sustenance":
            v = self.player.needs["physiology"]
            if v > self.config.sustenance_target:
                return (GoalStatus.COMPLETED, "生理需求已恢复至 %.0f" % v)
            return None
        if t == "help_npc":
            a = world.find_agent(ctx.get("npc_aid"))
            if a is None:
                return (GoalStatus.FAILED, "目标NPC不存在")
            if not a.alive:
                return (GoalStatus.FAILED, "目标NPC已死亡")
            if _min_need(a) > self.config.recovery_need:
                return (GoalStatus.COMPLETED,
                        "%s 的最低需求已恢复至 %.0f" % (a.name, _min_need(a)))
            return None
        if t == "relocate":
            px, py = self.player.pos.x, self.player.pos.y
            for r in world.resources:
                if r["amount"] > 0 and math.hypot(
                        r["pos"][0] - px, r["pos"][1] - py) <= self.config.area_rich_radius:
                    return (GoalStatus.COMPLETED,
                            "已抵达资源丰富区域（%s @ %s）" % (r["type"], r["pos"]))
            return None
        if t == "complete_trade":
            for e in self._events_since(world, EventType.TRADE,
                                        self.player.pid, g.created_tick):
                if e.target == ctx.get("npc_aid"):
                    return (GoalStatus.COMPLETED,
                            "与 %s 成交（%s）" % (ctx.get("npc_name"),
                                                 e.data.get("res")))
            return None
        if t == "build_home":
            if self.player.owned_buildings:
                return (GoalStatus.COMPLETED,
                        "住所已落成 @ %s" % (self.player.owned_buildings[-1],))
            return None
        if t == "create_work":
            evs = self._events_since(world, EventType.PRODUCE,
                                     self.player.pid, g.created_tick)
            if evs:
                return (GoalStatus.COMPLETED,
                        "作品已创作：%s（%s）" % (evs[-1].data.get("title"),
                                                 evs[-1].data.get("asset_id")))
            return None
        if t == "handle_legacy":
            d = world.find_agent(ctx.get("dead_aid"))
            if d is None:
                return (GoalStatus.FAILED, "死者档案不存在")
            if d.wealth <= 0:
                return (GoalStatus.COMPLETED,
                        "遗产 %.1f 已结算" % ctx.get("estate", 0))
            return None
        if t == "aid_friend":
            a = world.find_agent(ctx.get("friend_aid"))
            if a is None:
                return (GoalStatus.FAILED, "好友不存在")
            if not a.alive:
                return (GoalStatus.FAILED, "好友已死亡")
            if _min_need(a) > self.config.recovery_need:
                return (GoalStatus.COMPLETED,
                        "好友 %s 需求已恢复（%.0f）" % (a.name, _min_need(a)))
            return None
        if t == "sparring_duel":
            for e in self._events_since(world, EventType.DUEL,
                                        self.player.pid, g.created_tick):
                if e.target == ctx.get("npc_aid") and e.data.get("win"):
                    return (GoalStatus.COMPLETED,
                            "切磋获胜（%s 伤 %d）" % (e.data.get("skill"),
                                                     e.data.get("dmg", 0)))
            return None
        if t == "element_resonance":
            for e in self._events_since(world, EventType.DUEL,
                                        self.player.pid, g.created_tick):
                if e.data.get("win"):
                    return (GoalStatus.COMPLETED,
                            "元素共鸣达成（%s 引动 %s）" % (
                                ctx.get("element"), e.data.get("skill")))
            return None
        return None

    def update(self, world) -> List[dict]:
        """结算相位：完成/失败/过期，全部移入 history 并启动冷却。
        返回转移记录列表（GUI toast / 测试断言用）。"""
        out: List[dict] = []
        still: List[Goal] = []
        now = world._tick
        for g in self.active:
            res = self._settle(world, g)
            if res is None:
                if now >= g.deadline_tick:               # 完成优先于过期
                    g.status = GoalStatus.EXPIRED
                    g.finished_tick = now
                    self.history.append(g)
                    self._cooldown_until[g.gtype] = now + self.config.cooldowns.get(
                        g.gtype, 20)
                    out.append(self._transition(g))
                else:
                    still.append(g)
                continue
            st, reason = res
            g.status = st
            g.finished_tick = now
            g.fail_reason = reason
            self.history.append(g)
            self._cooldown_until[g.gtype] = now + self.config.cooldowns.get(g.gtype, 20)
            out.append(self._transition(g))
        self.active[:] = still                            # 原地更新，共享镜像引用不失效
        return out

    def step(self, world) -> List[dict]:
        """每 tick 一次：先结算旧目标（释放类型槽位），再触发新目标。"""
        return self.update(world) + [g.to_dict() for g in self.check(world)]

    # ---------------- 工具 ----------------

    def _transition(self, g: Goal) -> dict:
        return {"gid": g.gid, "gtype": g.gtype, "title": g.title,
                "status": g.status.value, "tick": g.finished_tick,
                "reason": g.fail_reason}

    def snapshot(self) -> dict:
        by_status = {s.value: sum(1 for g in self.history if g.status == s)
                     for s in GoalStatus}
        return {"active": len(self.active),
                "active_types": [g.gtype for g in self.active],
                "history": len(self.history), "by_status": by_status}


# ============================================================
# 遗产结算（handle_legacy 的执行点）
# ============================================================

def settle_legacy(world, dead_aid: str, heir_aid: Optional[str] = None,
                  by: str = "PLAYER") -> Optional[dict]:
    """结算死者遗产：wealth 划转给继承人；无继承人则归入国库。

    守恒（recompute）：两条路径都只是划转——
      继承：heir.wealth += amt 且 dead.wealth → 0，Σ(agents) 不变；
      无嗣：dead.wealth → 0 且 reserve.collect_fee(amt)（入国库），
            EconomicReserve.invariant_residual() 保持为 0。
    继承顺序（确定性）：显式 heir → 配偶（存活）→ friends 首位存活者 → 国库。
    记账：INTERACT 事件入 event_log 并登记因果图（构成公理三，与玩家
    交易同一通道）。
    """
    dead = world.find_agent(dead_aid)
    if dead is None or dead.alive:
        return None
    amt = dead.wealth
    if amt <= 0:
        return None
    heir = None
    if heir_aid:
        h = world.find_agent(heir_aid)
        if h is not None and h.alive:
            heir = h
    if heir is None and dead.partner_id:
        p = world.find_agent(dead.partner_id)
        if p is not None and p.alive:
            heir = p
    if heir is None and dead.friends:
        for fid in dead.friends:
            f = world.find_agent(fid)
            if f is not None and f.alive:
                heir = f
                break
    if heir is not None:
        heir.wealth += amt
        route, heir_used = "heir", heir.aid
    else:
        world.reserve.collect_fee(amt)
        route, heir_used = "treasury", None
    dead.wealth = 0.0
    ev = Event(eid=world.next_eid(), etype=EventType.INTERACT, actor=by,
               target=dead_aid, tick=world._tick,
               data={"action": "legacy_settlement", "amount": amt,
                     "route": route, "heir": heir_used})
    world.event_log.append(ev)
    world._record_event(ev)
    return {"dead_aid": dead_aid, "amount": amt, "route": route,
            "heir": heir_used, "event_id": ev.eid}


# ============================================================
# 装配子类：把目标层接进 tick 循环
# ============================================================

class GoalDrivenWorld(NohnWorld):
    """GoalGenerator 接入 tick 循环的纯增量装配：每 tick 先跑世界，
    再 step 目标层。目标层零 RNG 消耗、零账本写入 => 同 seed 世界轨迹
    与不挂载时逐字节一致（冒烟测试断言）。"""

    def __init__(self, config=None, goal_config: Optional[GoalConfig] = None):
        super().__init__(config)
        self.goal_config = goal_config
        self.goal_generator: Optional[GoalGenerator] = None
        self.last_goal_transitions: List[dict] = []

    def add_player(self, pid: str = "PLAYER", route: str = "magic"):
        p = super().add_player(pid, route=route)
        self.goal_generator = GoalGenerator(p, self, self.goal_config)
        return p

    def tick(self):
        te = super().tick()
        if self.goal_generator is not None and self.player is not None:
            self.last_goal_transitions = self.goal_generator.step(self)
        return te
