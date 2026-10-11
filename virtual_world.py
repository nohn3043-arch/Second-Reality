#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Second Reality v2.0 - Virtual World Model
Aligned with system/ layer: 5-layer needs + memory + compliant economy + perceive/think/act
Self-contained: pure in-memory simulation, runs GUI/headless standalone

分工声明（防止审计口径被混称）：
  - 本文件 = 社会仿真「演示逻辑层」，只依赖标准库，不 import system/。
    system/runtime.py 是本文件逻辑的服务化/可部署形态（见该文件头部说明）。
  - get_simulation_metrics() 是「仿真自评」，不是宪法审计。
    宪法级 19 项审计由 audit_engine.SecondPerspectiveAuditor().audit_world(world) 提供。
  - 全局确定性：所有随机数统一走 NohnWorld._rng（由 WorldConfig.seed 播种）。
    同一 (config, seed) => 世界状态逐字节可复现，可用 NohnWorld.state_hash() 取证。
"""
import random, math, time, json, hashlib
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional
from enum import Enum

FIVE_LAYER_NEEDS = ["physiology","safety","belonging","esteem","self_actualization"]
NEED_LABELS_CN = ["生理","安全","归属","尊重","自我实现"]
NEED_DECAY = {"physiology":0.3,"safety":0.2,"belonging":0.3,"esteem":0.2,"self_actualization":0.15}
UBI_DAILY=10.0; TAX_RATE=0.05; INFLATION_RATE=0.02; DEBT_LIMIT=-500.0
MAX_WEALTH=100000.0; WEALTH_HARDCAP_TAX=0.5
MEM_STM=20; MEM_LTM=200; MEM_CONSOL=0.3; MEM_DECAY=0.05; MEM_DECAY_INT=10

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
    _perceived:List[dict]=field(default_factory=list,repr=False)

    def perceive(self, world):
        vis=5; perceived=[]
        for o in world.agents:
            if o.aid==self.aid or not o.alive: continue
            d=math.hypot(o.pos.x-self.pos.x,o.pos.y-self.pos.y)
            if d<=vis: perceived.append({"type":"agent","id":o.aid,"name":o.name,
                "pos":(o.pos.x,o.pos.y),"state":o.state.value,"dist":d})
        for r in world.resources:
            if r["amount"]<=0: continue
            d=math.hypot(r["pos"][0]-self.pos.x,r["pos"][1]-self.pos.y)
            if d<=vis: perceived.append({"type":"resource","res_type":r["type"],
                "pos":r["pos"],"amount":r["amount"],"dist":d})
        for b in world.buildings:
            d=math.hypot(b["pos"][0]-self.pos.x,b["pos"][1]-self.pos.y)
            if d<=vis: perceived.append({"type":"building","b_type":b["type"],"pos":b["pos"],"dist":d})
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
            s=min(1.0,d); self.pos.x+=int(round(dx/d*s)); self.pos.y+=int(round(dy/d*s))
        self.pos.x=max(0,min(world.size-1,self.pos.x)); self.pos.y=max(0,min(world.size-1,self.pos.y))
    def _wander(self,world):
        rng=world._rng
        self.pos.x=max(0,min(world.size-1,self.pos.x+rng.choice([-1,0,1])))
        self.pos.y=max(0,min(world.size-1,self.pos.y+rng.choice([-1,0,1])))
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
        del d["_perceived"]; return d

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
        self._used_names=set(); self._init_world()
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
        self.resources.append({"type":rt,"pos":pos,"amount":self._rng.randint(8,25),
            "regen_rate":self._rng.uniform(0.15,0.4)})
    def _gen_name(self):
        avail=[n for n in self.NAMES if n not in self._used_names]
        n=self._rng.choice(avail) if avail else "Resident"+str(len(self._used_names))
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
        self.agents.append(a); self._agents_by_id[aid]=a; self._wb+=1
        self.event_log.append(Event(eid=self.next_eid(),etype=EventType.BIRTH,actor=aid,tick=self._tick,
            data={"parent_ids":list(parent_ids) if parent_ids else [],"generation":gen,"age":a.age}))
        return a
    def spawn_agent(self, pos=None): return self._spawn_agent(pos=pos)
    def next_eid(self):
        eid="E%06d"%self._eid; self._eid+=1; return eid
    def find_agent(self, aid):
        return self._agents_by_id.get(aid)   # 原先线性扫描，社交/交易每 tick 触发多次
    def consume_resource(self,x,y,amt):
        # 资源坐标已由 _spawn_resource 去重，故首个匹配即为唯一匹配（原先会漏扣同坐标的其余资源）
        for r in self.resources:
            if r["pos"]==(x,y) and r["amount"]>0: r["amount"]=max(0,r["amount"]-amt); return
    def _distribute_ubi(self):
        self._ubi_cycle+=1; alive=[a for a in self.agents if a.alive]
        amt=self.reserve.ubi_amount   # 原先硬编码 UBI_DAILY，config/reserve 改动不生效
        self.reserve.distribute_ubi(len(alive))
        for a in alive: a.receive_ubi(amt); a.last_ubi_tick=self._tick
        self.event_log.append(Event(eid=self.next_eid(),etype=EventType.UBI,actor="SYSTEM",tick=self._tick,
            data={"cycle":self._ubi_cycle,"amount_per":amt}))
    def _collect_taxes(self):
        alive=[a for a in self.agents if a.alive]; rate=self.reserve.tax_rate   # 同上：原先硬编码 TAX_RATE
        total=sum(a.pay_tax(max(0.0,a.wealth*rate)) for a in alive)
        self.reserve.collect_tax(total)
        self.event_log.append(Event(eid=self.next_eid(),etype=EventType.TAX,actor="SYSTEM",tick=self._tick,
            data={"total_collected":total}))
    def _apply_inflation(self): self.reserve.apply_inflation()
    def _check_reproduction(self):
        ev=[]; alive=[a for a in self.agents if a.alive]; cfg=self.config
        for a in alive:
            if not a.partner_id and a.age>cfg.marriage_age and a.needs["belonging"]>70:
                for b in alive:
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
        # 年龄以「岁」计：原先每 tick +1，本文件 tps=10 时第 80 tick 就进入老年死亡，社会必然瞬间灭绝
        if self._tick%self.config.ticks_per_year==0:
            for a in alive: a.age+=1
        for a in alive:
            a.perceive(self); d=a.think(self); te.extend(a.act(d,self))
        self._regenerate_resources(); self._build_houses()
        te.extend(self._check_reproduction()); te.extend(self._check_deaths()); te.extend(self._compliance_check())
        if self._tick%10==0: self._distribute_ubi()
        if self._tick%30==0: self._collect_taxes()
        if self._tick%50==0: self._apply_inflation()
        for b in self.buildings: b["age"]+=1
        self.event_log.extend(te)   # 原先另有 self.events 只增不减，且全仓无任何读取点（死字段+内存泄漏）
        if len(self.event_log)>5000: self.event_log=self.event_log[-3000:]
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

        这不是宪法审计。宪法级 19 项审计请调用
            audit_engine.SecondPerspectiveAuditor().audit_world(world)
        原方法名 get_audit_report 已废弃：名为 audit 却只有 7 维自评口径，
        与审计引擎的 19 维并列会造成"两个分数"的对外混称。
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
            "disclaimer":"仿真自评，非宪法 19 项审计；宪法审计见 audit_engine.SecondPerspectiveAuditor",
            "stats":s}
    def state_hash(self):
        """世界状态指纹：同一 (config, seed) 必得同一哈希——对外可复现性的取证手段。"""
        blob=json.dumps(self.export_state(),ensure_ascii=False,sort_keys=True,default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
    def export_state(self):
        return {"tick":self._tick,"config":self.config.__dict__,
            "agents":[a.to_dict() for a in self.agents],"resources":self.resources,
            "buildings":self.buildings,"stats":self.get_stats(),
            "reserve":{"money_supply":self.reserve.money_supply,"treasury":self.reserve.treasury,
                "total_ubi":self.reserve.total_ubi_distributed,"total_tax":self.reserve.total_tax_collected,
                "total_labor_created":self.reserve.total_labor_created,
                "inflation_created":self.reserve.inflation_created,
                "total_debt_relief":self.reserve.total_debt_relief,
                "genesis_unallocated":self.reserve.genesis_unallocated}}
    def save_state(self, fp):
        with open(fp,'w',encoding='utf-8') as f: json.dump(self.export_state(),f,ensure_ascii=False,indent=2,default=str)

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

BUILDING_STYLE={"house":{"h":20,"top":(216,118,106),"wall":(226,170,132)},
    "market":{"h":16,"top":(218,150,78),"wall":(240,198,142)},
    "workshop":{"h":16,"top":(180,142,110),"wall":(152,120,94)},
    "garden":{"h":12,"top":(130,198,112),"wall":(152,192,132)},
    "library":{"h":20,"top":(140,120,202),"wall":(122,104,178)}}

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

def build_ground(seed):
    """手绘感草地瓦片 + 岛边缘 + 岛下阴影，预渲染一次"""
    s=pygame.Surface((MAP_W,MAP_H))
    for gx in range(WORLD_SIZE):
        for gy in range(WORLD_SIZE):
            cx,cy=tile_center(gx,gy)
            n=_hash2(gx+seed,gy*3+seed)
            base=_lerp_color(PAL["grass_a"],PAL["grass_b"],n)
            pts=[(cx,cy-TH2),(cx+TW2,cy),(cx,cy+TH2),(cx-TW2,cy)]
            pygame.draw.polygon(s,base,pts)
            # 上半面提亮（赛璐璐两段式受光）
            pygame.draw.polygon(s,_lerp_color(base,PAL["grass_hi"],0.55),
                [(cx,cy-TH2),(cx+TW2,cy),(cx-TW2,cy)])
            # 手绘噪声：草叶/小花
            if n>0.84:
                pygame.draw.line(s,_darken(base,0.8),(cx-2,cy-2),(cx-3,cy+1),1)
                pygame.draw.line(s,_darken(base,0.8),(cx+1,cy-3),(cx+2,cy),1)
            elif n>0.72:
                pc=(252,220,180) if n>0.78 else (255,240,220)
                pygame.draw.circle(s,pc,(cx+3,cy-3),1)
            elif n<0.10:
                pygame.draw.circle(s,(112,168,120),(cx-3,cy+2),1)
    # 岛轮廓（粗描边 = 手绘 inking）
    top=tile_center(0,0); right=tile_center(WORLD_SIZE-1,0)
    bot=tile_center(WORLD_SIZE-1,WORLD_SIZE-1); left=tile_center(0,WORLD_SIZE-1)
    rim=[top,(right[0],right[1]+TH2),(bot[0],bot[1]+TH2),(left[0],left[1]+TH2)]
    pygame.draw.polygon(s,PAL["grass_edge"],rim,3)
    return s

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
    gx,gy=r["pos"]; t=r["type"]
    gxp,gyp=grid_ground(gx,gy)
    s=int(min(12,max(6,5+r["amount"]//3)))
    _draw_shadow(overlay,gxp,gyp,12,4)
    ink=PAL["ink"]
    if t=="food":     # 绿苹果
        pygame.draw.circle(screen,ink,(gxp,gyp-s//2),4)
        pygame.draw.circle(screen,(122,206,96),(gxp,gyp-s//2),3)
        pygame.draw.line(screen,ink,(gxp,gyp-s//2-3),(gxp,gyp-s//2-5),2)
        pygame.draw.ellipse(screen,(120,196,110),(gxp+1,gyp-s//2-6,5,3))
    elif t=="fruit":  # 红莓
        pygame.draw.circle(screen,ink,(gxp-3,gyp-s//4),3)
        pygame.draw.circle(screen,ink,(gxp+3,gyp-s//4),3)
        pygame.draw.circle(screen,ink,(gxp,gyp-s//4+3),3)
        for cx,cy in ((gxp-3,gyp-s//4),(gxp+3,gyp-s//4),(gxp,gyp-s//4+3)):
            pygame.draw.circle(screen,(236,110,110),(cx,cy),2)
        pygame.draw.ellipse(screen,(120,196,110),(gxp-2,gyp-s//2-3,5,3))
    elif t=="water":  # 水滴
        pygame.draw.polygon(screen,ink,[(gxp,gyp-s),(gxp+3,gyp-s//2),(gxp-3,gyp-s//2)])
        pygame.draw.circle(screen,(120,196,236),(gxp,gyp-s//2+1),3)
        pygame.draw.circle(screen,(110,190,236),(gxp,gyp-s//2+1),2)
        pygame.draw.circle(screen,(238,250,255),(gxp-1,gyp-s//2),1)
    elif t=="wood":   # 木段
        pygame.draw.rect(screen,ink,(gxp-4,gyp-4,9,5),border_radius=2)
        pygame.draw.rect(screen,(176,132,80),(gxp-3,gyp-3,7,3),border_radius=2)
        pygame.draw.circle(screen,(140,100,60),(gxp,gyp-2),2)
        pygame.draw.circle(screen,(176,132,80),(gxp,gyp-2),1)
    elif t=="stone":  # 矿石
        pygame.draw.polygon(screen,ink,[(gxp-4,gyp-1),(gxp-2,gyp-4),(gxp+3,gyp-3),(gxp+4,gyp+1),(gxp-1,gyp+2)])
        pygame.draw.polygon(screen,(150,152,164),[(gxp-4,gyp-1),(gxp-2,gyp-4),(gxp+3,gyp-3),(gxp+4,gyp+1),(gxp-1,gyp+2)])
        pygame.draw.polygon(screen,(186,188,196),[(gxp-4,gyp-1),(gxp-2,gyp-4),(gxp+1,gyp-3),(gxp-1,gyp+1)])
    elif t=="herb":   # 草药
        pygame.draw.line(screen,ink,(gxp,gyp),(gxp,gyp-5),2)
        for dx in (-2,0,2):
            pygame.draw.ellipse(screen,(96,200,128),(gxp+dx-2,gyp-7+(abs(dx)),4,3))
            pygame.draw.ellipse(screen,ink,(gxp+dx-2,gyp-7+(abs(dx)),4,3),1)
    elif t=="ore":    # 紫晶
        pygame.draw.polygon(screen,ink,[(gxp-3,gyp),(gxp-1,gyp-5),(gxp+3,gyp-4),(gxp+4,gyp+1),(gxp, gyp+2)])
        pygame.draw.polygon(screen,(150,110,190),[(gxp-3,gyp),(gxp-1,gyp-5),(gxp+3,gyp-4),(gxp+4,gyp+1),(gxp,gyp+2)])
        pygame.draw.line(screen,(238,238,255),(gxp-1,gyp-4),(gxp+2,gyp+1),1)

def draw_agent_anim(screen,overlay,a,selected,tick,world,warn_surf):
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
    cloth=COLORS.get("agent_"+state,COLORS["agent_idle"])
    hair=GEN_COLORS[a.generation%len(GEN_COLORS)]
    hx,hy=gxp,gyp-14
    sidx=(abs(gx)*31+gy)%7
    bob=int(math.sin(tick*0.09+sidx)*1.2) if state!="working" else 0
    hy+=bob
    _draw_shadow(overlay,gxp,gyp,14,5)
    # 身体（连身衣 + 腿）
    pygame.draw.rect(screen,PAL["ink"],(hx-6,hy+2,14,11),border_radius=5)
    pygame.draw.rect(screen,cloth,(hx-5,hy+3,12,9),border_radius=5)
    pygame.draw.line(screen,_darken(cloth,0.86),(hx-3,hy+10),(hx-4,hy+13),2)
    pygame.draw.line(screen,_darken(cloth,0.86),(hx+3,hy+10),(hx+4,hy+13),2)
    pygame.draw.line(screen,_lerp_color(cloth,(255,255,255),0.3),(hx-4,hy+4),(hx+3,hy+4),2)
    # 头（黑描边 + 肤色 + 发盖）
    pygame.draw.circle(screen,PAL["ink"],(hx,hy-7),8)
    pygame.draw.circle(screen,hair,(hx,hy-7),7)
    pygame.draw.circle(screen,PAL["ink"],(hx,hy-4),6)
    pygame.draw.circle(screen,PAL["skin"],(hx,hy-4),5)
    for bx in (-5,-1,4):  # 刘海
        pygame.draw.line(screen,hair,(hx+bx,hy-10),(hx+bx,hy-6),3)
    # 表情
    if state=="resting":
        for ex in (-2,2):
            pygame.draw.arc(screen,PAL["ink"],(hx+ex-3,hy-5,6,4),0.15,2.99,2)
    else:
        for ex in (-2,2):
            pygame.draw.ellipse(screen,(255,255,255),(hx+ex-2,hy-5,4,5))
            pygame.draw.circle(screen,(96,78,72),(hx+ex,hy-3),2)
            pygame.draw.circle(screen,(30,24,32),(hx+ex,hy-3),1)
            pygame.draw.circle(screen,(255,255,255),(hx+ex-1,hy-4),1)
        if state=="working":
            pygame.draw.circle(screen,(120,196,244),(hx+7,hy-9),2)
            pygame.draw.circle(screen,(188,236,255),(hx+6,hy-10),1)
    # 腮红
    pygame.draw.circle(screen,PAL["blush"],(hx-6,hy-2),2)
    pygame.draw.circle(screen,PAL["blush"],(hx+6,hy-2),2)
    # 嘴
    pygame.draw.arc(screen,PAL["ink"],(hx-2,hy-2,4,3),0.2,2.9,1)
    # 配偶爱心（浮动）
    if a.partner_id:
        p=world.find_agent(a.partner_id)
        if p and p.alive:
            by=hy-24+int(math.sin(tick*0.12)*1.5)
            pygame.draw.circle(screen,(240,110,160),(hx-2,by-1),2)
            pygame.draw.circle(screen,(240,110,160),(hx+2,by-1),2)
            pygame.draw.polygon(screen,(240,110,160),[(hx-3,by-1),(hx+3,by-1),(hx,by+2)])
    # 需求危机气泡
    if min(a.needs.values())<15:
        bx,byy=hx+7,hy-19
        pygame.draw.circle(screen,PAL["ink"],(bx,byy),6)
        pygame.draw.circle(screen,(238,96,84),(bx,byy),5)
        screen.blit(warn_surf,(bx-3,byy-5))
    # 选中框
    if selected and a.aid==selected.aid:
        _rounded(screen,(hx-12,hy-22,24,38),(255,238,120),radius=8,outline=(120,100,30),ow=1)
        _rounded(screen,(hx-11,hy-21,22,36),(255,238,120),radius=8,outline=(255,238,120),ow=2)

def run_gui(tps=10, max_ticks=None, seed=0, screenshot=None):
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
    config=WorldConfig(world_size=WORLD_SIZE,initial_agents=30,initial_resources=80,initial_buildings=8,seed=seed)
    world=NohnWorld(config)
    running=True; paused=False; speed=tps; selected=None; show_help=False
    show_heat=True; show_graph=True; show_eventfx=True; show_daynight=True
    sky_surf=build_sky(seed)
    ground_surf=build_ground(seed)
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
            _draw_shadow(overlay,gxp,gyp,14,5)
        # 昼夜/季节色调
        if show_daynight:
            ph=(world._tick%240)/240.0
            tint=_lerp_color((15,25,65),(75,50,10),abs(math.sin(ph*math.pi)))
            overlay.fill(tint+(18,))
        screen.blit(overlay,(0,0))
        # 实体按深度排序（画家算法：近的晚画）
        ents=[]
        for b in world.buildings:
            ents.append((b["pos"][0]+b["pos"][1],0,("b",b)))
        for r in world.resources:
            if r["amount"]<=0: continue
            ents.append((r["pos"][0]+r["pos"][1],1,("r",r)))
        for a in world.agents:
            ents.append((a.pos.x+a.pos.y,2,("a",a)))
        ents.sort(key=lambda e:(e[0],e[1]))
        for _,_,(kind,obj) in ents:
            if kind=="b": draw_building_anim(screen,overlay,obj,world._tick)
            elif kind=="r": draw_resource_anim(screen,overlay,obj)
            else: draw_agent_anim(screen,overlay,obj,selected,world._tick,world,warn_surf)
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
            _rounded(screen,(px+8,y,pw-16,26),(40,36,60),radius=8,outline=(120,110,80),ow=1)
            if not a.alive:
                screen.blit(font_b.render("[已故] %s (%s)"%(a.name,a.aid),True,COLORS["agent_dead"]),(px+16,y+6)); y+=26
            else:
                screen.blit(font_b.render("%s (%s) gen%d"%(a.name,a.aid,a.generation),True,(255,238,150)),(px+16,y+6)); y+=26
                screen.blit(font.render("状态: %s  年龄: %d"%(a.state.value,a.age),True,PAL["text"]),(px+10,y)); y+=14
                screen.blit(font.render("财富: %.0f  精力: %.0f"%(a.wealth,a.energy),True,PAL["text"]),(px+10,y)); y+=14
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
        hy=MAP_H+5
        screen.blit(font_s.render(
            "SPACE暂停 | +/- 速度 | 点击选中 | P截图 S存档 R重置 H帮助 | 视觉: %s"%
            ("".join(k for k,v in [("W",show_heat),("F",show_graph),("E",show_eventfx),("N",show_daynight)] if v) or "无"),
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

    def sample_history():
        s=world.get_stats()
        hist["pop"].append(s["alive"])
        hist["gini"].append(_gini([a.wealth for a in world.agents if a.alive]))
        hist["need"].append(sum(s["avg_needs"].values())/len(s["avg_needs"]))
        hist["money"].append(s["money_supply"])

    if screenshot:
        for _ in range(max_ticks or 600):
            note_events(world.tick()); sample_history()
        for _ in range(8): sample_history()
        del fx[:-8]
        draw_world(); draw_stats(); pygame.display.flip()
        pygame.image.save(screen,screenshot)
        print("Screenshot saved: %s (tick=%d)"%(screenshot,world._tick))
        pygame.quit(); return world

    while running:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            elif ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_SPACE: paused=not paused
                elif ev.key in (pygame.K_EQUALS,pygame.K_PLUS,pygame.K_KP_PLUS): speed=min(60,speed+5)
                elif ev.key in (pygame.K_MINUS,pygame.K_KP_MINUS): speed=max(1,speed-5)
                elif ev.key==pygame.K_s: world.save_state("second_reality_save.json"); print("Saved")
                elif ev.key==pygame.K_h: show_help=not show_help
                elif ev.key==pygame.K_w: show_heat=not show_heat
                elif ev.key==pygame.K_f: show_graph=not show_graph
                elif ev.key==pygame.K_e: show_eventfx=not show_eventfx
                elif ev.key==pygame.K_n: show_daynight=not show_daynight
                elif ev.key==pygame.K_p:
                    shot="second_reality_%06d.png"%world._tick
                    pygame.image.save(screen,shot); print("Screenshot saved: "+shot)
                elif ev.key==pygame.K_r: world=NohnWorld(config); selected=None; fx.clear(); feed.clear()
            elif ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1: handle_click(ev.pos)
        if not paused:
            note_events(world.tick()); sample_history()
            if max_ticks and world._tick>=max_ticks: running=False
        for f in fx: f["age"]+=1
        fx=[f for f in fx if f["age"]<f["ttl"]]
        draw_world(); draw_stats(); draw_tooltip(); pygame.display.flip()
        clock.tick(speed if speed>0 else 0)
    pygame.quit()
    return world

def run_headless(ticks=1000, verbose=False, seed=0):
    config=WorldConfig(world_size=60,initial_agents=30,initial_resources=80,initial_buildings=8,seed=seed)
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

def verify_determinism(ticks=300, seed=42):
    """同 (config, seed) 跑两遍互相独立的世界，比对状态指纹——对外可复现性的当场证据。"""
    def run_once():
        w=NohnWorld(WorldConfig(world_size=60,initial_agents=30,initial_resources=80,
            initial_buildings=8,seed=seed))
        for _ in range(ticks): w.tick()
        return w.state_hash()
    h1,h2=run_once(),run_once()
    ok=(h1==h2)
    print("=== Determinism verification (seed=%d, %d ticks) ==="%(seed,ticks))
    print("  run#1 state hash: %s"%h1)
    print("  run#2 state hash: %s"%h2)
    print("  VERDICT: %s"%("PASS - identical byte-for-byte" if ok else "FAIL - world is not reproducible"))
    return ok

if __name__=="__main__":
    import argparse, sys, os
    try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台默认 GBK，会把中文输出打成乱码
    except Exception: pass
    ap=argparse.ArgumentParser(description="Second Reality v2.0 - Virtual World Model (Anime 2.5D)")
    ap.add_argument("--headless",action="store_true",help="run without GUI")
    ap.add_argument("--ticks",type=int,default=1000,help="ticks to simulate (headless / determinism / screenshot)")
    ap.add_argument("--seed",type=int,default=0,help="world RNG seed; same seed + same config => reproducible")
    ap.add_argument("--metrics",action="store_true",
        help="print machine-readable simulation self-metrics (NOT the constitutional 19-dim audit)")
    ap.add_argument("--verify-determinism",action="store_true",
        help="run two independent same-seed worlds and compare state hashes")
    ap.add_argument("--screenshot",metavar="PATH",
        help="render one frame to PNG and exit (no display needed: forces SDL_VIDEODRIVER=dummy)")
    args=ap.parse_args()
    if args.verify_determinism:
        raise SystemExit(0 if verify_determinism(ticks=args.ticks,seed=args.seed) else 1)
    if args.screenshot:
        os.environ.setdefault("SDL_VIDEODRIVER","dummy")   # 必须在 pygame.init() 之前设置
        run_gui(seed=args.seed,max_ticks=args.ticks,screenshot=args.screenshot)
        raise SystemExit(0)
    world=run_headless(args.ticks,verbose=True,seed=args.seed) if args.headless else run_gui(seed=args.seed)
    if args.metrics:
        print(json.dumps(world.get_simulation_metrics(),ensure_ascii=False,indent=2,default=str))