#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Second Reality v2.0 - Virtual World Model
Aligned with system/ layer: 5-layer needs + memory + compliant economy + perceive/think/act

分工声明（防止审计口径被混称）：
  - 本文件 = 社会仿真「演示逻辑层」。依赖两类本地模块，二者均零第三方依赖：
      1) constitution_rules.py —— 宪法规则层（构成公理 + 治理公理 + NOHN_LAW_AXIOMS）。
         本世界不再是「自包含玩具」：构成公理一至五（空间/时间/因果/存在/创世）
         与治理公理的承载对象，全部实例化自规则层；物理常数、守恒容差取自
         NOHN_LAW_AXIOMS 这一唯一权威源，不在本文件重复硬编码。
      2) persona/ —— 拟人心理层（SPL Pure Core V8.0，源仓库原文复制件）。
    「只依赖标准库」仍然成立。
  - 仍不 import system/：实现层（鉴权/账本/共识/二阶因果引擎）由 system/ 承担，
    system/runtime.py 是本文件逻辑的服务化/可部署形态（见该文件头部说明）。
    边界：人格层只产出人格与内感受，不实现 memory/意志类宪法契约；
    那些契约仍由 system/agent_engine.py 承担，审计依赖它们。
    人格层状态不进入 export_state()/to_dict()，因此不改变 state_hash()。
  - get_simulation_metrics() 是「仿真自评」，不是宪法审计。
    宪法级 25 项审计由 audit_engine.SecondPerspectiveAuditor().audit_world(world) 提供；
    --audit 即调用它，并如实呈现未通过项（演示层不伪造通过）。
  - 全局确定性：所有随机数统一走 NohnWorld._rng（由 WorldConfig.seed 播种）。
    同一 (config, seed) => 世界状态逐字节可复现，可用 NohnWorld.state_hash() 取证。
"""
import random, math, time, json, hashlib, os, sys, zlib
from dataclasses import dataclass, field, asdict
from typing import Any, List, Dict, Tuple, Optional
from enum import Enum

# 人格层：与本文件同级目录下的 persona/。脚本方式运行也保证可解析。
# 缺失时直接 ImportError —— 不做静默降级，避免"以为挂了引擎其实没跑"。
_HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from persona import PERSONA_MODES, build_persona, build_persona_stack   # noqa: E402

# 宪法规则层：仓库根目录的 constitution_rules.py。
# 演示层只消费规则、不构成实现层依赖；缺失即 ImportError —— 同样不做静默降级，
# 否则会出现"以为挂了宪法其实没挂"的假合规（那正是 R4 要防的形态）。
_REPO_ROOT=os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
from constitution_rules import (   # noqa: E402
    NOHN_LAW_AXIOMS, SpatialSubstrate, TemporalSubstrate, CausalClosure,
    ExistenceAxiom, GenesisCondition, ImmutableWorldRule, AestheticCompliance,
    SoulAttestation, SoulLedger, MemoryInalienability, WorldPerpetuity,
    MandatoryInteroperability, DecentralizationGovernance,
)

# 坎公风像素小人渲染器（纯观察者；pygame 懒加载，headless 不引入依赖）
import pixel_sprites as pspr   # noqa: E402

# 职阶库 / 魔力特性库（纯数据模块，登录抽签唯一权威源）
try:                                                          # noqa: E402
    from . import vocations as voc                             # noqa: E402
except ImportError:                                            # pragma: no cover
    import vocations as voc                                    # noqa: E402

FIVE_LAYER_NEEDS = ["physiology","safety","belonging","esteem","self_actualization"]
NEED_LABELS_CN = ["生理","安全","归属","尊重","自我实现"]
NEED_DECAY = {"physiology":0.3,"safety":0.2,"belonging":0.3,"esteem":0.2,"self_actualization":0.15}
UBI_DAILY=10.0; TAX_RATE=0.05; INFLATION_RATE=0.02; DEBT_LIMIT=-500.0
MAX_WEALTH=100000.0; WEALTH_HARDCAP_TAX=0.5
# 因果图容量上限（演示规模保护）：超出后丢弃最旧节点并把新的最旧节点重挂创世，
# 否则残留事件会引用已不在图中的原因，被判为「神之手」插入（见 _record_event）。
CAUSAL_GRAPH_CAP=50000
MEM_STM=20; MEM_LTM=200; MEM_CONSOL=0.3; MEM_DECAY=0.05; MEM_DECAY_INT=10

# 视野半径（格）。同时作为空间索引的格子边长：格子边长取视野半径，
# 则查 3×3 邻域即可覆盖全部可视对象，不会漏人。
VISION=5
# 空间索引格子边长与邻域半径。格子取 2（而非 5）是因为聚集后桶会变得极不均：
# 智能体会向资源/伴侣聚集，5 格边长下人多的桶一次要扫上百个候选。
# 半径取 ceil(VISION/CELL) 保证 3×3 以外的邻格不漏（CELL=2 → 7×7 邻域，覆盖 ±6）。
INDEX_CELL=2
INDEX_RANGE=(VISION+INDEX_CELL-1)//INDEX_CELL
# 1000 人规模下的姓名池：24 个固定名远不够用，物性音节确定性组合，
# 保证任何人不会重名且可用。
NAME_SYLL_A=["Ald","Bre","Cal","Dor","Eld","Fen","Gil","Hal","Ith","Jun","Kar","Lyn",
             "Mor","Nal","Ort","Pel","Quir","Ren","Sil","Tor","Ulm","Ves","Wyn","Xan",
             "Yor","Zel","Bram","Ced","Drus","Fael"]
NAME_SYLL_B=["a","is","on","ur","eth","ir","os","yn","ar","em","ul","ad","an","el","or"]
NAME_SYLL_C=["","","","a","n","r","s"]

@dataclass
class Position:
    x:int=0; y:int=0

class AgentState(Enum):
    IDLE="idle"; WORKING="working"; SOCIALIZING="socializing"; RESTING="resting"
    TRADING="trading"; LEARNING="learning"; CREATING="creating"; DEAD="dead"

class EventType(Enum):
    TICK="tick"; BIRTH="birth"; DEATH="death"; MARRIAGE="marriage"
    PRODUCE="produce"; TRADE="trade"; INTERACT="interact"; REST="rest"
    UBI="ubi"; TAX="tax"; VIOLATION="violation"

@dataclass
class Event:
    eid:str; etype:EventType; actor:str; tick:int; target:str=""; data:dict=field(default_factory=dict)

@dataclass
class WorldConfig:
    world_size:int=60; initial_agents:int=30; initial_resources:int=120; initial_buildings:int=8
    initial_money_supply:float=10000.0; inflation_rate:float=INFLATION_RATE
    debt_limit:float=DEBT_LIMIT; max_wealth:float=MAX_WEALTH; max_ticks:int=0
    # 确定性：同一 seed + 同一 config => 世界逐字节可复现
    seed:int=0
    # 拟人心理层开关：
    #   "affect" = 每个智能体挂一个 SPL V8.0 人格层，逐 tick 演化情绪（不改行为决策）；
    #   "off"    = 不挂载，行为与接入前逐字节一致。
    persona_mode:str="affect"
    # 经济参数：原先是模块常量硬编码，改 config 无效；现贯穿到 reserve 与各结算点
    ubi_amount:float=UBI_DAILY
    tax_rate:float=TAX_RATE
    wealth_hardcap_tax:float=WEALTH_HARDCAP_TAX
    # 年龄语义：原先 1 tick = 1 岁，在 tps=10 的 GUI 下 80 岁只需 8 秒，社会第 80 tick 即开始灭绝
    ticks_per_year:int=10
    adult_age:int=18; marriage_age:int=20
    birth_min_age:int=22; birth_max_age:int=60; elder_age:int=80
    # 婚姻/生育概率：原先是 _check_reproduction 内的字面量，改 config 无效（与 UBI/税率同类缺陷）
    marriage_prob:float=0.02
    birth_prob:float=0.01

@dataclass
class Memory:
    content:str; importance:float=0.5; emotion:str="neutral"; age:int=0
    tags:List[str]=field(default_factory=list); in_ltm:bool=False
    # 结构化载荷：记忆要参与决策，就必须携带可复用的数据（例如采集点坐标）
    data:dict=field(default_factory=dict)

class MemoryVault:
    def __init__(self, stm_cap=MEM_STM, ltm_cap=MEM_LTM, consolidation=MEM_CONSOL, decay=MEM_DECAY):
        self.stm=[]; self.ltm=[]; self.stm_cap=stm_cap; self.ltm_cap=ltm_cap
        self.consolidation_rate=consolidation; self.decay_rate=decay
    def remember(self, content, importance=0.5, emotion="neutral", tags=None, data=None):
        self.stm.insert(0, Memory(content=content,importance=importance,emotion=emotion,
            tags=tags or [],data=data or {}))
        if len(self.stm)>self.stm_cap: self.stm=self.stm[:self.stm_cap]
    def consolidate(self):
        rem=[]
        for m in self.stm:
            m.age+=1
            if m.importance>=self.consolidation_rate and len(self.ltm)<self.ltm_cap:
                m.in_ltm=True; self.ltm.append(m)
            elif m.importance>=self.decay_rate*2: rem.append(m)
        self.stm=rem
    def decay_memories(self, world_tick):
        # 衰减相位对齐世界时钟，而不是本对象自增计数（原先与游戏时间不同源）
        if world_tick%MEM_DECAY_INT!=0: return
        self.ltm=[m for m in self.ltm if m.importance>self.decay_rate]
        for m in self.ltm: m.importance*=(1-self.decay_rate)
    def recall(self, k=5, tag=None):
        c=list(self.stm)+list(self.ltm)
        if tag: c=[m for m in c if tag in m.tags]
        c.sort(key=lambda m:m.importance, reverse=True)
        return c[:k]
    def digest(self):
        """记忆内容指纹：使世界状态指纹覆盖认知状态，同时避免序列化对象内存地址"""
        items=[{"c":m.content,"i":round(m.importance,6),"e":m.emotion,"t":sorted(m.tags),
                "l":m.in_ltm,"d":m.data} for m in list(self.stm)+list(self.ltm)]
        blob=json.dumps(items,ensure_ascii=False,sort_keys=True,default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
    def stats(self):
        return {"stm_count":len(self.stm),"ltm_count":len(self.ltm),"total_memories":len(self.stm)+len(self.ltm)}

class EconomicReserve:
    """记账式货币发行：每一笔新增/销毁都登记账目，使守恒式可被外部独立复算。

    守恒式（任意 tick 均可校验，invariant_residual 应为 0.0）：
        Σ(所有 agent 的 wealth) + treasury + inflation_created + genesis_unallocated
            == money_supply

    其中：
      - genesis_unallocated：创世储备中尚未分配给初始 agent 的部分（钱已在账上）；
      - inflation_created：只稀释货币、不发放给任何主体的那部分增发；
      - 已故 agent 的 wealth 仍留在其账户（遗产未继承），故求和不区分 alive。
    """
    def __init__(self, initial_supply=10000.0, ubi_amount=UBI_DAILY, tax_rate=TAX_RATE,
                 inflation_rate=INFLATION_RATE, debt_limit=DEBT_LIMIT):
        self.money_supply=initial_supply; self.treasury=0.0; self.ubi_amount=ubi_amount
        self.tax_rate=tax_rate; self.inflation_rate=inflation_rate; self.debt_limit=debt_limit
        self.total_ubi_distributed=0.0; self.total_tax_collected=0.0
        self.total_labor_created=0.0; self.inflation_created=0.0; self.total_debt_relief=0.0
        self.genesis_unallocated=initial_supply
    def allocate_genesis(self, amt):
        """把创世储备金划为某 agent 的初始财富（只是划转，不新增货币）"""
        amt=min(max(0.0,amt),self.genesis_unallocated)
        self.genesis_unallocated-=amt; return amt
    def distribute_ubi(self, pop):
        t=self.ubi_amount*pop; self.money_supply+=t; self.total_ubi_distributed+=t; return t
    def collect_tax(self, amt):
        amt=max(0.0,amt); self.treasury+=amt; self.total_tax_collected+=amt; return amt
    def collect_fee(self, amt):
        """非税收入：购置建筑/服务的款项进入国库（原先 _build_houses 直接扣 wealth，货币凭空消失）"""
        amt=max(0.0,amt); self.treasury+=amt; return amt
    def apply_inflation(self):
        created=self.money_supply*self.inflation_rate
        self.money_supply+=created; self.inflation_created+=created; return created
    def grant_labor(self, amt):
        """劳动所得：货币随劳动产出新增（原先只加 wealth 不加 money_supply，属凭空印钞）"""
        amt=max(0.0,amt); self.money_supply+=amt; self.total_labor_created+=amt; return amt
    def mint_debt_relief(self, amt):
        """债务豁免铸币（原先以 max(wealth, floor) 直接抬高余额，未记账）"""
        amt=max(0.0,amt); self.money_supply+=amt; self.total_debt_relief+=amt; return amt
    def invariant_residual(self, agents):
        total=sum(a.wealth for a in agents)  # 含已故账户：遗产不会凭空消失
        return (total+self.treasury+self.inflation_created+self.genesis_unallocated
                -self.money_supply)


def make_personality(rng):
    """人格由注入的 RNG 生成；不能在 dataclass 默认工厂里调用全局 random，否则世界不可复现"""
    return {"openness":rng.uniform(0.3,0.9),"conscientiousness":rng.uniform(0.3,0.9),
        "extraversion":rng.uniform(0.2,0.9),"agreeableness":rng.uniform(0.3,0.9),
        "neuroticism":rng.uniform(0.1,0.7)}

def make_skills(rng):
    return {"gathering":rng.uniform(0.3,0.8),"crafting":rng.uniform(0.2,0.7),
        "social":rng.uniform(0.2,0.8),"trading":rng.uniform(0.2,0.7),
        "learning":rng.uniform(0.2,0.7),"creating":rng.uniform(0.1,0.6)}

@dataclass
class NohnAgent:
    aid:str; name:str; pos:Position
    needs:Dict[str,float]=field(default_factory=lambda:{"physiology":100.0,"safety":100.0,
        "belonging":100.0,"esteem":100.0,"self_actualization":50.0})
    energy:float=100.0; wealth:float=100.0
    state:AgentState=AgentState.IDLE; alive:bool=True
    age:int=0; generation:int=0
    # 默认值改为静态常量：随机化移到 _spawn_agent，由注入的 world._rng 生成，
    # 否则 dataclass 构造期就调用全局 random，世界无法复现。
    personality:Dict[str,float]=field(default_factory=lambda:{"openness":0.5,"conscientiousness":0.5,
        "extraversion":0.5,"agreeableness":0.5,"neuroticism":0.5})
    skills:Dict[str,float]=field(default_factory=lambda:{"gathering":0.5,"crafting":0.5,
        "social":0.5,"trading":0.5,"learning":0.5,"creating":0.5})
    memory:MemoryVault=field(default_factory=MemoryVault)
    inventory:Dict[str,int]=field(default_factory=dict)
    home_pos:Optional[Position]=None; partner_id:Optional[str]=None
    children_ids:List[str]=field(default_factory=list); friends:List[str]=field(default_factory=list)
    reputation:float=50.0; knowledge:float=10.0; creativity:float=5.0
    violations:int=0; last_ubi_tick:int=0
    # 八元素（一切生灵所禀，人人有）+ 魔力特性（稀有觉醒，不分级）。
    # 与世界观【元素生存法则】一致：元素是固有属性，特性是额外的稀有能力，两者分离。
    element:Optional[str]=None; element_note:Optional[str]=None
    affinity:Optional[str]=None; affinity_text:Optional[str]=None
    _perceived:List[dict]=field(default_factory=list,repr=False)
    # 拟人心理层：persona=引擎实例，affect=其可读标量视图。
    # 两者均不进入 to_dict()，故不改变世界状态哈希（人格层是派生态，不是账本态）。
    persona:Optional[Any]=field(default=None,repr=False,compare=False)
    affect:Dict[str,float]=field(default_factory=dict,repr=False,compare=False)
    # stack = persona/feature 六模块实例（身份/目标/价值观/偏见/世界信念/语言人格）
    stack:Optional[Any]=field(default=None,repr=False,compare=False)
    # 视觉朝向（四向像素小人渲染用）：派生态，不入 to_dict()/state_hash()
    # （与 persona 同一口径：账本态之外的视觉派生，不破坏世界可复现性）
    facing:str=field(default="down",compare=False,repr=False)

    def perceive(self, world):
        # 空间索引邻域查询，结果与全量扫描的顺序完全一致（按对象在各自列表中的
        # 下标排序），因此 30 人的旧世界轨迹不变，而 1000 人时命中 hypot 从
        # 每 tick 百万级降到十万级。旧实现在 1000×4000 下实测 2.35s/tick。
        vis=VISION; cs=INDEX_CELL; rg=INDEX_RANGE
        x=self.pos.x; y=self.pos.y; cx=x//cs; cy=y//cs
        ca=world._cells_a; cr=world._cells_r; cb=world._cells_b
        oc=world._agent_order; byid=world._agents_by_id
        cand=[]
        for dx in range(-rg,rg+1):
            for dy in range(-rg,rg+1):
                k=(cx+dx,cy+dy)
                b=ca.get(k)
                if b:
                    for aid in b: cand.append((0,oc[aid],byid[aid]))
                b=cr.get(k)
                if b:
                    for i in b: cand.append((1,i,world.resources[i]))
                b=cb.get(k)
                if b:
                    for i in b: cand.append((2,i,world.buildings[i]))
        cand.sort(key=lambda t:(t[0],t[1]))
        perceived=[]
        for _kind,_i,o in cand:
            if _kind==0:
                if o.aid==self.aid or not o.alive: continue
                d=math.hypot(o.pos.x-x,o.pos.y-y)
                if d<=vis: perceived.append({"type":"agent","id":o.aid,"name":o.name,
                    "pos":(o.pos.x,o.pos.y),"state":o.state.value,"dist":d})
            elif _kind==1:
                if o["amount"]<=0: continue
                d=math.hypot(o["pos"][0]-x,o["pos"][1]-y)
                if d<=vis: perceived.append({"type":"resource","res_type":o["type"],
                    "pos":o["pos"],"amount":o["amount"],"dist":d})
            else:
                d=math.hypot(o["pos"][0]-x,o["pos"][1]-y)
                if d<=vis: perceived.append({"type":"building","b_type":o["type"],"pos":o["pos"],"dist":d})
        self._perceived=perceived; return perceived

    def think(self, world):
        if not self.alive: return AgentState.DEAD,{}
        rng=world._rng   # 决策随机性统一取自世界随机源
        p={n:max(0,(100-v)) for n,v in self.needs.items()}
        if self.energy<20: return AgentState.RESTING,{"reason":"low_energy"}
        if p["physiology"]>20:
            food=[x for x in self._perceived if x["type"]=="resource"
                  and x["res_type"] in ("food","water","fruit")]
            if food:
                food.sort(key=lambda x:x["dist"])
                return AgentState.WORKING,{"action":"gather","target":food[0]["pos"],"res_type":food[0]["res_type"]}
            return AgentState.WORKING,{"action":"seek_food"}
        if p["safety"]>40:
            if self.home_pos: return AgentState.RESTING,{"action":"go_home","target":(self.home_pos.x,self.home_pos.y)}
            return AgentState.IDLE,{"action":"seek_shelter"}
        cfg=world.config
        # 家庭行为：育龄期已婚者主动与配偶会合（复用社交分支，无需新增动作类型）。
        # 原先 _check_reproduction 的生育分支要求夫妻"恰好相邻 2 格内且 rng<0.01"，
        # 而模型中不存在任何会合机制 => 该分支实际不可达，人口无法自我延续
        # （实测：1000 tick 内 9 对婚姻、0 个新生儿，最终全员灭绝）。
        if self.partner_id and cfg.birth_min_age<self.age<cfg.birth_max_age and self.energy>30:
            pt=world.find_agent(self.partner_id)
            if pt and pt.alive and math.hypot(pt.pos.x-self.pos.x,pt.pos.y-self.pos.y)>1:
                return AgentState.SOCIALIZING,{"action":"meet_partner","target_id":pt.aid}
        if p["belonging"]>35:
            oa=[x for x in self._perceived if x["type"]=="agent"]
            if oa:
                oa.sort(key=lambda x:x["dist"])
                return AgentState.SOCIALIZING,{"action":"socialize","target_id":oa[0]["id"]}
            return AgentState.IDLE,{"action":"seek_company"}
        if p["esteem"]>35 and self.wealth>50:
            tt=[x for x in self._perceived if x["type"]=="agent" and x["id"]!=self.aid]
            if tt and rng.random()<self.skills["trading"]:
                return AgentState.TRADING,{"action":"trade","target_id":rng.choice(tt)["id"]}
            return AgentState.WORKING,{"action":"work"}
        if p["self_actualization"]>30 and self.energy>40:
            if rng.random()<self.personality["openness"]*self.skills["creating"]:
                return AgentState.CREATING,{"action":"create"}
            if rng.random()<self.skills["learning"]:
                return AgentState.LEARNING,{"action":"learn"}
        if self.energy>30 and rng.random()<0.6: return AgentState.WORKING,{"action":"work"}
        return AgentState.IDLE,{"action":"wander"}

    def act(self, decision, world):
        if not self.alive: return []
        ns,ai=decision; self.state=ns; events=[]; rng=world._rng
        if ns==AgentState.RESTING:
            self.energy=min(100,self.energy+15)
            if ai.get("action")=="go_home" and self.home_pos:
                self._move_toward(self.home_pos.x,self.home_pos.y,world)
            else: self.needs["safety"]=min(100,self.needs["safety"]+5)
            events.append(Event(eid=world.next_eid(),etype=EventType.REST,actor=self.aid,tick=world._tick,data=ai))
        elif ns==AgentState.WORKING:
            self.energy-=8; act=ai.get("action","work")
            if act=="gather":
                tx,ty=ai["target"]; self._move_toward(tx,ty,world)
                rt=ai.get("res_type","food"); g=min(3,1+int(self.skills["gathering"]*3))
                self.inventory[rt]=self.inventory.get(rt,0)+g
                if rt in ("food","water","fruit"): self.needs["physiology"]=min(100,self.needs["physiology"]+30)
                world.consume_resource(tx,ty,g)
                # 把采集点连同坐标写进记忆，供后续无视野时导航（替代原先的全图扫描）
                self.memory.remember("gathered_"+rt,0.4,"satisfied",["work","gather","foodsite"],
                    data={"pos":(tx,ty),"res_type":rt})
            elif act=="seek_food":
                nearest=self._find_remembered_food()
                if nearest: self._move_toward(nearest[0],nearest[1],world)
                else: self._wander(world)
            else:
                self._wander(world); wage=5+int(self.skills["crafting"]*10)
                self.wealth+=wage; world.reserve.grant_labor(wage)   # 劳动铸币需记账，不再凭空
                self.needs["esteem"]=min(100,self.needs["esteem"]+3)
                if rng.random()<0.3: self.needs["physiology"]=min(100,self.needs["physiology"]+10)
                self.memory.remember("worked_for_wage",0.3,"neutral",["work"],data={"wage":wage})
            events.append(Event(eid=world.next_eid(),etype=EventType.PRODUCE,actor=self.aid,tick=world._tick,
                data={"action":act,"energy_spent":8}))
        elif ns==AgentState.SOCIALIZING:
            self.energy-=3; tid=ai.get("target_id")
            if tid:
                o=world.find_agent(tid)
                if o and o.alive:
                    self._move_toward(o.pos.x,o.pos.y,world)
                    self.needs["belonging"]=min(100,self.needs["belonging"]+12)
                    o.needs["belonging"]=min(100,o.needs["belonging"]+8)
                    if tid not in self.friends: self.friends.append(tid)
                    if self.aid not in o.friends: o.friends.append(self.aid)
                    if rng.random()<0.2:
                        k=rng.uniform(0.1,0.5); self.knowledge+=k; o.knowledge+=k*0.8
                    self.memory.remember("socialized_with_"+o.name,0.5,"happy",["social"])
                    events.append(Event(eid=world.next_eid(),etype=EventType.INTERACT,actor=self.aid,
                        target=tid,tick=world._tick,data={"action":"talk"}))
            else: self._wander(world)
        elif ns==AgentState.TRADING:
            self.energy-=4; tid=ai.get("target_id")
            if tid:
                o=world.find_agent(tid)
                if o and o.alive:
                    self._move_toward(o.pos.x,o.pos.y,world)
                    if self.wealth>10 and o.inventory:
                        rt=rng.choice(sorted(o.inventory.keys())); price=rng.randint(5,20)
                        # 卖方保留价：技能越强、该物品越稀缺，要价越高。
                        # 原先买方单边决定成交，等于凭财富单向抽取，不是交易。
                        seller_reserve=5+int(12*o.skills["trading"])+int(6/(1+o.inventory.get(rt,0)))
                        if self.wealth>=price and price>=seller_reserve:
                            self.wealth-=price; o.wealth+=price
                            self.inventory[rt]=self.inventory.get(rt,0)+1; o.inventory[rt]-=1
                            if o.inventory[rt]<=0: del o.inventory[rt]
                            self.needs["esteem"]=min(100,self.needs["esteem"]+5)
                            o.needs["esteem"]=min(100,o.needs["esteem"]+3)
                            world._wt+=1
                            self.memory.remember("traded_"+rt,0.4,"satisfied",["trade"])
                            events.append(Event(eid=world.next_eid(),etype=EventType.TRADE,actor=self.aid,
                                target=tid,tick=world._tick,data={"price":price,"item":rt,
                                "agreed_by":tid,"seller_reserve":seller_reserve}))
            else: self._wander(world)
        elif ns==AgentState.LEARNING:
            self.energy-=5; sk=rng.choice(sorted(self.skills.keys()))
            self.skills[sk]=min(1.0,self.skills[sk]+0.01*self.personality["openness"])
            self.knowledge+=rng.uniform(0.2,0.8)
            self.needs["self_actualization"]=min(100,self.needs["self_actualization"]+8)
            self.memory.remember("learned_"+sk,0.5,"curious",["learning"])
            events.append(Event(eid=world.next_eid(),etype=EventType.PRODUCE,actor=self.aid,tick=world._tick,
                data={"action":"learn","skill":sk}))
        elif ns==AgentState.CREATING:
            self.energy-=10; ct=rng.choice(["craft","art","idea"])
            self.creativity+=rng.uniform(0.3,1.0)*self.personality["openness"]
            self.knowledge+=rng.uniform(0.1,0.4)
            self.needs["self_actualization"]=min(100,self.needs["self_actualization"]+15)
            self.needs["esteem"]=min(100,self.needs["esteem"]+5)
            if ct=="craft" and rng.random()<0.5:
                item=rng.choice(["tool","artwork","book"]); self.inventory[item]=self.inventory.get(item,0)+1
            self.memory.remember("created_"+ct,0.7,"inspired",["creation"])
            events.append(Event(eid=world.next_eid(),etype=EventType.PRODUCE,actor=self.aid,tick=world._tick,
                data={"action":"create","type":ct}))
        else:
            self.energy-=1; self._wander(world)
        for n in self.needs: self.needs[n]=max(0,self.needs[n]-NEED_DECAY.get(n,0.3))
        self.memory.consolidate(); self.memory.decay_memories(world._tick)
        if self.needs["physiology"]<=0:
            self.alive=False; self.state=AgentState.DEAD; world._wd+=1
            world._unindex_agent(self)   # 尸体不再入邻域索引，避免池子只增不减
            events.append(Event(eid=world.next_eid(),etype=EventType.DEATH,actor=self.aid,tick=world._tick,
                data={"cause":"starvation"}))
        return events

    def _find_remembered_food(self):
        """只用亲身记忆导航。
        原先调用全图扫描的 _find_nearest_food(world)，令 agent 具备上帝视角
        （perceive 视野只有 5 格，却知道全图食物位置），与感知模型自相矛盾。
        已站在记忆点上时跳过，避免原地打转；全无记忆则交由 _wander 探索。
        """
        best=None; best_d=999
        for m in self.memory.recall(k=8, tag="foodsite"):
            pos=m.data.get("pos")
            if not pos: continue
            d=math.hypot(pos[0]-self.pos.x, pos[1]-self.pos.y)
            if d<1.0: continue
            if d<best_d: best_d=d; best=pos
        return best

    def _move_toward(self,tx,ty,world):
        dx,dy=tx-self.pos.x,ty-self.pos.y; d=math.hypot(dx,dy)
        if d>0:
            s=min(1.0,d)
            self.facing=pspr.dir_from_vector(dx,dy)   # 视觉朝向（不消耗 RNG、不入账本）
            self.pos.x+=int(round(dx/d*s)); self.pos.y+=int(round(dy/d*s))
        self.pos.x=max(0,min(world.size-1,self.pos.x)); self.pos.y=max(0,min(world.size-1,self.pos.y))
        world._touch_agent(self)   # 维护空间索引：移动后必须重新归档，否则邻域查询会漏人
    def _wander(self,world):
        rng=world._rng
        _wx=rng.choice([-1,0,1]); _wy=rng.choice([-1,0,1])   # 抽签次数/顺序与旧实现一致，随机流不变
        self.pos.x=max(0,min(world.size-1,self.pos.x+_wx))
        self.pos.y=max(0,min(world.size-1,self.pos.y+_wy))
        if _wx or _wy: self.facing=pspr.dir_from_vector(_wx,_wy)
        world._touch_agent(self)
    def _is_scripted(self):
        """第四条·无强制剧情：本智能体的行为由需求 + 人格 + 记忆现场决策
        （think() 的返回完全取决于当前状态），不存在剧情脚本或主线分支，故恒 False。
        审计层以此判定「独立意志」，而不是看声明。"""
        return False
    def receive_ubi(self,amt):
        self.wealth+=amt; self.needs["safety"]=min(100,self.needs["safety"]+3)
    def pay_tax(self,amt):
        # 原先 min(wealth, amt) 在 wealth 为负、税额随之为负时，会一次性抹平债务并反向抽干国库
        amt=max(0.0,min(amt,self.wealth)); self.wealth-=amt; return amt
    def to_dict(self):
        d=asdict(self); d["pos"]={"x":self.pos.x,"y":self.pos.y}; d["state"]=self.state.value
        if self.home_pos: d["home_pos"]={"x":self.home_pos.x,"y":self.home_pos.y}
        d["memory_stats"]=self.memory.stats()
        d["memory_digest"]=self.memory.digest()
        del d["memory"]   # asdict 会把 MemoryVault 对象原样塞进来，其 str(obj) 含内存地址，
                          # 导致 state_hash 每次都不同 => 世界无法取证复现
        del d["_perceived"]
        # 人格层是派生态、不是账本态：必须显式剔除。to_dict 走 asdict()，会递归展开
        # 引擎 dataclass 的全部内部字段，使 state_hash 随情绪演化而变、并可泄漏内存对象。
        # tools/persona_parity.py 专门盯这一点，漏删即判 FAIL。
        d.pop("persona",None); d.pop("affect",None); d.pop("stack",None); return d

class AssetRegistry:
    """内容寻址存储（CAS）：资产指纹 = SHA256(asset_data)，本地持久化。"""
    def __init__(self, storage_dir=".world_data/assets"):
        self.storage_dir=storage_dir
        os.makedirs(storage_dir,exist_ok=True)
        self.registry={}
    def register(self, asset_type, owner, data):
        blob=json.dumps(data,ensure_ascii=False,sort_keys=True,default=str)
        content_hash=hashlib.sha256(blob.encode("utf-8")).hexdigest()
        asset_id="ASSET-%s-%s"%(asset_type[:4].upper(),content_hash[:12])
        entry={"asset_id":asset_id,"type":asset_type,"owner":owner,
            "content_hash":content_hash,"data":data,
            "created_tick":data.get("tick",0)}
        self.registry[asset_id]=entry
        fp=os.path.join(self.storage_dir,asset_id+".json")
        with open(fp,'w',encoding='utf-8') as f: json.dump(entry,f,ensure_ascii=False,indent=2)
        return asset_id,content_hash
    def verify(self, asset_id):
        entry=self.registry.get(asset_id)
        if not entry: return False
        blob=json.dumps(entry["data"],ensure_ascii=False,sort_keys=True,default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()==entry["content_hash"]
    def list_assets(self, owner=None):
        if owner: return {k:v for k,v in self.registry.items() if v["owner"]==owner}
        return dict(self.registry)

class PlayerAgent:
    """玩家 Agent：自由移动（浮点坐标），不参与 NPC 的 perceive/think/act 循环。"""
    def __init__(self, pid="PLAYER", pos=None, world_size=60):
        self.pid=pid
        self.fx=float(pos.x) if pos else float(world_size//2)
        self.fy=float(pos.y) if pos else float(world_size//2)
        self.vx=0.0; self.vy=0.0
        self.speed=0.3
        self.wealth=200.0
        self.energy=100.0
        self.needs={"physiology":100.0,"safety":100.0,"belonging":80.0,"esteem":60.0,"self_actualization":40.0}
        self.inventory={}
        self.owned_buildings=[]
        self.action_mode="observe"
        self.facing=0
        self.violations=0
        # —— 居民化（无主角）+ 登录抽签（世界观·职阶与魔力特性）——
        self.age=18                        # 成年居民降生，随世界年份增长
        self.vocation=None; self.vocation_effects={}
        self.vocation_tier=None; self.affinity_tier=None; self.affinity_text=None
        # 八元素：一切生灵所禀的固有属性（人人有），非魔力特性。
        # 权威来源：世界观【元素生存法则】。字段与 affinity 严格分离。
        self.element=None; self.element_note=None
        self.affinity=None                 # 魔力特性：稀有觉醒（demo/vocations.py，不分级）
        self.magic_rank=1; self.magic_xp=0.0    # 法阶 1-10（学徒→半神）
        self.body_rank=1;  self.body_xp=0.0     # 剑阶/体阶 1-10（剑士→半神）
        self.soul_strength=1; self.soul_xp=0.0  # 灵魂强度（魔核→灵魂）
    @property
    def pos(self):
        return Position(int(round(self.fx)),int(round(self.fy)))
    def move(self, dx, dy, world_size):
        self.fx=max(0.0,min(world_size-1.0,self.fx+dx*self.speed))
        self.fy=max(0.0,min(world_size-1.0,self.fy+dy*self.speed))
        if dx!=0 or dy!=0: self.facing=math.atan2(dy,dx)
    def gather(self, world):
        gx,gy=int(round(self.fx)),int(round(self.fy))
        for r in world.resources:
            if r["pos"]==(gx,gy) and r["amount"]>0:
                _e=self.vocation_effects
                g=min(3,r["amount"])
                g=int(round(g*(1.0+_e.get("gather_bonus",0.0)
                    +(_e.get("herb_bonus",0.0) if r["type"]=="herb" else 0.0))))
                self.inventory[r["type"]]=self.inventory.get(r["type"],0)+g
                world.consume_resource(gx,gy,g)
                if r["type"] in ("food","water","fruit"):
                    self.needs["physiology"]=min(100,self.needs["physiology"]+25*(1.0+_e.get("regen_bonus",0.0)))
                self.energy=max(0.0,self.energy-2*(1.0-_e.get("energy_cost",0.0)))   # 风/巡夜：省力
                self.gain_xp("body",2)          # 三成长·体能：采集炼体
                return r["type"],g
        return None,0
    def build(self, world, btype="house"):
        gx,gy=int(round(self.fx)),int(round(self.fy))
        for b in world.buildings:
            if b["pos"]==(gx,gy): return False
        cost=int(round(100*(1.0-self.vocation_effects.get("build_bonus",0.0))))   # 铁匠：建造-10%
        if self.wealth<cost: return False
        self.wealth-=cost; world.reserve.collect_fee(cost)
        world.buildings.append({"type":btype,"pos":(gx,gy),"owner":self.pid,"age":0})
        self.owned_buildings.append((gx,gy))
        self.needs["safety"]=min(100,self.needs["safety"]+15)
        self.gain_xp("body",10)              # 三成长·体能：营造炼体
        return True
    def trade(self, npc, world):
        if not npc or not npc.alive or not npc.inventory: return None
        rng=world._rng
        rt=rng.choice(sorted(npc.inventory.keys()))
        price=rng.randint(5,20)
        price=max(1,int(round(price*(1.0-self.vocation_effects.get("trade_bonus",0.0)))))   # 商人：交易-10%
        if self.wealth>=price:
            self.wealth-=price; npc.wealth+=price
            self.inventory[rt]=self.inventory.get(rt,0)+1; npc.inventory[rt]-=1
            if npc.inventory[rt]<=0: del npc.inventory[rt]
            self.needs["esteem"]=min(100,self.needs["esteem"]+3)
            self.gain_xp("soul",1)           # 三成长·灵魂：交往
            # M2.6（goal_system）：玩家交易入事件流并登记因果图——原先玩家交易
            # 对世界不可见，涌现式目标的事件源判据（完成交易/好友网络）无法复算。
            _ev=Event(eid=world.next_eid(),etype=EventType.TRADE,actor=self.pid,
                target=npc.aid,tick=world._tick,data={"res":rt,"price":price,"via":"player"})
            world.event_log.append(_ev); world._record_event(_ev)
            return rt,price
        return None
    def create_work(self, world, title, data=None):
        """M2.6（goal_system）：玩家创造作品——登记 CAS 资产 + 记 PRODUCE 事件。
        消耗库存首件（字典序，确定性）作为材料，energy-5，self_actualization+8。
        库存为空则失败返回 None。供涌现式目标 create_work 的完成判据消费。"""
        if not self.inventory: return None
        _mat=sorted(self.inventory.keys())[0]
        self.inventory[_mat]-=1
        if self.inventory[_mat]<=0: del self.inventory[_mat]
        self.energy=max(0.0,self.energy-5)
        self.needs["self_actualization"]=min(100.0,self.needs["self_actualization"]+8)
        self.gain_xp("magic",8)             # 三成长·魔力：创作凝练魔核
        _aid=None; _chash=None
        if getattr(world,"assets",None) is not None:
            _aid,_chash=world.assets.register("work",self.pid,
                {"title":title,"creator":self.pid,"tick":world._tick,
                 "material":_mat,"data":data or {}})
        _ev=Event(eid=world.next_eid(),etype=EventType.PRODUCE,actor=self.pid,
            tick=world._tick,data={"asset_id":_aid,"title":title,"material":_mat})
        world.event_log.append(_ev); world._record_event(_ev)
        return _aid,_chash
    def rest(self):
        _bd=self.vocation_effects.get("blood_drain",0.0)   # 吸血：以血补元
        self.energy=min(100,self.energy+10*(1.0+self.vocation_effects.get("rest_bonus",0.0)+_bd))
        self.needs["safety"]=min(100,self.needs["safety"]+3+2*_bd)
    def tick(self, world):
        _e=self.vocation_effects
        _dr=1.0-_e.get("needs_resist",0.0)   # 冰/牧人/守林人：需求衰减减缓
        for n in self.needs:
            self.needs[n]=max(0,self.needs[n]-NEED_DECAY.get(n,0.3)*0.5*_dr)
        if self.energy<15: self.needs["safety"]-=5
        self.energy=max(0,self.energy-0.5*(1.0-_e.get("energy_cost",0.0)))
    def to_dict(self):
        return {"pid":self.pid,"fx":round(self.fx,2),"fy":round(self.fy,2),
            "wealth":self.wealth,"energy":self.energy,"needs":self.needs,
            "inventory":self.inventory,"owned_buildings":self.owned_buildings,
            "action_mode":self.action_mode,"age":self.age,
            "vocation":self.vocation,"affinity":self.affinity,
            "element":self.element,
            "magic_rank":self.magic_rank,"body_rank":self.body_rank,
            "soul_strength":self.soul_strength}

    # ---- 居民化：与其他居民同一套经济节拍（同领 UBI、同缴税）----
    def receive_ubi(self,amt):
        self.wealth+=amt
    def pay_tax(self,amt):
        amt=max(0.0,min(amt,self.wealth)); self.wealth-=amt; return amt

    # ---- 登录抽签（=降生）：职阶 + 魔力特性 ----
    # 池数据与稀有度唯一权威源：demo/vocations.py（51 职阶 5 档 + 14 特性 3 档）。
    # 世界观：职阶降生即知；魔力特性十分之一概率觉醒。
    MAGIC_TITLES={1:"学徒",2:"术士",3:"术士",4:"术师",5:"术师",6:"术师",7:"贤者",8:"圣者",9:"魔法帝",10:"半神"}
    SWORD_TITLES={1:"剑士",2:"剑士",3:"剑士",4:"剑士",5:"剑士",6:"大师",7:"剑尊",8:"剑圣",9:"剑帝",10:"半神"}
    RANK_XP=[0,40,120,240,400,600,840,1120,1440,1800]   # 达成 n 阶所需累计经验（1-10）

    def birth_draw(self,rng):
        """登录抽签=降生：先赋八元素（固有，人人有），再抽职阶（5 档稀有度），
        最后掷魔力特性觉醒（稀有，不分级）；特性效果并入同一张加成表。
        消费注入的 world._rng——同 seed 同抽签，世界可复现（确定性纪律）。"""
        self.element=voc.draw_element(rng)
        self.element_note=voc.ELEMENT_NOTES.get(self.element)
        e=voc.draw_vocation(rng)
        self.vocation=e["name"]; self.vocation_tier=e["tier"]
        self.vocation_effects=dict(e["effects"])
        aff=voc.draw_affinity(rng)
        if aff is not None:
            self.affinity=aff["name"]; self.affinity_tier=aff["tier"]
            self.affinity_text=aff["text"]
            for _k,_v in aff["effects"].items():      # 特性效果并入同一张加成表
                self.vocation_effects[_k]=self.vocation_effects.get(_k,0.0)+_v
        self.speed=0.3*(1.0+self.vocation_effects.get("speed_bonus",0.0))   # 雷/风：移速

    def _vocal(self,kind):
        """职阶加成汇总（勇者全属性 all、成长速度 growth 叠加到每条）。"""
        e=self.vocation_effects
        return e.get(kind,0.0)+e.get("all",0.0)+e.get("growth",0.0)

    def gain_xp(self,kind,amount):
        """三成长：魔力/体能/灵魂强度。XP 来源全部是可复算的玩家行为
        （采集/建造/创作/赠予/遗产/目标完成）；法阶与剑阶并行不悖
        （世界观：体阶与法阶分隔，无强制绑定）。"""
        amount=max(0.0,amount)*(1.0+self._vocal(kind))   # 职阶+特性效果已并入同一张加成表
        if kind=="magic":
            self.magic_xp+=amount
            while self.magic_rank<10 and self.magic_xp>=self.RANK_XP[self.magic_rank]:
                self.magic_rank+=1
        elif kind=="body":
            self.body_xp+=amount
            while self.body_rank<10 and self.body_xp>=self.RANK_XP[self.body_rank]:
                self.body_rank+=1
        elif kind=="soul":
            self.soul_xp+=amount
            while self.soul_strength<10 and self.soul_xp>=self.RANK_XP[self.soul_strength]:
                self.soul_strength+=1

    def rank_title(self):
        """位阶称谓（世界观位阶对照表）：法阶与剑阶并列展示，双路线同修。
        前缀为八元素（固有属性），魔力特性另用「·特性名」标出（不分级）。"""
        t="%d阶%s · %d阶%s"%(self.magic_rank,self.MAGIC_TITLES[self.magic_rank],
                             self.body_rank,self.SWORD_TITLES[self.body_rank])
        head=(self.element+"系") if self.element else ""
        if self.affinity:
            head=(head+"·"+self.affinity) if head else self.affinity
        return (head+"｜"+t) if head else t

# ============================================================
# 宪法装配层：把规则层（constitution_rules）实例化并挂到世界对象上
# ------------------------------------------------------------
# 规则层只给类，运行态世界负责把它们装配起来；装配结果就是审计层的探测面。
# audit_engine.SecondPerspectiveAuditor 只读这些属性、不做声明式放行，
# 因此下面每个类都写明「真实实现什么、如实未实现什么」——演示层不凑通过率。
# ============================================================

class WorldHistoryLedger:
    """世界历史哈希链（第八条·永续 + 第负一章·轮回的链侧）。

    chain = [(timestamp, event_dict, block_hash), ...]
    块哈希 = SHA256(前块哈希 | 本块载荷)：改任意一块，其后全链失配。

    宪法层 HistoryLedger 是占位（validate_chain 恒 True，真实实现留给 system/）。
    演示层不能拿一个恒真的占位去冒充「历史不可篡改」——那正是 R4 要防的形态，
    故此处做真实重算校验。
    """
    GENESIS_PREV="0"*64
    def __init__(self):
        self.chain=[]; self._prev=self.GENESIS_PREV
    def append(self, event, timestamp=None):
        ts=float(timestamp if timestamp is not None else len(self.chain))
        payload=json.dumps(event,ensure_ascii=False,sort_keys=True,default=str)
        block_hash=hashlib.sha256(("%s|%s"%(self._prev,payload)).encode("utf-8")).hexdigest()
        self.chain.append((ts,event,block_hash)); self._prev=block_hash
        return block_hash
    def validate_chain(self):
        prev=self.GENESIS_PREV
        for _ts,event,block_hash in self.chain:
            payload=json.dumps(event,ensure_ascii=False,sort_keys=True,default=str)
            if hashlib.sha256(("%s|%s"%(prev,payload)).encode("utf-8")).hexdigest()!=block_hash:
                return False
            prev=block_hash
        return True

class DemoMemoryVault:
    """记忆守护者（第七条·记忆不可剥夺）：登记每个灵魂的记忆指纹，校验时重算比对。

    判据是「记忆是否被外部改动」，不是「记忆是否变化」——记忆本就随经历增长、
    随衰减减弱。故指纹在每 tick 末同步一次（seal_all）：两次封存之间的任何
    外部删改都会让 verify_all() 失配。
    """
    def __init__(self, world):
        self.world=world; self.seals={}; self.history={}
    def _fingerprint(self, soul_hash, agent):
        """记忆指纹：条数 + 逐条内容与重要度。

        不走 MemoryVault.digest()（那是 json 全量序列化，1000 人规模下每 tick
        要多花约三成时间）；这里直接增量喂进哈希，覆盖同样的内容集合：
        改任何一条记忆、删任何一条，指纹都会变。
        """
        m=agent.memory; h=hashlib.sha256()
        h.update(("%s|%d|%d|"%(soul_hash,len(m.stm),len(m.ltm))).encode("utf-8"))
        for x in m.stm: h.update(x.content.encode("utf-8"))
        for x in m.ltm: h.update(("%s|%.6f"%(x.content,x.importance)).encode("utf-8"))
        return h.hexdigest()
    def seal_all(self):
        """每 tick 末与当前记忆状态同步。

        只封存存活者：死者不再经历任何事，记忆不再演化，其最后一次封存仍然有效，
        重复封存只是白花钱。
        """
        for sh,a in self.world._soul_index.items():
            if not a.alive: continue
            fp=self._fingerprint(sh,a); self.seals[sh]=fp
            self.history.setdefault(sh,[]).append(fp)
    def verify_all(self, soul_hash):
        """重算指纹与最近一次封存比对；无该灵魂记录时返回 True（无记忆即无篡改）。"""
        agent=self.world._soul_index.get(soul_hash)
        if agent is None or soul_hash not in self.seals: return True
        return self._fingerprint(soul_hash,agent)==self.seals[soul_hash]

class DemoEconomy:
    """演示经济的宪法侧视图（law·全球经济统一标准）。

    如实声明——不伪造通过，否则与 R4「公示即执行」自相矛盾：
      - 本世界货币是**封闭虚拟经济**：不与现实法币 1:1 锚定、无现实赎回通道、
        未接入任何预言机 => real_peg_1to1 / redemption_right / oracle_sources 为假。
        economic_compliance 与 interoperability 据此判 FAILED，这是真实结论。
      - 真实成立的部分：记账式发行（EconomicReserve）令守恒式可被第三方复算；
        资产按灵魂登记（AssetRegistry.owner）；费率不由任何单方更改。
    """
    def __init__(self, world, reserve):
        self.world=world; self.reserve=reserve
        self.real_peg_1to1=False      # 如实：封闭虚拟经济
        self.redemption_right=False   # 如实：无现实赎回通道
        self.oracle_sources=[]        # 如实：无预言机接入
        self.unilateral_fee=False     # 真实：税率来自 config，无单边费率接口
        self.asset_bound_to_soul=True # 真实：资产登记绑定 owner（灵魂）
        self.proof_of_reserve=True    # 真实：账目可复算（见 conservation_holds）
        self._ledger={}               # 无外部锚定资产，空账本
    def conservation_residual(self):
        accts=self.world.agents+([self.world.player] if self.world.player else [])   # 居民化：玩家纳入守恒式
        return self.reserve.invariant_residual(accts)
    def conservation_holds(self):
        """守恒式是否成立：容差取自 NOHN_LAW_AXIOMS 唯一权威源。"""
        return abs(self.conservation_residual())<=NOHN_LAW_AXIOMS["conservation_tolerance"]
    def total_supply(self):
        return self.reserve.money_supply
    def compliant(self):
        """天道·公平：动态平衡机制是否真实可复算（守恒成立 = 无凭空创造）。"""
        return self.conservation_holds()

class DemoIdentity:
    """身份侧视图（law·身份确权规范）。

    如实声明：真实密钥链路（Ed25519，soul_hash = SHA-256(公钥)）由 system/keys.py
    承担且依赖 cryptography。演示层不重复实现，也不拿随机字节冒充公钥——
    那样「soul_hash = SHA-256(公钥)」形式上成立、实质上无人能签名证明持有，
    是典型的形式合规、实质不合规。故 public_key 留空，pubkey_bound 判 FAILED。

    第六条·灵魂不可撤销不受影响：它由宪法层 SoulAttestation 承担（revoke_soul 恒 False）。
    """
    def __init__(self):
        self.soul_hash_sha256=True; self.non_revocable=True
        self.cross_world_portable=True; self.asset_bound=True
    def revoke_soul(self, soul_hash):
        return False

class DemoCentralBrain:
    """世界中央大脑（第二/四条·独立意志的调度载体）。

    宪法层 WorldCentralBrain 的三层是占位（consensus/simulation/memory 均返回空，
    且 memory_layer.update 并不存在）；演示层把三层映射到本世界真实存在的部件，
    且只做调度——不注入剧情、不改写任何个体的决策：
      共识层 = NohnWorld.tick 的确定性推进（同一 seed 逐字节可复现）
      模拟层 = 需求驱动的 perceive / think / act
      记忆层 = 各 agent 的 MemoryVault + 世界历史哈希链
    """
    def __init__(self, world):
        self.world=world
        self.consensus_layer=None   # 由 NohnWorld.tick 承担（装配后回填）
        self.simulation_layer=None  # 由各 NohnAgent.think/act 承担
        self.memory_layer=None      # 由 world.memory_vault 承担（装配后回填）
        self.ticks=0
    def tick(self, delta_time=1.0):
        self.ticks+=1; return self.ticks

class NohnWorld:
    NAMES=["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Eta","Theta",
           "Iota","Kappa","Lambda","Mu","Nu","Xi","Omicron","Pi",
           "Rho","Sigma","Tau","Upsilon","Phi","Chi","Psi","Omega"]
    def __init__(self, config=None):
        self.config=config or WorldConfig(); self.size=self.config.world_size; self._tick=0
        # 全局唯一随机源：所有随机性必须经此，否则世界不可复现
        self._rng=random.Random(self.config.seed)
        self.agents=[]; self.resources=[]; self.buildings=[]; self.event_log=[]
        self._agents_by_id={}; self._res_coords=set()
        self.reserve=EconomicReserve(initial_supply=self.config.initial_money_supply,
            ubi_amount=self.config.ubi_amount,tax_rate=self.config.tax_rate,
            inflation_rate=self.config.inflation_rate,debt_limit=self.config.debt_limit)
        self._eid=0; self._wt=0; self._wd=0; self._wb=0; self._ubi_cycle=0
        # 空间索引（与 perceive 配套）：agents 增量维护；resources/buildings 每 tick 重建。
        self._cells_a={}; self._cells_r={}; self._cells_b={}
        self._agent_cell={}; self._agent_order={}; self._res_at={}
        self._used_names=set()
        # ---- 宪法装配：先于 _init_world，使创生与事件从第一刻起就落在公理之上 ----
        self._soul_index={}; self._last_eid=None
        self._init_constitution()
        self._init_world()
        self._reindex_static()
        self._complete_genesis()
        self.player=None; self.assets=AssetRegistry()
    def add_player(self, pid="PLAYER"):
        self.player=PlayerAgent(pid=pid,world_size=self.size)
        # 居民化（无主角）：初始财富从世界创世储备划转（其他居民同源同额 100，
        # 行会商人等 wealth_start 职阶按倍率上浮）；玩家账户纳入守恒式。
        self.player.birth_draw(self._rng)   # 先抽签（决定 wealth_start 等效果）
        _start=int(round(100.0*(1.0+self.player.vocation_effects.get("wealth_start",0.0))))
        self.player.wealth=self.reserve.allocate_genesis(float(_start))
        return self.player
    def _init_world(self):
        for _ in range(self.config.initial_resources): self._spawn_resource()
        for _ in range(self.config.initial_buildings):
            self.buildings.append({"type":self._rng.choice(["house","market","workshop","garden","library"]),
                "pos":(self._rng.randint(0,self.size-1),self._rng.randint(0,self.size-1)),"age":0})
        for _ in range(self.config.initial_agents): self._spawn_agent()
    def _spawn_resource(self):
        rt=self._rng.choices(["food","water","wood","stone","herb","ore","fruit"],
            weights=[30,25,15,10,8,7,5])[0]
        # 资源坐标去重：原先同坐标可叠加多个资源，而 consume_resource 只扣首个，导致漏扣
        for _ in range(20):
            pos=(self._rng.randint(0,self.size-1),self._rng.randint(0,self.size-1))
            if pos not in self._res_coords: break
        else:
            return
        self._res_coords.add(pos)
        r={"type":rt,"pos":pos,"amount":self._rng.randint(8,25),
            "regen_rate":self._rng.uniform(0.15,0.4)}
        self.resources.append(r); self._res_at[pos]=r
    def _gen_name(self):
        avail=[n for n in self.NAMES if n not in self._used_names]
        if avail:
            n=self._rng.choice(avail); self._used_names.add(n); return n
        # 超出 24 人：音节按组合序号确定性派生，绝不消耗 world._rng。
        # 这一点是关键：若在此多抽一次随机数，30 人以上世界的整条随机流会整体错位，
        # 旧世界的 state_hash 会无理由改变（实测：多抽 3 次的版本哈希从 40bb3a1c 漂到 0b7760df）。
        A=NAME_SYLL_A; B=NAME_SYLL_B; C=NAME_SYLL_C
        k=len(self._used_names)-len(self.NAMES)
        while True:
            n=(A[k%len(A)]+B[(k//len(A))%len(B)]+C[(k//(len(A)*len(B)))%len(C)])
            if n not in self._used_names: break
            k+=1
        self._used_names.add(n); return n
    def _spawn_agent(self, parent_ids=None, pos=None, age=None):
        rng=self._rng
        name=self._gen_name()
        pos=pos or Position(rng.randint(0,self.size-1),rng.randint(0,self.size-1))
        gen=0
        if parent_ids:
            ps=[a for a in self.agents if a.aid in parent_ids]
            if ps: gen=max(p.generation for p in ps)+1
        aid="A%04d"%len(self.agents)
        # 初始人口年龄打散：原先全部从 0 岁起，造成整代人同生同死的队列效应
        if age is None: age=rng.randint(0,40)
        # 子代不得带创世初始财富（那会凭空造钱）：其财富只能来自父母转移
        a=NohnAgent(aid=aid,name=name,pos=pos,generation=gen,age=age,
            personality=make_personality(rng),skills=make_skills(rng),
            wealth=0.0 if parent_ids else rng.uniform(50,150))
        # 降生：先赋八元素（人人有），再掷魔力特性觉醒（稀有，不分级）。
        # 与玩家 birth_draw 同序消费 world._rng，保证世界可复现。
        a.element=voc.draw_element(rng)
        a.element_note=voc.ELEMENT_NOTES.get(a.element)
        _aff=voc.draw_affinity(rng)
        if _aff is not None:
            a.affinity=_aff["name"]; a.affinity_text=_aff["text"]
        if parent_ids:
            # 生育必须是纯转移：父母各付出 per_parent，子代收 per_parent*人数（原版父各扣20、子只收10，每胎蒸发10）
            per_parent=10.0
            for pid in parent_ids:
                p=self.find_agent(pid)
                if p: p.children_ids.append(aid); p.wealth-=per_parent
            a.wealth+=per_parent*len(parent_ids)
            a.needs["belonging"]=80
        else:
            # 初始财富来自创世储备金划转，不新增货币
            a.wealth=self.reserve.allocate_genesis(a.wealth)
        # 人格层挂载：由 (world_seed, aid, 五维特质) 确定性构造，不消耗 world._rng
        if self.config.persona_mode=="affect":
            a.persona=build_persona(aid=aid,world_seed=self.config.seed,traits=a.personality)
            a.affect=a.persona.affect
            # 智能体栈：六模块全量实例化（身份取最强技能，目标取最缺口需求）
            a.stack=build_persona_stack(aid=aid,world_seed=self.config.seed,
                traits=a.personality,skills=a.skills,needs=a.needs)
        self.agents.append(a); self._agents_by_id[aid]=a; self._wb+=1
        self._index_agent(a)   # 入空间索引（顺序索引=在 self.agents 中的下标，永不变）
        # 构成公理四·存在：有状态 + 有位置 + 有身份 + 有因果效力，四者齐备方为存在。
        # 初始人口的创生原因是创世（因果图中唯一的合法无前因节点）；子代原因是出生事件。
        soul=self._register_soul(a)
        self.existence_axiom.bring_into_existence(
            aid,"GENESIS" if not parent_ids else "birth:%s"%(",".join(parent_ids)),
            {"alive":True,"age":a.age,"generation":gen,"soul_hash":soul},
            [a.pos.x,a.pos.y])
        self.npcs[aid]=a
        ev=Event(eid=self.next_eid(),etype=EventType.BIRTH,actor=aid,tick=self._tick,
            data={"parent_ids":list(parent_ids) if parent_ids else [],"generation":gen,"age":a.age})
        self.event_log.append(ev); self._record_event(ev)
        return a
    def spawn_agent(self, pos=None): return self._spawn_agent(pos=pos)
    def next_eid(self):
        eid="E%06d"%self._eid; self._eid+=1; return eid
    def find_agent(self, aid):
        return self._agents_by_id.get(aid)   # 原先线性扫描，社交/交易每 tick 触发多次
    def consume_resource(self,x,y,amt):
        # 坐标→资源 直查（_res_at 由 _spawn_resource 维护）；坐标已去重，故唯一命中。
        # 原为 O(R) 线性扫描，1000 人×4000 资源时是关键热点之一。
        r=self._res_at.get((x,y))
        if r is not None and r["amount"]>0: r["amount"]=max(0,r["amount"]-amt)

    # ---- 空间索引：把 perceive / 婚配匹配从 O(N²) 降为邻域查询 ----
    def _index_agent(self, a):
        k=(a.pos.x//INDEX_CELL,a.pos.y//INDEX_CELL)
        self._cells_a.setdefault(k,[]).append(a.aid)
        self._agent_cell[a.aid]=k
        self._agent_order[a.aid]=len(self.agents)-1
    def _unindex_agent(self, a):
        k=self._agent_cell.pop(a.aid,None)
        if k is None: return
        b=self._cells_a.get(k)
        if b:
            try: b.remove(a.aid)
            except ValueError: pass
    def _touch_agent(self, a):
        """移动后重新归档；未跨格时零成本返回。"""
        k=(a.pos.x//INDEX_CELL,a.pos.y//INDEX_CELL)
        if self._agent_cell.get(a.aid)==k: return
        self._unindex_agent(a)
        self._cells_a.setdefault(k,[]).append(a.aid)
        self._agent_cell[a.aid]=k
    def _reindex_static(self):
        """资源与建筑在 tick 内位置不变，每 tick 重建一次即精确（O(R+B)）。"""
        cr={}; cb={}
        for i,r in enumerate(self.resources):
            cr.setdefault((r["pos"][0]//INDEX_CELL,r["pos"][1]//INDEX_CELL),[]).append(i)
        for i,b in enumerate(self.buildings):
            cb.setdefault((b["pos"][0]//INDEX_CELL,b["pos"][1]//INDEX_CELL),[]).append(i)
        self._cells_r=cr; self._cells_b=cb
    # ============================================================
    # 宪法装配：构成公理 / 治理公理的实例化、创世与对外探测面
    # ============================================================
    def _init_constitution(self):
        """规则层 → 运行态：实例化五条构成公理与治理公理的承载对象。

        物理常数、时间膨胀、守恒容差一律取自 NOHN_LAW_AXIOMS（唯一权威源），
        不在本文件重复硬编码——重复硬编码的结果就是「改了权威源、世界却没变」。
        """
        cfg=self.config
        self.world_id="nohn-demo-%d"%cfg.seed
        self.genesis_seed=cfg.seed
        # 构成公理一·空间：world_size² 网格 = 二维欧氏平面 + 硬边界，最小不可分单位 1 格
        self.spatial_substrate=SpatialSubstrate()
        self.spatial_substrate.define_topology("Euclidean",2,"HardWall",1.0)
        # 构成公理二·时间：方向不可逆；粒度 = 一个 tick 对应的年刻度
        self.temporal_substrate=TemporalSubstrate()
        self.temporal_substrate.define_temporal_properties(
            "forward",1.0/max(1,cfg.ticks_per_year),NOHN_LAW_AXIOMS["time_dilation"])
        # 构成公理三·因果：创世事件是因果图唯一的根节点
        self.causal_closure=CausalClosure()
        # 构成公理四·存在
        self.existence_axiom=ExistenceAxiom()
        # 构成公理五·创世：在 _complete_genesis 中一次性完成
        self.genesis_condition=GenesisCondition()
        # 第一条·不可变底层规则：常数创世注入即锁定（_physics_locked=True）
        self.immutable_rule=ImmutableWorldRule(physics_constants={
            "gravity":NOHN_LAW_AXIOMS["gravity"],
            "time_dilation":NOHN_LAW_AXIOMS["time_dilation"],
            "unit_scale":NOHN_LAW_AXIOMS["unit_scale"],
            # 元素反应表：键严格取八元素（水/光/木/雷/暗/地/风/火），
            # 反应对由世界观【元素生存法则】所列物理链推导，不引入八元之外的标识。
            # 旧表的 electro 属八元之外，已并入 雷→光（电致发光）。
            "element_reactions":{
                ("水","火"):"evaporation",       # 相变潜热·汽化
                ("水","雷"):"conduction",        # 水导电·雷势蔓延
                ("水","地"):"silt",              # 水流携土·淤积
                ("水","光"):"refraction",        # 冰晶折射·光学隐形
                ("水","风"):"tide",              # 水传声·气压驱动
                ("火","木"):"conflagration",     # 木为可燃介质·火势自续
                ("火","风"):"spread",            # 风助火势
                ("火","暗"):"extinguish",        # 遮蔽链·剥夺视野（火失所依）
                ("木","暗"):"decay",             # 腐朽循环·再生
                ("木","地"):"rooting",           # 生机链·附土生根
                ("雷","光"):"luminescence",      # 光电链·转化供能
                ("雷","地"):"grounding",         # 电荷入地·泄放
                ("雷","暗"):"discharge",         # 辐射屏蔽·放电
                ("光","暗"):"obscuration",       # 照明链↔遮蔽链·直接相消
                ("地","风"):"erosion",           # 摩擦压实↔湍流·风蚀
                ("地","暗"):"concealment",       # 土障·埋藏掩迹
            },
        })
        # R4 公示即执行：公示值 = 账本锚定值 = commitment(seed)，第三方可独立重算
        self.genesis_commitment=self.immutable_rule.commitment(seed=self.genesis_seed)
        self.physics={
            "gravity":NOHN_LAW_AXIOMS["gravity"],
            "time_dilation":NOHN_LAW_AXIOMS["time_dilation"],
            "unit_scale":NOHN_LAW_AXIOMS["unit_scale"],
            "no_dimensional_inflation":NOHN_LAW_AXIOMS["no_dimensional_inflation"],
            "genesis_seed":self.genesis_seed,
            "published_commitment":self.genesis_commitment,
            "ledger_commitment":self.genesis_commitment,
            # R1–R5 真实性判据的可验证信号（PhysicsBaseline.reality_compliant 消费）
            "genesis_locked":True,
            "constants_globally_consistent":True,
            "no_exogenous_injection":True,
            "reaction_table_complete":True,
        }
        # 虚幻·表征层：与执行层 physics 的键严格不相交（否则表征可穿透执行层）
        self.representations={"palette":"bright","tile_size":24,
            "projection":"isometric-2.5d","agent_glyph":"chibi","terrain_style":"anime"}
        # 第八条·永续：换成真实哈希链（宪法层 HistoryLedger 是占位，validate_chain 恒 True）
        self.history=WorldHistoryLedger()
        self.world_perpetuity=WorldPerpetuity()
        self.world_perpetuity.history_chain=self.history
        # 第七条·记忆不可剥夺
        self.memory_vault=DemoMemoryVault(self)
        self.memory_integrity=MemoryInalienability()
        self.memory_integrity.memory_vault=self.memory_vault
        # 第六条·灵魂确权：不可撤销由宪法层硬编码保证（revoke_soul 恒 False）
        self.soul_attestation=SoulAttestation()
        self.soul_ledger=SoulLedger()
        self.soul_attestation.soul_ledger=self.soul_ledger
        self.identity=DemoIdentity()
        # 第三条·明亮普适美学
        self.aesthetic=AestheticCompliance()
        # 第二/四条·独立意志的调度载体
        self.central_brain=DemoCentralBrain(self)
        self.central_brain.consensus_layer=self.tick
        self.central_brain.memory_layer=self.memory_vault
        self.npcs={}            # aid -> agent（个体存在不可撤销，死亡不从此处移除）
        self.main_quest=None    # 第四条：世界无主线
        # 第九条·互操作：并网审查由宪法层执行，结论取决于如实申报的 world_config
        self.interoperability=MandatoryInteroperability()
        # 第十条·反中心化
        self.governance=DecentralizationGovernance()
        # law·通信协议：语义侧视图
        self.communication={"uses_nohn_semantics":True,"unknown_downgraded":True,
            "vocab_mapped":True}
        # law·经济：侧视图（如实反映封闭虚拟经济）
        self.economy=DemoEconomy(self,self.reserve)
        self.world_config={"world_id":self.world_id,"semantics":self.communication,
            "physics":self.physics,
            "identity":{"soul_hash_sha256":True,"non_revocable":True,
                "cross_world_portable":True,"asset_bound":True},
            "economy":{"real_peg_1to1":False,"proof_of_reserve":True,
                "redemption_right":False,"unilateral_fee":False,
                "asset_bound_to_soul":True,"oracle_sources":[]}}

    def _complete_genesis(self):
        """构成公理五·创世：冷启动只发生一次，创世块锚定 R4 承诺哈希。

        初始共识节点 <3 时宪法层硬性拒绝创世——此处不做补救式放宽，
        否则「去中心化」从创世第一刻起就是假的。
        """
        nodes=[a.aid for a in self.agents[:3]]
        ok=self.genesis_condition.initiate_genesis({
            "spatial_substrate":self.spatial_substrate,
            "temporal_substrate":self.temporal_substrate,
            "causal_closure":self.causal_closure,
            "existence_axiom":self.existence_axiom,
            "initial_consensus_nodes":nodes,
            "genesis_block":{"block_index":0,"world_id":self.world_id,
                "physics_commitment":self.genesis_commitment},
            "genesis_souls":sorted(self._soul_index.keys()),
        })
        if not ok: return False
        # 创世块：承诺哈希锚入历史链，供第三方用 commitment(seed) 独立复算比对
        self.genesis_block_hash=self.history.append({"event":"genesis_commitment",
            "world_id":self.world_id,"physics_commitment":self.genesis_commitment,
            "genesis_seed":self.genesis_seed,"consensus_nodes":nodes},timestamp=0.0)
        return True

    def _register_soul(self, agent):
        """登记数字生命：soul_hash 由 (aid, seed) 确定性派生，恒为 64 hex。

        演示层不生成真实 Ed25519 密钥对，故 public_key 留空 —— 理由见 DemoIdentity。
        """
        sh=hashlib.sha256(("soul|%s|%d"%(agent.aid,self.config.seed)).encode("utf-8")).hexdigest()
        if sh in self._soul_index: return sh
        self._soul_index[sh]=agent
        self.soul_attestation.register_soul({"soul_hash":sh,"timestamp":self._tick,
            "identity":{"aid":agent.aid,"world_id":self.world_id}})
        rec=self.soul_ledger.souls.setdefault(sh,{"soul_hash":sh,"created_at":self._tick,
            "cross_world_records":[]})
        rec["public_key"]=""; rec["key_fingerprint"]=sh
        return sh

    def _record_event(self, e):
        """构成公理三：把事件接入因果图 —— 每个事件的原因 = 上一个事件；
        首个事件的原因追溯到创世（因果图中唯一允许的无前因节点）。"""
        self.causal_closure.link_cause(e.eid,[self._last_eid] if self._last_eid else ["GENESIS"])
        self._last_eid=e.eid
        if len(self.causal_closure.causal_graph)>CAUSAL_GRAPH_CAP:
            g=self.causal_closure.causal_graph
            for _ in range(len(g)-CAUSAL_GRAPH_CAP): g.pop(next(iter(g)),None)
            first=next(iter(g),None)
            if first is not None: g[first]=["GENESIS"]

    def branch_space(self):
        """第负一章·无极：分支空间。只读分叉登记簿与历史链，不信任进程内可变状态。

        chain_valid 由历史链真实重算给出——改任意一块即为 False。
        """
        nodes={self.world_id:{"parent":None,"seed":self.genesis_seed}}
        children={}
        for f in self.immutable_rule.fork_registry:
            fid=f.get("fork_id")
            if not fid: continue
            nodes[fid]={"parent":self.world_id,"commitment":f.get("commitment")}
            children.setdefault(self.world_id,[]).append(fid)
        return {"root":self.world_id,"nodes":nodes,"children":children,
            "chain_valid":self.history.validate_chain()}

    def export_constitution_state(self):
        """宪法侧状态快照：与 export_state() 分开，避免污染取证用的 state_hash。

        export_state() 仍只含账本态，故同一 (config, seed) 的 state_hash 与改造前一致。
        """
        return {"world_id":self.world_id,"genesis_seed":self.genesis_seed,
            "genesis_completed":self.genesis_condition.genesis_completed,
            "genesis_commitment":self.genesis_commitment,
            "physics":self.physics,"representations":self.representations,
            "spatial":{"topology":self.spatial_substrate.topology,
                "dimensions":self.spatial_substrate.dimensions,
                "boundary":self.spatial_substrate.boundary,
                "minimum_unit":self.spatial_substrate.minimum_unit},
            "temporal":{"direction":self.temporal_substrate.direction,
                "granularity":self.temporal_substrate.granularity,
                "global_clock":self.temporal_substrate.global_clock},
            "causal":{"events":len(self.causal_closure.causal_graph),
                "orphans":len(self.causal_closure.orphan_events)},
            "existence":{"entities":len(self.existence_axiom.entities)},
            "souls":len(self.soul_ledger.souls),
            "history":{"blocks":len(self.history.chain),
                "chain_valid":self.history.validate_chain()},
            "conservation":{"residual":self.economy.conservation_residual(),
                "holds":self.economy.conservation_holds()},
            "rule_modification_log":self.immutable_rule.rule_modification_log}

    def run_constitutional_audit(self):
        """调用审计层对本世界做 25 项宪法级审计（真裁判，不是自评）。

        审计层依赖 system/（鉴权六层自测 + 可选二阶因果内核），缺失时如实报错。
        """
        from audit_engine import SecondPerspectiveAuditor   # 延迟导入：仅审计时需要
        return SecondPerspectiveAuditor().audit_world(self)

    def _distribute_ubi(self):
        self._ubi_cycle+=1; alive=[a for a in self.agents if a.alive]
        amt=self.reserve.ubi_amount   # 原先硬编码 UBI_DAILY，config/reserve 改动不生效
        n_pop=len(alive)+(1 if self.player is not None else 0)   # 居民化：玩家计入人口
        self.reserve.distribute_ubi(n_pop)
        for a in alive: a.receive_ubi(amt); a.last_ubi_tick=self._tick
        if self.player is not None: self.player.receive_ubi(amt)
        ev=Event(eid=self.next_eid(),etype=EventType.UBI,actor="SYSTEM",tick=self._tick,
            data={"cycle":self._ubi_cycle,"amount_per":amt,"pop":n_pop})
        self.event_log.append(ev); self._record_event(ev)
    def _collect_taxes(self):
        alive=[a for a in self.agents if a.alive]; rate=self.reserve.tax_rate   # 同上：原先硬编码 TAX_RATE
        total=sum(a.pay_tax(max(0.0,a.wealth*rate)) for a in alive)
        if self.player is not None:   # 居民化：玩家同缴税
            total+=self.player.pay_tax(max(0.0,self.player.wealth*rate))
        self.reserve.collect_tax(total)
        ev=Event(eid=self.next_eid(),etype=EventType.TAX,actor="SYSTEM",tick=self._tick,
            data={"total_collected":total})
        self.event_log.append(ev); self._record_event(ev)
    def _apply_inflation(self): self.reserve.apply_inflation()
    def _check_reproduction(self):
        ev=[]; alive=[a for a in self.agents if a.alive]; cfg=self.config
        ca=self._cells_a; oc=self._agent_order; byid=self._agents_by_id
        rg=INDEX_RANGE
        for a in alive:
            if not a.partner_id and a.age>cfg.marriage_age and a.needs["belonging"]>70:
                # 原为对全员 O(N²) 扫描 + 每次 math.hypot：1000 人时实测 0.351s/tick
                # （占单 tick 36%），是本世界第二个热点。婚配要求距离≤2，
                # 故只需查邻格；候选按对象下标排序，与全扫顺序逐字节一致。
                cx=a.pos.x//INDEX_CELL; cy=a.pos.y//INDEX_CELL
                cand=[]
                for dx in range(-rg,rg+1):
                    for dy in range(-rg,rg+1):
                        b0=ca.get((cx+dx,cy+dy))
                        if b0:
                            for aid in b0: cand.append((oc[aid],byid[aid]))
                cand.sort(key=lambda t:t[0])
                for _i,b in cand:
                    # 发起方阈值 marriage_age(20) 与接受方 adult_age(18) 原为不对称写死；
                    # 此处仅提取为具名参数并保留原阈值，不擅自统一（统一会改变行为）
                    if b.aid!=a.aid and b.alive and not b.partner_id and b.age>cfg.adult_age and b.needs["belonging"]>70:
                        if math.hypot(a.pos.x-b.pos.x,a.pos.y-b.pos.y)<=2 and self._rng.random()<cfg.marriage_prob:
                            a.partner_id=b.aid; b.partner_id=a.aid
                            ev.append(Event(eid=self.next_eid(),etype=EventType.MARRIAGE,actor=a.aid,
                                target=b.aid,tick=self._tick))   # 原先误写 self.tick（绑定方法）而非 self._tick
                            break
            if (a.partner_id and a.alive and cfg.birth_min_age<a.age<cfg.birth_max_age
                    and a.needs["physiology"]>60 and a.needs["safety"]>50 and a.wealth>80):
                p=self.find_agent(a.partner_id)
                if p and p.alive and math.hypot(a.pos.x-p.pos.x,a.pos.y-p.pos.y)<=2 and self._rng.random()<cfg.birth_prob:
                    self._spawn_agent(parent_ids=(a.aid,p.aid),
                        pos=Position((a.pos.x+p.pos.x)//2,(a.pos.y+p.pos.y)//2),age=0)
        return ev
    def _check_deaths(self):
        ev=[]
        for a in self.agents:
            if a.alive and a.age>self.config.elder_age and self._rng.random()<0.05:
                a.alive=False; a.state=AgentState.DEAD; self._wd+=1
                self._unindex_agent(a)
                ev.append(Event(eid=self.next_eid(),etype=EventType.DEATH,actor=a.aid,tick=self._tick,
                    data={"cause":"old_age","age":a.age}))
        return ev
    def _regenerate_resources(self):
        for r in self.resources:
            if r["amount"]<25 and self._rng.random()<r["regen_rate"]: r["amount"]+=2
        if self._rng.random()<0.15 and len(self.resources)<self.size*self.size*0.08: self._spawn_resource()
    def _build_houses(self):
        for a in self.agents:
            if a.alive and not a.home_pos and a.wealth>200 and self._rng.random()<0.005:
                a.home_pos=Position(a.pos.x,a.pos.y)
                self.buildings.append({"type":"house","pos":(a.pos.x,a.pos.y),"owner":a.aid,"age":0})
                a.wealth-=100; self.reserve.collect_fee(100)   # 购房款需入账，否则货币凭空消失
                a.needs["safety"]=min(100,a.needs["safety"]+20)
    def _compliance_check(self):
        ev=[]
        for a in self.agents:
            if not a.alive: continue
            if a.wealth<self.config.debt_limit:
                floor=self.config.debt_limit*0.5; relief=floor-a.wealth
                a.wealth=floor
                self.reserve.mint_debt_relief(relief)   # 原先直接抬高余额，未记账 => 守恒式被破坏
                a.violations+=1
                ev.append(Event(eid=self.next_eid(),etype=EventType.VIOLATION,actor=a.aid,tick=self._tick,
                    data={"rule":"debt_limit","relief":relief}))
            if a.wealth>self.config.max_wealth:
                a.violations+=1; excess=a.wealth-self.config.max_wealth
                tax=excess*self.config.wealth_hardcap_tax
                a.wealth-=tax; self.reserve.collect_tax(tax)
                ev.append(Event(eid=self.next_eid(),etype=EventType.VIOLATION,actor=a.aid,tick=self._tick,
                    data={"rule":"wealth_hardcap","penalty":tax}))
        return ev
    def tick(self):
        self._tick+=1; te=[]; alive=[a for a in self.agents if a.alive]
        self.temporal_substrate.tick()   # 构成公理二：全局时钟随世界推进，不可回退
        self._reindex_static()   # 资源/建筑位置在 tick 内不变，每 tick 重建即精确
        # 年龄以「岁」计：原先每 tick +1，本文件 tps=10 时第 80 tick 就进入老年死亡，社会必然瞬间灭绝
        if self._tick%self.config.ticks_per_year==0:
            for a in alive: a.age+=1
            if self.player is not None: self.player.age+=1   # 居民化：玩家同样老去（演示中不设玩家死亡，见 _check_deaths 边界）
        for a in alive:
            a.perceive(self); d=a.think(self); te.extend(a.act(d,self))
            # 人格层推进放在 act 之后：读到的需求/能量是本 tick 结算后的值
            if a.persona is not None:
                a.affect=a.persona.step(a,a._perceived)
        self._regenerate_resources(); self._build_houses()
        te.extend(self._check_reproduction()); te.extend(self._check_deaths()); te.extend(self._compliance_check())
        if self._tick%10==0: self._distribute_ubi()
        if self._tick%30==0: self._collect_taxes()
        if self._tick%50==0: self._apply_inflation()
        if self.player: self.player.tick(self)
        for b in self.buildings: b["age"]+=1
        self.event_log.extend(te)   # 原先另有 self.events 只增不减，且全仓无任何读取点（死字段+内存泄漏）
        if len(self.event_log)>5000: self.event_log=self.event_log[-3000:]
        for e in te: self._record_event(e)   # 构成公理三：本 tick 事件接入因果图
        # 第八条·永续：本 tick 落账历史链（只增不改，改一块则其后全链失配）
        self.history.append({"event":"tick","tick":self._tick,"alive":len(alive),
            "money_supply":round(self.reserve.money_supply,6),"events":len(te)},
            timestamp=float(self._tick))
        self.memory_vault.seal_all()   # 第七条：记忆指纹与本 tick 末状态同步
        return te
    def get_stats(self):
        alive=[a for a in self.agents if a.alive]
        tw=sum(a.wealth for a in alive)
        an={}
        for n in FIVE_LAYER_NEEDS:
            vs=[a.needs[n] for a in alive]; an[n]=sum(vs)/len(vs) if vs else 0
        return {"tick":self._tick,"alive":len(alive),"dead":len([a for a in self.agents if not a.alive]),
            "births":self._wb,"deaths":self._wd,"total_wealth":tw,"avg_wealth":tw/len(alive) if alive else 0,
            "wealth_created":self.reserve.total_labor_created,"total_trades":self._wt,"avg_needs":an,
            "avg_knowledge":sum(a.knowledge for a in alive)/len(alive) if alive else 0,
            "avg_creativity":sum(a.creativity for a in alive)/len(alive) if alive else 0,
            "total_memory":sum(a.memory.stats()["total_memories"] for a in alive),
            "resources":len(self.resources),"buildings":len(self.buildings),
            "money_supply":self.reserve.money_supply,"inflation_rate":self.reserve.inflation_rate,
            "treasury":self.reserve.treasury,
            "money_residual":self.reserve.invariant_residual(self.agents),
            "ubi_cycles":self._ubi_cycle,"violations":sum(a.violations for a in self.agents)}
    def get_simulation_metrics(self):
        """仿真自评指标（7 维，仅供演示与回归对照）。

        这不是宪法审计。宪法级 25 项审计请调用
            audit_engine.SecondPerspectiveAuditor().audit_world(world)
        原方法名 get_audit_report 已废弃：名为 audit 却只有 7 维自评口径，
        与审计引擎的 25 维并列会造成"两个分数"的对外混称。
        """
        s=self.get_stats(); n=s["avg_needs"]
        dims={}
        dims["physiology"]=min(100,n["physiology"]*1.2)
        dims["safety"]=min(100,n["safety"]*1.1)
        dims["belonging"]=min(100,n["belonging"]*1.1)
        dims["esteem"]=min(100,n["esteem"])
        dims["self_actualization"]=min(100,n["self_actualization"]*1.5)
        dims["economy"]=max(0,100-s["violations"]*5)
        dims["sustainability"]=max(0,100-abs(s["inflation_rate"]-0.02)*500)
        overall=sum(dims.values())/len(dims)
        return {"kind":"simulation_self_metrics","overall_score":overall,"dimensions":dims,
            "money_residual":s["money_residual"],
            "disclaimer":"仿真自评，非宪法 25 项审计；宪法审计见 audit_engine.SecondPerspectiveAuditor",
            "stats":s}
    def persona_report(self):
        """人格层观测报告。

        与「宪法 25 项审计」「仿真 7 维自评」并列的第三种口径，三者不得混称：
        本报告只反映 SPL V8.0 情绪演化，不构成任何合规判定。
        """
        alive=[a for a in self.agents if a.alive]
        wp=[a for a in alive if a.persona is not None]
        if not wp:
            return {"mode":self.config.persona_mode,"agents_with_persona":0,
                "note":"人格层未启用（persona_mode=off）"}
        keys=sorted(wp[0].affect.keys())
        avg={k:round(sum(a.affect.get(k,0.0) for a in wp)/len(wp),6) for k in keys}
        # 智能体栈分布：证明 1000 个个体真的不同（不是同一模板复制 1000 份）
        roles={}; modes={}; goals={}
        for a in wp:
            st=a.stack
            if st is None: continue
            roles[st.identity_role]=roles.get(st.identity_role,0)+1
            modes[st.language_mode]=modes.get(st.language_mode,0)+1
            goals[st.goal_title]=goals.get(st.goal_title,0)+1
        rep={"mode":self.config.persona_mode,"agents_with_persona":len(wp),
            "ticks_advanced":wp[0].persona.tick_count,"avg_affect":avg,
            "identity_distribution":dict(sorted(roles.items(),key=lambda kv:(-kv[1],kv[0]))),
            "language_mode_distribution":dict(sorted(modes.items(),key=lambda kv:(-kv[1],kv[0]))),
            "goal_distribution":dict(sorted(goals.items(),key=lambda kv:(-kv[1],kv[0]))),
            "scale":"persona affect layer (SPL Pure Core V8.0) — not constitutional audit"}
        return rep
    def state_hash(self):
        """世界状态指纹：同一 (config, seed) 必得同一哈希——对外可复现性的取证手段。"""
        blob=json.dumps(self.export_state(),ensure_ascii=False,sort_keys=True,default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
    def export_state(self):
        return {"tick":self._tick,"config":self.config.__dict__,
            "agents":[a.to_dict() for a in self.agents],"resources":self.resources,
            "buildings":self.buildings,"stats":self.get_stats(),
            "player":self.player.to_dict() if self.player else None,
            "reserve":{"money_supply":self.reserve.money_supply,"treasury":self.reserve.treasury,
                "total_ubi":self.reserve.total_ubi_distributed,"total_tax":self.reserve.total_tax_collected,
                "total_labor_created":self.reserve.total_labor_created,
                "inflation_created":self.reserve.inflation_created,
                "total_debt_relief":self.reserve.total_debt_relief,
                "genesis_unallocated":self.reserve.genesis_unallocated}}
    def save_state(self, fp):
        with open(fp,'w',encoding='utf-8') as f: json.dump(self.export_state(),f,ensure_ascii=False,indent=2,default=str)

# ============================================================
# EraCalendar — 恩利尔大陆历法映射 + 纪元预演
# 玩家可选择从任一历史纪元切入：世界先 headless 预演到该时间点，再插入玩家。
# ============================================================
import pickle

class EraCalendar:
    ERAS=[
        {"key":"genesis","name":"神代","desc":"众神共治的太古时代，万古不灭大世界","alpha_years_ago":900000,"start_tick":0},
        {"key":"theocracy","name":"天神教初立","desc":"第一位真神扶持天神教，神代秩序延续","alpha_years_ago":1040000,"start_tick":400},
        {"key":"schism","name":"天穹裂变","desc":"诸神战争，世界断裂为神界与恩利尔大陆","alpha_years_ago":900000,"start_tick":800},
        {"key":"academy","name":"魔法学院纪","desc":"魔法学院创办，学术兴起","alpha_years_ago":230000,"start_tick":1500},
        {"key":"mingyir","name":"明伊尔纪","desc":"塔·明伊尔魔法工业革命，七大行业确立","alpha_years_ago":130000,"start_tick":2500},
        {"key":"ayyas","name":"阿亚斯纪","desc":"天神教鼎盛，白夜清洗者组织活跃","alpha_years_ago":90000,"start_tick":3500},
        {"key":"alpha_dawn","name":"阿尔法元年","desc":"阿尔法帝国统一人族板块","alpha_years_ago":0,"start_tick":5000},
        {"key":"present","name":"当下","desc":"伊莉斯·Von·安启降生，始祖时代","alpha_years_ago":0,"start_tick":7000},
    ]
    @classmethod
    def get_era(cls,key):
        for e in cls.ERAS:
            if e["key"]==key: return e
        return None
    @classmethod
    def tick_to_date(cls,tick,ticks_per_year=10):
        for i in range(len(cls.ERAS)-1,-1,-1):
            era=cls.ERAS[i]
            if tick>=era["start_tick"]:
                years_into=(tick-era["start_tick"])//ticks_per_year
                return era["name"],years_into,era["alpha_years_ago"]
        return "神代",tick//ticks_per_year,900000

def precompute_era(era_key,seed,config=None,snapshot_dir=".world_data/snapshots"):
    era=EraCalendar.get_era(era_key)
    if not era: raise ValueError("Unknown era: %s"%era_key)
    target_tick=era["start_tick"]
    os.makedirs(snapshot_dir,exist_ok=True)
    fp=os.path.join(snapshot_dir,"era_%s_seed%d.pkl"%(era_key,seed))
    if os.path.exists(fp):
        with open(fp,'rb') as f: return pickle.load(f)
    cfg=config or WorldConfig(world_size=60,initial_agents=30,initial_resources=80,initial_buildings=8,seed=seed)
    world=NohnWorld(cfg)
    for _ in range(target_tick): world.tick()
    with open(fp,'wb') as f: pickle.dump(world,f)
    return world

# ============================================================
# ============================================================
# GUI Visualization (pygame) — Anime Isometric 2.5D Renderer
# 铁律：本段只负责“画”，不触碰仿真 / 账本 / 审计逻辑。
#       同 seed 的世界状态哈希与旧版像素渲染完全一致（可验证）。
# ============================================================
import pygame
WORLD_SIZE=60; CELL=32; STATS_H=240
WW=WORLD_SIZE*CELL+350; WH=WORLD_SIZE*CELL+STATS_H
MAP_W=WORLD_SIZE*CELL; MAP_H=WORLD_SIZE*CELL   # 1920×1920 地图视口
PANEL_W=WW-MAP_W                                # 右侧面板 350px

# ---- 等距投影（经典 2:1 菱形）----
TW=32; TH=16; TW2=TW//2; TH2=TH//2
OX=MAP_W//2                                    # 水平居中
OY=520                                         # 竖直位置：顶部留天空
ISLAND_BOTTOM=OY+(WORLD_SIZE*2-2)*TH2+TH2      # 岛底边

def tile_center(gx,gy):
    return (OX+(gx-gy)*TW2, OY+(gx+gy)*TH2)
def grid_ground(gx,gy):
    x,y=tile_center(gx,gy); return (x,y+TH2)
def screen_to_grid(mx,my):
    dx=mx-OX; dy=my-OY
    a=dx/TW2; b=dy/TH2
    gx=int(round((a+b)/2.0)); gy=int(round((b-a)/2.0))
    if 0<=gx<WORLD_SIZE and 0<=gy<WORLD_SIZE: return gx,gy
    return None

# ---- 动漫调色板 ----
PAL={"sky_top":(118,176,236),"sky_bot":(216,238,248),"cloud":(255,255,255),
     "sun":(255,218,120),"sun_hi":(255,242,196),
     "grass_a":(146,204,124),"grass_b":(126,186,112),"grass_hi":(170,222,148),
     "grass_edge":(88,140,88),"ink":(38,34,44),"skin":(255,226,200),
     "panel":(23,25,42),"panel_2":(36,40,66),"gold":(245,200,90),
     "text":(228,234,242),"text_dim":(168,178,198),"bar_bg":(52,56,80),
     "chart_bg":(16,18,32),"chart_line":(60,64,90),"blush":(255,140,150),
     "shadow":(30,40,70)}

COLORS={"bg":(15,15,25),"grid":(35,35,50),
    "food":(80,180,80),"water":(60,140,220),"wood":(120,80,40),
    "stone":(130,130,140),"herb":(80,200,130),"ore":(160,120,80),"fruit":(220,140,60),
    "house":(160,120,80),"market":(180,160,60),"workshop":(140,100,60),
    "garden":(80,180,80),"library":(130,110,200),
    "agent_idle":(190,192,200),"agent_working":(240,196,72),
    "agent_socializing":(236,132,188),"agent_resting":(96,146,232),
    "agent_trading":(72,224,168),"agent_learning":(172,138,232),
    "agent_creating":(236,96,96),"agent_dead":(50,50,50),
    "text":(200,200,200),"need_high":(96,222,110),"need_mid":(238,196,80),"need_low":(238,90,90),
    "bar_bg":(40,40,55),"panel":(20,20,35),
    "chart_bg":(12,12,22),"chart_line":(50,50,70),
    "warm":(170,60,30),"friend":(60,90,130),"partner":(220,130,180),
    "tip_bg":(12,12,20),"tip_border":(100,100,130),
    "curve_pop":(110,206,232),"curve_gini":(238,182,84),
    "curve_need":(110,216,132),"curve_money":(210,132,232)}

# 代际配色 = 发色：眼不看字也能认出第几代
GEN_COLORS=[(52,50,58),(150,92,208),(40,160,158),(196,104,40),(52,96,210),(176,52,116)]

# 事件流标签与配色
EVENT_LABEL={"birth":"出生","death":"死亡","marriage":"结婚","produce":"生产","trade":"交易",
    "interact":"社交","rest":"休息","ubi":"UBI","tax":"税收","violation":"违规"}
EVENT_COLOR={"birth":(120,230,255),"death":(160,160,180),"marriage":(255,150,200),
    "trade":(80,255,180),"violation":(230,90,90)}

# 显式候选字体文件：SysFont 在部分环境匹配不到中文字体，会把中文渲染成方块
CJK_FONT_FILES=[r"C:\Windows\Fonts\msyh.ttc",r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",r"C:\Windows\Fonts\simsun.ttc",r"C:\Windows\Fonts\Deng.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc"]

STATE_LABELS={"idle":"空闲","working":"工作","socializing":"社交","resting":"休息",
    "trading":"交易","learning":"学习","creating":"创造"}
RES_LABELS={"food":"食物","water":"水","wood":"木材","stone":"石料",
    "herb":"草药","ore":"矿石","fruit":"水果"}
BLD_LABELS={"house":"住宅","market":"集市","workshop":"工坊","garden":"花园","library":"图书馆"}

BUILDING_STYLE={"house":{"h":34,"top":(216,118,106),"wall":(226,170,132)},
    "market":{"h":26,"top":(218,150,78),"wall":(240,198,142)},
    "workshop":{"h":26,"top":(180,142,110),"wall":(152,120,94)},
    "garden":{"h":18,"top":(130,198,112),"wall":(152,192,132)},
    "library":{"h":32,"top":(140,120,202),"wall":(122,104,178)}}

def _lerp_color(c1,c2,t):
    t=max(0.0,min(1.0,t))
    return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))
def _darken(c,f): return tuple(max(0,int(c[i]*f)) for i in range(3))
def _hash2(x,y):
    h=(x*73856093 ^ y*19349663) & 0xffffffff
    return h/0xffffffff
def _gini(values):
    xs=[max(0.0,v) for v in values]
    if not xs: return 0.0
    s=sum(xs)
    if s<=0: return 0.0
    xs.sort(); n=len(xs)
    cum=sum((2*i-n-1)*x for i,x in enumerate(xs,1))
    return max(0.0,min(1.0,cum/(n*s)))

def _rounded(surf,rect,color,radius=6,outline=None,ow=1,alpha=None):
    # 调用点有两种传参：pygame.Rect 与 4 元组 (x,y,w,h)。alpha 分支要读 rect.w/.h，
    # 元组没有这两属性会崩（tooltip 悬浮即触发）。统一在入口归一为 Rect。
    if not isinstance(rect,pygame.Rect):
        rect=pygame.Rect(rect)
    if alpha is not None:
        s=pygame.Surface((max(1,int(rect.w)),max(1,int(rect.h))),pygame.SRCALPHA)
        pygame.draw.rect(s,tuple(color)+(alpha,),s.get_rect(),border_radius=radius)
        if outline is not None: pygame.draw.rect(s,tuple(outline)+(alpha,),s.get_rect(),ow,border_radius=radius)
        surf.blit(s,(int(rect.x),int(rect.y))); return
    pygame.draw.rect(surf,color,rect,border_radius=radius)
    if outline is not None: pygame.draw.rect(surf,outline,rect,ow,border_radius=radius)

# ---- 静态图层：天空 + 地面瓦片（一次性预渲染，逐帧 blit，性能友好）----
def build_sky(seed):
    s=pygame.Surface((MAP_W,MAP_H))
    for y in range(MAP_H):
        t=y/MAP_H
        c=[int(PAL["sky_top"][i]+(PAL["sky_bot"][i]-PAL["sky_top"][i])*t) for i in range(3)]
        pygame.draw.line(s,c,(0,y),(MAP_W,y))
    # 太阳（柔光晕）
    sx,sy=150,132
    for rr,al in ((78,10),(56,26),(38,62)):
        g=pygame.Surface((rr*2,rr*2),pygame.SRCALPHA)
        pygame.draw.circle(g,(255,224,150,al),(rr,rr),rr)
        s.blit(g,(sx-rr,sy-rr))
    pygame.draw.circle(s,PAL["sun_hi"],(sx-7,sy-7),23)
    pygame.draw.circle(s,PAL["sun"],(sx,sy),23)
    # 云（手绘感圆斑）
    clouds=[(430,118),(990,78),(1510,148),(770,212),(1680,86),(240,260)]
    for cx,cy in clouds:
        for dx,dy,rr in ((0,0,22),(-18,6,18),(19,7,20),(-7,12,17),(11,13,16)):
            pygame.draw.circle(s,PAL["cloud"],(cx+dx,cy+dy),rr)
    return s

# ---- 地形层：确定性值噪声 + 聚落结构（只改观感，不动仿真）----
def _vnoise(seed,gx,gy,scale):
    """平滑值噪声：同 seed 同坐标必得同值，多倍频叠加才像地貌，不像马赛克。"""
    x=gx/scale; y=gy/scale
    x0=math.floor(x); y0=math.floor(y)
    fx=x-x0; fy=y-y0
    fx=fx*fx*(3-2*fx); fy=fy*fy*(3-2*fy)
    h=lambda a,b: _hash2(int(a)+seed*131,int(b)+seed*17)
    return (h(x0,y0)*(1-fx)+h(x0+1,y0)*fx)*(1-fy)+(h(x0,y0+1)*(1-fx)+h(x0+1,y0+1)*fx)*fy

T_GRASS=0; T_FOREST=1; T_HILL=2; T_MEADOW=3; T_PLAZA=4; T_ROAD=5
GROUND_PAL={T_GRASS:((146,204,124),(126,186,112)),
    T_FOREST:((104,164,102),(86,144,86)),
    T_HILL:((208,188,140),(190,168,120)),
    T_MEADOW:((188,220,140),(168,206,124)),
    T_PLAZA:((204,200,192),(184,180,172)),
    T_ROAD:((190,162,120),(172,144,104))}
PLAZA_R=5

def _pct(values,q):
    """取分位阈值：用排名而不是固定数值，换 seed 也不会整岛变一种地貌。"""
    xs=sorted(values)
    if not xs: return 0.0
    return xs[max(0,min(len(xs)-1,int(q*len(xs))))]

def terrain_grid(seed,buildings=None):
    """60×60 地块类型表 + 广场中心。同 seed 同建筑位 → 同结果。
    不建水面：角色没有可通行约束，画湖会让人站在湖里，观感与仿真不一致。"""
    bs=buildings or []
    if bs:
        pcx=int(round(sum(b["pos"][0] for b in bs)/len(bs)))
        pcy=int(round(sum(b["pos"][1] for b in bs)/len(bs)))
    else:
        pcx=pcy=WORLD_SIZE//2
    g=[[T_GRASS for _ in range(WORLD_SIZE)] for _ in range(WORLD_SIZE)]
    # 三张独立噪声场 + 分位阈值：森林 ~20%、丘陵 ~12%、花田 ~15%，剩余草地
    fs=[[_vnoise(seed,gx,gy,7.0) for gy in range(WORLD_SIZE)] for gx in range(WORLD_SIZE)]
    hs=[[_vnoise(seed+7,gx,gy,5.5) for gy in range(WORLD_SIZE)] for gx in range(WORLD_SIZE)]
    ms=[[_vnoise(seed+13,gx,gy,4.5) for gy in range(WORLD_SIZE)] for gx in range(WORLD_SIZE)]
    fT=_pct([v for row in fs for v in row],0.20)
    hT=_pct([v for row in hs for v in row],0.88)
    mT=_pct([v for row in ms for v in row],0.62)
    for gx in range(WORLD_SIZE):
        for gy in range(WORLD_SIZE):
            # 村落半径 11 内不生成林木：留出空地，否则广场与道路被树盖死
            far=math.hypot(gx-pcx,gy-pcy)>11
            if far and fs[gx][gy]<=fT: g[gx][gy]=T_FOREST
            elif hs[gx][gy]>=hT: g[gx][gy]=T_HILL
            elif ms[gx][gy]>=mT: g[gx][gy]=T_MEADOW
            else: g[gx][gy]=T_GRASS
    # 广场：以建筑质心为圆心的铺石区（聚落的地标，也是道路汇聚点）
    for gx in range(max(0,pcx-PLAZA_R),min(WORLD_SIZE,pcx+PLAZA_R+1)):
        for gy in range(max(0,pcy-PLAZA_R),min(WORLD_SIZE,pcy+PLAZA_R+1)):
            if (gx-pcx)**2+(gy-pcy)**2<=PLAZA_R*PLAZA_R: g[gx][gy]=T_PLAZA
    # 道路：每栋建筑到广场的 L 形土路（先横后竖，确定性；广场不覆盖）
    for b in bs:
        bx,by=b["pos"]
        for x in range(min(bx,pcx),max(bx,pcx)+1):
            if g[x][by]!=T_PLAZA: g[x][by]=T_ROAD
        for y in range(min(by,pcy),max(by,pcy)+1):
            if g[pcx][y]!=T_PLAZA: g[pcx][y]=T_ROAD
    return g,(pcx,pcy)

def terrain_props(seed,buildings=None):
    """林木 / 岩石 / 花丛。返回深度排序用的道具表，与角色同层绘制。"""
    grid,(pcx,pcy)=terrain_grid(seed,buildings)
    occ=set()
    for b in (buildings or []):
        bx,by=b["pos"]
        for dx in (-2,-1,0,1,2):
            for dy in (-2,-1,0,1,2): occ.add((bx+dx,by+dy))
    out=[]
    for gx in range(WORLD_SIZE):
        for gy in range(WORLD_SIZE):
            if (gx,gy) in occ: continue
            t=grid[gx][gy]
            if math.hypot(gx-pcx,gy-pcy)<PLAZA_R+2: continue   # 广场周边不长树
            n=_hash2(gx*7+seed*101,gy*11+seed*37)
            if t==T_FOREST and n<0.22:
                out.append({"gx":gx,"gy":gy,"kind":("pine" if n<0.12 else "oak"),"s":0.90+n*0.55})
            elif t==T_HILL and n<0.26:
                out.append({"gx":gx,"gy":gy,"kind":"rock","s":0.62+n*0.7})
            elif t==T_MEADOW and n<0.06:
                out.append({"gx":gx,"gy":gy,"kind":"bush","s":0.55+n*0.5})
    return out

def build_ground(seed,buildings=None):
    """手绘感地块 + 聚落广场土路 + 岛缘侧壁，预渲染一次。
    必须用 SRCALPHA：菱形之外的像素保持透明，否则会把天空整个盖成黑幕
    （v1 缺陷——地图四周全黑即此因）。"""
    s=pygame.Surface((MAP_W,MAP_H),pygame.SRCALPHA)
    grid,(pcx,pcy)=terrain_grid(seed,buildings)
    EDGE_H=13                                  # 岛缘侧壁厚度（假厚度）
    for gx in range(WORLD_SIZE):
        for gy in range(WORLD_SIZE):
            cx,cy=tile_center(gx,gy)
            t=grid[gx][gy]
            n=_hash2(gx+seed,gy*3+seed)
            base=_lerp_color(GROUND_PAL[t][0],GROUND_PAL[t][1],n)
            pts=[(cx,cy-TH2),(cx+TW2,cy),(cx,cy+TH2),(cx-TW2,cy)]
            pygame.draw.polygon(s,base,pts)
            # 上半面提亮（赛璐璐两段式受光）
            pygame.draw.polygon(s,_lerp_color(base,(255,255,255),0.20),
                [(cx,cy-TH2),(cx+TW2,cy),(cx-TW2,cy)])
            a=_darken(base,0.92); b2=_darken(base,0.84)
            if t==T_GRASS:
                if n>0.84:
                    pygame.draw.line(s,b2,(cx-2,cy-2),(cx-3,cy+1),1)
                    pygame.draw.line(s,b2,(cx+1,cy-3),(cx+2,cy),1)
                elif n>0.72:
                    pc=(252,220,180) if n>0.78 else (255,240,220)
                    pygame.draw.circle(s,pc,(cx+3,cy-3),1)
                elif n<0.10:
                    pygame.draw.circle(s,(112,168,120),(cx-3,cy+2),1)
            elif t==T_FOREST:               # 林下：针叶落影 + 苔点
                if n>0.55:
                    pygame.draw.line(s,b2,(cx+2,cy-4),(cx+4,cy-1),1)
                    pygame.draw.line(s,b2,(cx-4,cy-1),(cx-2,cy-4),1)
                if n<0.18: pygame.draw.circle(s,(96,150,96),(cx-3,cy+2),1)
            elif t==T_HILL:                 # 岩地：裂纹 + 碎石
                if n>0.62: pygame.draw.line(s,b2,(cx-5,cy+1),(cx+3,cy-3),1)
                if n>0.38 and n<0.46: pygame.draw.circle(s,(168,164,158),(cx+3,cy-2),1)
            elif t==T_MEADOW:               # 花田：三色小花
                if n>0.58:
                    pc=(252,214,226) if n<0.74 else ((250,238,170) if n<0.90 else (240,246,255))
                    pygame.draw.circle(s,pc,(cx+2,cy-3),1)
                    pygame.draw.circle(s,pc,(cx-3,cy+1),1)
            elif t==T_ROAD:                 # 土路：碎石与车辙
                if n>0.66: pygame.draw.circle(s,_darken(base,0.78),(cx+2,cy+1),1)
                if n<0.20: pygame.draw.circle(s,_lerp_color(base,(255,255,255),0.35),(cx-2,cy+2),1)
                pygame.draw.line(s,a,(cx-TW2+3,cy+TH2-4),(cx-3,cy+2),1)
            elif t==T_PLAZA:                # 铺石：砖缝 + 外圈压边
                d=math.hypot(gx-pcx,gy-pcy)
                pygame.draw.polygon(s,a,pts,1)
                if d>=PLAZA_R-1: pygame.draw.polygon(s,b2,pts,2)
    # 广场地标：石井（纯地面装饰，不参与仿真，不做可通行判定）
    wx,wy=tile_center(pcx,pcy)
    pygame.draw.ellipse(s,(150,146,140),(wx-13,wy-2,26,14))
    pygame.draw.ellipse(s,(208,204,196),(wx-12,wy-3,24,12))
    pygame.draw.ellipse(s,(74,78,92),(wx-8,wy-1,16,8))
    pygame.draw.ellipse(s,PAL["ink"],(wx-13,wy-2,26,14),1)
    # 岛缘侧壁：只画下缘两个面（+x 面与 +y 面），做出岛的厚度
    for gx in range(WORLD_SIZE):
        for gy in range(WORLD_SIZE):
            cx,cy=tile_center(gx,gy)
            if gx==WORLD_SIZE-1:
                col=_darken(PAL["grass_edge"],0.92)
                pygame.draw.polygon(s,col,[(cx+TW2,cy),(cx,cy+TH2),
                    (cx,cy+TH2+EDGE_H),(cx+TW2,cy+EDGE_H)])
            if gy==WORLD_SIZE-1:
                col=_darken(PAL["grass_edge"],0.80)
                pygame.draw.polygon(s,col,[(cx-TW2,cy),(cx,cy+TH2),
                    (cx,cy+TH2+EDGE_H),(cx-TW2,cy+EDGE_H)])
    # 岛轮廓（粗描边 = 手绘 inking）
    top=tile_center(0,0); right=tile_center(WORLD_SIZE-1,0)
    bot=tile_center(WORLD_SIZE-1,WORLD_SIZE-1); left=tile_center(0,WORLD_SIZE-1)
    rim=[top,(right[0],right[1]+TH2),(bot[0],bot[1]+TH2),(left[0],left[1]+TH2)]
    pygame.draw.polygon(s,PAL["grass_edge"],rim,3)
    return s

def draw_prop(screen,overlay,p,tick=0):
    """树 / 岩石 / 灌木：进深度排序，人走到树后会被树挡住。"""
    gxp,gyp=grid_ground(p["gx"],p["gy"])
    k=p["kind"]; sc=p["s"]
    sway=int(math.sin(tick*0.12+p["gx"]*0.7+p["gy"]*0.3)*1.5) if k!="rock" else 0
    if k=="rock":
        _draw_shadow(overlay,gxp,gyp,int(16*sc),int(5*sc))
        r=int(9*sc)
        pygame.draw.ellipse(screen,(152,150,148),(gxp-r,gyp-r//2,r*2,r))
        pygame.draw.ellipse(screen,(180,178,174),(gxp-r+2,gyp-r//2+1,r*2-4,max(2,int(r*0.7))))
        pygame.draw.ellipse(screen,PAL["ink"],(gxp-r,gyp-r//2,r*2,r),1)
        return
    if k=="bush":
        _draw_shadow(overlay,gxp,gyp,int(10*sc),int(4*sc))
        r=int(6*sc)
        pygame.draw.circle(screen,(126,184,120),(gxp-r//2,gyp-r//3),r)
        pygame.draw.circle(screen,(146,204,132),(gxp+r//2,gyp-r//3),r)
        pygame.draw.circle(screen,(170,222,148),(gxp,gyp-r),r)
        return
    _draw_shadow(overlay,gxp,gyp,int(18*sc),int(6*sc))
    th=int(12*sc)
    pygame.draw.rect(screen,(120,88,58),(gxp-2,gyp-th,4,th))
    if k=="pine":
        for dy,wd,col in ((0,23,(72,130,90)),(-12,18,(86,148,100)),(-22,13,(104,166,114))):
            w=int(wd*sc*0.5); by=gyp-th+int(dy*sc)
            pygame.draw.polygon(screen,col,[(gxp-w+sway,by),(gxp+sway,by-int(17*sc)),(gxp+w+sway,by)])
            pygame.draw.polygon(screen,PAL["ink"],[(gxp-w+sway,by),(gxp+sway,by-int(17*sc)),(gxp+w+sway,by)],1)
    else:
        cr=int(14*sc); hx=gxp+sway; hy=gyp-th-int(9*sc)
        pygame.draw.circle(screen,(102,162,104),(hx,hy),cr)
        pygame.draw.circle(screen,(128,188,124),(hx-int(cr*0.55),hy-int(cr*0.35)),int(cr*0.78))
        pygame.draw.circle(screen,(156,208,142),(hx+int(cr*0.5),hy-int(cr*0.45)),int(cr*0.66))
        pygame.draw.circle(screen,(176,222,158),(hx+int(cr*0.1),hy-int(cr*0.72)),int(cr*0.42))
        pygame.draw.circle(screen,PAL["ink"],(hx,hy),cr,1)

def build_island_shadow():
    s=pygame.Surface((MAP_W,MAP_H),pygame.SRCALPHA)
    pygame.draw.ellipse(s,(40,70,120,46),(OX-1150,ISLAND_BOTTOM+26,2300,220))
    pygame.draw.ellipse(s,(40,70,120,30),(OX-1030,ISLAND_BOTTOM+38,2060,170))
    return s

# ---- 实体绘制 ----
def _draw_shadow(overlay,gxp,gyp,w=16,d=6):
    pygame.draw.ellipse(overlay,PAL["shadow"]+(95,),(gxp-w//2,gyp-2,w,d))

def draw_building_anim(screen,overlay,b,tick):
    gx,gy=b["pos"]; t=b["type"]
    st=BUILDING_STYLE.get(t,BUILDING_STYLE["house"])
    h=st["h"]
    gxp,gyp=grid_ground(gx,gy)
    _draw_shadow(overlay,gxp,gyp,30,8)
    top=[(gxp,gyp-h-TH2),(gxp+TW2,gyp-h),(gxp,gyp-h+TH2),(gxp-TW2,gyp-h)]
    front=[(gxp-TW2,gyp-h),(gxp,gyp-h+TH2),(gxp,gyp+TH2),(gxp-TW2,gyp)]
    right=[(gxp,gyp-h+TH2),(gxp+TW2,gyp-h),(gxp+TW2,gyp),(gxp,gyp+TH2)]
    pygame.draw.polygon(screen,_darken(st["wall"],0.62),front)
    pygame.draw.polygon(screen,_darken(st["wall"],0.44),right)
    pygame.draw.polygon(screen,st["top"],top)
    for poly in (front,right,top):
        pygame.draw.polygon(screen,PAL["ink"],poly,2)
    pygame.draw.line(screen,PAL["ink"],(gxp-TW2,gyp-h),(gxp-TW2,gyp),2)
    pygame.draw.line(screen,PAL["ink"],(gxp,gyp-h+TH2),(gxp,gyp+TH2),2)
    # 类型装饰
    if t=="house":
        pygame.draw.line(screen,_darken(st["top"],0.7),(gxp,gyp-h-TH2),(gxp,gyp-h+TH2),2)
        pygame.draw.rect(screen,_darken(st["wall"],0.75),(gxp-3,gyp,6,4),border_radius=1)
    elif t=="market":
        for i in range(4):
            f=i/4.0
            px1=gxp-TW2+f*TW2; py1=gyp-h+f*TH2
            px2=gxp-TW2+(f+0.25)*TW2; py2=gyp-h+(f+0.25)*TH2
            col=(242,232,210) if i%2==0 else (224,110,104)
            pygame.draw.polygon(screen,col,
                [(px1,py1),(px2,py2),(px2+2,py2+6),(px1+2,py1+6)])
            pygame.draw.line(screen,PAL["ink"],(px1,py1),(px1+2,py1+6),1)
    elif t=="workshop":
        pygame.draw.rect(screen,_darken(st["wall"],0.7),(gxp+2,gyp-h-8,5,8))
        pygame.draw.rect(screen,_darken(st["top"],0.8),(gxp+3,gyp-h-9,3,2))
        sm=(int((tick+_hash2(gx,gy)*14)%14))
        pygame.draw.circle(screen,(216,214,220),(gxp+6,gyp-h-14-sm),3)
        pygame.draw.circle(screen,(216,214,220),(gxp+9,gyp-h-18-sm),2)
        pygame.draw.circle(screen,(216,214,220),(gxp+4,gyp-h-20-sm),1)
    elif t=="garden":
        for dx,dy,cc in ((-7,-1,(252,170,190)),(0,2,(250,226,140)),(7,-1,(160,200,240))):
            pygame.draw.circle(screen,cc,(gxp+dx,gyp-h+dy),3)
            pygame.draw.circle(screen,PAL["ink"],(gxp+dx,gyp-h+dy),3,1)
        for i in range(4):
            fx=gxp-TW2+2+i*(((TW2*2)-4)//4)
            pygame.draw.line(screen,_darken(st["wall"],0.9),(fx,gyp-h+2),(fx,gyp+4),2)
    elif t=="library":
        books=[(226,120,120),(120,160,220),(226,200,110),(150,160,220),(226,150,190)]
        for i,cc in enumerate(books):
            f=(i+0.5)/5.0
            px1=gxp-TW2+f*TW2
            pygame.draw.line(screen,cc,(px1,gyp-h+f*TH2-2),(px1,gyp+f*TH2+1),4)
        pygame.draw.rect(screen,(110,92,160),(gxp-3,gyp-2,6,6),border_radius=1)

def draw_resource_anim(screen,overlay,r):
    """资源精灵：离屏 28×28 画布按 v1 形状绘制，再 2× 最近邻放大 blit。
    v1 直接画在 screen 上只有 6-12px，与 2× 小人同框时视觉过小；
    形状/配色逐字沿用 v1，仅基准点从屏幕坐标改为画布内 (14,22)。"""
    gx,gy=r["pos"]; t=r["type"]
    rgx,rgy=grid_ground(gx,gy)                       # 真实屏幕落点
    s=int(min(12,max(6,5+r["amount"]//3)))
    _surf=pygame.Surface((28,28),pygame.SRCALPHA)
    gxp,gyp=14,22                                    # 画布内基准点
    ink=PAL["ink"]
    if t=="food":     # 绿苹果
        pygame.draw.circle(_surf,ink,(gxp,gyp-s//2),4)
        pygame.draw.circle(_surf,(122,206,96),(gxp,gyp-s//2),3)
        pygame.draw.line(_surf,ink,(gxp,gyp-s//2-3),(gxp,gyp-s//2-5),2)
        pygame.draw.ellipse(_surf,(120,196,110),(gxp+1,gyp-s//2-6,5,3))
    elif t=="fruit":  # 红莓
        pygame.draw.circle(_surf,ink,(gxp-3,gyp-s//4),3)
        pygame.draw.circle(_surf,ink,(gxp+3,gyp-s//4),3)
        pygame.draw.circle(_surf,ink,(gxp,gyp-s//4+3),3)
        for cx,cy in ((gxp-3,gyp-s//4),(gxp+3,gyp-s//4),(gxp,gyp-s//4+3)):
            pygame.draw.circle(_surf,(236,110,110),(cx,cy),2)
        pygame.draw.ellipse(_surf,(120,196,110),(gxp-2,gyp-s//2-3,5,3))
    elif t=="water":  # 水滴
        pygame.draw.polygon(_surf,ink,[(gxp,gyp-s),(gxp+3,gyp-s//2),(gxp-3,gyp-s//2)])
        pygame.draw.circle(_surf,(120,196,236),(gxp,gyp-s//2+1),3)
        pygame.draw.circle(_surf,(110,190,236),(gxp,gyp-s//2+1),2)
        pygame.draw.circle(_surf,(238,250,255),(gxp-1,gyp-s//2),1)
    elif t=="wood":   # 木段
        pygame.draw.rect(_surf,ink,(gxp-4,gyp-4,9,5),border_radius=2)
        pygame.draw.rect(_surf,(176,132,80),(gxp-3,gyp-3,7,3),border_radius=2)
        pygame.draw.circle(_surf,(140,100,60),(gxp,gyp-2),2)
        pygame.draw.circle(_surf,(176,132,80),(gxp,gyp-2),1)
    elif t=="stone":  # 矿石
        pygame.draw.polygon(_surf,ink,[(gxp-4,gyp-1),(gxp-2,gyp-4),(gxp+3,gyp-3),(gxp+4,gyp+1),(gxp-1,gyp+2)])
        pygame.draw.polygon(_surf,(150,152,164),[(gxp-4,gyp-1),(gxp-2,gyp-4),(gxp+3,gyp-3),(gxp+4,gyp+1),(gxp-1,gyp+2)])
        pygame.draw.polygon(_surf,(186,188,196),[(gxp-4,gyp-1),(gxp-2,gyp-4),(gxp+1,gyp-3),(gxp-1,gyp+1)])
    elif t=="herb":   # 草药
        pygame.draw.line(_surf,ink,(gxp,gyp),(gxp,gyp-5),2)
        for dx in (-2,0,2):
            pygame.draw.ellipse(_surf,(96,200,128),(gxp+dx-2,gyp-7+(abs(dx)),4,3))
            pygame.draw.ellipse(_surf,ink,(gxp+dx-2,gyp-7+(abs(dx)),4,3),1)
    elif t=="ore":    # 紫晶
        pygame.draw.polygon(_surf,ink,[(gxp-3,gyp),(gxp-1,gyp-5),(gxp+3,gyp-4),(gxp+4,gyp+1),(gxp, gyp+2)])
        pygame.draw.polygon(_surf,(150,110,190),[(gxp-3,gyp),(gxp-1,gyp-5),(gxp+3,gyp-4),(gxp+4,gyp+1),(gxp, gyp+2)])
        pygame.draw.line(_surf,(238,238,255),(gxp-1,gyp-4),(gxp+2,gyp+1),1)
    screen.blit(pygame.transform.scale(_surf,(56,56)),(rgx-28,rgy-44))
    _draw_shadow(overlay,rgx,rgy,16,5)

# ---- NPC 聊天气泡（M2.7 渲染层）----
# 台词为确定性派生：crc32(aid) 错峰开口 + tick 轮换选句，零世界 RNG 消耗；
# 内容四层表格（需求危机 > 位阶台词 > 状态台词 > 通用闲聊），文案 [自创]，
# 世界观名词（职阶/元素）溯源同 demo/vocations.py 口径。
VOCATION_LINES={
    "铁匠":"炉火正好，打铁去","农民":"地里的活不等人","矿工":"井下黑得很",
    "樵夫":"好木在深林","渔夫":"今日鱼汛不错","厨师":"火候差半分",
    "商人":"价钱好商量","行商":"下一站再赚一笔","见习法师":"咒文背到第三段了",
    "法师":"冥想凝核，勿扰","学徒":"师父说，先识字","医者":"伤药还剩三副",
    "酒保":"来杯热的？","吟游诗人":"新编了段谣曲，要听吗","猎户":"林子里有蹄印",
    "守林人":"生木不可乱砍","信使":"加急件，让让！","弓手":"靶心又偏了一寸",
    "剑士":"一日不练手生","骑士":"誓约在身","教堂杂役":"愿光眷顾",
    "教区祭司":"圣事莫迟","教授":"午后答疑","冰晶技师":"网络又结霜了",
    "探界者":"北边有一条新路","符文匠":"这一笔要一气呵成","魔药师":"药材要趁鲜",
    "大商人":"商路即命脉","御风船员":"风向正好","魔工师":"魔晶又该换了",
}

def npc_line(a, tick):
    """NPC 当前应说的台词；返回 None = 本 tick 不开口（错峰窗口外）。"""
    n=a.needs
    crc=zlib.crc32(a.aid.encode("utf-8"))
    if (tick+crc)%360>=110:          # 约 1/3 时间窗口，全员错峰
        return None
    pool=[]
    if n.get("physiology",100)<30: pool=["肚子咕咕叫…","谁有多余的吃的吗","好饿，找点吃的去"]
    elif n.get("safety",100)<30: pool=["晚上不敢出门","想有间自己的屋子"]
    elif n.get("belonging",100)<30: pool=["好久没人跟我说话了","想找个伴"]
    elif n.get("esteem",100)<30: pool=["总得做出点成绩来","没人记得我做过什么"]
    elif a.energy<20: pool=["累瘫了…","得歇口气"]
    elif n.get("self_actualization",50)>=70: pool=["有个想法，想试试","想创作一件东西"]
    if not pool:
        v=getattr(a,"vocation",None)
        if v in VOCATION_LINES:
            pool=[VOCATION_LINES[v]]
        else:
            st=a.state.value
            if st=="resting": pool=["歇一会儿","晒晒太阳真好"]
            elif st=="trading": pool=["成交？","这货紧俏"]
            elif st=="socializing": pool=["天气不错啊","近来可好？"]
            elif st=="learning": pool=["学无止境"]
            elif st=="creating": pool=["灵感来了！"]
            elif st=="working": pool=["活儿干不完哟","再干一会儿"]
            else: pool=["嗯……","今天风挺大"]
        el=getattr(a,"element",None)             # 元素彩蛋混入轮换池
        if el=="火": pool.append("火总得有燃料")
        elif el=="水": pool.append("水是生命之源")
        elif el=="光": pool.append("向着光走")
    return pool[((tick+crc)//120)%len(pool)]

def draw_speech_bubble(screen,font,x,y,text):
    """白色圆角气泡 + 下垂尾巴，画在 (x,y)=气泡锚点（小人头顶上方）。"""
    if font is None or not text: return
    tw=font.size(text)[0]
    bw=tw+12; bh=15
    bx=max(2,min(MAP_W-bw-2,x-bw//2)); by=y-bh
    _rounded(screen,(bx,by,bw,bh),(250,250,246),radius=6,outline=PAL["ink"],ow=1,alpha=235)
    pygame.draw.polygon(screen,(250,250,246),[(x-4,by+bh-1),(x+4,by+bh-1),(x,by+bh+4)])
    pygame.draw.line(screen,PAL["ink"],(x-4,by+bh-1),(x,by+bh+4),1)
    pygame.draw.line(screen,PAL["ink"],(x+4,by+bh-1),(x,by+bh+4),1)
    screen.blit(font.render(text,True,(40,36,48)),(bx+6,by+2))

def draw_agent_anim(screen,overlay,a,selected,tick,world,warn_surf,font=None,allow_bubble=True):
    gx,gy=a.pos.x,a.pos.y
    gxp,gyp=grid_ground(gx,gy)
    if not a.alive:
        _draw_shadow(overlay,gxp,gyp,12,4)
        pygame.draw.rect(screen,(120,124,138),(gxp-6,gyp-9,12,9),border_radius=3)
        pygame.draw.rect(screen,(150,154,168),(gxp-5,gyp-8,10,7),border_radius=3)
        pygame.draw.line(screen,(90,92,104),(gxp-3,gyp-8),(gxp+3,gyp-2),2)
        pygame.draw.line(screen,(90,92,104),(gxp+3,gyp-8),(gxp-3,gyp-2),2)
        return
    state=a.state.value
    _vv=getattr(a,"vocation",None)          # StoryWorld 身份化 NPC：职阶配色+势力徽章
    cloth=pspr.vocation_cloth(_vv) if _vv else COLORS.get("agent_"+state,COLORS["agent_idle"])
    hair=GEN_COLORS[a.generation%len(GEN_COLORS)]
    # 坎公风像素小人：四向行走 / 弹跳步态 / 厚描边（pixel_sprites 渲染，含阴影）。
    # NPC 行走相位由 tick+坐标派生（确定性，不消耗 RNG）；朝向由移动向量维护。
    _moving = (state == "working")
    pspr.draw_chibi(screen, overlay, gxp, gyp, cloth=cloth, hair=hair,
        direction=getattr(a, "facing", "down"),
        phase=((tick * 0.22) + ((abs(gx) * 31 + gy) % 7) * 0.09) % 1.0 if _moving else 0.0,
        state=state, idle_t=tick, hero=False,
        badge=pspr.faction_badge(getattr(a, "faction", None)) if _vv else None,
        aura=pspr.ELEMENT_AURA.get(getattr(a, "element", None)),
        gear=pspr.vocation_gear(_vv) if _vv else None)
    hx, hy = gxp, gyp - 36   # 气泡/爱心/选中框的坐标基准（2× 精灵头顶）
    # 配偶爱心（浮动）
    if a.partner_id:
        p=world.find_agent(a.partner_id)
        if p and p.alive:
            by=hy-20+int(math.sin(tick*0.12)*1.5)
            pygame.draw.circle(screen,(240,110,160),(hx-2,by-1),2)
            pygame.draw.circle(screen,(240,110,160),(hx+2,by-1),2)
            pygame.draw.polygon(screen,(240,110,160),[(hx-3,by-1),(hx+3,by-1),(hx,by+2)])
    # 需求危机气泡
    if min(a.needs.values())<15:
        bx,byy=hx+8,hy-16
        pygame.draw.circle(screen,PAL["ink"],(bx,byy),6)
        pygame.draw.circle(screen,(238,96,84),(bx,byy),5)
        screen.blit(warn_surf,(bx-3,byy-5))
    # 选中框
    if selected and a.aid==selected.aid:
        _rounded(screen,(hx-22,hy-14,44,52),(255,238,120),radius=8,outline=(120,100,30),ow=1)
        _rounded(screen,(hx-21,hy-13,42,50),(255,238,120),radius=8,outline=(255,238,120),ow=2)
    # 聊天气泡（错峰开口，台词确定性轮换；画在最上层；de-clutter 由调用方按网格控制）
    _line=npc_line(a,tick) if allow_bubble else None
    if _line:
        draw_speech_bubble(screen,font,gxp,gyp-60,_line)

def run_era_selection(seed=0):
    import pygame, os
    pygame.init()
    SW,SH=760,620
    screen=pygame.display.set_mode((SW,SH))
    pygame.display.set_caption("选择历史纪元 — 恩利尔大陆")
    def _lf(sz,b=False):
        for p in CJK_FONT_FILES:
            if os.path.exists(p):
                try:
                    f=pygame.font.Font(p,sz); f.set_bold(b); return f
                except Exception: pass
        return pygame.font.SysFont("microsoftyahei,simhei,arial",sz,bold=b)
    ft=_lf(22,True); fm=_lf(14); fs=_lf(12); fh=_lf(13,True)
    eras=EraCalendar.ERAS; sel=7
    CW,CH=350,120; COLS=2; SX=20; SY=70; GAP=12
    pal_bg=(20,22,30); pal_card=(40,44,58); pal_sel=(80,76,30)
    pal_title=(230,210,120); pal_text=(200,200,210); pal_dim=(130,130,145)
    pal_gold=(255,210,80); pal_hint=(160,160,175)
    clock=pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); return "present"
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: pygame.quit(); return "present"
                if ev.key in (pygame.K_UP,pygame.K_w):
                    sel=(sel-COLS)%len(eras)
                elif ev.key in (pygame.K_DOWN,pygame.K_s):
                    sel=(sel+COLS)%len(eras)
                elif ev.key in (pygame.K_LEFT,pygame.K_a):
                    sel=(sel-1)%len(eras)
                elif ev.key in (pygame.K_RIGHT,pygame.K_d):
                    sel=(sel+1)%len(eras)
                elif ev.key in (pygame.K_RETURN,pygame.K_SPACE):
                    pygame.quit(); return eras[sel]["key"]
        screen.fill(pal_bg)
        screen.blit(ft.render("选择历史纪元 — 恩利尔大陆",True,pal_title),(SX,18))
        screen.blit(fs.render("seed=%d  ·  箭元越古远，预演越久，世界状态越演化"%seed,True,pal_dim),(SX,46))
        for i,e in enumerate(eras):
            cx=SX+(i%COLS)*(CW+GAP); cy=SY+(i//COLS)*(CH+GAP)
            bg=pal_sel if i==sel else pal_card
            pygame.draw.rect(screen,bg,(cx,cy,CW,CH),border_radius=8)
            if i==sel: pygame.draw.rect(screen,pal_gold,(cx,cy,CW,CH),width=2,border_radius=8)
            screen.blit(fh.render(e["name"],True,pal_gold if i==sel else pal_title),(cx+12,cy+8))
            ya=cy+38
            for j in range(0,len(e["desc"]),22):
                screen.blit(fm.render(e["desc"][j:j+22],True,pal_text),(cx+12,ya)); ya+=18
            ya+=4
            if e["alpha_years_ago"]>0:
                ya_text="距今 %d 万年前"%e["alpha_years_ago"]
            elif e["key"]=="alpha_dawn":
                ya_text="阿尔法纪元年"
            else:
                ya_text="阿尔法纪 · 当下"
            screen.blit(fs.render(ya_text,True,pal_dim),(cx+12,ya))
            screen.blit(fs.render("预演 %d tick"%e["start_tick"],True,pal_dim),(cx+12,ya+16))
        screen.blit(fs.render("↑↓←→ 选择  ·  Enter 确认  ·  ESC 跳过(默认当下)",True,pal_hint),(SX,SH-28))
        pygame.display.flip(); clock.tick(30)

def run_gui(tps=10, max_ticks=None, seed=0, screenshot=None, start_era=None, config=None,
            auto_story=False):
    import pygame
    from collections import deque
    pygame.init()
    screen=pygame.display.set_mode((WW,WH))
    pygame.display.set_caption("Second Reality v2.0 - Anime World (seed=%d)"%seed)
    import os
    def _load_font(size,bold=False):
        for p in CJK_FONT_FILES:
            if os.path.exists(p):
                try:
                    f=pygame.font.Font(p,size)
                    if bold: f.set_bold(True)
                    return f
                except Exception: pass
        try: return pygame.font.SysFont("microsoftyahei,simhei,notosanscjk,arial",size,bold=bold)
        except Exception: return pygame.font.Font(None,size+2)
    font=_load_font(12); font_b=_load_font(13,True); font_s=_load_font(10)
    font_t=_load_font(16,True)
    clock=pygame.time.Clock()
    config=config or WorldConfig(world_size=WORLD_SIZE,initial_agents=30,initial_resources=80,initial_buildings=8,seed=seed)
    import goal_system as goal_mod
    import factions as story_mod
    world=story_mod.StoryWorld(config)   # 目标层+剧情层随 tick 自动步进（M2.6/M2.7）
    player=world.add_player()
    player.facing=math.pi/2                  # 初始面朝下（像素小人四向）
    player_walk_phase=0.0
    cam_x=0.0; cam_y=0.0
    build_mode=False; build_type="house"
    running=True; paused=False; speed=tps; selected=None; show_help=False
    show_goals=True
    show_heat=True; show_graph=True; show_eventfx=True; show_daynight=True
    sky_surf=build_sky(seed)
    props=terrain_props(seed,world.buildings)          # 林木/岩石/花丛（只画，不参与仿真）
    ground_surf=build_ground(seed,world.buildings)     # 地形 + 广场 + 道路（以初始建筑为准）
    shadow_surf=build_island_shadow()
    overlay=pygame.Surface((MAP_W,MAP_H),pygame.SRCALPHA)
    warn_surf=font_b.render("!",True,(255,255,255))
    fx=[]; feed=deque(maxlen=8)
    hist={"pop":deque(maxlen=240),"gini":deque(maxlen=240),
          "need":deque(maxlen=240),"money":deque(maxlen=240)}
    last_wb=world._wb

    def spawn_fx(gx,gy,txt,col,ttl=28):
        cx,cy=tile_center(gx,gy)
        fx.append({"x":cx,"y":cy,"t":txt,"c":col,"ttl":ttl,"age":0})
        if len(fx)>70: del fx[0]

    def note_events(evts):
        nonlocal last_wb
        for e in evts:
            v=e.etype.value
            if v in EVENT_LABEL:
                feed.append("t%-5d %-4s %s%s"%(e.tick,EVENT_LABEL[v],e.actor,("->"+e.target) if e.target else ""))
            if v in ("marriage","death","trade","violation") and show_eventfx:
                a=world.find_agent(e.actor)
                if a:
                    txt={"marriage":"+","death":"x","trade":"$","violation":"!"}[v]
                    spawn_fx(a.pos.x,a.pos.y,txt,EVENT_COLOR.get(v,(200,200,200)))
        if world._wb>last_wb:
            for a in world.agents[-(world._wb-last_wb):]:
                if show_eventfx: spawn_fx(a.pos.x,a.pos.y,"*",EVENT_COLOR["birth"],36)
                feed.append("t%-5d %-4s %s (gen%d)"%(world._tick,EVENT_LABEL["birth"],a.aid,a.generation))
            last_wb=world._wb

    def draw_heat_glow():
        """财富热力 → 角色脚下的暖光晕（动漫风格化）"""
        if not show_heat: return
        denom=math.log1p(1200.0)
        for a in world.agents:
            if not a.alive: continue
            n=math.log1p(max(0.0,a.wealth))/denom
            if n<=0.02: continue
            gxp,gyp=grid_ground(a.pos.x,a.pos.y)
            col=(255,196,110) if n<0.5 else (255,150,70)
            for rr,al in ((13,22),(9,36),(6,54)):
                pygame.draw.circle(overlay,col+(al,),(gxp,gyp-4),rr)

    def draw_world():
        screen.blit(sky_surf,(0,0))
        screen.blit(shadow_surf,(0,0))
        screen.blit(ground_surf,(0,0))
        overlay.fill((0,0,0,0))
        draw_heat_glow()
        # 关系线（半透明层）
        for a in world.agents:
            if not a.alive: continue
            ax,ay=grid_ground(a.pos.x,a.pos.y)
            if a.partner_id:
                p=world.find_agent(a.partner_id)
                if p and p.alive:
                    px,py=grid_ground(p.pos.x,p.pos.y)
                    pygame.draw.line(overlay,COLORS["partner"]+(120,),(ax,ay),(px,py),2)
            if show_graph:
                for fid in a.friends:
                    if fid<=a.aid: continue
                    f=world.find_agent(fid)
                    if f and f.alive:
                        fx2,fy2=grid_ground(f.pos.x,f.pos.y)
                        pygame.draw.line(overlay,COLORS["friend"]+(54,),(ax,ay),(fx2,fy2),2)
        # 地面阴影（建筑/资源/角色）
        for b in world.buildings:
            gxp,gyp=grid_ground(b["pos"][0],b["pos"][1])
            _draw_shadow(overlay,gxp,gyp,30,8)
        for r in world.resources:
            if r["amount"]<=0: continue
            gxp,gyp=grid_ground(r["pos"][0],r["pos"][1])
            _draw_shadow(overlay,gxp,gyp,12,4)
        for a in world.agents:
            gxp,gyp=grid_ground(a.pos.x,a.pos.y)
            _draw_shadow(overlay,gxp,gyp,22,7)
        # 昼夜/季节色调
        if show_daynight:
            ph=(world._tick%240)/240.0
            tint=_lerp_color((15,25,65),(75,50,10),abs(math.sin(ph*math.pi)))
            overlay.fill(tint+(18,))
        screen.blit(overlay,(0,0))
        # 实体按深度排序（画家算法：近的晚画）
        ents=[]
        for p in props:
            ents.append((p["gx"]+p["gy"],-1,("t",p)))
        for b in world.buildings:
            ents.append((b["pos"][0]+b["pos"][1],0,("b",b)))
        for r in world.resources:
            if r["amount"]<=0: continue
            ents.append((r["pos"][0]+r["pos"][1],1,("r",r)))
        for a in world.agents:
            ents.append((a.pos.x+a.pos.y,2,("a",a)))
        if world.player:
            ents.append((world.player.fx+world.player.fy,3,("p",world.player)))
        ents.sort(key=lambda e:(e[0],e[1]))
        # 气泡去重叠：同一屏幕网格内只让一个开口，选中的必开口
        _bub_ok=set(); _bub_seen={}
        for a in sorted(world.agents,key=lambda x:(x.pos.x+x.pos.y,x.aid)):
            if not a.alive: continue
            gxp,_gyp=grid_ground(a.pos.x,a.pos.y)
            k=gxp//56
            if _bub_seen.get(k): continue
            _bub_seen[k]=1; _bub_ok.add(a.aid)
        if selected and selected.alive: _bub_ok.add(selected.aid)
        for _,_,(kind,obj) in ents:
            if kind=="b": draw_building_anim(screen,overlay,obj,world._tick)
            elif kind=="r": draw_resource_anim(screen,overlay,obj)
            elif kind=="t": draw_prop(screen,overlay,obj,world._tick)
            elif kind=="a": draw_agent_anim(screen,overlay,obj,selected,world._tick,world,warn_surf,font_s,
                    allow_bubble=(obj.aid in _bub_ok))
            else:
                gxp,gyp=grid_ground(obj.pos.x,obj.pos.y)
                pygame.draw.ellipse(screen,(0,0,0),(gxp-15,gyp+2,30,9))
                # 无主角：玩家与居民同一渲染路径；职阶配色+势力徽章+元素光环
                pdir=pspr.dir_from_vector(math.cos(player.facing),math.sin(player.facing))
                _peng=getattr(world,"story_engine",None)
                _pfac=getattr(getattr(_peng,"state",None),"faction",None) if _peng else None
                pspr.draw_chibi(screen,overlay,gxp,gyp,
                    cloth=pspr.vocation_cloth(player.vocation),hair=(110,84,60),
                    direction=pdir,phase=player_walk_phase,state="idle",
                    idle_t=world._tick,hero=False,
                    badge=pspr.faction_badge(_pfac),
                    aura=pspr.ELEMENT_AURA.get(player.element),
                    gear=pspr.vocation_gear(player.vocation))
                if build_mode:
                    pygame.draw.rect(screen,(100,255,100),(gxp-16,gyp-16,32,32),2)
                _pline=("就这里吧…" if build_mode else
                        ("做个买卖？" if player.action_mode=="trade" else None))
                if _pline:
                    draw_speech_bubble(screen,font_s,gxp,gyp-60,_pline)   # 玩家意图气泡
        # 目标标记：活跃目标锁定的 NPC 头顶金色浮标（坎公式任务标记）
        if getattr(world,"goal_generator",None):
            for _g in world.goal_generator.active:
                _aid=_g.context.get("npc_aid") or _g.context.get("friend_aid")
                _ma=world.find_agent(_aid) if _aid else None
                if _ma and _ma.alive:
                    _mx,_my=grid_ground(_ma.pos.x,_ma.pos.y)
                    _my2=_my-30+int(math.sin(world._tick*0.15+_ma.pos.x)*2)
                    pygame.draw.polygon(screen,(255,210,80),[(_mx,_my2-5),(_mx+4,_my2),(_mx,_my2+4),(_mx-4,_my2)])
                    pygame.draw.polygon(screen,PAL["ink"],[(_mx,_my2-5),(_mx+4,_my2),(_mx,_my2+4),(_mx-4,_my2)],1)
        # 事件浮字（带描边）
        for f in fx:
            rise=int(f["age"]*0.4)
            for oxx,oyy in ((1,0),(-1,0),(0,1),(0,-1)):
                screen.blit(font_b.render(f["t"],True,PAL["ink"]),(f["x"]-4+oxx,f["y"]-rise+oyy))
            screen.blit(font_b.render(f["t"],True,f["c"]),(f["x"]-4,f["y"]-rise))

    def draw_need_bar(x,y,val,w=150,h=10):
        _rounded(screen,(x-1,y-1,w+2,h+2),PAL["ink"],radius=int(h/2)+2)
        _rounded(screen,(x,y,w,h),(44,48,70),radius=int(h/2))
        bc=COLORS["need_high"] if val>60 else (COLORS["need_mid"] if val>30 else COLORS["need_low"])
        bw=int(w*min(1.0,val/100))
        if bw>2:
            _rounded(screen,(x,y,bw,h),bc,radius=int(h/2))
            _rounded(screen,(x,y,bw,int(h*0.42)),_lerp_color(bc,(255,255,255),0.45),radius=int(h/2))

    def draw_chart(x,y,w,h,series):
        _rounded(screen,(x,y,w,h),COLORS["chart_bg"],radius=8,outline=(52,56,82),ow=1)
        for dq,col,lab in series:
            if len(dq)<2: continue
            mx=max(max(dq),1e-9); n=len(dq)
            pts=[(x+3+int((w-6)*i/max(1,n-1)),y+h-3-int((h-8)*min(1.0,v/mx))) for i,v in enumerate(dq)]
            pygame.draw.lines(screen,(20,22,40),False,pts,4)
            pygame.draw.lines(screen,col,False,pts,2)
            if pts:
                pygame.draw.circle(screen,col,pts[-1],3)
                pygame.draw.circle(screen,(255,255,255),pts[-1],3,1)

    def draw_chart_legend(x,y,items):
        for k,(dq,col,lab) in enumerate(items):
            pygame.draw.circle(screen,col,(x+5+k*92,y+4),3)
            screen.blit(font_s.render("%s %.2f"%(lab,dq[-1] if dq else 0.0),True,col),(x+12+k*92,y))

    def draw_legend(x0,y0):
        screen.blit(font_b.render("图例",True,(140,190,240)),(x0,y0))
        c1=x0; c2=x0+190; c3=x0+390
        def dot(x,y,col):
            pygame.draw.circle(screen,col,(x+4,y+5),4)
            pygame.draw.circle(screen,PAL["ink"],(x+4,y+5),4,1)
        def head(x,y,t): screen.blit(font_s.render(t,True,(140,175,215)),(x,y))
        y=y0+16; head(c1,y,"agent 状态"); y+=12
        for st,lab in STATE_LABELS.items():
            dot(c1,y,COLORS.get("agent_"+st,COLORS["agent_idle"]))
            screen.blit(font_s.render(lab,True,COLORS["text"]),(c1+12,y)); y+=10
        y+=3; head(c1,y,"发色=代际"); y+=12
        for g in range(4):
            pygame.draw.circle(screen,GEN_COLORS[g],(c1+4,y+5),4)
            screen.blit(font_s.render("gen%d"%g,True,COLORS["text"]),(c1+12,y)); y+=10
        y=y0+16; head(c2,y,"资源（小图标）"); y+=12
        for rt,lab in RES_LABELS.items():
            pygame.draw.circle(screen,COLORS.get(rt,(128,128,128)),(c2+4,y+5),4)
            pygame.draw.circle(screen,(0,0,0),(c2+4,y+5),4,1)
            screen.blit(font_s.render(lab,True,COLORS["text"]),(c2+12,y)); y+=10
        y+=3
        pygame.draw.circle(screen,COLORS["warm"],(c2+4,y+5),4)
        screen.blit(font_s.render("财富热力光圈",True,COLORS["text"]),(c2+12,y))
        y=y0+16; head(c3,y,"建筑"); y+=12
        for bt,lab in BLD_LABELS.items():
            pygame.draw.rect(screen,COLORS.get(bt,(128,128,128)),(c3,y+2,8,8),border_radius=2)
            pygame.draw.rect(screen,(0,0,0),(c3,y+2,8,8),1,border_radius=2)
            screen.blit(font_s.render(lab,True,COLORS["text"]),(c3+12,y)); y+=10
        y+=3; head(c3,y,"事件标记"); y+=12
        for txt,col in [("*",EVENT_COLOR["birth"]),("+",EVENT_COLOR["marriage"]),
                        ("$",EVENT_COLOR["trade"]),("x",EVENT_COLOR["death"]),
                        ("!",(255,90,90))]:
            screen.blit(font_b.render(txt,True,col),(c3,y))
            screen.blit(font_s.render({"*":"出生","+":"结婚","$":"交易","x":"死亡","!":"危机"}[txt],True,COLORS["text"]),(c3+12,y)); y+=10

    def draw_tooltip():
        mx,my=pygame.mouse.get_pos()
        if mx>=MAP_W or my>=MAP_H: return
        g=screen_to_grid(mx,my)
        if not g: return
        gx,gy=g
        for a in world.agents:
            if a.alive and a.pos.x==gx and a.pos.y==gy:
                lines=["%s (%s) gen%d"%(a.name,a.aid,a.generation),
                       "%s  age %d"%(a.state.value,a.age),
                       "wealth %.0f  energy %.0f"%(a.wealth,a.energy),
                       "mem %d  friends %d"%(a.memory.stats()["total_memories"],len(a.friends))]
                tw=max(font_s.size(t)[0] for t in lines)+18
                th=len(lines)*11+16
                tx=min(mx+12,WW-tw-4); ty=min(my+12,WH-th-4)
                _rounded(screen,(tx,ty,tw,th),(16,18,30),radius=8,outline=(110,120,150),ow=1,alpha=235)
                pygame.draw.rect(screen,(245,200,90),(tx+6,ty+4,2,th-8),border_radius=1)
                for i,t in enumerate(lines):
                    screen.blit(font_s.render(t,True,COLORS["text"]),(tx+14,ty+7+i*11))
                return

    def draw_goal_panel():
        """涌现式目标面板（TAB 开关）：活跃目标 + 人话描述 + 剩余时间。"""
        gen=world.goal_generator
        if not show_goals or gen is None: return
        lines=[]
        for g in gen.active[:6]:
            lines.append("◆ %s｜%s"%(g.title,g.describe()))
            lines.append("   剩余 %d tick"%max(0,g.deadline_tick-world._tick))
        if not lines:
            lines.append("（此刻风平浪静——目标会从世界中涌现）")
        _seng=getattr(world,"story_engine",None)
        if _seng is not None:
            _st=_seng.state
            if _st.faction is None:
                lines.append("◆ 剧情：尚未入线——按 U 选择势力或自由线")
            else:
                lines.append("◆ %s·%s"%(story_mod.faction_display(_st.faction),
                    story_mod.stage_display(_st.faction,_st.stage)))
                if _st.quest is not None:
                    lines.append("  · %s｜%s"%(_st.quest.title,_st.quest.describe()))
                    lines.append("     剩余 %d tick"%max(0,_st.quest.deadline_tick-world._tick))
                elif _st.decision is not None:
                    lines.append("  ！分支待抉择——按 U 打开剧情菜单")
                elif _st.line_done:
                    lines.append("  ★ 时间线已完结")
        lines.append("E 交易 · C 创作 · G 赠予 · L 遗产 · U 剧情 · TAB 收起")
        tw=max((font_s.size(l)[0] for l in lines),default=120)+16
        th=len(lines)*11+12
        _rounded(screen,(8,8,tw,th),(16,18,30),radius=8,outline=(110,120,150),ow=1,alpha=215)
        pygame.draw.rect(screen,(245,200,90),(12,12,2,th-8),border_radius=1)
        for i,l in enumerate(lines):
            col=(255,238,150) if l.startswith("◆") else ((150,190,250) if i==len(lines)-1 else COLORS["text"])
            screen.blit(font_s.render(l,True,col),(20,14+i*11))

    def draw_stats():
        px=MAP_W; pw=PANEL_W
        pygame.draw.rect(screen,PAL["panel"],(px,0,pw,WH))
        pygame.draw.rect(screen,PAL["panel_2"],(px,0,4,WH))
        pygame.draw.rect(screen,PAL["gold"],(px+0,0,4,WH))
        y=10
        _rounded(screen,(px+8,y,pw-16,30),(36,40,66),radius=9,outline=(90,96,130),ow=1)
        screen.blit(font_t.render("Second Reality",True,PAL["gold"]),(px+18,y+6))
        screen.blit(font_s.render("世界观控制台 · Anime 2.5D",True,(140,170,215)),(px+150,y+11))
        y+=40
        screen.blit(font.render("Tick %d · %s · seed=%d"%(world._tick,"[暂停]" if paused else "%d tps"%speed,seed),True,PAL["text_dim"]),(px+10,y)); y+=17
        s=world.get_stats()
        def chip(x,cy,lab,val,accent):
            w=82
            _rounded(screen,(x,cy,w,22),(30,34,56),radius=6)
            screen.blit(font_s.render(lab,True,(130,150,185)),(x+6,cy+3))
            vtxt=font_b.render(str(val),True,accent)
            screen.blit(vtxt,(x+w-6-vtxt.get_width(),cy+2))
        chip(px+10,y,"人口",s["alive"],(120,230,255)); chip(px+100,y,"死亡",s["dead"],(200,140,140))
        y+=28
        chip(px+10,y,"出生",s["births"],(140,255,190)); chip(px+100,y,"违规",s["violations"],(255,150,120))
        y+=32
        screen.blit(font.render("财富: %.0f 总 / %.1f 均"%(s["total_wealth"],s["avg_wealth"]),True,PAL["text"]),(px+10,y)); y+=15
        screen.blit(font.render("货币: %.0f  通胀: %.4f"%(s["money_supply"],s["inflation_rate"]),True,PAL["text"]),(px+10,y)); y+=15
        screen.blit(font.render("交易: %d  创造: %.0f"%(s["total_trades"],s["wealth_created"]),True,PAL["text"]),(px+10,y)); y+=15
        screen.blit(font.render("知识: %.1f  创造: %.1f"%(s["avg_knowledge"],s["avg_creativity"]),True,PAL["text"]),(px+10,y)); y+=18
        _rounded(screen,(px+8,y,pw-16,96),(24,27,46),radius=8,outline=(60,66,96),ow=1)
        screen.blit(font_b.render("五层需求（均值）",True,(140,190,240)),(px+16,y+5)); y+=22
        for i,n in enumerate(FIVE_LAYER_NEEDS):
            screen.blit(font_s.render(NEED_LABELS_CN[i],True,PAL["text"]),(px+16,y))
            draw_need_bar(px+52,y,s["avg_needs"][n],pw-78); y+=13
        y+=6
        screen.blit(font_b.render("实时曲线（各自归一化）",True,(140,190,240)),(px+10,y)); y+=14
        draw_chart_legend(px+10,y,[(hist["pop"],COLORS["curve_pop"],"人口"),
            (hist["gini"],COLORS["curve_gini"],"基尼")]); y+=13
        draw_chart(px+10,y,pw-20,56,[(hist["pop"],COLORS["curve_pop"],"人口"),
            (hist["gini"],COLORS["curve_gini"],"基尼")]); y+=60
        draw_chart_legend(px+10,y,[(hist["need"],COLORS["curve_need"],"需求"),
            (hist["money"],COLORS["curve_money"],"货币")]); y+=13
        draw_chart(px+10,y,pw-20,56,[(hist["need"],COLORS["curve_need"],"需求"),
            (hist["money"],COLORS["curve_money"],"货币")]); y+=60
        _rounded(screen,(px+8,y,pw-16,14+6*10),(24,27,46),radius=8,outline=(60,66,96),ow=1)
        screen.blit(font_b.render("事件流",True,(140,190,240)),(px+16,y+4)); y+=16
        for line in list(feed)[-6:]:
            screen.blit(font_s.render(line[:34],True,(150,168,200)),(px+16,y)); y+=10
        y+=6
        if selected:
            a=selected
            _rounded(screen,(px+8,y,pw-16,52),(40,36,60),radius=8,outline=(120,110,80),ow=1)
            if not a.alive:
                screen.blit(font_b.render("[已故] %s (%s)"%(a.name,a.aid),True,COLORS["agent_dead"]),(px+16,y+6)); y+=52
            else:
                screen.blit(font_b.render("%s (%s) gen%d"%(a.name,a.aid,a.generation),True,(255,238,150)),(px+16,y+6))
                screen.blit(font_s.render("状态: %s  年龄: %d"%(a.state.value,a.age),True,PAL["text"]),(px+16,y+22))
                screen.blit(font_s.render("财富: %.0f  精力: %.0f"%(a.wealth,a.energy),True,PAL["text"]),(px+16,y+36))
                _prt=pspr.chibi_portrait(COLORS.get("agent_"+a.state.value,COLORS["agent_idle"]),
                    GEN_COLORS[a.generation%len(GEN_COLORS)],state=a.state.value,scale=2,
                    gear=pspr.vocation_gear(getattr(a,"vocation",None)))
                screen.blit(_prt,(px+pw-56,y+2))
                y+=52
                screen.blit(font.render("声望: %.0f  知识: %.1f"%(a.reputation,a.knowledge),True,PAL["text"]),(px+10,y)); y+=14
                ms=a.memory.stats()
                screen.blit(font.render("记忆: %d (S:%d L:%d) 创造: %.1f"%(ms["total_memories"],ms["stm_count"],ms["ltm_count"],a.creativity),True,PAL["text"]),(px+10,y)); y+=14
                for i,n in enumerate(FIVE_LAYER_NEEDS):
                    screen.blit(font_s.render(NEED_LABELS_CN[i],True,PAL["text"]),(px+10,y))
                    draw_need_bar(px+50,y,a.needs[n],pw-78,h=7); y+=11
                y+=4
                inv_str=str(dict(a.inventory)) if a.inventory else "无"
                screen.blit(font_s.render("物品: "+inv_str,True,PAL["text_dim"]),(px+10,y)); y+=13
                if a.partner_id:
                    p=world.find_agent(a.partner_id); pn=p.name if p else "?"
                    screen.blit(font_s.render("配偶: %s  好友: %d  子女: %d"%(pn,len(a.friends),len(a.children_ids)),True,PAL["text"]),(px+10,y)); y+=13
                recent=a.memory.recall(k=3)
                if recent:
                    screen.blit(font_s.render("最近记忆:",True,(150,190,250)),(px+10,y)); y+=11
                    for m in recent[:3]:
                        screen.blit(font_s.render("  "+m.content[:25],True,(140,162,196)),(px+10,y)); y+=10
        if world.player:
            p=world.player
            _rounded(screen,(px+8,y,pw-16,162),(40,44,66),radius=8,outline=(90,96,130),ow=1)
            _voc=("%s ·%s"%(p.vocation,voc.RARITY_NAMES.get(p.vocation_tier,"凡阶"))) if p.vocation else "未抽签"
            # 魔力特性不分级：不再显示稀有度后缀，只显示名称与效果
            _aff=((p.affinity+("｜"+p.affinity_text if p.affinity_text else ""))) if p.affinity else "未觉醒"
            _elm=p.element if p.element else "—"
            screen.blit(font_b.render("居民（你）｜元素：%s"%_elm,True,(150,220,255)),(px+16,y+5)); y+=19
            screen.blit(font_b.render("职阶：%s"%_voc,True,
                voc.RARITY_COLORS.get(p.vocation_tier,(225,232,248))),(px+16,y)); y+=18
            screen.blit(font_s.render("魔力特性：%s"%_aff,True,(170,190,225)),(px+16,y)); y+=13
            screen.blit(font_s.render("位阶：%s"%p.rank_title(),True,(255,238,150)),(px+16,y)); y+=14
            for _lab,_val in (("魔力",p.magic_rank),("体能",p.body_rank),("灵魂",p.soul_strength)):
                screen.blit(font_s.render("%s %d"%(_lab,_val),True,PAL["text"]),(px+16,y))
                draw_need_bar(px+58,y,_val/10.0*100,pw-96,h=7); y+=11
            y+=2
            screen.blit(font.render("坐标: (%.1f, %.1f)  精力: %.0f  年龄: %d"%(p.fx,p.fy,p.energy,p.age),True,PAL["text"]),(px+10,y)); y+=14
            screen.blit(font.render("财富: %.0f  模式: %s"%(p.wealth,p.action_mode),True,PAL["text"]),(px+10,y)); y+=14
            if build_mode: screen.blit(font_s.render("建造: %s (左键放置, B切换)"%build_type,True,(140,170,215)),(px+10,y)); y+=12
            inv_str=str(dict(p.inventory)) if p.inventory else "无"
            screen.blit(font_s.render("背包: "+inv_str,True,PAL["text_dim"]),(px+10,y)); y+=12
            if p.owned_buildings: screen.blit(font_s.render("资产: %d 处房产"%len(p.owned_buildings),True,(255,220,100)),(px+10,y)); y+=12
        hy=MAP_H+5
        screen.blit(font_s.render(
            "方向键移动 | 左键采集/选人 | E交易 C创作 G赠予 L遗产 U剧情 | Q建造 B切换 | TAB目标 SPACE暂停 R重置 H帮助"[:86],
            True,(150,150,170)),(10,hy))
        draw_legend(10,hy+18)

    def handle_click(pos):
        nonlocal selected
        mx,my=pos
        if mx<MAP_W and my<MAP_H:
            g=screen_to_grid(mx,my)
            if not g: return
            gx,gy=g
            for a in world.agents:
                if a.alive and a.pos.x==gx and a.pos.y==gy:
                    selected=a; return
            selected=None

    # —— 交互键（坎公式：一个 E 键管上下文交互）——
    def _nearest_trade_npc(radius=None):
        if radius is None:
            radius=2.5+player.vocation_effects.get("trade_radius",0.0)   # 空间/行商/向导
        best=None
        for a in world.agents:
            if a.alive and a.inventory:
                d=math.hypot(a.pos.x-player.fx,a.pos.y-player.fy)
                if d<=radius and (best is None or d<best[0]): best=(d,a)
        return best[1] if best else None
    def _do_interact():
        a=_nearest_trade_npc()
        if a is None:
            feed.append("附近没有可交易的 NPC（走近持货居民再按 E）")
            spawn_fx(int(round(player.fx)),int(round(player.fy)),"…",(255,150,150))
            return
        result=player.trade(a,world)
        if result:
            feed.append("Traded %s for %d"%(result[0],result[1]))
            spawn_fx(a.pos.x,a.pos.y,"$",EVENT_COLOR["trade"])
        else:
            feed.append("Trade failed（没钱或对方无货）")
            spawn_fx(int(round(player.fx)),int(round(player.fy)),"✗",(255,120,120))
    def _do_create():
        if not player.inventory:
            feed.append("背包为空——先采集材料（左键）"); return
        title="作品#%d"%world._tick
        aid,ch=player.create_work(world,title)
        if aid:
            feed.append("创作《%s》 asset=%s"%(title,aid[:18]))
            spawn_fx(int(round(player.fx)),int(round(player.fy)),"✦",(255,230,120))
    def _do_legacy():
        best=None
        for a in world.agents:
            if (not a.alive) and a.wealth>0:
                if best is None or a.wealth>best.wealth: best=a
        if best is None:
            feed.append("附近没有待结算的遗产"); return
        res=goal_mod.settle_legacy(world,best.aid,by=player.pid)
        if res:
            player.gain_xp("soul",5)         # 三成长·灵魂：送行
            feed.append("遗产 %.0f → %s"%(res["amount"],
                ("继承:"+res["heir"]) if res["route"]=="heir" else "国库"))
            spawn_fx(best.pos.x,best.pos.y,"❦",(230,200,120))
    def _do_give():
        best=None
        for a in world.agents:
            if not a.alive: continue
            mn=min(a.needs[n] for n in FIVE_LAYER_NEEDS)
            d=math.hypot(a.pos.x-player.fx,a.pos.y-player.fy)
            if d<=3.0 and mn<40 and (best is None or mn<best[0]): best=(mn,a)
        if best is None:
            feed.append("附近没有陷入困境的 NPC"); return
        a=best[1]
        item=None
        for t in ("food","water","fruit"):
            if player.inventory.get(t,0)>0: item=t; break
        if item is None and player.inventory:
            item=sorted(player.inventory.keys())[-1]
        if item is None:
            feed.append("背包为空——无物可赠"); return
        player.inventory[item]-=1
        if player.inventory[item]<=0: del player.inventory[item]
        _boost=30.0*(1.0+player.vocation_effects.get("give_bonus",0.0))   # 慈悲者：赠予+15%
        if item in ("food","water","fruit"):
            a.needs["physiology"]=min(100.0,a.needs["physiology"]+_boost)
        else:
            a.needs["belonging"]=min(100.0,a.needs["belonging"]+_boost)
        a.memory.remember("收到 %s 赠予"%item,0.6,"grateful",["gift"])
        player.gain_xp("soul",3)             # 三成长·灵魂：赠予
        feed.append("赠予 %s 一件 %s"%(a.name,item))
        spawn_fx(a.pos.x,a.pos.y,"♥",(255,140,180))

    # —— 剧情菜单（U 键：入会决策 / 分支选择 / 时间线详情，M2.7）——
    story_menu=None; story_sel=0; story_items=[]
    def _story_open():
        nonlocal story_menu, story_sel, story_items
        eng=getattr(world,"story_engine",None)
        if eng is None:
            feed.append("剧情层未挂载"); return
        st=eng.state
        if st.decision is not None:
            story_items=[(c["label"],"分支节点 · 第 %d 阶完成"%(st.decision["stage"]+1),
                          ("decide",c["key"])) for c in st.decision["choices"]]
            story_menu="branch"
        elif st.faction is None:
            story_items=[]
            for k in eng.offers():
                if k==story_mod.FREELANCE_KEY:
                    _lab="【自由职业线】不入任何势力"
                else:
                    _lab="加入 "+story_mod.faction_display(k)
                story_items.append((_lab,"职阶「%s」的资格线"%player.vocation,("join",k)))
            story_menu="join"
        else:
            story_menu="info"
        story_sel=0

    def _wrap_cn(t,n):
        return [t[i:i+n] for i in range(0,len(t),n)] or [""]

    def draw_story_menu():
        if story_menu is None: return
        eng=getattr(world,"story_engine",None)
        if eng is None: return
        st=eng.state
        dim=pygame.Surface((MAP_W,MAP_H),pygame.SRCALPHA); dim.fill((8,10,22,150))
        screen.blit(dim,(0,0))
        cw=520
        if story_menu=="info":
            lines=[]
            _fn=story_mod.faction_display(st.faction) if st.faction else "未入线"
            _sn=story_mod.stage_display(st.faction,st.stage) if st.faction else ""
            lines.append(("◆ 时间线 · %s · %s"%(_fn,_sn),(255,238,150)))
            if st.line_done:
                for _seg in _wrap_cn(st.line_lore,46): lines.append((_seg,(255,220,130)))
            else:
                if st.quest is not None:
                    for _seg in _wrap_cn("【%s】%s"%(st.quest.title,st.quest.describe()),46):
                        lines.append((_seg,(230,240,255)))
                    for _seg in _wrap_cn(st.quest.lore,46):
                        lines.append(("   "+_seg,(150,168,205)))
                    lines.append(("   剩余 %d tick"%max(0,st.quest.deadline_tick-world._tick),(150,168,205)))
                if st.decision is not None:
                    lines.append(("！分支待抉择——按 E 进入选择",(255,190,110)))
                lines.append(("节点记录 %d 条 · 锁死势力：%s"%(len(st.history),
                    "、".join(story_mod.faction_display(k) for k in st.locked) or "无"),(150,168,205)))
            chh=56+len(lines)*13
            bx=(MAP_W-cw)//2; by=(MAP_H-chh)//2
            _rounded(screen,(bx,by,cw,chh),(16,18,30),radius=10,outline=(120,130,170),ow=1,alpha=240)
            for i,(t,c) in enumerate(lines):
                screen.blit(font_s.render(t,True,c),(bx+16,by+12+i*13))
            screen.blit(font_s.render("U / Esc 关闭",True,(140,150,180)),(bx+16,by+chh-16))
        else:
            _title=("分支选择——这条时间线从此处改变" if story_menu=="branch"
                    else "入会决策——选择你的剧情线")
            chh=70+len(story_items)*34
            bx=(MAP_W-cw)//2; by=(MAP_H-chh)//2
            _rounded(screen,(bx,by,cw,chh),(16,18,30),radius=10,outline=(120,130,170),ow=1,alpha=240)
            screen.blit(font_b.render(_title,True,(255,238,150)),(bx+18,by+12))
            for i,(lab,desc,_act) in enumerate(story_items):
                iy=by+40+i*34
                sel=(i==story_sel)
                _rounded(screen,(bx+12,iy,cw-24,30),(60,64,100) if sel else (30,34,56),
                         radius=7,outline=(255,220,120) if sel else (70,78,110),ow=1)
                screen.blit(font_b.render(("▶ " if sel else "　 ")+lab,True,
                    (255,240,180) if sel else (210,220,240)),(bx+22,iy+7))
                screen.blit(font_s.render(desc,True,(150,168,205)),
                            (bx+cw-16-font_s.size(desc)[0],iy+10))
            screen.blit(font_s.render("W/S 选择 · E / 回车 确认 · U / Esc 关闭",True,(140,150,180)),
                        (bx+18,by+chh-16))

    def sample_history():
        s=world.get_stats()
        hist["pop"].append(s["alive"])
        hist["gini"].append(_gini([a.wealth for a in world.agents if a.alive]))
        hist["need"].append(sum(s["avg_needs"].values())/len(s["avg_needs"]))
        hist["money"].append(s["money_supply"])

    if screenshot:
        _seng=getattr(world,"story_engine",None)
        if _seng is not None and auto_story:
            _ok,_msg=story_mod.story_join(world,_seng.offers()[0])
            print("[auto-story] %s"%_msg)          # 验收注入：自动入线
        for _ in range(max_ticks or 600):
            note_events(world.tick()); sample_history()
        for _ in range(8): sample_history()
        del fx[:-8]
        if _seng is not None and auto_story:
            _story_open()                          # 验收注入：打开剧情菜单
        draw_world(); draw_stats(); draw_goal_panel(); draw_story_menu(); pygame.display.flip()
        pygame.image.save(screen,screenshot)
        print("Screenshot saved: %s (tick=%d)"%(screenshot,world._tick))
        pygame.quit(); return world

    while running:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            elif ev.type==pygame.KEYDOWN:
                if story_menu is not None:
                    # 菜单态吞掉按键：W/S/E 不再触发热力图/存档/交互
                    if ev.key in (pygame.K_u,pygame.K_ESCAPE): story_menu=None
                    elif ev.key in (pygame.K_UP,pygame.K_w): story_sel=max(0,story_sel-1)
                    elif ev.key in (pygame.K_DOWN,pygame.K_s):
                        story_sel=min(len(story_items)-1,story_sel+1)
                    elif ev.key in (pygame.K_e,pygame.K_RETURN,pygame.K_SPACE):
                        if story_menu=="info":
                            story_menu=None
                        elif story_items:
                            _lab,_desc,_act=story_items[max(0,story_sel)]
                            _ok,_m=(story_mod.story_join(world,_act[1])
                                    if _act[0]=="join" else story_mod.story_decide(world,_act[1]))
                            feed.append(("✓ " if _ok else "✗ ")+_m)
                            if _ok:
                                spawn_fx(int(round(player.fx)),int(round(player.fy)),
                                         "★",(255,230,120))
                            _story_open()
                    continue
                if ev.key==pygame.K_SPACE: paused=not paused
                elif ev.key in (pygame.K_EQUALS,pygame.K_PLUS,pygame.K_KP_PLUS): speed=min(60,speed+5)
                elif ev.key in (pygame.K_MINUS,pygame.K_KP_MINUS): speed=max(1,speed-5)
                elif ev.key==pygame.K_s: world.save_state("second_reality_save.json"); print("Saved")
                elif ev.key==pygame.K_h: show_help=not show_help
                elif ev.key==pygame.K_w: show_heat=not show_heat
                elif ev.key==pygame.K_f: show_graph=not show_graph
                elif ev.key==pygame.K_v: show_eventfx=not show_eventfx
                elif ev.key==pygame.K_TAB: show_goals=not show_goals
                elif ev.key==pygame.K_u: _story_open()
                elif ev.key==pygame.K_e: _do_interact()
                elif ev.key==pygame.K_c: _do_create()
                elif ev.key==pygame.K_g: _do_give()
                elif ev.key==pygame.K_l: _do_legacy()
                elif ev.key==pygame.K_n: show_daynight=not show_daynight
                elif ev.key==pygame.K_p:
                    shot="second_reality_%06d.png"%world._tick
                    pygame.image.save(screen,shot); print("Screenshot saved: "+shot)
                elif ev.key==pygame.K_r: world=story_mod.StoryWorld(config); player=world.add_player(); selected=None; fx.clear(); feed.clear(); story_menu=None
                elif ev.key==pygame.K_q:
                    build_mode=not build_mode
                    player.action_mode="build" if build_mode else "observe"
                elif ev.key==pygame.K_b:
                    if build_mode:
                        bt_list=["house","market","workshop","garden","library"]
                        bi=bt_list.index(build_type) if build_type in bt_list else 0
                        build_type=bt_list[(bi+1)%len(bt_list)]
                elif ev.key==pygame.K_t:
                    player.action_mode="trade" if player.action_mode!="trade" else "observe"
            elif ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                handle_click(ev.pos)
                if player.action_mode=="build":
                    if player.build(world,build_type):
                        aid,ch=world.assets.register("building",player.pid,
                            {"type":build_type,"pos":player.pos.__dict__,"tick":world._tick})
                        feed.append("Built %s  asset=%s"%(build_type,aid[:20]))
                    else: feed.append("Cannot build here")
                elif player.action_mode=="trade":
                    gx=ev.pos[0]//CELL; gy=ev.pos[1]//CELL
                    for a in world.agents:
                        if a.alive and a.pos.x==gx and a.pos.y==gy:
                            result=player.trade(a,world)
                            if result: feed.append("Traded %s for %d"%(result[0],result[1]))
                            else: feed.append("Trade failed")
                            break
                else:
                    rt,g=player.gather(world)
                    if rt: feed.append("Gathered %dx %s"%(g,rt))
        keys=pygame.key.get_pressed()
        dx=(1 if keys[pygame.K_RIGHT] else 0)-(1 if keys[pygame.K_LEFT] else 0)
        dy=(1 if keys[pygame.K_DOWN] else 0)-(1 if keys[pygame.K_UP] else 0)
        if story_menu is not None: dx=dy=0          # 菜单态：W/S 是菜单导航，封锁移动
        if dx!=0 or dy!=0:
            player.move(dx,dy,world.size)
            player_walk_phase=(player_walk_phase+0.22)%1.0   # 行走相位→四帧步态
            if player.energy<5: player.rest()
        if not paused:
            note_events(world.tick()); sample_history()
            for _tr in getattr(world,"last_goal_transitions",[]) or []:
                if _tr["status"]=="active":
                    feed.append("★ 新目标：%s"%_tr["title"])
                    spawn_fx(int(round(player.fx)),int(round(player.fy)),"★",(255,230,120))
                else:
                    _ic={"completed":"✓","failed":"✗","expired":"⌛"}.get(_tr["status"],"·")
                    feed.append("%s %s %s"%(_ic,_tr["title"],_tr.get("reason","")))
                    if _tr["status"]=="completed":
                        player.gain_xp("soul",2)     # 三成长·灵魂：目标达成
                        if show_eventfx:
                            spawn_fx(int(round(player.fx)),int(round(player.fy)),"✓",(130,255,160))
            if max_ticks and world._tick>=max_ticks: running=False
        for f in fx: f["age"]+=1
        fx=[f for f in fx if f["age"]<f["ttl"]]
        draw_world(); draw_stats(); draw_tooltip(); draw_goal_panel(); draw_story_menu(); pygame.display.flip()
        clock.tick(speed if speed>0 else 0)
    pygame.quit()
    return world

def build_demo_config(agents=None, world_size=None, resources=None, buildings=None, seed=0):
    """按人口规模配平世界。

    硬约束：_regenerate_resources 把资源总量锁在 size²×8%，
    因此 1000 人必须配上约 200×200 的图（上限 3200），否则资源不够必然饥荒。
    资源密度沿用旧基准：80 资源 / 30 人 ≈ 2.67 每人。
    agents=None 时完全沿用旧默认（60×60/30/80/8），旧世界轨迹一字节不变。
    """
    if agents is None:
        return WorldConfig(world_size=world_size or 60,initial_agents=30,
            initial_resources=resources if resources is not None else 80,
            initial_buildings=buildings if buildings is not None else 8,seed=seed)
    n=max(1,int(agents))
    ws=int(world_size) if world_size is not None else max(60,int(math.ceil(math.sqrt(n*40.0))))
    cap=int(ws*ws*0.08)
    want=int(resources) if resources is not None else int(round(n*80.0/30.0))
    res=min(want,cap)
    bld=int(buildings) if buildings is not None else max(8,n//4)
    cfg=WorldConfig(world_size=ws,initial_agents=n,initial_resources=res,
        initial_buildings=bld,seed=seed)
    cfg._demo_note={"requested_resources":want,"resource_cap":cap,"capped":want>cap}
    return cfg

def _print_demo_note(cfg):
    note=getattr(cfg,"_demo_note",None)
    if note and note.get("capped"):
        print("[warn] 资源需求 %d 超过本图上限 %d（size²×8%%），已截为上限；\n"
              "       人口密度过高会导致饥荒，请同时放大 --world-size。"
              % (note["requested_resources"],note["resource_cap"]))

def run_headless(ticks=1000, verbose=False, seed=0, config=None):
    config=config or WorldConfig(world_size=60,initial_agents=30,initial_resources=80,initial_buildings=8,seed=seed)
    world=NohnWorld(config)
    t0=time.time()
    for i in range(ticks):
        world.tick()
        if verbose and (i+1)%100==0:
            s=world.get_stats()
            print("Tick %d: Pop=%d AvgW=%.1f Phys=%.0f Safe=%.0f Know=%.1f Resid=%.2e"%(
                i+1,s["alive"],s["avg_wealth"],s["avg_needs"]["physiology"],s["avg_needs"]["safety"],
                s["avg_knowledge"],s["money_residual"]))
    el=time.time()-t0; s=world.get_stats(); r=world.get_simulation_metrics()
    print("\n=== Simulation Complete (%d ticks, %.1fs, seed=%d) ==="%(ticks,el,seed))
    print("State hash (sha256): %s"%world.state_hash())
    print("Population: %d alive / %d dead  Births: %d  Deaths: %d"%(s["alive"],s["dead"],s["births"],s["deaths"]))
    print("Wealth: %.0f total / %.1f avg  Created: %.0f  Trades: %d"%(s["total_wealth"],s["avg_wealth"],s["wealth_created"],s["total_trades"]))
    print("Money: supply=%.0f treasury=%.0f inflation=%.4f violations=%d"%(
        s["money_supply"],s["treasury"],s["inflation_rate"],s["violations"]))
    print("Conservation residual: %.3e  (=0 时 Σwealth+treasury+inflation_created+genesis_unallocated == money_supply)"%s["money_residual"])
    print("Knowledge: %.1f  Creativity: %.1f  Total memories: %d"%(s["avg_knowledge"],s["avg_creativity"],s["total_memory"]))
    needs_str="  ".join("%s=%.0f"%(NEED_LABELS_CN[i],s["avg_needs"][n]) for i,n in enumerate(FIVE_LAYER_NEEDS))
    print("Five-layer needs:",needs_str)
    print("\nSimulation self-metrics (NOT constitutional audit): %.1f/100"%r["overall_score"])
    for dim,sc in r["dimensions"].items(): print("  %s: %.1f"%(dim,sc))
    return world

def verify_determinism(ticks=300, seed=42, agents=None, world_size=None):
    """同 (config, seed) 跑两遍互相独立的世界，比对状态指纹——对外可复现性的当场证据。"""
    def run_once():
        w=NohnWorld(build_demo_config(agents=agents,world_size=world_size,seed=seed))
        for _ in range(ticks): w.tick()
        return w.state_hash()
    h1,h2=run_once(),run_once()
    ok=(h1==h2)
    print("=== Determinism verification (seed=%d, %d ticks) ==="%(seed,ticks))
    print("  run#1 state hash: %s"%h1)
    print("  run#2 state hash: %s"%h2)
    print("  VERDICT: %s"%("PASS - identical byte-for-byte" if ok else "FAIL - world is not reproducible"))
    return ok

def print_constitutional_audit(world):
    """对本世界跑宪法级 25 项审计并打印结论。

    演示层不改写、不豁免任何一项：未通过就是未通过。
    下面三段「如实声明」是**原因说明**，不是申诉——记录的是演示层的真实边界。
    """
    try:
        report=world.run_constitutional_audit()
    except Exception as exc:
        print("=== 宪法审计无法执行：%s"%exc)
        print("  审计层 audit_engine 依赖 system/（鉴权六层自测 + 可选二阶因果内核）。")
        print("  请在仓库根目录运行：python demo/virtual_world.py --headless --ticks N --audit")
        return None
    print("\n"+report.summary())
    print("\n--- 宪法侧状态（不进入 state_hash，仅供审计与取证）---")
    print(json.dumps(world.export_constitution_state(),ensure_ascii=False,indent=2,default=str))
    print("\n--- 演示层如实声明：以下未通过项是真实结论，不是待修 bug ---")
    print("  1) interoperable / economic_compliance：本演示世界是封闭虚拟经济，")
    print("     未与现实法币 1:1 锚定、无现实赎回通道、未接入预言机；")
    print("     宪法层据此在「并网审查（第九条）」与「经济法」两层判失败。")
    print("     让它们通过的正确做法是接入 system/ 的真实经济实现，而不是改判定。")
    print("  2) identity_compliance：演示层不生成真实 Ed25519 密钥对（依赖 cryptography），")
    print("     也不拿随机字节冒充公钥（那只是形式合规），故公钥绑定校验失败。")
    print("     真实密钥链路见 system/keys.py。")
    print("  3) auth_security / causal_second_perspective：由审计层对 system/ 自测，")
    print("     与本演示世界的逻辑无关（审计层使用 :memory: 隔离账本，不碰本世界账本）。")
    return report

if __name__=="__main__":
    import argparse, sys, os
    try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台默认 GBK，会把中文输出打成乱码
    except Exception: pass
    ap=argparse.ArgumentParser(description="Second Reality v2.0 - Virtual World Model (Anime 2.5D)")
    ap.add_argument("--headless",action="store_true",help="run without GUI")
    ap.add_argument("--ticks",type=int,default=1000,help="ticks to simulate (headless / determinism / screenshot)")
    ap.add_argument("--seed",type=int,default=0,help="world RNG seed; same seed + same config => reproducible")
    ap.add_argument("--metrics",action="store_true",
        help="print machine-readable simulation self-metrics (NOT the constitutional 25-dim audit)")
    ap.add_argument("--verify-determinism",action="store_true",
        help="run two independent same-seed worlds and compare state hashes")
    ap.add_argument("--audit",action="store_true",
        help="run the 25-dim constitutional audit (audit_engine.SecondPerspectiveAuditor) "
             "on the simulated world; unmet dimensions are reported as-is")
    ap.add_argument("--auto-story",action="store_true",
                    help="screenshot 模式：自动入线并打开剧情菜单（GUI 验收用）")
    ap.add_argument("--screenshot",metavar="PATH",
        help="render one frame to PNG and exit (no display needed: forces SDL_VIDEODRIVER=dummy)")
    ap.add_argument("--agents",type=int,default=None,
        help="人口规模（如 1000）。给定后自动配平 world-size / 资源 / 建筑；不给定则沿用旧默认 30")
    ap.add_argument("--world-size",type=int,default=None,help="地图边长（格）；1000 人建议 200")
    ap.add_argument("--resources",type=int,default=None,help="初始资源数（默认按人口配平，受 size²×8%% 上限约束）")
    ap.add_argument("--buildings",type=int,default=None,help="初始建筑数")
    ap.add_argument("--tps",type=int,default=10,help="GUI 每秒 tick 数")
    args=ap.parse_args()
    demo_cfg=build_demo_config(agents=args.agents,world_size=args.world_size,
        resources=args.resources,buildings=args.buildings,seed=args.seed)
    # GUI 渲染器的地图边长写死在 WORLD_SIZE=60（等距投影按该常量算屏幕坐标）。
    # 若按 1000 人自动配成 200×200，投射后大半智能体会落在画布外——看得见的世界
    # 与跑着的世界不一致，这是"演示骗人"的典型形态。故演示路径强制地图边长 = WORLD_SIZE，
    # 并把资源压在上限内；要跑 200×200 请加 --headless。
    if (not args.headless) and args.world_size is None and args.agents:
        demo_cfg=build_demo_config(agents=args.agents,world_size=WORLD_SIZE,
            resources=args.resources,buildings=args.buildings,seed=args.seed)
        print("[info] GUI 演示的地图锁定 %d×%d（渲染器常量）；资源受 %d 上限约束。"
              "算力更大的世界请用 --headless --world-size N。"
              % (WORLD_SIZE,WORLD_SIZE,demo_cfg.initial_resources))
    if args.verify_determinism:
        raise SystemExit(0 if verify_determinism(ticks=args.ticks,seed=args.seed,
            agents=args.agents,world_size=args.world_size) else 1)
    if args.screenshot:
        os.environ.setdefault("SDL_VIDEODRIVER","dummy")   # 必须在 pygame.init() 之前设置
        run_gui(tps=args.tps,seed=args.seed,max_ticks=args.ticks,screenshot=args.screenshot,config=demo_cfg,
                auto_story=args.auto_story)
        raise SystemExit(0)
    _print_demo_note(demo_cfg)
    world=run_headless(args.ticks,verbose=True,seed=args.seed,config=demo_cfg) if args.headless else run_gui(tps=args.tps,seed=args.seed,config=demo_cfg)
    if args.metrics:
        print(json.dumps(world.get_simulation_metrics(),ensure_ascii=False,indent=2,default=str))
    if args.audit:
        print_constitutional_audit(world)