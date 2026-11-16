# -*- coding: utf-8 -*-
"""势力剧情矩阵与分支时间线系统（StoryEngine）—— M2.7
====================================================================

定位
----
M2.6 涌现式目标系统（goal_system.py，8 类基础目标）之上的剧情层：
**势力 × 职阶 × 阶位 × 分支选择** 的矩阵式时间线。设计原则（推演模式收敛）：

  - 剧情不围绕传说人物手写——传说人物只作顶阶 lore 彩蛋；常规剧情绑定
    **身份化 NPC**（创世抽签赋职阶/势力归属的世界居民）；
  - 模板少量手写（6 势力 × 4 阶位 + 自由职业线），组合空间靠
    **资格矩阵（69 职阶）× NPC 身份（69×8×6）× 世界状态槽位** 展开；
  - 单玩家单时间线：入会不可逆（除叛离分支），分支选择互相锁死，
    全部记录于 StoryState.flags/locked，事件源可复算。

三条硬纪律（与 goal_system.py 同一标准，tools/goal_system_smoke.py 断言）
------------------------------------------------------------------
  1) **零世界 RNG 消耗**。NPC 身份用 random.Random("story:<seed>:<aid>")
     派生流抽签（persona 层同一先例：virtual_world.py build_persona）；
     StoryEngine 全部选择用确定性排序（数值→距离→aid 字典序）。
     挂载/不挂载剧情层：state_hash 与世界 RNG 状态逐字节一致。
  2) **纯观察者**。StoryState/story 任务全部为玩家运行时属性（不改
     PlayerAgent/NohnAgent 类定义，to_dict()/state_hash() 不变）；
     判据只读公开世界状态（inventory / wealth / needs / owned_buildings /
     event_log），第三方可在任一 tick 独立复算。
  3) **公示即执行**。七种剧情机制（gather_n / trade_distinct / craft_n /
     rank_reach / wealth_reach / build_first / travel_away）全部只用
     PlayerAgent 既有动作（gather/trade/create_work/build/rest/迁移）与
     事件源（TRADE/PRODUCE），不存在只触发达不成的假剧情。

诚实边界（如实声明，不得隐去）
------------------------------------------------------------------
  A. PlayerAgent 无 give 动作（赠予仅 GUI 有），故本层不设赠予类机制；
  B. 本层只提供引擎与 API（story_join/story_decide），GUI 目标面板接线
     与 RealWorld（真栈世界）挂载属后续版本；
  C. 剧情文案全部为**自创**（模块级统一声明）；文中引用的世界观名词
     （势力、阶位称谓、传说人物）出处见 demo/vocations.py 溯源注释；
  D. NPC 的职阶/势力归属是**派生态**（不入 to_dict/state_hash），
     其作用域仅限剧情层选择与展示，不影响 NPC 行为决策。

剧情线结构
------------------------------------------------------------------
  入会决策（story_join，含 freelance 自由职业线兜底）
    → 每阶位一条主线任务（模板 × 世界状态槽位：元素映射资源、同门 NPC、
      相对基线的财富/位阶目标）
    → 完成 → 分支节点（story_decide，2-3 选：接受晋升 / 谢绝留守 /
      叛离改投他宗[仅存在其他资格势力时]）
    → 顶阶完成 → 加冕（line_complete + lore 彩蛋）或退隐留守。
  失败/过期 → 冷却后同阶位重新生成（上下文由彼时世界状态重填，
    时间线不换线）。

用法
----
  from demo.factions import StoryWorld, story_join, story_decide
  w = StoryWorld(WorldConfig(seed=7))
  p = w.add_player()
  story_join(w, "theocracy")          # 或 "freelance"
  while running:
      w.tick()                        # 剧情层随 tick 自动步进
      if w.story_engine.state.decision:
          story_decide(w, "accept")   # 玩家分支选择
"""

import math
import os
import random
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))            # demo/
_REPO_ROOT = os.path.dirname(_HERE)
for _p in (_REPO_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 模块身份纪律：与 goal_system.py 同一口径——消费方与本模块必须共享同一个
# virtual_world / goal_system 模块对象（否则两套 EventType 比对恒 False）。
try:                                                          # noqa: E402
    from .virtual_world import (                              # noqa: E402,F401
        Event, EventType, FIVE_LAYER_NEEDS, NohnWorld,
    )
    from .goal_system import GoalDrivenWorld                  # noqa: E402,F401
    from . import vocations as voc                            # noqa: E402
except ImportError:                                           # pragma: no cover
    from virtual_world import (                               # noqa: E402,F401
        Event, EventType, FIVE_LAYER_NEEDS, NohnWorld,
    )
    from goal_system import GoalDrivenWorld                   # noqa: E402,F401
    import vocations as voc                                   # noqa: E402

FREELANCE_KEY = "freelance"
FREELANCE_NAME = "自由身"

STORY_DEADLINE = 500          # 阶位任务基础期限（tick），×(1+deadline_bonus)
STORY_COOLDOWN = 60           # 过期/失败后重生成冷却（tick）


# ============================================================
# 资格矩阵：职阶 → 可加入势力
# 显式名录（主题对应，世界观点名的教廷/学院/行会/军镇体系称谓）
# ∪ 效果键规则（职阶加成键 → 对口势力）；"all"（勇者/魔王）通吃。
# 覆盖纪律：69 职阶每个至少一条线（势力或自由职业线），smoke 断言。
# ============================================================
EXPLICIT_QUALIFY = {
    "theocracy": {"教堂杂役", "医者", "书记官", "吟游诗人", "战地医官",
                  "教区祭司", "圣殿骑士", "教区主教", "大主教", "慈悲者"},
    "academy": {"见习法师", "抄写员", "书记官", "学徒", "宫廷学士", "符文匠",
                "魔药师", "法师", "冰晶技师", "教授", "魔工师", "贤者",
                "圣者", "魔法帝", "解构者", "光辉",
                "宫廷法师", "魔法学院教授", "魔法学院主任"},
    "guild": {"商人", "行商", "行会商人", "大商人", "车夫", "码头工", "织匠",
              "陶工", "厨师", "渔夫", "酒保", "裁缝", "牧人", "冰晶技师",
              "皇帝"},
    "knights": {"战士", "骑士", "剑士", "枪兵", "弓手", "城卫长", "圣殿骑士",
                "游侠队长", "剑术大师", "剑尊", "剑帝", "魔王", "码头工"},
    "rangers": {"猎户", "守林人", "拾荒者", "向导", "信使", "刺客", "弓手",
                "游侠队长", "探界者", "巡夜人", "车夫", "渔夫", "牧人",
                "御风船员"},
    "artisans": {"铁匠", "木匠", "裁缝", "陶工", "织匠", "矿工", "樵夫",
                 "农民", "药圃工", "符文匠", "魔工师", "营造师", "魔药师",
                 "毒药师", "厨师", "冰晶技师", "巡夜人"},
}
EFFECT_QUALIFY = {
    "theocracy": {"soul_xp", "give_bonus"},
    "academy": {"magic_xp"},
    "guild": {"trade_bonus", "wealth_start"},
    "knights": {"body_xp"},
    "rangers": {"speed_bonus"},
    "artisans": {"build_bonus", "herb_bonus"},
}
FACTION_KEYS = ("theocracy", "academy", "guild", "knights", "rangers", "artisans")


def eligible_factions(vocation, effects) -> List[str]:
    """职阶的资格势力（确定性字典序）。空表 = 只走自由职业线。"""
    out = []
    e = effects or {}
    universal = "all" in e
    for k in FACTION_KEYS:
        if (vocation in EXPLICIT_QUALIFY.get(k, set())
                or universal
                or (EFFECT_QUALIFY.get(k, set()) & set(e.keys()))):
            out.append(k)
    return sorted(out)


# ============================================================
# 元素 → 资源映射（剧情槽位：采集任务的资源类型由玩家元素决定）
# 八元素见 vocations.ELEMENT_ORDER；映射为演示层自创，确定性即可。
# ============================================================
_ELEMENT_RES = {"水": "water", "木": "fruit", "火": "food", "光": "fruit",
                "雷": "food", "暗": "water", "地": "food", "风": "fruit"}


def _element_res(element):
    return _ELEMENT_RES.get(element, "food")


def _npc_display(a) -> str:
    """身份化 NPC 展示名：「职阶·名」。名字池（希腊字母）不动以保旧世界
    哈希，身份维度以派生属性补足（诚实边界 D）。"""
    return "%s·%s" % (getattr(a, "vocation", None) or "居民", a.name)


# ============================================================
# NPC 身份化：random.Random("story:<seed>:<aid>") 派生流，零世界 RNG
# ============================================================

def assign_npc_identity(a, world_seed) -> None:
    """给一名 NPC 赋职阶/势力归属（派生态，运行时属性）。
    已赋过（有 faction 属性）则跳过；子代降生后由引擎惰性补赋。"""
    if getattr(a, "faction", None) is not None:
        return
    rng = random.Random("story:%s:%s" % (world_seed, a.aid))
    e = voc.draw_vocation(rng)
    a.vocation = e["name"]
    a.vocation_tier = e["tier"]
    a.vocation_effects = dict(e["effects"])
    elig = eligible_factions(a.vocation, a.vocation_effects)
    a.faction = rng.choice(elig) if elig else FREELANCE_KEY


# ============================================================
# 剧情任务对象
# ============================================================

@dataclass
class StoryQuest:
    sid: str
    qkey: str
    title: str
    lore: str
    faction: str
    stage: int
    mechanic: str
    created_tick: int
    deadline_tick: int
    ctx: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"           # active/completed/failed/expired
    finished_tick: Optional[int] = None
    note: str = ""

    def describe(self) -> str:
        c = self.ctx
        m = self.mechanic
        if m == "gather_n":
            return "采集 %s ×%d（为 %s 备料）" % (c.get("res_type"), c.get("count"),
                                                 c.get("mentor", "同门"))
        if m == "trade_distinct":
            return "与 %d 名不同的居民成交（结识人脉）" % c.get("count")
        if m == "duel_win":
            return "与 %s 切磋并获胜（剧情切磋·R 键，切磋无死亡）" % c.get(
                "opponent_name", "同门")
        if m == "craft_n":
            return "创作 %d 件作品（PRODUCE 入 CAS）" % c.get("count")
        if m == "rank_reach":
            return "位阶修至 %s 阶 %d（三成长·%s）" % (
                {"magic": "法", "body": "体", "soul": "魂"}[c.get("kind", "magic")],
                c.get("target"), c.get("kind"))
        if m == "wealth_reach":
            return "积攒资财至 %.0f" % c.get("target", 0)
        if m == "build_first":
            return "营建一处所属建筑"
        if m == "travel_away":
            return "远行至距降生点 %.0f 格之外" % c.get("dist")
        return self.qkey

    def to_dict(self) -> dict:
        return {"sid": self.sid, "qkey": self.qkey, "title": self.title,
                "lore": self.lore, "faction": self.faction, "stage": self.stage,
                "mechanic": self.mechanic, "created_tick": self.created_tick,
                "deadline_tick": self.deadline_tick, "ctx": self.ctx,
                "status": self.status, "finished_tick": self.finished_tick,
                "note": self.note, "describe": self.describe()}


@dataclass
class StoryState:
    """单玩家时间线状态机（派生态：玩家运行时属性 player.story）。"""
    faction: Optional[str] = None        # None = 尚未入线（等待入会决策）
    stage: int = 0                       # 阶位索引 0..3
    flags: Dict[str, Any] = field(default_factory=dict)
    locked: List[str] = field(default_factory=list)   # 永久锁死的势力（叛离）
    quest: Optional[StoryQuest] = None
    decision: Optional[Dict[str, Any]] = None         # 待玩家分支选择
    history: List[dict] = field(default_factory=list)
    line_done: bool = False
    line_lore: str = ""

    def to_dict(self) -> dict:
        return {"faction": self.faction, "stage": self.stage,
                "flags": dict(self.flags), "locked": list(self.locked),
                "quest": self.quest.to_dict() if self.quest else None,
                "decision": self.decision,
                "history": len(self.history), "line_done": self.line_done,
                "line_lore": self.line_lore}


# ============================================================
# 势力数据（阶位阶梯 + 剧情模板 + 顶阶彩蛋）
# 文案自创（诚实边界 C）；称谓体系与世界观势力结构对齐。
# ============================================================

def _fac(key, name, motto, stages, lore_top):
    return {"key": key, "name": name, "motto": motto,
            "stages": stages, "lore_top": lore_top}

# stages: 4 项，每项 {"name": 阶位称谓, "quest": 剧情模板}
# 模板: {"qkey","title","lore","mechanic", 参数(count/delta/amount/dist)}


FACTIONS = [
    _fac("theocracy", "天神教",
         "第一位真神扶持的教团，圣事与凝聚是全部教义",
         [
             {"name": "教区杂役", "quest": {
                 "qkey": "th_s1", "title": "探访教众",
                 "lore": "[自创] 殿前洒扫之余，走访城中教众——天神教相信人与人的纽带即神恩的容器。",
                 "mechanic": "trade_distinct", "count": 2}},
             {"name": "辅祭", "quest": {
                 "qkey": "th_s2", "title": "抄经制器",
                 "lore": "[自创] 辅祭的第一课：亲手誊抄一卷经文、制一件圣器，献于祭坛。",
                 "mechanic": "craft_n", "count": 1}},
             {"name": "教区祭司", "quest": {
                 "qkey": "th_s3", "title": "什一之奉",
                 "lore": "[自创] 祭司须以身作则：先在世上积下足够的资财，再谈施予。",
                 "mechanic": "wealth_reach", "amount": 80}},
             {"name": "教区主教", "quest": {
                 "qkey": "th_s4", "title": "圣典编纂",
                 "lore": "[自创] 主教之位以三卷圣典为凭——教省的文书库因你而厚。",
                 "mechanic": "craft_n", "count": 2}},
         ],
         "[自创] 加冕主教时，礼拜文念及教史：「十位大主教皆八阶圣者」（世界观点名）——你位列其座侧。"),
    _fac("academy", "魔法学院",
         "入学须先识字会算术；六阶起任教授",
         [
             {"name": "旁听生", "quest": {
                 "qkey": "ac_s1", "title": "采药备料",
                 "lore": "[自创] 学院不收学费，收你的第一份作业：按你禀赋的元素备齐一篮材料。",
                 "mechanic": "gather_n", "count": 6}},
             {"name": "正式学员", "quest": {
                 "qkey": "ac_s2", "title": "斗法之课",
                 "lore": "[自创] 正式学员的门槛：与同门斗法一场——法术是法阶的证明；直接操控元素力者极罕，不在此课之列。",
                 "mechanic": "duel_win"}},
             {"name": "学士", "quest": {
                 "qkey": "ac_s3", "title": "凝核进阶",
                 "lore": "[自创] 学士袍以法阶为线——魔核再进一阶，线色即变。",
                 "mechanic": "rank_reach", "kind": "magic", "delta": 1}},
             {"name": "教授", "quest": {
                 "qkey": "ac_s4", "title": "著作等身",
                 "lore": "[自创] 「六阶起任」是学院铁律（世界观点名）；教授席位还要求三件署名之作。",
                 "mechanic": "craft_n", "count": 2}},
         ],
         "[自创] 就任大典上，首座提及旧史：「魔法帝九阶而止于传说」（世界观位阶表）——教席望你走得更远。"),
    _fac("guild", "商盟行会",
         "商路即血脉，契约即律法",
         [
             {"name": "学徒伙计", "quest": {
                 "qkey": "gu_s1", "title": "理货起家",
                 "lore": "[自创] 行会的规矩：先在货栈理清四手货，才配谈买卖。",
                 "mechanic": "gather_n", "count": 4}},
             {"name": "行商", "quest": {
                 "qkey": "gu_s2", "title": "三城三客",
                 "lore": "[自创] 行商的徽记要三枚客户印：三处不同的成交，缺一不可。",
                 "mechanic": "trade_distinct", "count": 3}},
             {"name": "行会成员", "quest": {
                 "qkey": "gu_s3", "title": "入会本金",
                 "lore": "[自创] 行会席位以本金为凭——账上的数字就是你的信用。",
                 "mechanic": "wealth_reach", "amount": 120}},
             {"name": "大商人", "quest": {
                 "qkey": "gu_s4", "title": "商路贯通",
                 "lore": "[自创] 大商人的名号要求五处商路驿印——「商路贯通」（世界观点名大商人职阶）。",
                 "mechanic": "trade_distinct", "count": 5}},
         ],
         "[自创] 顶阶授印时，会长引旧档：「皇帝马尔杜克亦列行会名册」（世界观人物录）——商路尽头连着王座。"),
    _fac("knights", "骑士团",
         "誓约高于性命，甲胄即是法律",
         [
             {"name": "侍从", "quest": {
                 "qkey": "kn_s1", "title": "入门切磋",
                 "lore": "[自创] 侍从的第一课是剑：与同门切磋一场——招式见血汗，不见伤残（切磋无死亡）。",
                 "mechanic": "duel_win"}},
             {"name": "见习骑士", "quest": {
                 "qkey": "kn_s2", "title": "晋阶之誓",
                 "lore": "[自创] 见习骑士的誓词以体阶为凭——体炼再进一阶，誓约才算落音。",
                 "mechanic": "rank_reach", "kind": "body", "delta": 1}},
             {"name": "骑士", "quest": {
                 "qkey": "kn_s3", "title": "营建哨所",
                 "lore": "[自创] 每名正式骑士要在辖地营建一处哨所——骑士团的法律立在砖石里。",
                 "mechanic": "build_first"}},
             {"name": "圣殿骑士", "quest": {
                 "qkey": "kn_s4", "title": "四盟之誓",
                 "lore": "[自创] 圣殿骑士的誓约要与四方盟友共立（教廷武备，世界观点名）。",
                 "mechanic": "trade_distinct", "count": 4}},
         ],
         "[自创] 授甲礼上，团长诵誓：「圣殿骑士属教廷武备」（世界观点名）——你的甲胄自此双记教团与骑士团。"),
    _fac("rangers", "游侠公会",
         "路在脚下，信在途中",
         [
             {"name": "随行者", "quest": {
                 "qkey": "ra_s1", "title": "初识远路",
                 "lore": "[自创] 公会不考武艺，考脚力：走到离降生点十二格之外的荒地再回来报到。",
                 "mechanic": "travel_away", "dist": 12}},
             {"name": "斥候", "quest": {
                 "qkey": "ra_s2", "title": "八份采样",
                 "lore": "[自创] 斥候的日志以物证为页：八份野外采样，一份不能少。",
                 "mechanic": "gather_n", "count": 8}},
             {"name": "游侠", "quest": {
                 "qkey": "ra_s3", "title": "三处投契",
                 "lore": "[自创] 游侠走险路，靠的是沿途三处可靠的交易人情。",
                 "mechanic": "trade_distinct", "count": 3}},
             {"name": "探界者", "quest": {
                 "qkey": "ra_s4", "title": "界外之地",
                 "lore": "[自创] 探界者的徽记只授给走过二十格外之人（世界观点名探界者·菲莉亚的妖精方向感）。",
                 "mechanic": "travel_away", "dist": 20}},
         ],
         "[自创] 授徽时，老探界者说：「方向感是妖精的天赋，路是所有人的」（世界观探界者溯源）——你的路标自此入公会图档。"),
    _fac("artisans", "匠人工会",
         "手艺不撒谎，成品会说话",
         [
             {"name": "杂徒", "quest": {
                 "qkey": "ar_s1", "title": "识材八样",
                 "lore": "[自创] 匠人的第一课在矿山与林地：亲手过手八份材料，才算识材。",
                 "mechanic": "gather_n", "count": 8}},
             {"name": "学徒", "quest": {
                 "qkey": "ar_s2", "title": "出师之作",
                 "lore": "[自创] 学徒出师要交一件完整成品——指纹入库，终身可查（CAS）。",
                 "mechanic": "craft_n", "count": 1}},
             {"name": "匠师", "quest": {
                 "qkey": "ar_s3", "title": "立灶开坊",
                 "lore": "[自创] 匠师要有自己的坊：一处名下建筑，就是工会的执照。",
                 "mechanic": "build_first"}},
             {"name": "宗匠", "quest": {
                 "qkey": "ar_s4", "title": "双璧传世",
                 "lore": "[自创] 宗匠之号以两件传世之作为凭——矮人符文匠的老规矩（世界观点名符文天赋）。",
                 "mechanic": "craft_n", "count": 2}},
         ],
         "[自创] 授名礼上，宗匠们击砧为贺：「魔晶动力的时代属于会造的人」（世界观魔法工业）——你的名字入了工会的器谱。"),
]

FREELANCE_STAGES = [
    {"name": "谋生者", "quest": {"qkey": "fl_s1", "title": "糊口之资",
                                 "lore": "[自创] 不入任何势力，先靠双手糊口：攒下一篮自己的收成。",
                                 "mechanic": "gather_n", "count": 5}},
    {"name": "熟手", "quest": {"qkey": "fl_s2", "title": "街坊人情",
                               "lore": "[自创] 自由身的本钱是人情：与两处街坊做成买卖。",
                               "mechanic": "trade_distinct", "count": 2}},
    {"name": "行家", "quest": {"qkey": "fl_s3", "title": "拿手之作",
                               "lore": "[自创] 行家有一件拿得出手的作品。",
                               "mechanic": "craft_n", "count": 1}},
    {"name": "名师", "quest": {"qkey": "fl_s4", "title": "安身立命",
                               "lore": "[自创] 名师的招牌是家业：攒下足以安身的资财。",
                               "mechanic": "wealth_reach", "amount": 100}},
]
FREELANCE_LORE_TOP = "[自创] 你没入任何势力，但整条街都认得你的名字——自由身走到头，就是这这句话。"

_FACTION_BY_KEY = {f["key"]: f for f in FACTIONS}


def _stages_of(fkey):
    if fkey == FREELANCE_KEY:
        return FREELANCE_STAGES
    return _FACTION_BY_KEY[fkey]["stages"]


def _faction_name(fkey):
    return FREELANCE_NAME if fkey == FREELANCE_KEY else _FACTION_BY_KEY[fkey]["name"]


def faction_display(fkey):
    """势力显示名（GUI / 剧情文本公共入口）。"""
    return _faction_name(fkey)


def stage_display(fkey, idx):
    """阶位显示名；idx 越界按顶阶处理（GUI 面板安全取值）。"""
    stages = _stages_of(fkey) if fkey else []
    if not stages:
        return "无"
    return stages[max(0, min(int(idx), len(stages) - 1))]["name"]


# ============================================================
# 七种剧情机制：完成判据（纯读，全部可复算）
# ============================================================

def _events_since(world, etype, actor, since_tick) -> List[Event]:
    out = []
    for e in world.event_log:
        if e.etype == etype and e.actor == actor and e.tick >= since_tick:
            out.append(e)
    return out


def _min_need(agent) -> float:
    return min(agent.needs.get(n, 100.0) for n in FIVE_LAYER_NEEDS)


def _mech_mentor(world, player, fkey) -> str:
    """同门 NPC 作为剧情人名槽位（确定性：aid 字典序首位；无同门取最近）。"""
    px, py = player.fx, player.fy
    same = [a for a in world.agents
            if a.alive and getattr(a, "faction", None) == fkey and a.aid != player.pid]
    if same:
        return _npc_display(sorted(same, key=lambda a: a.aid)[0])
    near = [a for a in world.agents if a.alive]
    if near:
        return _npc_display(min(near, key=lambda a: (round(
            math.hypot(a.pos.x - px, a.pos.y - py), 4), a.aid)))
    return "同门"


def _build_ctx(player, world, fkey, tpl, now) -> Dict[str, Any]:
    """模板 → 上下文槽位（世界状态填充；零 RNG，全部确定性）。"""
    m = tpl["mechanic"]
    ctx: Dict[str, Any] = {"since_tick": now, "mentor": _mech_mentor(world, player, fkey)}
    if m == "gather_n":
        ctx["res_type"] = _element_res(player.element)
        ctx["count"] = tpl["count"]
    elif m == "trade_distinct":
        ctx["count"] = tpl["count"]
    elif m == "duel_win":
        px, py = player.fx, player.fy
        cands = [a for a in world.agents
                 if a.alive and a.aid != player.pid]
        if cands:
            t = min(cands, key=lambda a: (round(
                math.hypot(a.pos.x - px, a.pos.y - py), 4), a.aid))
            ctx["npc_aid"] = t.aid
            ctx["opponent_name"] = _npc_display(t)
        else:
            ctx["npc_aid"] = None
            ctx["opponent_name"] = "同门"
    elif m == "craft_n":
        ctx["count"] = tpl["count"]
    elif m == "rank_reach":
        kind = tpl["kind"]
        cur = {"magic": player.magic_rank, "body": player.body_rank,
               "soul": player.soul_strength}[kind]
        ctx["kind"] = kind
        ctx["target"] = cur + tpl["delta"]
        ctx["baseline"] = cur
    elif m == "wealth_reach":
        ctx["target"] = round(player.wealth) + tpl["amount"]
        ctx["baseline"] = round(player.wealth)
    elif m == "build_first":
        ctx["had"] = bool(player.owned_buildings)
    elif m == "travel_away":
        ctx["origin"] = (round(player.fx, 2), round(player.fy, 2))
        ctx["dist"] = tpl["dist"]
    return ctx


def _mech_complete(player, world, q: StoryQuest) -> Optional[str]:
    """完成判据：返回 None=未完成；返回字符串=完成备注。纯读。"""
    c = q.ctx
    m = q.mechanic
    if m == "gather_n":
        if player.inventory.get(c["res_type"], 0) >= c["count"]:
            return "已备齐 %s ×%d" % (c["res_type"], c["count"])
        return None
    if m == "trade_distinct":
        ids = {e.target for e in _events_since(world, EventType.TRADE, player.pid,
                                               c["since_tick"])}
        if len(ids) >= c["count"]:
            return "已与 %d 名居民成交" % len(ids)
        return None
    if m == "duel_win":
        for e in _events_since(world, EventType.DUEL, player.pid, c["since_tick"]):
            if e.target == c.get("npc_aid") and e.data.get("win"):
                return "已胜 %s（%s 伤 %d）" % (c.get("opponent_name"),
                                               e.data.get("skill"),
                                               e.data.get("dmg", 0))
        return None
    if m == "craft_n":
        n = len(_events_since(world, EventType.PRODUCE, player.pid, c["since_tick"]))
        if n >= c["count"]:
            return "已完成 %d 件创作" % n
        return None
    if m == "rank_reach":
        v = {"magic": player.magic_rank, "body": player.body_rank,
             "soul": player.soul_strength}[c["kind"]]
        if v >= c["target"]:
            return "%s 阶已达 %d" % (c["kind"], v)
        return None
    if m == "wealth_reach":
        if player.wealth >= c["target"]:
            return "资财已达 %.0f" % player.wealth
        return None
    if m == "build_first":
        if player.owned_buildings:
            return "建筑已落成 @ %s" % (player.owned_buildings[-1],)
        return None
    if m == "travel_away":
        ox, oy = c["origin"]
        if math.hypot(player.fx - ox, player.fy - oy) >= c["dist"]:
            return "已远行至 %.1f 格外" % math.hypot(player.fx - ox, player.fy - oy)
        return None
    return None


# 分支选择构造（确定性；叛离仅当存在其他资格势力且未锁死）

def _promotion_choices(player, state: StoryState, is_top: bool) -> List[dict]:
    ch = []
    if is_top:
        ch.append({"key": "ascend", "label": "加冕：走完这条时间线", "effect": "line_complete"})
        ch.append({"key": "remain", "label": "退隐：留守顶阶", "effect": "stay"})
    else:
        nxt = _stages_of(state.faction)[state.stage + 1]["name"]
        ch.append({"key": "accept", "label": "接受晋升：%s" % nxt, "effect": "advance"})
        ch.append({"key": "refuse", "label": "谢绝晋升，留守本阶", "effect": "stay"})
    if state.faction != FREELANCE_KEY:
        others = [k for k in eligible_factions(player.vocation, player.vocation_effects)
                  if k != state.faction and k not in state.locked]
        if others:
            ch.append({"key": "defect",
                       "label": "叛离改投：%s" % "、".join(_faction_name(k) for k in others),
                       "effect": "defect", "targets": others})
    return ch


# ============================================================
# StoryEngine：单玩家时间线引擎（纯观察者，零世界 RNG）
# ============================================================

class StoryEngine:
    def __init__(self, player, world=None):
        self.player = player
        self.state = StoryState()
        self._cooldown_until = -1
        self._qid = 0
        player.story = self.state                    # 运行时属性镜像（纪律 2）
        self.last_transitions: List[dict] = []

    # ---------- 对外 API（玩家动作；零 RNG） ----------

    def offers(self) -> List[str]:
        """入会窗口：资格势力（字典序）+ 自由职业线兜底。"""
        elig = eligible_factions(self.player.vocation, self.player.vocation_effects)
        return elig + [FREELANCE_KEY]

    def join(self, fkey: str, world=None) -> Tuple[bool, str]:
        st = self.state
        if st.faction is not None:
            return False, "已入 %s，剧情线进行中（单玩家单线）" % _faction_name(st.faction)
        if fkey in st.locked:
            return False, "%s 已被永久锁死（叛离过）" % _faction_name(fkey)
        if fkey not in self.offers():
            return False, "%s 不在资格名单（职阶=%s）" % (_faction_name(fkey), self.player.vocation)
        st.faction = fkey
        st.stage = 0
        st.flags["joined_tick"] = (world._tick if world is not None else 0)
        st.history.append({"tick": st.flags["joined_tick"], "kind": "join",
                           "detail": "入 %s（职阶=%s）" % (_faction_name(fkey), self.player.vocation)})
        return True, "入 %s · 阶位【%s】" % (_faction_name(fkey),
                                            _stages_of(fkey)[0]["name"])

    def decide(self, choice_key: str, world=None) -> Tuple[bool, str]:
        st = self.state
        if st.decision is None:
            return False, "当前没有待决分支"
        ch = next((c for c in st.decision["choices"] if c["key"] == choice_key), None)
        if ch is None:
            return False, "无效分支选项：%s" % choice_key
        now = world._tick if world is not None else 0
        eff = ch["effect"]
        if eff == "advance":
            st.stage += 1
        elif eff == "stay":
            st.flags["stay_S%d" % st.stage] = True
        elif eff == "defect":
            old = st.faction
            st.locked.append(old)
            st.faction = ch["targets"][0]            # 默认首个资格势力（确定性）
            st.stage = 0
            st.flags["defected_from"] = old
        elif eff == "line_complete":
            st.line_done = True
            st.line_lore = self._lore_top()
        st.decision = None
        st.history.append({"tick": now, "kind": "decide",
                           "detail": "%s（%s）" % (ch["label"], eff)})
        return True, ch["label"]

    def _lore_top(self) -> str:
        f = self.state.faction
        return (FREELANCE_LORE_TOP if f == FREELANCE_KEY
                else _FACTION_BY_KEY[f]["lore_top"])

    # ---------- 引擎步进 ----------

    def _faction_display(self) -> str:
        return _faction_name(self.state.faction or "?")

    def _transition(self, kind, detail, tick) -> dict:
        return {"kind": kind, "detail": detail, "tick": tick,
                "faction": self.state.faction, "stage": self.state.stage}

    def _generate_quest(self, world) -> Optional[StoryQuest]:
        st = self.state
        now = world._tick
        stages = _stages_of(st.faction)
        if st.stage >= len(stages):
            return None
        tpl = stages[st.stage]["quest"]
        _dlb = (getattr(self.player, "vocation_effects", None) or {}).get("deadline_bonus", 0.0)
        q = StoryQuest(
            sid="SQ%04d" % self._qid, qkey=tpl["qkey"], title=tpl["title"],
            lore=tpl["lore"], faction=st.faction, stage=st.stage,
            mechanic=tpl["mechanic"], created_tick=now,
            deadline_tick=now + int(round(STORY_DEADLINE * (1.0 + _dlb))),
            ctx=_build_ctx(self.player, world, st.faction, tpl, now))
        self._qid += 1
        return q

    def step(self, world) -> List[dict]:
        out: List[dict] = []
        if self.player is None:
            return out
        now = world._tick
        # 惰性身份化：覆盖创世后新降生的 NPC（派生流，零世界 RNG）
        for a in world.agents:
            if getattr(a, "faction", None) is None:
                assign_npc_identity(a, world.config.seed)
        st = self.state
        if st.line_done or st.faction is None or st.decision is not None:
            self.last_transitions = out
            return out                                   # 等待玩家动作或已完线
        # 1) 结算活跃任务
        if st.quest is not None:
            q = st.quest
            note = _mech_complete(self.player, world, q)
            if note is not None:
                q.status = "completed"; q.finished_tick = now; q.note = note
                st.history.append({"tick": now, "kind": "quest_complete",
                                   "detail": "【%s】%s — %s" % (q.title, q.describe(), note)})
                out.append(self._transition("quest_complete", q.title, now))
                is_top = st.stage >= len(_stages_of(st.faction)) - 1
                st.quest = None
                st.decision = {"stage": st.stage, "is_top": is_top,
                               "choices": _promotion_choices(self.player, st, is_top)}
                out.append(self._transition("decision_open",
                                            "分支节点：第 %d 阶完成" % (st.stage + 1), now))
            elif now >= q.deadline_tick:
                q.status = "expired"; q.finished_tick = now
                q.note = "期限已至（%d tick）" % STORY_DEADLINE
                st.history.append({"tick": now, "kind": "quest_expire",
                                   "detail": "【%s】%s" % (q.title, q.describe())})
                out.append(self._transition("quest_expired", q.title, now))
                st.quest = None
                self._cooldown_until = now + STORY_COOLDOWN
            self.last_transitions = out
            if st.quest is None or st.decision is not None:
                return out
        # 2) 生成新任务（冷却已过）
        if st.quest is None and now >= self._cooldown_until:
            q = self._generate_quest(world)
            if q is not None:
                st.quest = q
                out.append(self._transition("quest_new", q.title, now))
        self.last_transitions = out
        return out

    def snapshot(self) -> dict:
        st = self.state
        by_status = {}
        for h in st.history:
            by_status[h["kind"]] = by_status.get(h["kind"], 0) + 1
        return {"faction": st.faction, "stage": st.stage,
                "quest": st.quest.qkey if st.quest else None,
                "decision": st.decision is not None,
                "line_done": st.line_done, "history": dict(by_status)}


# 模块级 API（GUI / 测试入口）：引擎经 world.story_engine 定位

def story_join(world, fkey: str) -> Tuple[bool, str]:
    eng = getattr(world, "story_engine", None)
    if eng is None:
        return False, "世界未挂载剧情层（应使用 StoryWorld）"
    return eng.join(fkey, world)


def story_decide(world, choice_key: str) -> Tuple[bool, str]:
    eng = getattr(world, "story_engine", None)
    if eng is None:
        return False, "世界未挂载剧情层（应使用 StoryWorld）"
    return eng.decide(choice_key, world)


# ============================================================
# 装配子类：NPC 身份化 + 剧情层接入 tick 循环
# ============================================================

class StoryWorld(GoalDrivenWorld):
    """GoalDrivenWorld 之上的纯增量装配：
    - 创世时为全部 NPC 赋身份（职阶/势力归属，派生流，零世界 RNG）；
    - add_player 挂 StoryEngine（player.story 运行时属性）；
    - tick 末尾步进剧情层。
    同 seed 下与不挂载剧情层的 NohnWorld state_hash 逐字节一致（纪律 1）。"""

    def __init__(self, config=None, goal_config=None):
        super().__init__(config, goal_config)
        self.story_engine: Optional[StoryEngine] = None
        self.last_story_transitions: List[dict] = []
        for a in self.agents:
            assign_npc_identity(a, self.config.seed)

    def add_player(self, pid: str = "PLAYER"):
        p = super().add_player(pid)
        self.story_engine = StoryEngine(p, self)
        return p

    def tick(self):
        te = super().tick()
        if self.story_engine is not None and self.player is not None:
            self.last_story_transitions = self.story_engine.step(self)
        return te


# ============================================================
# 库自检（返回问题列表；空列表 = 通过）
# ============================================================

def verify_story_pool() -> List[str]:
    problems = []
    # 1) 覆盖完整性：69 职阶每个至少一条线（资格势力或自由职业线）
    uncovered = []
    for e in voc.VOCATION_POOL:
        if not eligible_factions(e["name"], e["effects"]):
            uncovered.append(e["name"])
    if uncovered:
        problems.append("以下职阶无任何资格势力（只能走自由线）：%s" % uncovered)
    # 2) 每势力 4 阶位、每阶位一个模板、机制合法
    legal_mech = {"gather_n", "trade_distinct", "craft_n", "rank_reach",
                  "wealth_reach", "build_first", "travel_away", "duel_win"}
    for f in FACTIONS:
        if len(f["stages"]) != 4:
            problems.append("势力 %s 阶位数=%d（应为 4）" % (f["key"], len(f["stages"])))
        for s in f["stages"]:
            if s["quest"]["mechanic"] not in legal_mech:
                problems.append("势力 %s 阶位 %s 机制非法：%s"
                                % (f["key"], s["name"], s["quest"]["mechanic"]))
    if len(FREELANCE_STAGES) != 4:
        problems.append("自由职业线阶位数=%d（应为 4）" % len(FREELANCE_STAGES))
    for s in FREELANCE_STAGES:
        if s["quest"]["mechanic"] not in legal_mech:
            problems.append("自由线阶位 %s 机制非法：%s" % (s["name"], s["quest"]["mechanic"]))
    # 3) 势力名合法
    if set(_FACTION_BY_KEY.keys()) != set(FACTION_KEYS):
        problems.append("势力注册表与 FACTION_KEYS 不一致")
    return problems
