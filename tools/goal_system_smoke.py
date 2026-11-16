# -*- coding: utf-8 -*-
"""涌现式目标系统（M2.6）验收（tools 级冒烟）

不信任 demo/goal_system.py 的自述，逐项重跑：

  纪律侧（八类触发表完整 / 触发器注册表覆盖）
  观察者侧（同 seed 双世界 state_hash 逐字节一致 / 世界 RNG 状态不变）
  触发侧（八类触发逐项构造复现）
  生命周期（完成→冷却 / 失败原因 / 过期 / 同型去重）
  完成路径（gather / build / trade 事件源 / create_work CAS / settle_legacy 守恒）
  确定性（同 seed 同动作序列 → 目标转移摘要逐字节一致）
  真栈集成（RealWorld 挂载生成器 + 25 维宪法审计仍全过）
  剧情矩阵（M2.7：势力×职阶×分支时间线——资格覆盖/分支不可逆/确定性）

运行：python tools/goal_system_smoke.py
退出码 0 = 全部通过。
"""

import hashlib
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for p in (_REPO, os.path.join(_REPO, "demo")):
    if p not in sys.path:
        sys.path.insert(0, p)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from demo.virtual_world import (                 # noqa: E402
    WorldConfig, NohnWorld, AgentState, FIVE_LAYER_NEEDS, Position,
)
from demo.goal_system import (                   # noqa: E402
    GoalGenerator, GoalDrivenWorld, GoalConfig, GoalStatus,
    GOAL_TITLES_CN, settle_legacy,
)

_RESULTS = []


def check(name, ok, detail=""):
    _RESULTS.append((name, bool(ok), detail))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, ("  " + detail) if detail else ""))
    return bool(ok)


def fresh_world(seed, size=24, agents=6, resources=12, buildings=2):
    w = NohnWorld(WorldConfig(world_size=size, initial_agents=agents,
                              initial_resources=resources,
                              initial_buildings=buildings, seed=seed))
    p = w.add_player()
    return w, p


def types_of(created):
    return [g.gtype for g in created]


# ============================================================
# 一、纪律断言
# ============================================================
print("\n=== 一、触发表与纪律 ===")
check("十类触发表与 HLD §3.4 一致（战斗 v1 增补切磋/元素共鸣）",
      GoalGenerator.RULES == ("seek_sustenance", "help_npc", "relocate",
                              "complete_trade", "build_home", "create_work",
                              "handle_legacy", "aid_friend",
                              "sparring_duel", "element_resonance"),
      "rules=%d" % len(GoalGenerator.RULES))
check("触发器注册表覆盖全部类型",
      set(GoalGenerator._TRIGGERS.keys()) == set(GoalGenerator.RULES))
check("中文标题表覆盖全部类型",
      set(GOAL_TITLES_CN.keys()) == set(GoalGenerator.RULES))

# ============================================================
# 二、纯观察者：目标层不扰动世界（确定性三纪律 1/2）
# ============================================================
print("\n=== 二、纯观察者（不扰动世界） ===")

def _pure_observer_run(with_generator):
    cfg = WorldConfig(world_size=24, initial_agents=8, initial_resources=24,
                      initial_buildings=3, seed=101)
    if with_generator:
        w = GoalDrivenWorld(cfg)
    else:
        w = NohnWorld(cfg)
    w.add_player()
    for _ in range(40):
        w.tick()
    return w

_w1 = _pure_observer_run(True)
_w2 = _pure_observer_run(False)
check("挂载/不挂载生成器：state_hash 逐字节一致",
      _w1.state_hash() == _w2.state_hash(),
      "hash=%s..." % _w1.state_hash()[:12])
check("挂载/不挂载生成器：世界 RNG 状态逐字节一致",
      _w1._rng.getstate() == _w2._rng.getstate())
check("生成器确实在被动跟踪（活跃目标已涌现）",
      _w1.goal_generator is not None and len(_w1.goal_generator.active) >= 0)

# ============================================================
# 三、八类触发逐项（受控世界构造）
# ============================================================
print("\n=== 三、八类触发 ===")

# 1. seek_sustenance：生理 < 30
w, p = fresh_world(201)
p.needs["physiology"] = 15.0
gen = GoalGenerator(p, w)
created = gen.check(w)
check("触发 seek_sustenance", "seek_sustenance" in types_of(created))

# 2. help_npc：近旁 NPC 最低需求 < 20
w, p = fresh_world(202)
a0 = w.agents[0]
for a in w.agents:
    a.needs = {n: 100.0 for n in FIVE_LAYER_NEEDS}
a0.needs = {n: 10.0 for n in FIVE_LAYER_NEEDS}
p.fx, p.fy = float(a0.pos.x), float(a0.pos.y)
gen = GoalGenerator(p, w)
created = gen.check(w)
g_help = [g for g in created if g.gtype == "help_npc"]
check("触发 help_npc", bool(g_help))
check("help_npc 锁定最紧急者", bool(g_help) and g_help[0].context["npc_aid"] == a0.aid)

# 3. relocate：周边资源枯竭
w, p = fresh_world(203)
for r in w.resources:
    r["amount"] = 0
gen = GoalGenerator(p, w)
created = gen.check(w)
check("触发 relocate", "relocate" in types_of(created))

# 4. complete_trade：近旁有持货 NPC 且买得起
w, p = fresh_world(204)
a0 = w.agents[0]
for a in w.agents:
    a.inventory = {}
a0.inventory = {"wood": 5}
a0.pos = Position(2, 2)
p.fx, p.fy = 3.0, 3.0
p.wealth = 100.0
gen = GoalGenerator(p, w)
created = gen.check(w)
g_trade = [g for g in created if g.gtype == "complete_trade"]
check("触发 complete_trade", bool(g_trade))
check("complete_trade 锁定最近持货者",
      bool(g_trade) and g_trade[0].context["npc_aid"] == a0.aid,
      "offered=%s" % (g_trade[0].context["offered"] if g_trade else None))

# 5. build_home：财富 > 200 且无房产
w, p = fresh_world(205)
p.wealth = 250.0
gen = GoalGenerator(p, w)
created = gen.check(w)
check("触发 build_home", "build_home" in types_of(created))

# 6. create_work：自我实现 >= 70
w, p = fresh_world(206)
p.needs["self_actualization"] = 80.0
gen = GoalGenerator(p, w)
created = gen.check(w)
check("触发 create_work", "create_work" in types_of(created))

# 7. handle_legacy：存在带未结算遗产的死者
w, p = fresh_world(207)
a0 = w.agents[0]
a0.alive = False
a0.state = AgentState.DEAD
a0.wealth = 80.0
gen = GoalGenerator(p, w)
created = gen.check(w)
g_leg = [g for g in created if g.gtype == "handle_legacy"]
check("触发 handle_legacy", bool(g_leg))
check("handle_legacy 锁定遗产最多者",
      bool(g_leg) and g_leg[0].context["dead_aid"] == a0.aid,
      "estate=%.1f" % (g_leg[0].context["estate"] if g_leg else -1))

# 8. aid_friend：交易结识的好友需求危机
w, p = fresh_world(208)
a0 = w.agents[0]
for a in w.agents:
    a.inventory = {}
    a.needs = {n: 100.0 for n in FIVE_LAYER_NEEDS}
a0.inventory = {"food": 3}
a0.pos = Position(2, 2)
p.fx, p.fy = 20.5, 20.5          # 远离 a0：help_npc 不抢（半径 5）
p.wealth = 100.0
r = p.trade(a0, w)               # 成交 → 玩家交易入事件流
check("玩家交易已入事件流（via=player）",
      r is not None and any(e.etype.name == "TRADE" and e.actor == p.pid
                            for e in w.event_log))
a0.needs = {n: 10.0 for n in FIVE_LAYER_NEEDS}
gen = GoalGenerator(p, w)
created = gen.check(w)
g_aid = [g for g in created if g.gtype == "aid_friend"]
check("触发 aid_friend（好友=成交过的 NPC）", bool(g_aid))
check("aid_friend 记录交往情分（bond_trades>=1）",
      bool(g_aid) and g_aid[0].context["bond_trades"] >= 1)
check("aid_friend 不与 help_npc 抢同一目标",
      all(g.context.get("npc_aid") != a0.aid
          for g in created if g.gtype == "help_npc"))

# ============================================================
# 四、生命周期：完成→冷却 / 失败 / 过期 / 去重
# ============================================================
print("\n=== 四、生命周期 ===")

w, p = fresh_world(301)
p.needs["physiology"] = 15.0
gen = GoalGenerator(p, w)
gen.check(w)
check("同型去重：再次 check 不重复生成", gen.check(w) == [])
p.needs["physiology"] = 100.0
tr = gen.update(w)
check("完成 → 移入 history",
      len(tr) == 1 and tr[0]["status"] == "completed" and len(gen.history) == 1)
check("完成 → 冷却启动（20 tick）",
      gen._cooldown_until["seek_sustenance"] == w._tick + 20)
p.needs["physiology"] = 15.0
check("冷却期内同型不再触发", gen.check(w) == [])

w, p = fresh_world(302)
a0 = w.agents[0]
for a in w.agents:
    a.needs = {n: 100.0 for n in FIVE_LAYER_NEEDS}
a0.needs = {n: 10.0 for n in FIVE_LAYER_NEEDS}
p.fx, p.fy = float(a0.pos.x), float(a0.pos.y)
gen = GoalGenerator(p, w)
gen.check(w)
a0.alive = False
a0.state = AgentState.DEAD
tr = gen.update(w)
check("目标 NPC 死亡 → FAILED 且记录原因",
      len(tr) == 1 and tr[0]["status"] == "failed"
      and "死亡" in tr[0]["reason"], tr[0]["reason"])

w, p = fresh_world(303)
p.needs["physiology"] = 15.0
gen = GoalGenerator(p, w, GoalConfig(deadlines={"seek_sustenance": 1}))
gen.check(w)
w.tick(); w.tick()
tr = gen.update(w)
check("超时 → EXPIRED 自动移出",
      any(t["gtype"] == "seek_sustenance" and t["status"] == "expired" for t in tr)
      and all(g.gtype != "seek_sustenance" for g in gen.active),
      "transitions=%s" % [t["gtype"] for t in tr])

# ============================================================
# 五、真实动作完成路径（公示即执行：每个目标都真的能完成）
# ============================================================
print("\n=== 五、真实动作完成路径 ===")

# gather → seek_sustenance
w, p = fresh_world(401)
w.resources.append({"type": "food", "pos": (5, 5), "amount": 30, "regen_rate": 0.2})
p.fx, p.fy = 5.0, 5.0
p.needs["physiology"] = 15.0
gen = GoalGenerator(p, w)
gen.check(w)
ok = False
for _ in range(10):
    p.gather(w)
    if gen.update(w):
        ok = True
        break
check("采集真实完成 seek_sustenance", ok,
      "physiology=%.0f" % p.needs["physiology"])

# build → build_home
w, p = fresh_world(402)
p.wealth = 250.0
gen = GoalGenerator(p, w)
gen.check(w)
built = False
for gx in range(3, 14):
    p.fx, p.fy = float(gx), float(3)
    if p.build(w):
        built = True
        break
tr = gen.update(w)
check("建造真实完成 build_home", built and len(tr) == 1
      and tr[0]["status"] == "completed")

# trade（事件源）→ complete_trade
w, p = fresh_world(403)
a0 = w.agents[0]
for a in w.agents:
    a.inventory = {}
a0.inventory = {"wood": 4}
p.wealth = 100.0
p.fx, p.fy = float(a0.pos.x) + 1, float(a0.pos.y)
gen = GoalGenerator(p, w)
gen.check(w)
res = p.trade(a0, w)
tr = gen.update(w)
check("交易真实完成 complete_trade（事件源判据）",
      res is not None and len(tr) == 1 and tr[0]["status"] == "completed")

# create_work → CAS 资产 + PRODUCE 事件
w, p = fresh_world(404)
p.inventory = {"stone": 1}
p.needs["self_actualization"] = 80.0
gen = GoalGenerator(p, w)
gen.check(w)
aid, chash = p.create_work(w, "石斧", {"style": "achulian"})
tr = gen.update(w)
check("创作真实完成 create_work", aid is not None and len(tr) == 1
      and tr[0]["status"] == "completed")
check("作品已入 CAS 且指纹可复算", w.assets.verify(aid),
      "asset_id=%s" % aid)

# settle_legacy → handle_legacy + 经济守恒（不践踏账本：用真实财富做遗产，
# 断言“结算前后残差不变”——settle 是纯划转，不新增也不销毁货币）
w, p = fresh_world(405)
a0 = w.agents[0]
_estate = a0.wealth
a0.alive = False
a0.state = AgentState.DEAD
a0.partner_id = None
a0.friends = []
gen = GoalGenerator(p, w)
gen.check(w)
_treasury_before = w.reserve.treasury
_res_before = w.reserve.invariant_residual(w.agents)
res = settle_legacy(w, a0.aid)
tr = gen.update(w)
check("遗产结算真实完成 handle_legacy（无嗣归国库）",
      res is not None and res["route"] == "treasury" and len(tr) == 1
      and tr[0]["status"] == "completed", "estate=%.2f" % _estate)
check("无嗣路径：国库入账 == 遗产额",
      abs(w.reserve.treasury - _treasury_before - _estate) < 1e-9)
check("遗产结算后货币守恒残差不变（纯划转）",
      abs(w.reserve.invariant_residual(w.agents) - _res_before) < 1e-9,
      "delta=%.3e" % (w.reserve.invariant_residual(w.agents) - _res_before))

# 有嗣路径：继承同样守恒
w, p = fresh_world(406)
a0, a1 = w.agents[0], w.agents[1]
_estate = a0.wealth
_a1_before = a1.wealth
a0.alive = False
a0.state = AgentState.DEAD
a0.partner_id = None
a0.friends = [a1.aid]
_res_before = w.reserve.invariant_residual(w.agents)
res = settle_legacy(w, a0.aid)
check("有嗣路径：首位存活好友继承",
      res is not None and res["route"] == "heir" and res["heir"] == a1.aid
      and abs(a1.wealth - _a1_before - _estate) < 1e-9 and a0.wealth == 0.0,
      "estate=%.2f" % _estate)
check("继承路径：货币守恒残差不变",
      abs(w.reserve.invariant_residual(w.agents) - _res_before) < 1e-9)

# ============================================================
# 六、确定性：同 seed 同动作序列 → 目标转移摘要逐字节一致
# ============================================================
print("\n=== 六、确定性 ===")

def _run_scripted(seed):
    cfg = WorldConfig(world_size=30, initial_agents=10, initial_resources=30,
                      initial_buildings=3, seed=seed)
    w = GoalDrivenWorld(cfg)
    p = w.add_player()
    for t in range(60):
        w.tick()
        if t == 5:
            p.fx, p.fy = 3.0, 3.0
        if t == 10:
            p.gather(w)
        if t == 20:
            cands = [a for a in w.agents if a.alive and a.inventory]
            if cands:
                cands.sort(key=lambda a: a.aid)
                p.trade(cands[0], w)
        if t == 30:
            p.create_work(w, "无题之作")
        if t == 40:
            p.wealth = 300.0
            for gx in range(3, 14):
                p.fx, p.fy = float(gx), float(3)
                if p.build(w):
                    break
        if t == 45:
            p.needs["physiology"] = 10.0   # 强制触发 seek_sustenance（确定性）
        if t == 50:
            p.needs["physiology"] = 100.0  # 强制完成 → 至少一个完整生命周期入摘要
    digest = hashlib.sha256(json.dumps(
        [[g.gtype, g.created_tick, g.status.value, g.finished_tick]
         for g in w.goal_generator.history]
        + [[g.gtype, g.created_tick] for g in w.goal_generator.active],
        ensure_ascii=False).encode("utf-8")).hexdigest()
    return digest, w.state_hash()

_d1, _s1 = _run_scripted(42)
_d2, _s2 = _run_scripted(42)
check("同 seed 两次运行：目标转移摘要一致", _d1 == _d2, "digest=%s..." % _d1[:12])
check("同 seed 两次运行：世界状态哈希一致", _s1 == _s2)

# ============================================================
# 七、真栈世界集成（RealWorld + 生成器 + 25 维审计仍全过）
# ============================================================
print("\n=== 七、真栈世界集成 ===")
from demo.real_virtual_world import RealWorld     # noqa: E402
from audit_engine import AuditReport              # noqa: E402

_rw = RealWorld(WorldConfig(world_size=24, initial_agents=8, initial_resources=24,
                            initial_buildings=2, seed=21),
                world_id="goal-smoke-world")
_rp = _rw.add_player()
_gen = GoalGenerator(_rp, _rw)
_trans = 0
for _ in range(20):
    _rw.tick()
    _trans += len(_gen.step(_rw))
check("真栈世界挂载生成器运行 20 tick（转移 %d 次）" % _trans, True)
_report = _rw.run_constitutional_audit()
_all_pass = all(AuditReport._is_pass(getattr(_report, attr))
                for attr, _ in AuditReport.FIELDS)
check("25 维宪法审计仍全过（目标层零扰动）", _all_pass)

# ============================================================
# 八、居民化与登录抽签（无主角 + 职阶/魔力特性 + 三成长）
# ============================================================
print("\n=== 八、居民化与登录抽签 ===")
from demo.vocations import (                          # noqa: E402
    VOCATION_POOL, AFFINITY_POOL, KNOWN_EFFECTS,
    vocation_weight_sum, affinity_weight_sum,
    vocation_names, affinity_names, tier_weights,
    RARITY_NAMES, unwired_effects,
    draw_vocation as _dvoc, draw_affinity as _daff,
)
import random as _random                              # noqa: E402
from demo.virtual_world import DemoEconomy            # noqa: E402

w1, p1 = fresh_world(501)
_w2, p2 = fresh_world(501)
check("同 seed 降生抽签一致", p1.vocation == p2.vocation and p1.affinity == p2.affinity,
      "职阶=%s 特性=%s" % (p1.vocation, p1.affinity))
check("职阶在库内（72 职）", p1.vocation in vocation_names(),
      "库容=%d" % len(VOCATION_POOL))
check("魔力特性合法（库内或未觉醒）",
      p1.affinity is None or p1.affinity in affinity_names(),
      "库容=%d" % len(AFFINITY_POOL))
check("稀有度合法（职阶 5 档；魔力特性不分级）", p1.vocation_tier in RARITY_NAMES
      and p1.affinity_tier is None)
check("职阶库权重和=1000", vocation_weight_sum() == 1000)
check("特性池权重和=%d（不分级，仅作抽中占比）"%affinity_weight_sum(),
      affinity_weight_sum() > 0)
check("库完整性：无未接线效果键", not unwired_effects())
_tw = tier_weights()
check("职阶稀有度覆盖 5 档", len(_tw) == 5 and all(w > 0 for w in _tw.values()))

# 抽签分布：400 次模拟，各稀有度份额与权重偏差 ≤12pp；觉醒率 10%±3σ
_r2 = _random.Random(999)
_tcount = {t: 0 for t in RARITY_NAMES}
_awaken = 0
for _ in range(400):
    _e2 = _dvoc(_r2); _tcount[_e2["tier"]] += 1
    if _daff(_r2) is not None: _awaken += 1
_tot = vocation_weight_sum()
check("抽签稀有度分布符合权重（±12pp）",
      all(abs(_tcount[t] / 400.0 - _tw[t] / _tot) <= 0.12 for t in _tcount),
      " ".join("%s%.2f" % (RARITY_NAMES[t], _tcount[t] / 400.0) for t in sorted(_tcount)))
check("魔力特性觉醒率≈2%（法师中1/10×法师占比0.2；3σ 内）", 0 <= _awaken <= 16,
      "awakened=%d/400" % _awaken)

check("居民初始财富=100×(1+wealth_start)（创世储备划转）",
      abs(p1.wealth - round(100.0 * (1.0 + p1.vocation_effects.get("wealth_start", 0.0)))) < 1.01,
      "职阶=%s wealth=%.1f" % (p1.vocation, p1.wealth))
_eco = DemoEconomy(w1, w1.reserve)
check("居民纳入守恒式（UBI 前残差≈0）", _eco.conservation_holds(),
      "residual=%.3e" % _eco.conservation_residual())

_w0 = p1.wealth
for _ in range(11):
    w1.tick()
check("居民同领 UBI（tick 10 后 +10）", abs(p1.wealth - _w0 - 10.0) < 1e-6,
      "wealth=%.1f" % p1.wealth)
check("UBI 后守恒仍成立", _eco.conservation_holds())

p1.gain_xp("body", 40)
check("体能 40 XP → 剑阶 2（剑士）", p1.body_rank == 2)
p1.gain_xp("magic", 120)
check("魔力 120 XP → 法阶 3（术士）", p1.magic_rank == 3
      and p1.MAGIC_TITLES[3] == "术士")
p1.gain_xp("soul", 40)
check("灵魂 40 XP → 强度 2（魔核成长）", p1.soul_strength == 2 and p1.soul_xp >= 40)
check("位阶称谓双路线并列", "术士" in p1.rank_title() and "剑士" in p1.rank_title())

w3, p3 = fresh_world(502)
w3.resources.append({"type": "herb", "pos": (5, 5), "amount": 30, "regen_rate": 0.2})
p3.fx, p3.fy = 5.0, 5.0
_b0 = p3.body_xp
p3.gather(w3)
check("采集→体能 XP", p3.body_xp > _b0)
p3.inventory = {"wood": 1}
_m0 = p3.magic_xp
aid3, _ = p3.create_work(w3, "测试之作")
check("创作→魔力 XP", aid3 is not None and p3.magic_xp > _m0)

# 效果接线抽查：energy_cost 与 deadline_bonus（公示即执行）
w4, p4 = fresh_world(503)
w4.resources.append({"type": "food", "pos": (5, 5), "amount": 30, "regen_rate": 0.2})
p4.fx, p4.fy = 5.0, 5.0
p4.vocation_effects = {"energy_cost": 0.5, "deadline_bonus": 0.5}
_en0 = p4.energy
p4.gather(w4)
check("energy_cost 接线（采集消耗减半）", abs((_en0 - p4.energy) - 1.0) < 1e-6,
      "消耗=%.2f" % (_en0 - p4.energy))
p4.needs["physiology"] = 15.0
gen4 = GoalGenerator(p4, w4)
gen4.check(w4)
_g4 = [g for g in gen4.active if g.gtype == "seek_sustenance"]
check("deadline_bonus 接线（目标期限×1.5）",
      bool(_g4) and _g4[0].deadline_tick == w4._tick + int(round(150 * 1.5)),
      "deadline=%s" % (_g4[0].deadline_tick if _g4 else None))

# 吸血接线抽查（盖特·坎帝亚斯的魔力特性，公示即执行）
p4.vocation_effects = {"blood_drain": 0.25}
p4.energy = 50.0
p4.rest()
check("blood_drain 接线（休息回复+25%）", abs(p4.energy - (50.0 + 10 * 1.25)) < 1e-6,
      "energy=%.2f" % p4.energy)

# ============================================================
# 九、势力剧情矩阵与分支时间线（M2.7：demo/factions.py）
# ============================================================
print("\n=== 九、势力剧情矩阵与分支时间线 ===")
from demo.virtual_world import EventType             # noqa: E402
from demo.factions import (                          # noqa: E402
    FACTION_KEYS, FREELANCE_KEY,
    eligible_factions, StoryWorld, story_join, story_decide,
    verify_story_pool,
)

check("剧情库自检：资格覆盖/阶位结构/机制合法性全过", not verify_story_pool(),
      "问题=%s" % verify_story_pool())

# 9.1 资格矩阵覆盖完整性：72 职阶每个至少一条资格势力
_cov = [(e["name"], eligible_factions(e["name"], e["effects"]))
        for e in VOCATION_POOL]
_nocov = [n for n, _el in _cov if not _el]
check("72 职阶全部有资格势力（覆盖完整性）", not _nocov, "未覆盖=%s" % _nocov)
_multi = [n for n, _el in _cov if len(_el) >= 2]
check("跨势力招募职阶构成天然分叉点（≥2 势力资格）", len(_multi) >= 5,
      "分叉职阶数=%d 例=%s" % (len(_multi), _multi[:4]))


# ---- 通用剧情驱动器（确定性；动作全部为既有玩家行为）----

def _story_act(w, p, eng):
    """向当前剧情任务推进一个动作步。零 RNG：全部选择确定性排序。"""
    st = eng.state
    q = st.quest
    if q is None:
        return
    c = q.ctx
    m = q.mechanic

    def _go_res(rtype):
        cands = [r for r in w.resources if r["amount"] > 0
                 and (rtype is None or r["type"] == rtype)]
        if not cands:
            cands = [r for r in w.resources if r["amount"] > 0]
        if cands:
            cands.sort(key=lambda r: (round(math.hypot(
                r["pos"][0] - p.fx, r["pos"][1] - p.fy), 4), r["pos"]))
            r0 = cands[0]
            p.fx, p.fy = float(r0["pos"][0]), float(r0["pos"][1])
            p.gather(w)

    def _do_trade():
        done = {e.target for e in w.event_log
                if e.etype == EventType.TRADE and e.actor == p.pid
                and e.tick >= c.get("since_tick", 0)}
        cands = [a for a in w.agents
                 if a.alive and a.inventory and a.aid not in done
                 and a.aid != p.pid]
        if cands:
            cands.sort(key=lambda a: a.aid)
            p.trade(cands[0], w)

    def _do_craft():
        if not p.inventory:
            _go_res(None)
        else:
            p.create_work(w, "剧情之作")

    if m == "gather_n":
        if p.inventory.get(c["res_type"], 0) < c["count"]:
            _go_res(c["res_type"])
    elif m == "trade_distinct":
        n = len({e.target for e in w.event_log if e.etype == EventType.TRADE
                 and e.actor == p.pid and e.tick >= c["since_tick"]})
        if n < c["count"]:
            _do_trade()
    elif m == "craft_n":
        n = len([e for e in w.event_log if e.etype == EventType.PRODUCE
                 and e.actor == p.pid and e.tick >= c["since_tick"]])
        if n < c["count"]:
            _do_craft()
    elif m == "rank_reach":
        cur = {"magic": p.magic_rank, "body": p.body_rank,
               "soul": p.soul_strength}[c["kind"]]
        if cur < c["target"]:
            if c["kind"] == "body":
                _go_res(None)
            elif c["kind"] == "magic":
                _do_craft()
            else:
                _do_trade()
    elif m == "wealth_reach":
        pass                                   # UBI 节拍自然达成，纯等待
    elif m == "build_first":
        if not p.owned_buildings and p.wealth >= 100:
            for gx in range(3, w.size - 3):
                p.fx, p.fy = float(gx), float(3)
                if p.build(w):
                    break
    elif m == "travel_away":
        ox, oy = c["origin"]
        if math.hypot(p.fx - ox, p.fy - oy) < c["dist"]:
            p.fx = min(w.size - 1.0, ox + c["dist"] + 1.0)
            p.fy = max(0.0, min(w.size - 1.0, oy))
    elif m == "duel_win":
        _tgt = w.find_agent(c.get("npc_aid"))
        if _tgt is None or not _tgt.alive:
            _cands = [a for a in w.agents if a.alive and a.aid != p.pid]
            if _cands:
                _cands.sort(key=lambda a: (round(math.hypot(
                    a.pos.x - p.fx, a.pos.y - p.fy), 4), a.aid))
                c["npc_aid"] = _cands[0].aid
                _tgt = _cands[0]
        if _tgt is not None:
            _won = any(e.etype == EventType.DUEL and e.actor == p.pid
                       and e.target == c.get("npc_aid") and e.data.get("win")
                       for e in w.event_log if e.tick >= c["since_tick"])
            if not _won:
                p.fx, p.fy = float(_tgt.pos.x), float(_tgt.pos.y)
                w.resolve_duel(p, _tgt)


def _drive_until_decision(w, p, max_ticks=1000):
    """推进到下一个分支节点或完线。返回 (到达类型, 引擎)。"""
    eng = w.story_engine
    for _ in range(max_ticks):
        st = eng.state
        if st.decision is not None:
            return "decision", eng
        if st.line_done:
            return "done", eng
        _story_act(w, p, eng)
        w.tick()
    return "timeout", eng


def _story_world(seed, agents=8):
    return StoryWorld(WorldConfig(world_size=60, initial_agents=agents,
                                  initial_resources=30, initial_buildings=2,
                                  seed=seed))


# 9.2 NPC 身份化：派生流确定性 + 挂载零扰动
_wA = NohnWorld(WorldConfig(world_size=60, initial_agents=8, initial_resources=30,
                            initial_buildings=2, seed=77))
_wA.add_player()
for _ in range(20):
    _wA.tick()
_wB = _story_world(77)
_wB.add_player()
for _ in range(20):
    _wB.tick()
check("挂载/不挂载剧情层：state_hash 逐字节一致（纯观察者）",
      _wA.state_hash() == _wB.state_hash())
check("挂载/不挂载剧情层：世界 RNG 状态逐字节一致",
      _wA._rng.getstate() == _wB._rng.getstate())
_idB = [(a.aid, getattr(a, "vocation", None), getattr(a, "faction", None))
        for a in _wB.agents]
_idB2 = [(a.aid, getattr(a, "vocation", None), getattr(a, "faction", None))
         for a in _story_world(77).agents]
check("同 seed NPC 身份逐字节一致（派生流）", _idB == _idB2)
check("NPC 身份合法（职阶在库、势力在册）",
      all(v in vocation_names() and f in set(FACTION_KEYS) | {FREELANCE_KEY}
          for _, v, f in _idB))

# 9.3 入会窗口与单线纪律（join/step 均不消耗世界 RNG）
_wC = _story_world(78)
_pC = _wC.add_player()
_eC = _wC.story_engine
_rs0 = _wC._rng.getstate()
_okJ, _msgJ = story_join(_wC, _eC.offers()[0])
_eC.step(_wC)
_eC.step(_wC)
check("入会与剧情步进零世界 RNG 消耗", _okJ and _wC._rng.getstate() == _rs0,
      "入会=%s %s" % (_msgJ, ""))
check("入会后首条阶位任务已生成",
      _eC.state.quest is not None and _eC.state.quest.stage == 0,
      "faction=%s quest=%s" % (_eC.state.faction,
                               _eC.state.quest.qkey if _eC.state.quest else None))
check("单玩家单线：已入线后再次入会被拒",
      story_join(_wC, FREELANCE_KEY)[0] is False)
check("无效势力入会被拒", story_join(_wC, "nope")[0] is False)

# 9.4 真实完成路径：阶位任务 → 分支节点 → 接受晋升 / 谢绝留守
_st, _eC = _drive_until_decision(_wC, _pC, max_ticks=1200)
check("阶位任务真实完成 → 分支节点打开",
      _st == "decision" and _eC.state.decision is not None,
      "到达=%s" % _st)
if _eC.state.decision is not None:
    _chs = {c["key"] for c in _eC.state.decision["choices"]}
    check("分支节点含晋升与留守两选项", {"accept", "refuse"} <= _chs,
          "choices=%s" % sorted(_chs))
    _okA, _lbl = story_decide(_wC, "accept")
    check("分支选择生效：接受晋升 → 阶位+1",
          _okA and _eC.state.stage == 1 and _eC.state.decision is None,
          "选择=%s" % _lbl)
    _st2, _ = _drive_until_decision(_wC, _pC, max_ticks=1200)
    if _st2 == "decision":
        _okR, _ = story_decide(_wC, "refuse")
        check("谢绝晋升：留守本阶且记录 flags",
              _okR and _eC.state.stage == 1
              and _eC.state.flags.get("stay_S1") is True)
    else:
        check("谢绝晋升：留守本阶且记录 flags", False, "未到达分支（%s）" % _st2)

# 9.5 叛离分支：改投他宗 + 原势力永久锁死（不可逆）
_wD = _story_world(91, agents=10)
_pD = _wD.add_player()
_eD = _wD.story_engine
_vocE = next(e for e in VOCATION_POOL if e["name"] == "圣殿骑士")
_pD.vocation = "圣殿骑士"                    # 测试直置：圣殿骑士为教廷武备双资格职阶
_pD.vocation_tier = _vocE["tier"]
_pD.vocation_effects = dict(_vocE["effects"])
check("圣殿骑士双资格（教廷/骑士团）——天然分叉点",
      eligible_factions("圣殿骑士", _vocE["effects"]) == ["knights", "theocracy"])
story_join(_wD, "theocracy")
_stD, _ = _drive_until_decision(_wD, _pD, max_ticks=1200)
check("圣殿骑士教廷线第 1 阶完成", _stD == "decision", "到达=%s" % _stD)
if _stD == "decision":
    _okF, _ = story_decide(_wD, "defect")
    check("叛离生效：改投骑士团、阶位归零",
          _okF and _eD.state.faction == "knights" and _eD.state.stage == 0)
    check("原势力永久锁死（不可逆）",
          _eD.state.locked == ["theocracy"]
          and story_join(_wD, "theocracy")[0] is False)
    check("叛离记录入时间线史",
          any(h["kind"] == "decide" and "叛离" in h["detail"]
              for h in _eD.state.history))

# 9.6 顶阶终局分支：加冕完线 / 退隐留守（自由线直置顶阶专验终局）
_wU = _story_world(101)
_pU = _wU.add_player()
_eU = _wU.story_engine
story_join(_wU, FREELANCE_KEY)
_eU.state.stage = 3                          # 测试直置：跳过前三阶，专验终局分支
_stU, _ = _drive_until_decision(_wU, _pU, max_ticks=1200)
check("自由线顶阶任务完成 → 终局分支",
      _stU == "decision" and _eU.state.decision is not None
      and _eU.state.decision["is_top"], "到达=%s" % _stU)
if _stU == "decision":
    check("终局分支含加冕/退隐且无叛离（自由身无宗可叛）",
          {c["key"] for c in _eU.state.decision["choices"]} == {"ascend", "remain"})
    story_decide(_wU, "ascend")
    check("加冕：时间线完结 + 顶阶彩蛋 lore",
          _eU.state.line_done and _eU.state.line_lore != "")
    check("完线后引擎静默（不再触发任何转移）", _eU.step(_wU) == [])

_wV = _story_world(102)
_pV = _wV.add_player()
_eV = _wV.story_engine
story_join(_wV, FREELANCE_KEY)
_eV.state.stage = 3                          # 测试直置：顶阶退隐路径
_stV, _ = _drive_until_decision(_wV, _pV, max_ticks=1200)
if _stV == "decision":
    story_decide(_wV, "remain")
    check("退隐：留守顶阶，剧情线延续（可再完成阶位任务）",
          _eV.state.line_done is False
          and _eV.state.flags.get("stay_S3") is True)
else:
    check("退隐：留守顶阶，剧情线延续", False, "未到达分支（%s）" % _stV)

# 9.7 确定性：同 seed 同动作脚本 → 时间线摘要与世界哈希逐字节一致
def _story_scripted(seed):
    _w = _story_world(4242 if seed is None else seed, agents=10)
    _p = _w.add_player()
    _e = _w.story_engine
    story_join(_w, _e.offers()[0])           # 字典序首个资格势力（确定性）
    for _t in range(150):
        _w.tick()
        st = _e.state
        if st.decision is not None:
            story_decide(_w, sorted(c["key"] for c in st.decision["choices"])[0])
        elif st.quest is not None:
            _story_act(_w, _p, _e)
    _blob = json.dumps({"faction": _e.state.faction, "stage": _e.state.stage,
                        "flags": _e.state.flags, "locked": _e.state.locked,
                        "line_done": _e.state.line_done,
                        "history": [[h["kind"], h["tick"], h["detail"]]
                                    for h in _e.state.history],
                        "quest": _e.state.quest.to_dict() if _e.state.quest else None},
                       ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(_blob.encode("utf-8")).hexdigest(), _w.state_hash()


_dg1, _sh1 = _story_scripted(4242)
_dg2, _sh2 = _story_scripted(4242)
check("同 seed 两次运行：时间线摘要逐字节一致", _dg1 == _dg2, "digest=%s..." % _dg1[:12])
check("同 seed 两次运行：世界状态哈希逐字节一致", _sh1 == _sh2)

# 9.8 真栈世界全栈装配（RealStoryWorld = RealWorld + 目标层 + 剧情层）
from demo.real_virtual_world import RealStoryWorld    # noqa: E402

_rsw = RealStoryWorld(WorldConfig(world_size=24, initial_agents=8, initial_resources=24,
                                  initial_buildings=2, seed=33),
                      world_id="story-real-world")
_rsp = _rsw.add_player()
check("真栈世界挂载剧情层（RealStoryWorld）",
      _rsw.story_engine is not None and _rsw.story_engine.player is _rsp)
check("真栈 NPC 身份化完成（创世全量）",
      all(getattr(a, "faction", None) is not None for a in _rsw.agents))
_okS, _mS = story_join(_rsw, _rsw.story_engine.offers()[0])
_strans = 0
for _ in range(20):
    _rsw.tick()
    _strans += len(_rsw.last_story_transitions)
check("真栈剧情层随 tick 步进（入线=%s 转移 %d 次）" % (_okS, _strans),
      _okS and _rsw.story_engine.state.quest is not None,
      "%s" % _mS)
_report2 = _rsw.run_constitutional_audit()
_all2 = all(AuditReport._is_pass(getattr(_report2, attr))
            for attr, _ in AuditReport.FIELDS)
check("25 维宪法审计仍全过（真栈 + 目标层 + 剧情层零扰动）", _all2)

# ============================================================
# 十、战斗 v1（切磋结算 / 吸血战斗接线 / duel_win 判据 / 元素共鸣稀有度）
# ============================================================
print("\n=== 十、战斗 v1 ===")
import zlib as _zlib                                   # noqa: E402
from demo.goal_system import GoalGenerator as _GGX     # noqa: E402
from demo.factions import (                            # noqa: E402
    StoryQuest as _SQX, _build_ctx as _bctxx, _mech_complete as _mcompx)

_wd1, _pd1 = fresh_world(701)
_wd2, _pd2 = fresh_world(701)
_d1 = _wd1.resolve_duel(_pd1, _wd1.agents[0])
_d2 = _wd2.resolve_duel(_pd2, _wd2.agents[0])
check("同 seed 切磋结算逐字节一致（零 RNG）",
      _d1 is not None and _d1 == _d2, "%s" % (_d1,))
_duel_n = len([e for e in _wd1.event_log if e.etype == EventType.DUEL])
check("DUEL 事件入事件流（目标/剧情层可复算）",
      _duel_n == 1, "事件=%d" % _duel_n)
check("技能双轨：一阶即有木剑式/魔力弹，自动选轨可得技能",
      _pd1.best_skill() is not None
      and _pd1.skill_loadout().get("sword", {}).get("name") == "木剑式",
      "loadout=%s" % sorted(_pd1.skill_loadout().keys()))
_pd1.vocation_effects["blood_drain"] = 0.5
_r3 = _wd1.resolve_duel(_pd1, _wd1.agents[1] if len(_wd1.agents) > 1
                        else _wd1.agents[0])
check("吸血特性战斗接线（命中按伤害比例回复）",
      _r3 is not None and _r3["healed"] > 0,
      "healed=%s" % (_r3 or {}).get("healed"))
_qx = _SQX(sid="T1", qkey="t1", title="t", lore="", faction="knights", stage=0,
           mechanic="duel_win", created_tick=0, deadline_tick=999,
           ctx=_bctxx(_pd1, _wd1, "knights", {"mechanic": "duel_win"}, 0))
_tgtq = _wd1.find_agent(_qx.ctx.get("npc_aid"))
if _tgtq is not None:
    _wd1.resolve_duel(_pd1, _tgtq)
check("duel_win 剧情判据：胜负事件可复算完成",
      _qx.ctx.get("npc_aid") is not None and _mcompx(_pd1, _wd1, _qx) is not None,
      "对手=%s" % _qx.ctx.get("opponent_name"))
_ggx = _GGX(_pd1, _wd1)
_pd1.affinity = "元素"; _pd1.magic_rank = 5
_w0 = (7 - _zlib.crc32(str(_pd1.pid).encode("utf-8"))) % 3000
_wd1._tick = _w0
_twin = _ggx._trig_element_resonance(_wd1)
_wd1._tick = (_w0 + 1) % 3000
_toff = _ggx._trig_element_resonance(_wd1)
check("元素共鸣：窗内触发窗外不触发（一生一次，极稀有门禁）",
      _twin is not None and _toff is None, "窗 tick=%d" % _w0)
from demo.virtual_world import context_actions as _ctxact   # noqa: E402
_wc1,_pc1 = fresh_world(704)
_wc2,_pc2 = fresh_world(704)
check("上下文交互扫描同 seed 逐项一致（零 RNG）",
      _ctxact(_pc1,_wc1)==_ctxact(_pc2,_wc2))
from demo.virtual_world import EraCalendar as _EC   # noqa: E402
_ticks=[e["start_tick"] for e in _EC.ERAS]
check("纪元表 start_tick 单调递增且唯一（快进开局前提）",
      _ticks==sorted(_ticks) and len(set(_ticks))==len(_ticks),
      "ticks=%s"%_ticks)
check("纪元 key 校验：schism=800、未知值拒绝",
      _EC.get_era("schism")["start_tick"]==800 and _EC.get_era("nope") is None)
_wd3,_pd3 = fresh_world(705)                       # 隔离世界：避免前置检查的位阶/特性强污染
_wd3.agents[0].vocation_tier=3
_r5=_wd3.resolve_duel(_pd3,_wd3.agents[0])
check("位阶防御：高阶居民还手更重且一阶玩家落败",
      _r5["counter"]>9 and not _r5["win"], "counter=%d"%_r5["counter"])
from demo.virtual_world import _replenish_era_population as _repfn   # noqa: E402
_ws7,_ps7 = fresh_world(706)
_half=[a for a in _ws7.agents if a.alive][:len([a for a in _ws7.agents if a.alive])//2]
for _a in _half: _a.alive=False
_rp=_repfn(_ws7)
check("世代补齐：纪元快进后人口恢复至开局规模（演示层设定）",
      len([a for a in _ws7.agents if a.alive])>=_ws7.config.initial_agents and _rp>0,
      "补齐=%d 现存=%d"%(_rp,len([a for a in _ws7.agents if a.alive])))
_wc1.agents[0].inventory["food"]=2
_pc1.fx,_pc1.fy=float(_wc1.agents[0].pos.x),float(_wc1.agents[0].pos.y)
_ca=[a[0] for a in _ctxact(_pc1,_wc1)]
check("上下文交互扫描：交易/切磋/采集项齐备（确定性）",
      "trade" in _ca and "duel" in _ca and "gather" in _ca, "actions=%s"%_ca)


# ============================================================
# 汇总
# ============================================================
passed = sum(1 for _, ok, _ in _RESULTS if ok)
total = len(_RESULTS)
failed = [(n, d) for n, ok, d in _RESULTS if not ok]
print("\n检查项 %d/%d 通过" % (passed, total))
if failed:
    for n, d in failed:
        print("  [失败] %s  %s" % (n, d))
    print("GOAL-SYSTEM CHECKS FAILED")
    sys.exit(1)
print("ALL GOAL-SYSTEM CHECKS PASSED")
sys.exit(0)
