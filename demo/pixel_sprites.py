# -*- coding: utf-8 -*-
"""坎公骑冠剑（Guardian Tales）风格像素小人渲染器 v2
====================================================================

纯观察者渲染模块：只读世界数据、只产出绘制调用，不触碰世界状态、
不消耗 world._rng（goal_system_smoke 的 state_hash 断言覆盖此纪律）。

v2 升级（M2.7 渲染改造，与 NPC 身份化配套）：
  - 职阶配色：vocation_cloth() 以 crc32 确定性映射 12 色板——同职阶同色系，
    画面上可辨识「铁匠/法师/商人」的身份差异；未挂载身份层的旧世界
    （NohnWorld/GoalDrivenWorld）回退状态色，行为与 v1 完全一致；
  - 势力徽章：faction_badge() 胸口 2×2 徽记（教廷金白/学院蓝紫/商盟金黄…）；
  - 元素光环：ELEMENT_AURA 脚下双层椭圆光圈（八元素各一色，画 overlay）；
  - 眨眼：idle 时按 idle_t 周期闭眼（确定性派生，不消耗 RNG）；
  - 保留 v1 全部基础：Q 比例 chibi（20×24）、四向、四帧行走+弹跳+摆臂、
    厚描边平涂、主角金围巾红披风、最近邻立绘放大。

pygame 懒加载：仅在渲染函数内 import——headless 路径
（smoke / audit）不因此引入 pygame 依赖。
"""

import math
import zlib

INK = (32, 27, 40)
SKIN = (255, 224, 197)
PANTS = (74, 66, 88)
WHITE = (255, 255, 255)
EYEW = (250, 250, 255)
PUPIL = (36, 28, 40)
BLUSH = (255, 170, 160)
CAPE = (206, 64, 54)
SCARF = (255, 208, 88)

# —— 职阶服装 12 色板（明快饱和，坎公式）——
VOCATION_PALETTE = (
    (226, 88, 84),   # 朱红
    (86, 156, 226),  # 钴蓝
    (96, 190, 110),  # 草绿
    (238, 170, 70),  # 橙
    (168, 120, 220), # 紫
    (70, 190, 200),  # 青
    (235, 120, 170), # 粉
    (206, 206, 110), # 黄绿
    (150, 140, 220), # 蓝紫
    (220, 150, 95),  # 棕
    (120, 180, 235), # 天蓝
    (240, 200, 90),  # 金
)
# —— 势力徽记色（与 factions.py FACTION_KEYS 对齐）——
FACTION_BADGE = {
    "theocracy": (250, 240, 200),   # 教廷：金白
    "academy": (150, 140, 255),     # 学院：蓝紫
    "guild": (255, 205, 80),        # 商盟：金黄
    "knights": (235, 95, 95),       # 骑士团：绯红
    "rangers": (110, 200, 120),     # 游侠：森绿
    "artisans": (235, 150, 70),     # 匠人：铜橙
    "freelance": (170, 178, 192),   # 自由身：灰
}
# —— 八元素光环（脚底光圈，与 ELEMENT_ORDER 对齐）——
ELEMENT_AURA = {
    "水": (90, 170, 255), "光": (255, 240, 170), "木": (110, 210, 120),
    "雷": (170, 120, 255), "暗": (110, 90, 130), "地": (170, 130, 90),
    "风": (120, 230, 210), "火": (255, 130, 80),
}

_CACHE = {}

SPRITE_SCALE = 2   # 32×16 菱形格上的小人放大倍数（最近邻，保像素感）


def _dk(c, f=0.76):
    return tuple(max(0, int(v * f)) for v in c)


def _lt(c, f=0.38):
    return tuple(min(255, int(v + (255 - v) * f)) for v in c)


def dir_from_vector(dx, dy):
    """移动向量 → 四向朝向（视觉派生态，不入账本）。"""
    if dx == 0 and dy == 0:
        return "down"
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


def vocation_cloth(name):
    """职阶名 → 服装主色。crc32 确定性映射（跨进程稳定，不用 hash() 随机化）。"""
    if not name:
        return (186, 196, 214)
    return VOCATION_PALETTE[zlib.crc32(name.encode("utf-8")) % len(VOCATION_PALETTE)]


def faction_badge(key):
    """势力 key → 胸口徽记色；未入线/未知返回 None（不画）。"""
    return FACTION_BADGE.get(key)


# —— 职阶配饰：程序化区分身份（与 vocation_cloth 同构，crc32 无关、显式名录）——
# staff   法杖：施法者（法师系）
# book    典籍：教职/学者（教授、学士、书记官）
# glasses 眼镜：学院高层/研究者（主任）
# circlet 额冠：位阶顶端（魔法帝、贤者、圣者、解构者）
VOCATION_GEAR = {
    "见习法师": "staff", "法师": "staff", "宫廷法师": "staff",
    "教授": "book", "魔法学院教授": "book", "宫廷学士": "book",
    "书记官": "book", "抄写员": "book", "学徒": "book",
    "魔法学院主任": "glasses",
    "贤者": "circlet", "圣者": "circlet", "魔法帝": "circlet",
    "解构者": "circlet",
}


def vocation_gear(name):
    """职阶名 → 配饰种类（staff/book/glasses/circlet）或 None。

    与 vocation_cloth 同为纯观察者映射：只读职阶名，不触碰世界状态。
    """
    return VOCATION_GEAR.get(name)


def _render(cloth, hair, direction, frame, state, hero, badge=None, gear=None):
    """在 20×24 画布上绘制一个朝向/帧位的 chibi（脚底 y≈23）。

    gear: 职阶配饰（staff/book/glasses/circlet），由 vocation_gear() 派生。
    """
    import pygame
    if direction == "left":          # 左向 = 右向镜像（像素级精确）
        base = _render(cloth, hair, "right", frame, state, hero, badge, gear)
        return pygame.transform.flip(base, True, False)
    surf = pygame.Surface((20, 24), pygame.SRCALPHA)
    lift_l = 1 if frame == 1 else 0
    lift_r = 1 if frame == 3 else 0
    bounce = 1 if frame in (1, 2) else 0
    # —— 腿（行走交替）——
    def leg(x, lift):
        y0 = 19 - lift
        pygame.draw.rect(surf, INK, (x - 1, y0 - 1, 5, 6 - lift), border_radius=2)
        pygame.draw.rect(surf, PANTS, (x, y0, 3, 4 - lift), border_radius=1)
    leg(7, lift_l)
    leg(11, lift_r)
    # —— 身体（含主角披风）——
    by = 14 - bounce
    if hero:
        pygame.draw.rect(surf, INK, (2, by, 4, 7), border_radius=1)
        pygame.draw.rect(surf, CAPE, (3, by, 2, 5), border_radius=1)
        pygame.draw.rect(surf, INK, (14, by, 4, 7), border_radius=1)
        pygame.draw.rect(surf, CAPE, (15, by, 2, 5), border_radius=1)
    pygame.draw.rect(surf, INK, (4, by - 1, 12, 8), border_radius=3)
    pygame.draw.rect(surf, cloth, (5, by, 10, 6), border_radius=2)
    pygame.draw.rect(surf, _lt(cloth, 0.30), (5, by, 10, 2), border_radius=1)
    pygame.draw.rect(surf, _dk(cloth, 0.68), (5, by + 5, 10, 1))      # 下摆阴影线
    if hero:
        pygame.draw.rect(surf, SCARF, (5, by + 2, 10, 1))
    # —— 胸口势力徽记（2×2，INK 衬边）——
    if badge is not None:
        pygame.draw.rect(surf, INK, (8, by + 1, 4, 4), border_radius=1)
        pygame.draw.rect(surf, badge, (9, by + 2, 2, 2))
    # —— 手持配饰（先画，让手臂覆盖其上形成「持握」）——
    if gear == "staff":                     # 右侧法杖：杖身 + 宝石杖首
        pygame.draw.rect(surf, INK, (17, 5, 2, 18))
        pygame.draw.rect(surf, (150, 110, 70), (17, 6, 1, 16))
        pygame.draw.rect(surf, INK, (16, 3, 4, 4), border_radius=1)
        pygame.draw.rect(surf, (150, 210, 255), (17, 4, 2, 2))
    elif gear == "book":                    # 左侧典籍：封面 + 内页
        pygame.draw.rect(surf, INK, (0, by + 1, 5, 6), border_radius=1)
        pygame.draw.rect(surf, (238, 226, 196), (1, by + 2, 3, 4))
        pygame.draw.rect(surf, _dk(cloth, 0.7), (1, by + 2, 1, 4))
    # —— 手臂（背向时藏在身后）——
    if direction != "up":
        ay_l = by + (1 if frame == 3 else 0)
        ay_r = by + (1 if frame == 1 else 0)
        pygame.draw.rect(surf, INK, (2, ay_l - 1, 4, 6), border_radius=2)
        pygame.draw.rect(surf, _dk(cloth, 0.82), (3, ay_l, 2, 4), border_radius=1)
        pygame.draw.rect(surf, INK, (14, ay_r - 1, 4, 6), border_radius=2)
        pygame.draw.rect(surf, _dk(cloth, 0.82), (15, ay_r, 2, 4), border_radius=1)
    # —— 头 ——
    hy = 8 - bounce
    pygame.draw.circle(surf, INK, (10, hy), 8)
    pygame.draw.circle(surf, SKIN, (10, hy), 7)
    pygame.draw.circle(surf, INK, (10, hy - 1), 8)
    pygame.draw.circle(surf, hair, (10, hy - 1), 7)
    if direction == "up":
        pygame.draw.rect(surf, _dk(hair, 0.85), (8, hy - 7, 4, 2), border_radius=1)
    else:
        # 脸部（刘海以下）
        pygame.draw.circle(surf, SKIN, (10, hy + 3), 5)
        pygame.draw.rect(surf, SKIN, (5, hy + 2, 10, 5))
        pygame.draw.rect(surf, hair, (4, hy - 1, 12, 2))       # 刘海边缘
        if direction == "down":
            if state in ("resting", "blink"):
                pygame.draw.rect(surf, INK, (5, hy + 2, 3, 1))
                pygame.draw.rect(surf, INK, (12, hy + 2, 3, 1))
            else:
                for ex in (5, 12):
                    pygame.draw.rect(surf, EYEW, (ex, hy + 1, 3, 3))
                    pygame.draw.rect(surf, PUPIL, (ex + 1, hy + 2, 2, 2))
                    pygame.draw.rect(surf, WHITE, (ex + 1, hy + 1, 1, 1))
                pygame.draw.rect(surf, _dk(SKIN, 0.85), (9, hy + 5, 3, 1))
            pygame.draw.rect(surf, BLUSH, (4, hy + 4, 2, 1))
            pygame.draw.rect(surf, BLUSH, (14, hy + 4, 2, 1))
        elif direction == "right":
            pygame.draw.rect(surf, hair, (3, hy - 5, 5, 9))     # 后脑发量
            pygame.draw.rect(surf, EYEW, (11, hy + 1, 3, 3))
            pygame.draw.rect(surf, PUPIL, (12, hy + 2, 2, 2))
            pygame.draw.rect(surf, WHITE, (12, hy + 1, 1, 1))
            pygame.draw.rect(surf, _dk(SKIN, 0.85), (11, hy + 5, 2, 1))
        # （left 由 right 镜像得到）
    # —— 头部配饰 ——
    if gear == "circlet":                   # 额冠：发际线金带 + 中央饰件
        pygame.draw.rect(surf, (255, 215, 120), (4, hy - 4, 12, 1))
        pygame.draw.rect(surf, (255, 235, 170), (9, hy - 6, 2, 2))
    if gear == "glasses" and direction == "down":
        pygame.draw.rect(surf, (60, 50, 70), (4, hy, 5, 5), 1)      # 左镜框
        pygame.draw.rect(surf, (60, 50, 70), (11, hy, 5, 5), 1)     # 右镜框
        pygame.draw.rect(surf, (60, 50, 70), (9, hy + 2, 2, 1))     # 鼻梁
    elif gear == "glasses" and direction == "right":
        pygame.draw.rect(surf, (60, 50, 70), (10, hy, 6, 5), 1)     # 侧镜框
    # —— 状态饰件 ——
    if state == "working":
        pygame.draw.rect(surf, (140, 214, 255), (17, 3, 2, 3))  # 汗滴
        pygame.draw.rect(surf, (215, 242, 255), (17, 3, 1, 1))
    elif state == "creating":
        pygame.draw.rect(surf, (255, 236, 140), (16, 3, 3, 1))
        pygame.draw.rect(surf, (255, 236, 140), (17, 2, 1, 3))
    return surf


def _cached(key, builder):
    surf = _CACHE.get(key)
    if surf is None:
        surf = builder()
        if len(_CACHE) > 600:
            _CACHE.clear()
        _CACHE[key] = surf
    return surf


def draw_chibi(screen, overlay, cx, cy, *, cloth, hair, direction="down",
               phase=0.0, state="idle", idle_t=0, hero=False,
               badge=None, aura=None, gear=None):
    """在屏幕 (cx, cy)=脚底中心 处绘制一个小人；阴影/光环画到 overlay。

    badge: 势力徽记色（胸口 2×2）或 None；
    aura:  元素光圈色（脚下双层椭圆）或 None；
    gear:  职阶配饰（staff/book/glasses/circlet）或 None；
    眨眼：idle 且 (idle_t % 173) < 9 且面朝下 → 闭眼帧（确定性派生）；
    2× 最近邻放大（SPRITE_SCALE）：32×16 菱形格上 20×24 原生精灵过小，
    放大后约为格宽 1.25 倍——坎公式的头身占比。缓存键含缩放档。"""
    import pygame
    if state == "idle" and direction == "down" and (int(idle_t) % 173) < 9:
        state = "blink"
    frame = int((phase % 1.0) * 4) % 4
    if state == "resting":
        frame = 0
    key = (tuple(cloth), tuple(hair), direction, frame, state, bool(hero),
           tuple(badge) if badge else None, gear)
    surf = _cached(key, lambda: _render(cloth, hair, direction, frame, state, hero, badge, gear))
    sc = SPRITE_SCALE
    if sc > 1:
        skey = key + ("x%d" % sc,)
        surf = _cached(skey, lambda: pygame.transform.scale(
            surf, (20 * sc, 24 * sc)))
    bob = int(math.sin(idle_t * 0.09) * 1.2) if state != "working" else 0
    if overlay is not None:
        if aura is not None:
            pygame.draw.ellipse(overlay, aura + (36,), (cx - 17, cy - 4, 34, 9))
            pygame.draw.ellipse(overlay, aura + (58,), (cx - 12, cy - 4, 24, 7))
        pygame.draw.ellipse(overlay, (0, 0, 0, 90), (cx - 13, cy - 3, 26, 6))
    screen.blit(surf, (cx - 10 * sc, cy - 22 * sc - bob * sc))


def chibi_portrait(cloth, hair, direction="down", state="idle", hero=False,
                   scale=3, badge=None, gear=None):
    """立绘：最近邻放大（无平滑，保持像素感），供侧栏选中面板使用。"""
    import pygame
    key = (tuple(cloth), tuple(hair), direction, 0, state, bool(hero), int(scale),
           tuple(badge) if badge else None, gear)
    return _cached(key, lambda: pygame.transform.scale(
        _render(cloth, hair, direction, 0, state, hero, badge, gear),
        (20 * int(scale), 24 * int(scale))))
