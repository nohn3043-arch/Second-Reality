# -*- coding: utf-8 -*-
"""职阶库与魔力特性库（登录抽签的唯一权威源）
====================================================================

世界观锚点（恩利尔大陆世界观 · 职阶与魔力特性 / 阿尔法纪元人物录）：
  - 职阶仅本人降生时自动知晓；普通职阶加成约 10%，一辈子只能做对应职业；
    特殊职阶稀有，特殊个体可有两个或三个；特殊职阶通常被天神教招揽培养。
  - 魔力特性非常稀有，法师中出现的概率也只有十分之一，高级特性更少。
  - 职阶加成在基础能力上叠加；魔力特性与职阶能影响万物一生。
  - 元素为「一切生灵所禀」，是固有属性，**不是**魔力特性（见 ELEMENT_* 常量）。

本库三条硬规则（可复核，tools/goal_system_smoke.py 逐条断言）：
  1) **始祖不入抽卡池**。始祖为伊莉斯专属职阶（真神），不出现在降生抽签中。
  2) **魔力特性不分级**。世界观原文只说「稀有 / 更稀有」，未给分档体系；
     本库不设 tier，亦不引入时空、星辰、命运一类越出世界观的概念型特性。
  3) **每个条目可溯源**。凡世界观点名者，text 内注明出处；凡按物理链推导者，
     注明「推导」二字，不与原文混淆。

效果键语义与唯一接线点（公示即执行：库里不允许出现未出现的键，
tools/goal_system_smoke.py 以 KNOWN_EFFECTS 断言完整性）：

  键               语义                        接线点
  gather_bonus     采集产量 ×(1+v)             PlayerAgent.gather
  herb_bonus       草药采集额外 ×(1+v)          PlayerAgent.gather
  regen_bonus      进食回复 ×(1+v)             PlayerAgent.gather
  energy_cost      精力消耗 ×(1−v)             PlayerAgent.gather / tick
  build_bonus      建造费用 ×(1−v)             PlayerAgent.build
  trade_bonus      买入价 ×(1−v)               PlayerAgent.trade
  trade_radius     交互半径 +v 格              GUI _nearest_trade_npc
  give_bonus       赠予强度 ×(1+v)             GUI _do_give
  magic_xp         魔力成长 ×(1+v)             PlayerAgent.gain_xp
  body_xp          体能成长 ×(1+v)             PlayerAgent.gain_xp
  soul_xp          灵魂成长 ×(1+v)             PlayerAgent.gain_xp
  sword_power      剑法威力 ×(1+v)             PlayerAgent（切磋结算·战斗 v1）
  spell_power      法术威力 ×(1+v)             PlayerAgent（切磋结算；禀赋元素另+5% 风味）
  all              上列行为加成通用叠加          PlayerAgent._vocal
  growth           三成长全局加速（叠加）        PlayerAgent._vocal
  speed_bonus      移速 ×(1+v)                 PlayerAgent.birth_draw（重设 speed）
  needs_resist     需求衰减 ×(1−v)             PlayerAgent.tick
  rest_bonus       休息回复 ×(1+v)             PlayerAgent.rest
  wealth_start     初始财富 ×(1+v)             NohnWorld.add_player（创世划转）
  deadline_bonus   涌现目标期限 ×(1+v)          GoalGenerator.check
  blood_drain      吸血：受伤/战斗后回复生命体质    PlayerAgent.rest（推导接线）

纯数据模块：只依赖标准库；同 rng 调用序列必得同抽签（确定性纪律）。
"""

import random

# ------------------------------------------------------------
# 稀有度（职阶用；魔力特性不分级，故不适用）
# ------------------------------------------------------------
RARITY_NAMES = {0: "凡阶", 1: "精阶", 2: "珍阶", 3: "稀阶", 4: "传说"}
RARITY_COLORS = {0: (198, 204, 216), 1: (120, 220, 140), 2: (110, 170, 255),
                 3: (196, 120, 255), 4: (255, 200, 80)}

KNOWN_EFFECTS = frozenset({
    "gather_bonus", "herb_bonus", "regen_bonus", "energy_cost", "build_bonus",
    "trade_bonus", "trade_radius", "give_bonus", "magic_xp", "body_xp",
    "soul_xp", "all", "growth", "speed_bonus", "needs_resist", "rest_bonus",
    "wealth_start", "deadline_bonus", "blood_drain",
    "sword_power", "spell_power",
})


def _e(name, tier, w, effects, text):
    return {"name": name, "tier": tier, "w": w,
            "effects": effects, "text": text}


# ------------------------------------------------------------
# 八元素（一切生灵所禀的固有属性，非魔力特性）
# 权威来源：世界观【元素生存法则】——生存梯度位次 水>光>木>雷>暗>地>风>火
# 日月属至尊大道，非八元素之列，不在本表内。
# ------------------------------------------------------------
ELEMENT_ORDER = ["水", "光", "木", "雷", "暗", "地", "风", "火"]
ELEMENT_NOTES = {
    "水": "第1位，八系唯一「治愈、续航、隐匿、感知、规避」五项俱全",
    "光": "第2位，照明/波动/聚焦/光电/光学迷彩/光压/光疗，缺控场",
    "木": "第3位，生机/光合/生长增殖/腐朽循环/演化控制，缺机动",
    "雷": "第4位，静电力场/蓄电感应/磁感索敌/以电御体/电疗，缺隐匿",
    "暗": "第5位，隐蔽/声学静默/辐射屏蔽/遮蔽剥夺视野，无治愈无硬防",
    "地": "第6位，物质壁垒/晶体硬度/摩擦压实，缺机动与治愈",
    "风": "第7位，伯努利升力/湍流伪装/声学扰乱/气压控场，无治愈无硬防",
    "火": "第8位，生存函数为无，须仰外部可燃介质，五缺",
}
# 元素权重：等权。世界观只给序数梯度，未给数值，故不臆造加权。
ELEMENT_WEIGHTS = {k: 1 for k in ELEMENT_ORDER}


def draw_element(rng):
    """降生抽元素（人人有，八系之一）。"""
    return rng.choices(ELEMENT_ORDER, weights=[ELEMENT_WEIGHTS[k] for k in ELEMENT_ORDER])[0]


# ------------------------------------------------------------
# 职阶池
# 结构：凡阶 = 谋生职业（约 10% 加成，一辈子一种）；
#       精/珍/稀 = 有技艺或身份门槛的进阶职（世界观未逐一点名，
#                 但与之相符的称谓出现在教廷、学院、军队体系中）；
#       传说 = 世界观**点名**的特殊职阶，效果数值原样照录。
# 始祖不在池内（伊莉斯专属，真神级，不进降生抽签）。
# 权重和恰为 1000。
# ------------------------------------------------------------
VOCATION_POOL = [
    # ================= 凡阶（约 10%，谋生之道）=================
    _e("农民",     0, 19, {"gather_bonus": 0.10}, "作物+10%"),
    _e("铁匠",     0, 17, {"build_bonus": 0.10}, "建造-10%"),
    _e("矿工",     0, 17, {"gather_bonus": 0.08, "body_xp": 0.05}, "采集+8% 体炼+5%"),
    _e("樵夫",     0, 14, {"gather_bonus": 0.08, "energy_cost": 0.05}, "采集+8% 省力"),
    _e("渔夫",     0, 14, {"regen_bonus": 0.10}, "进食回复+10%"),
    _e("牧人",     0, 13, {"needs_resist": 0.05}, "需求衰减-5%"),
    _e("厨师",     0, 13, {"regen_bonus": 0.12}, "进食回复+12%"),
    _e("裁缝",     0, 12, {"needs_resist": 0.06}, "需求衰减-6%"),
    _e("木匠",     0, 13, {"build_bonus": 0.08, "body_xp": 0.04}, "建造-8%"),
    _e("战士",     0, 17, {"body_xp": 0.10}, "体炼+10%"),
    _e("弓手",     0, 12, {"speed_bonus": 0.05}, "移速+5%"),
    _e("枪兵",     0, 12, {"body_xp": 0.06, "needs_resist": 0.04}, "体炼+6%"),
    _e("刺客",     0, 8, {"speed_bonus": 0.08, "energy_cost": 0.05}, "疾行 省力"),
    _e("见习法师", 0, 15, {"magic_xp": 0.10}, "魔力+10%"),
    _e("抄写员",   0, 10, {"magic_xp": 0.08, "soul_xp": 0.03}, "魔力+8%"),
    _e("书记官",   0, 10, {"magic_xp": 0.06, "soul_xp": 0.06}, "文理兼修"),
    _e("商人",     0, 15, {"trade_bonus": 0.10}, "买入-10%"),
    _e("行商",     0, 12, {"trade_bonus": 0.06, "trade_radius": 1}, "交易范围+1"),
    _e("车夫",     0, 11, {"speed_bonus": 0.06}, "移速+6%"),
    _e("码头工",   0, 11, {"body_xp": 0.08, "gather_bonus": 0.04}, "负重"),
    _e("信使",     0, 10, {"speed_bonus": 0.10}, "移速+10%"),
    _e("向导",     0, 11, {"trade_radius": 1, "speed_bonus": 0.04}, "识途"),
    _e("猎户",     0, 13, {"gather_bonus": 0.10}, "狩猎+10%"),
    _e("守林人",   0, 10, {"needs_resist": 0.08}, "需求衰减-8%"),
    _e("药圃工",   0, 10, {"herb_bonus": 0.20}, "草药+20%"),
    _e("医者",     0, 11, {"soul_xp": 0.10}, "灵魂+10%"),
    _e("酒保",     0, 10, {"give_bonus": 0.08}, "善言"),
    _e("吟游诗人", 0, 10, {"soul_xp": 0.08, "give_bonus": 0.05}, "灵魂+8%"),
    _e("织匠",     0, 11, {"trade_bonus": 0.05, "needs_resist": 0.05}, "勤俭"),
    _e("陶工",     0, 11, {"build_bonus": 0.06, "gather_bonus": 0.05}, "制坯"),
    _e("驯兽师",   0, 10, {"body_xp": 0.05, "soul_xp": 0.05}, "通灵"),
    _e("巡夜人",   0, 10, {"energy_cost": 0.10}, "夜警 省力"),
    _e("拾荒者",   0, 9, {"gather_bonus": 0.12}, "搜寻+12%"),
    _e("教堂杂役", 0, 10, {"soul_xp": 0.08}, "虔诚"),
    _e("学徒",     0, 11, {"magic_xp": 0.06, "body_xp": 0.06}, "初学乍练"),

    # ================= 精阶（15-20%，需技艺/资格门槛）=================
    _e("骑士",     1, 27, {"body_xp": 0.15, "build_bonus": 0.10}, "体炼+15%"),
    _e("宫廷学士", 1, 23, {"magic_xp": 0.18}, "魔力+18%"),
    _e("行会商人", 1, 23, {"trade_bonus": 0.15, "wealth_start": 0.20}, "家资+20%"),
    _e("战地医官", 1, 22, {"soul_xp": 0.15, "give_bonus": 0.10}, "仁心"),
    _e("游侠队长", 1, 22, {"speed_bonus": 0.10, "body_xp": 0.10}, "矫健"),
    _e("符文匠",   1, 22, {"magic_xp": 0.12, "build_bonus": 0.12}, "镌纹（矮人符文天赋）"),
    _e("魔药师",   1, 22, {"herb_bonus": 0.25, "trade_bonus": 0.08}, "魔药（学院魔药科）"),
    _e("法师",     1, 23, {"magic_xp": 0.18, "soul_xp": 0.05}, "冥想凝核"),
    _e("剑士",     1, 23, {"body_xp": 0.18}, "呼吸法淬体"),
    _e("城卫长",   1, 20, {"body_xp": 0.12, "needs_resist": 0.05}, "守备"),
    _e("教区祭司", 1, 20, {"soul_xp": 0.15, "give_bonus": 0.08}, "圣事（教廷基层）"),
    _e("营造师",   1, 21, {"build_bonus": 0.18}, "工程"),
    _e("宫廷法师", 1, 23, {"magic_xp": 0.18, "soul_xp": 0.05}, "宫廷直属（帝室顾问）"),

    # ================= 珍阶（22-30%，有明确编制/稀缺技艺）=================
    _e("圣殿骑士", 2, 21, {"body_xp": 0.20, "soul_xp": 0.10}, "誓约（教廷武备）"),
    _e("冰晶技师", 2, 19, {"magic_xp": 0.15, "trade_bonus": 0.15}, "冰晶网络（学院学科）"),
    _e("御风船员", 2, 19, {"speed_bonus": 0.15, "energy_cost": 0.10}, "御风（飞空艇）"),
    _e("教区主教", 2, 19, {"soul_xp": 0.20, "give_bonus": 0.12}, "教省教务"),
    _e("教授",     2, 19, {"magic_xp": 0.20, "soul_xp": 0.10}, "六阶起任（学院）"),
    _e("大商人",   2, 19, {"trade_bonus": 0.22, "wealth_start": 0.30}, "商路贯通"),
    _e("魔工师",   2, 19, {"build_bonus": 0.20, "magic_xp": 0.10}, "魔晶动力（魔法工业）"),
    _e("剑术大师", 2, 17, {"body_xp": 0.22, "speed_bonus": 0.06}, "六阶剑术"),
    _e("魔法学院教授", 2, 19, {"magic_xp": 0.20, "soul_xp": 0.10}, "学院教授（六阶起任）"),

    # ================= 稀阶（30-40%，一域之望）=================
    _e("贤者",     3, 14, {"soul_xp": 0.20, "magic_xp": 0.20, "deadline_bonus": 0.30},
       "精神力+20% 魔力+20% 智力+20%（艾尔菲亚·推导）"),
    _e("剑尊",     3, 14, {"body_xp": 0.25, "speed_bonus": 0.10}, "七阶剑术（推导）"),
    _e("圣者",     3, 11, {"soul_xp": 0.25, "magic_xp": 0.15}, "八阶圣者（推导）"),
    _e("大主教",   3, 10, {"soul_xp": 0.25, "give_bonus": 0.15}, "十位大主教皆八阶圣者"),
    _e("探界者",   3, 11, {"trade_radius": 3, "speed_bonus": 0.10},
       "方向感+50% 路径记忆+30%（菲莉亚·妖精）"),
    _e("剑帝",     3, 8, {"body_xp": 0.30, "sword_power": 0.30, "deadline_bonus": 0.20},
       "剑术伤害+30% 悟性+50% 剑术精通+30%（盖特）"),
    _e("魔法帝",   3, 8, {"magic_xp": 0.30, "soul_xp": 0.20}, "九阶魔法帝（推导）"),
    _e("魔法学院主任", 3, 12, {"magic_xp": 0.22, "soul_xp": 0.12}, "学院主任（八阶）"),

    # ================= 传说（世界观点名的特殊职阶）=================
    # 始祖不在此处：伊莉斯专属、真神级，不入降生抽签。
    _e("解构者",   4, 4, {"magic_xp": 0.30, "soul_xp": 0.30},
       "分析+30% 悟性+30%（塔·明伊尔）"),
    _e("毒药师",   4, 4, {"herb_bonus": 0.50, "soul_xp": 0.20},
       "毒与草药理解+50% 智力+20%（艾德里克）"),
    _e("慈悲者",   4, 5, {"give_bonus": 0.30, "soul_xp": 0.15},
       "善良+20% 信任+30% 共情+15% 凝聚力+10% 治愈+15%（阿亚斯·DE）"),
    _e("勇者",     4, 4, {"all": 0.15, "growth": 0.20, "needs_resist": 0.25},
       "全属性+15% 高位威压抗性+25% 守护意志+20% 成长+20%"),
    _e("魔王",     4, 4, {"all": 0.20, "body_xp": 0.20, "blood_drain": 0.15},
       "核心属性+20% 威压+25% 战斗直觉+20% 生命汲取+15%"),
    _e("皇帝",     4, 4, {"trade_bonus": 0.30, "soul_xp": 0.30, "deadline_bonus": 0.30},
       "威势+30% 智力+30% 洞察力+30%（马尔杜克）"),
    _e("光辉",     4, 3, {"magic_xp": 0.20, "spell_power": 0.20, "soul_xp": 0.10, "regen_bonus": 0.25},
       "光系+20% 凝聚+10% 光元素亲和+30% 净化+25%（卡尔修斯）"),
]


# ------------------------------------------------------------
# 魔力特性池
# 世界观：非常稀有，法师中亦只十分之一，高级特性更少。
# **不分级**：世界观点明「稀有/更稀有」的层次差异，但未给分档体系；
#   本库不设 tier，改用「权重」表达稀有度（数值越小越罕见）。
# **不含**时空、星辰、命运、灵魂共鸣等越出世界观的概念型特性
#   （旧版此类条目为自创，已移除）。
# 结构：八元素类（每系 3-4 项）+ 功能类（吸血等）。
# 凡世界观点名者注明出处；凡按元素物理链推导者标「推导」。
# ------------------------------------------------------------
AWAKEN_RATE = 0.02   # 见下方说明：法师中 1/10，法师占总人口少数 ⇒ 总人口远低于 1/10

AFFINITY_POOL = [
    # ============ 水系（生存梯度第 1 位，五项俱全）============
    _e("流水", None, 12, {"regen_bonus": 0.12, "energy_cost": 0.20, "magic_xp": 0.10},
       "水系威力+10% 消耗-20% 自愈+10% 水系精通+10%（塔·明伊尔）"),
    _e("净化", None, 10, {"regen_bonus": 0.15, "needs_resist": 0.06},
       "生命链·净化治愈（推导）"),
    _e("冰晶", None, 10, {"needs_resist": 0.10, "trade_radius": 1},
       "相变潜热·蓄能、冰晶折射·光学隐形（推导）"),
    _e("潮息", None, 9, {"energy_cost": 0.12, "rest_bonus": 0.15},
       "三态循环·再生不竭（推导）"),

    # ============ 光系（第 2 位）============
    _e("威光", None, 10, {"magic_xp": 0.30, "soul_xp": 0.08},
       "光系魔法加成+30%（马尔杜克·神耀大帝）"),
    _e("辉疗", None, 10, {"regen_bonus": 0.18, "give_bonus": 0.10},
       "光疗·治愈、光压·护盾（推导）"),
    _e("迷彩", None, 9, {"energy_cost": 0.10, "speed_bonus": 0.05},
       "光学迷彩·隐匿，折射偏转视线（推导）"),

    # ============ 木系（第 3 位）============
    _e("木灵亲和", None, 10, {"herb_bonus": 0.10, "magic_xp": 0.10},
       "木系威力+10% 精通+10%，森林感知（菲莉亚·妖精）"),
    _e("生机", None, 11, {"regen_bonus": 0.14, "give_bonus": 0.08},
       "生机链·生命恢复与生机灌注（推导）"),
    _e("缠藤", None, 9, {"gather_bonus": 0.12, "needs_resist": 0.05},
       "演化链·控制：毒藤缠绕、麻痹花粉（推导）"),
    _e("腐朽再生", None, 8, {"rest_bonus": 0.20, "herb_bonus": 0.15},
       "腐朽循环·再生（推导）"),

    # ============ 雷系（第 4 位）============
    _e("疾雷", None, 10, {"speed_bonus": 0.12, "magic_xp": 0.08},
       "以电御体·自强化（推导）"),
    _e("电磁护盾", None, 9, {"needs_resist": 0.10, "body_xp": 0.08},
       "静电力场链·电磁护盾（推导）"),
    _e("磁感", None, 9, {"trade_radius": 2, "soul_xp": 0.06},
       "磁感索敌·感知（推导）"),
    _e("电疗", None, 8, {"regen_bonus": 0.12, "rest_bonus": 0.12},
       "电疗·愈，电刺激生机、除颤复苏（推导）"),

    # ============ 暗系（第 5 位）============
    _e("匿影", None, 10, {"energy_cost": 0.10, "soul_xp": 0.06},
       "隐蔽链·藏身形掩气息（推导）"),
    _e("静默", None, 9, {"needs_resist": 0.08, "speed_bonus": 0.05},
       "声学静默链、辐射屏蔽·反感知（推导）"),
    _e("遮蔽", None, 8, {"trade_bonus": 0.10, "gather_bonus": 0.08},
       "遮蔽链·剥夺视野（推导）"),

    # ============ 地系（第 6 位）============
    _e("磐固", None, 10, {"build_bonus": 0.15, "needs_resist": 0.06},
       "物质链·防御壁垒、晶体链·硬度（推导）"),
    _e("土障", None, 9, {"build_bonus": 0.10, "body_xp": 0.10},
       "摩擦压实链·土障（推导）"),
    _e("矿感", None, 9, {"gather_bonus": 0.15, "trade_radius": 1},
       "感知依赖大地（推导）"),

    # ============ 风系（第 7 位）============
    _e("轻身", None, 10, {"speed_bonus": 0.10, "energy_cost": 0.06},
       "伯努利链·升力与侧向规避（推导）"),
    _e("湍流", None, 9, {"speed_bonus": 0.06, "needs_resist": 0.06},
       "湍流链·干扰伪装（推导）"),
    _e("气压场", None, 8, {"trade_radius": 1, "give_bonus": 0.10},
       "气压链·控场（推导）"),

    # ============ 火系（第 8 位，须仰外部可燃介质）============
    _e("灼炼", None, 9, {"magic_xp": 0.12, "body_xp": 0.06},
       "须仰外部可燃介质（推导）"),
    _e("爆燃", None, 8, {"body_xp": 0.12, "energy_cost": 0.08},
       "纯粹破坏与爆发（推导）"),
    _e("引燃", None, 8, {"gather_bonus": 0.10, "build_bonus": 0.08},
       "以外部介质续燃（推导）"),

    # ============ 功能类（非元素，世界观点名）============
    _e("吸血", None, 10, {"blood_drain": 0.20, "regen_bonus": 0.10},
       "吸收附近血液/生命力回复（盖特·剑皇公）"),
    _e("元素", None, 5, {"magic_xp": 0.10, "growth": 0.10},
       "能使用所有元素魔法，元素魔法加成+10%（艾尔菲亚）"),
]

# 觉醒率推导（不臆造）：
#   世界观：魔力特性「法师中十分之一」；法师占总人口为少数（学院入学 8-10 岁、
#   须先识字会算术，凡人普遍无位阶）。取法师占比 1/5 作演示层假设，
#   则总人口觉醒率 ≈ 0.10 × 0.2 = 0.02。该 0.2 为**演示层参数**，非世界观数值。
MAGE_POPULATION_SHARE = 0.20
AWAKEN_RATE = 0.10 * MAGE_POPULATION_SHARE


# ------------------------------------------------------------
# 技能双轨（战斗 v1）：技能=魔法或剑法——体阶解锁剑法（耗精力），
# 法阶解锁魔法（耗魔力）。直接操控元素力**不入公共技能表**：
# 世界观中能直接操控元素力者极罕（「元素」魔力特性持有者 ≈0.36%，
# bug 级强者），禀赋元素仅作法术风味调制（结算层 +5%）。
# 纯数据零 RNG；power 为基准威力，结算层乘 位阶/职阶加成。
# ------------------------------------------------------------
SWORD_ARTS = [
    {"name": "木剑式",   "rank": 1, "power": 10, "cost": 6},
    {"name": "连斩",     "rank": 3, "power": 18, "cost": 10},
    {"name": "破甲击",   "rank": 5, "power": 28, "cost": 15},
    {"name": "剑气斩",   "rank": 7, "power": 42, "cost": 22},
    {"name": "剑域",     "rank": 9, "power": 60, "cost": 30},
]
MAGIC_SPELLS = [
    {"name": "魔力弹",   "rank": 1, "power": 9,  "cost": 6},
    {"name": "魔光束",   "rank": 3, "power": 16, "cost": 10},
    {"name": "聚能炮",   "rank": 5, "power": 26, "cost": 16},
    {"name": "连锁咒",   "rank": 7, "power": 40, "cost": 24},
    {"name": "禁咒·星陨", "rank": 9, "power": 58, "cost": 34},
]


def current_skill(rank, table):
    """该轨当前可用的最高阶技能（阶不足返回 None；表按 rank 升序给出）。"""
    best = None
    for s in table:
        if s["rank"] <= rank and (best is None or s["rank"] > best["rank"]):
            best = s
    return best


# ------------------------------------------------------------
# 抽签接口（确定性：只消费传入的 rng）
# ------------------------------------------------------------
def draw_vocation(rng):
    return rng.choices(VOCATION_POOL, weights=[e["w"] for e in VOCATION_POOL])[0]


def draw_affinity(rng):
    """先掷觉醒（AWAKEN_RATE），觉醒后按池内权重抽特性；未觉醒返回 None。"""
    if rng.random() >= AWAKEN_RATE:
        return None
    return rng.choices(AFFINITY_POOL, weights=[e["w"] for e in AFFINITY_POOL])[0]


def vocation_weight_sum():
    return sum(e["w"] for e in VOCATION_POOL)


def affinity_weight_sum():
    return sum(e["w"] for e in AFFINITY_POOL)


def vocation_names():
    return [e["name"] for e in VOCATION_POOL]


def affinity_names():
    return [e["name"] for e in AFFINITY_POOL]


def tier_weights():
    """各稀有度权重份额（供分布检验复算）。"""
    out = {t: 0 for t in RARITY_NAMES}
    for e in VOCATION_POOL:
        out[e["tier"]] += e["w"]
    return out


def unwired_effects():
    """库完整性自检：返回所有未接线的效果键（应为空列表——公示即执行）。"""
    out = []
    for pool in (VOCATION_POOL, AFFINITY_POOL):
        for e in pool:
            for k in e["effects"]:
                if k not in KNOWN_EFFECTS and (id(pool), k) not in out:
                    out.append((id(pool), k))
    return out


def verify_pool():
    """库的自检清单（返回问题列表；空列表=通过）。"""
    problems = []
    # 1) 始祖不得入池
    if any(e["name"] == "始祖" for e in VOCATION_POOL):
        problems.append("始祖进入了抽签池（应为伊莉斯专属，不入抽签）")
    # 2) 职阶权重和
    if vocation_weight_sum() != 1000:
        problems.append("职阶权重和=%d（应为 1000）" % vocation_weight_sum())
    # 3) 魔力特性不分级
    if any(e["tier"] is not None for e in AFFINITY_POOL):
        problems.append("魔力特性出现了 tier 值（世界观未给分档体系）")
    # 4) 不得含概念型特性（时空/星辰/命运类）
    banned = {"空间", "时光", "星穹", "命运", "星辉", "时空双鉴", "灵魂共鸣", "创世之息"}
    hit = banned & {e["name"] for e in AFFINITY_POOL}
    if hit:
        problems.append("魔力特性含越出世界观的概念型条目：%s" % sorted(hit))
    # 5) 八元素不得作为魔力特性
    hit2 = set(ELEMENT_ORDER) & {e["name"] for e in AFFINITY_POOL}
    if hit2:
        problems.append("八元素被误列为魔力特性：%s（元素是固有属性）" % sorted(hit2))
    # 6) 未接线效果
    if unwired_effects():
        problems.append("存在未接线效果键：%s" % unwired_effects())
    # 7) 八元素完整
    if set(ELEMENT_ORDER) != {"水", "光", "木", "雷", "暗", "地", "风", "火"}:
        problems.append("八元素集合不正确")
    return problems
