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
# GUI Visualization (pygame)
# ============================================================
WORLD_SIZE=60; CELL=10; STATS_H=200
WW=WORLD_SIZE*CELL+300; WH=WORLD_SIZE*CELL+STATS_H
COLORS={"bg":(20,20,30),"grid":(40,40,55),
    "food":(100,200,100),"water":(80,150,255),"wood":(139,90,43),
    "stone":(150,150,160),"herb":(100,220,150),"ore":(180,140,100),"fruit":(255,160,80),
    "house":(180,140,100),"market":(200,180,80),"workshop":(160,120,80),
    "garden":(100,200,100),"library":(150,130,220),
    "agent_idle":(200,200,200),"agent_working":(255,220,80),
    "agent_socializing":(255,150,200),"agent_resting":(100,150,255),
    "agent_trading":(80,255,180),"agent_learning":(180,150,255),
    "agent_creating":(255,100,100),"agent_dead":(60,60,60),
    "text":(220,220,220),"need_high":(80,220,100),"need_mid":(220,200,80),"need_low":(220,80,80),
    "bar_bg":(50,50,65),"panel":(25,25,40),
    "chart_bg":(16,16,26),"chart_line":(60,60,80),
    "warm":(196,72,40),"friend":(74,106,150),"partner":(255,150,200),
    "tip_bg":(16,16,24),"tip_border":(120,120,150),
    "curve_pop":(120,220,255),"curve_gini":(255,190,90),
    "curve_need":(120,230,140),"curve_money":(220,140,255)}

# 代际配色：眼不看文字也能认出第几代
GEN_COLORS=[(30,30,30),(130,80,190),(0,150,150),(180,90,0),(0,70,190),(150,0,90)]

# 事件流标签与配色（用于右侧滚动事件与网格浮字）
EVENT_LABEL={"birth":"出生","death":"死亡","marriage":"结婚","produce":"生产","trade":"交易",
    "interact":"社交","rest":"休息","ubi":"UBI","tax":"税收","violation":"违规"}
EVENT_COLOR={"birth":(120,230,255),"death":(150,150,170),"marriage":(255,150,200),
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

def _gini(values):
    """基尼系数：0=完全平均，1=完全不均。用于把"贫富分化"变成可看的数字。"""
    xs=[max(0.0,v) for v in values]
    if not xs: return 0.0
    s=sum(xs)
    if s<=0: return 0.0
    xs.sort(); n=len(xs)
    cum=sum((2*i-n-1)*x for i,x in enumerate(xs,1))
    return max(0.0,min(1.0,cum/(n*s)))

def _lerp_color(c1,c2,t):
    t=max(0.0,min(1.0,t))
    return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))

def run_gui(tps=10, max_ticks=None, seed=0, screenshot=None):
    import pygame
    from collections import deque
    pygame.init()
    screen=pygame.display.set_mode((WW,WH))
    pygame.display.set_caption("Second Reality v2.0 - Virtual World  (seed=%d)"%seed)
    import os
    def _load_font(size,bold=False):
        """优先按文件路径加载含 CJK 字形的字体；SysFont 不可靠（会把中文渲染成方块）"""
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
    clock=pygame.time.Clock()
    config=WorldConfig(world_size=WORLD_SIZE,initial_agents=30,initial_resources=80,initial_buildings=8,seed=seed)
    world=NohnWorld(config)
    running=True; paused=False; speed=tps; selected=None; show_help=False
    # 视觉开关（默认全开；现场可按键逐层关闭，不被特效淹没）
    show_heat=True; show_graph=True; show_eventfx=True; show_daynight=True
    # 半透明叠加层：pygame 在普通 Surface 上会忽略 4 元组颜色的 alpha，必须走 SRCALPHA 图层
    overlay=pygame.Surface((WORLD_SIZE*CELL,WORLD_SIZE*CELL),pygame.SRCALPHA)
    warn_surf=font_b.render("!",True,(255,90,90))
    fx=[]                      # 网格浮字
    feed=deque(maxlen=8)       # 右侧事件流
    hist={"pop":deque(maxlen=240),"gini":deque(maxlen=240),
          "need":deque(maxlen=240),"money":deque(maxlen=240)}
    last_wb=world._wb

    def spawn_fx(gx,gy,txt,col,ttl=28):
        fx.append({"x":gx*CELL+CELL//2,"y":gy*CELL+CELL//2,"t":txt,"c":col,"ttl":ttl,"age":0})
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
        if world._wb>last_wb:   # 出生事件写入 event_log 而非 tick 返回值，故以新生人口数增量探测
            for a in world.agents[-(world._wb-last_wb):]:
                if show_eventfx: spawn_fx(a.pos.x,a.pos.y,"*",EVENT_COLOR["birth"],36)
                feed.append("t%-5d %-4s %s (gen%d)"%(world._tick,EVENT_LABEL["birth"],a.aid,a.generation))
            last_wb=world._wb

    def draw_building(b):
        bx,by=b["pos"]; t=b["type"]; c=COLORS.get(t,(128,128,128))
        r=pygame.Rect(bx*CELL+1,by*CELL+1,CELL-2,CELL-2)
        pygame.draw.rect(screen,c,r)
        pygame.draw.rect(screen,(0,0,0),r,1)
        cx,cy=r.center
        if t=="house":   # 屋顶
            pygame.draw.polygon(screen,(90,60,40),[(r.left,cy),(cx,r.top+1),(r.right,cy)])
        elif t=="market":  pygame.draw.circle(screen,(255,240,180),(cx,cy),2)
        elif t=="workshop":
            pygame.draw.line(screen,(60,40,20),(r.left+2,r.bottom-2),(r.right-2,r.top+2),1)
            pygame.draw.line(screen,(60,40,20),(r.left+2,r.top+2),(r.right-2,r.bottom-2),1)
        elif t=="garden":
            pygame.draw.circle(screen,(240,120,160),(cx-2,cy),1); pygame.draw.circle(screen,(240,120,160),(cx+2,cy),1)
        elif t=="library":
            for i in range(3): pygame.draw.line(screen,(60,50,120),(r.left+2+i*3,cy-2),(r.left+2+i*3,cy+2),2)

    def draw_heatmap():
        """财富热力：把每个 agent 的财富按对数归一化成底色，叠在网格之下"""
        denom=math.log1p(1200.0)
        for a in world.agents:
            if not a.alive: continue
            n=math.log1p(max(0.0,a.wealth))/denom
            if n<=0.02: continue
            pygame.draw.rect(screen,_lerp_color(COLORS["bg"],COLORS["warm"],n),
                (a.pos.x*CELL,a.pos.y*CELL,CELL,CELL))

    def draw_world():
        pygame.draw.rect(screen,COLORS["bg"],(0,0,WORLD_SIZE*CELL,WORLD_SIZE*CELL))
        if show_heat: draw_heatmap()
        for x in range(0,WORLD_SIZE*CELL+1,CELL):
            pygame.draw.line(screen,COLORS["grid"],(x,0),(x,WORLD_SIZE*CELL))
        for y in range(0,WORLD_SIZE*CELL+1,CELL):
            pygame.draw.line(screen,COLORS["grid"],(0,y),(WORLD_SIZE*CELL,y))
        for r in world.resources:
            if r["amount"]<=0: continue
            rx,ry=r["pos"]; c=COLORS.get(r["type"],(128,128,128))
            # 资源用方形、agent 用圆形：形状即区分（否则"休息"与"水"同为蓝色圆点，无法辨识）
            s=max(2,min(CELL//2-1,int(r["amount"]//3)))
            rect=pygame.Rect(rx*CELL+CELL//2-s,ry*CELL+CELL//2-s,s*2,s*2)
            pygame.draw.rect(screen,c,rect)
            pygame.draw.rect(screen,(0,0,0),rect,1)
        for b in world.buildings: draw_building(b)
        # 关系线走半透明层（普通 Surface 会丢弃 alpha，导致连线过实、盖住 agent）
        overlay.fill((0,0,0,0))
        for a in world.agents:
            if not a.alive: continue
            ax,ay=a.pos.x*CELL+CELL//2,a.pos.y*CELL+CELL//2
            if a.partner_id:
                p=world.find_agent(a.partner_id)
                if p and p.alive:
                    pygame.draw.line(overlay,COLORS["partner"]+(110,),(ax,ay),
                        (p.pos.x*CELL+CELL//2,p.pos.y*CELL+CELL//2),1)
            if show_graph:
                for fid in a.friends:
                    if fid<=a.aid: continue          # 每对只画一次
                    f=world.find_agent(fid)
                    if f and f.alive:
                        pygame.draw.line(overlay,COLORS["friend"]+(48,),(ax,ay),
                            (f.pos.x*CELL+CELL//2,f.pos.y*CELL+CELL//2),1)
        if show_daynight:                            # 昼夜/季节色调：压低强度，仅作氛围
            ph=(world._tick%240)/240.0
            tint=_lerp_color((20,30,80),(90,60,10),abs(math.sin(ph*math.pi)))
            overlay.fill(tint+(16,))
        screen.blit(overlay,(0,0))
        for a in world.agents:
            cx,cy=a.pos.x*CELL+CELL//2,a.pos.y*CELL+CELL//2
            if not a.alive:
                pygame.draw.line(screen,COLORS["agent_dead"],(cx-3,cy-3),(cx+3,cy+3),1)
                pygame.draw.line(screen,COLORS["agent_dead"],(cx-3,cy+3),(cx+3,cy-3),1)
                continue
            c=COLORS.get("agent_"+a.state.value,COLORS["agent_idle"])
            pygame.draw.circle(screen,c,(cx,cy),CELL//2-1)
            pygame.draw.circle(screen,GEN_COLORS[a.generation%len(GEN_COLORS)],(cx,cy),CELL//2-1,1)
            if min(a.needs.values())<15: screen.blit(warn_surf,(cx+3,cy-9))   # 需求危机警示
            if selected and a.aid==selected.aid:
                pygame.draw.circle(screen,(255,255,100),(cx,cy),CELL//2+2,2)
        for f in fx:
            rise=int(f["age"]*0.4)
            screen.blit(font_b.render(f["t"],True,f["c"]),(f["x"]-4,f["y"]-rise))

    def draw_need_bar(x,y,val,w=150,h=8):
        pygame.draw.rect(screen,COLORS["bar_bg"],(x,y,w,h))
        bc=COLORS["need_high"] if val>60 else (COLORS["need_mid"] if val>30 else COLORS["need_low"])
        pygame.draw.rect(screen,bc,(x,y,int(w*val/100),h))

    def draw_chart(x,y,w,h,series):
        """迷你折线：每条序列按自身最大值归一化，只看走势形状（数值由上方图例给出）"""
        pygame.draw.rect(screen,COLORS["chart_bg"],(x,y,w,h))
        pygame.draw.rect(screen,COLORS["chart_line"],(x,y,w,h),1)
        for dq,col,lab in series:
            if len(dq)<2: continue
            mx=max(max(dq),1e-9); n=len(dq)
            pts=[(x+1+int((w-2)*i/max(1,n-1)),y+h-2-int((h-6)*min(1.0,v/mx))) for i,v in enumerate(dq)]
            pygame.draw.lines(screen,col,False,pts,1)

    def draw_chart_legend(x,y,items):
        """图例画在图表框之外，避免文字压在曲线上"""
        for k,(dq,col,lab) in enumerate(items):
            screen.blit(font_s.render("%s %.2f"%(lab,dq[-1] if dq else 0.0),True,col),(x+k*92,y))

    def draw_legend(x0,y0):
        """图例：填在世界下方的空白区，让画面自解释（投资方不必问"这个颜色是什么意思"）"""
        screen.blit(font_b.render("图例",True,(180,220,255)),(x0,y0))
        c1=x0; c2=x0+190; c3=x0+390
        def dot(x,y,col):
            pygame.draw.circle(screen,col,(x+5,y+5),4)
            pygame.draw.circle(screen,(0,0,0),(x+5,y+5),4,1)
        def head(x,y,t): screen.blit(font_s.render(t,True,(150,180,220)),(x,y))
        y=y0+18; head(c1,y,"agent 状态"); y+=13
        for st,lab in STATE_LABELS.items():
            dot(c1,y,COLORS.get("agent_"+st,COLORS["agent_idle"]))
            screen.blit(font_s.render(lab,True,COLORS["text"]),(c1+14,y)); y+=11
        y+=4; head(c1,y,"圆环=代际"); y+=13
        for g in range(4):
            pygame.draw.circle(screen,GEN_COLORS[g],(c1+5,y+5),4,2)
            screen.blit(font_s.render("gen%d"%g,True,COLORS["text"]),(c1+14,y)); y+=11
        y=y0+18; head(c2,y,"资源（方形）  agent（圆形）"); y+=13
        for rt,lab in RES_LABELS.items():
            r=pygame.Rect(c2+1,y+1,9,9); pygame.draw.rect(screen,COLORS.get(rt,(128,128,128)),r)
            pygame.draw.rect(screen,(0,0,0),r,1)
            screen.blit(font_s.render(lab,True,COLORS["text"]),(c2+14,y)); y+=11
        y+=4
        r=pygame.Rect(c2+1,y+1,10,10)
        pygame.draw.rect(screen,COLORS["warm"],r); pygame.draw.rect(screen,(0,0,0),r,1)
        screen.blit(font_s.render("财富热力底图",True,COLORS["text"]),(c2+16,y))
        y=y0+18; head(c3,y,"建筑"); y+=13
        for bt,lab in BLD_LABELS.items():
            r=pygame.Rect(c3,y+1,9,9); pygame.draw.rect(screen,COLORS.get(bt,(128,128,128)),r)
            pygame.draw.rect(screen,(0,0,0),r,1)
            screen.blit(font_s.render(lab,True,COLORS["text"]),(c3+14,y)); y+=11
        y+=4; head(c3,y,"事件标记"); y+=13
        for txt,col,lab in [("*",EVENT_COLOR["birth"],"出生"),("+",EVENT_COLOR["marriage"],"结婚"),
                            ("$",EVENT_COLOR["trade"],"交易"),("x",EVENT_COLOR["death"],"死亡"),
                            ("!",(255,90,90),"需求<15")]:
            screen.blit(font_b.render(txt,True,col),(c3,y))
            screen.blit(font_s.render(lab,True,COLORS["text"]),(c3+14,y)); y+=11

    def draw_tooltip():
        mx,my=pygame.mouse.get_pos()
        if mx>=WORLD_SIZE*CELL or my>=WORLD_SIZE*CELL: return
        gx,gy=mx//CELL,my//CELL
        for a in world.agents:
            if a.alive and a.pos.x==gx and a.pos.y==gy:
                lines=["%s (%s) gen%d"%(a.name,a.aid,a.generation),
                       "%s  age %d"%(a.state.value,a.age),
                       "wealth %.0f  energy %.0f"%(a.wealth,a.energy),
                       "mem %d  friends %d"%(a.memory.stats()["total_memories"],len(a.friends))]
                tw=max(font_s.size(t)[0] for t in lines)+12
                th=len(lines)*11+10
                tx=min(mx+12,WW-tw-4); ty=min(my+12,WH-th-4)
                box=pygame.Surface((tw,th),pygame.SRCALPHA)
                box.fill(COLORS["tip_bg"]+(225,))
                pygame.draw.rect(box,COLORS["tip_border"],(0,0,tw,th),1)
                screen.blit(box,(tx,ty))
                for i,t in enumerate(lines):
                    screen.blit(font_s.render(t,True,COLORS["text"]),(tx+6,ty+5+i*11))
                return

    def draw_stats():
        px=WORLD_SIZE*CELL; pw=WW-px
        pygame.draw.rect(screen,COLORS["panel"],(px,0,pw,WH))
        pygame.draw.line(screen,(60,60,80),(px,0),(px,WH),2)
        y=8
        s=world.get_stats()
        screen.blit(font_b.render("Second Reality v2.0",True,(255,220,100)),(px+10,y)); y+=20
        st="Tick: %d  %s  seed=%d"%(world._tick,"[PAUSED]" if paused else "[%d tps]"%speed,seed)
        screen.blit(font.render(st,True,COLORS["text"]),(px+10,y)); y+=18
        screen.blit(font.render("Pop: %d alive / %d dead  B:%d D:%d"%(s["alive"],s["dead"],s["births"],s["deaths"]),True,COLORS["text"]),(px+10,y)); y+=16
        screen.blit(font.render("Wealth: %.0f total / %.1f avg"%(s["total_wealth"],s["avg_wealth"]),True,COLORS["text"]),(px+10,y)); y+=14
        screen.blit(font.render("Money: %.0f  Infl: %.4f  Viol: %d"%(s["money_supply"],s["inflation_rate"],s["violations"]),True,COLORS["text"]),(px+10,y)); y+=14
        screen.blit(font.render("Trades: %d  Created: %.0f  Mem: %d"%(s["total_trades"],s["wealth_created"],s["total_memory"]),True,COLORS["text"]),(px+10,y)); y+=14
        screen.blit(font.render("Know: %.1f  Creat: %.1f  Bldg: %d"%(s["avg_knowledge"],s["avg_creativity"],s["buildings"]),True,COLORS["text"]),(px+10,y)); y+=20
        screen.blit(font_b.render("五层需求 (均值)",True,(180,220,255)),(px+10,y)); y+=18
        for i,n in enumerate(FIVE_LAYER_NEEDS):
            screen.blit(font_s.render(NEED_LABELS_CN[i],True,COLORS["text"]),(px+10,y))
            draw_need_bar(px+50,y,s["avg_needs"][n],pw-75); y+=14
        y+=6
        screen.blit(font_b.render("实时曲线（各自归一化）",True,(180,220,255)),(px+10,y)); y+=15
        draw_chart_legend(px+10,y,[(hist["pop"],COLORS["curve_pop"],"人口"),
            (hist["gini"],COLORS["curve_gini"],"基尼")]); y+=13
        draw_chart(px+10,y,pw-20,58,[(hist["pop"],COLORS["curve_pop"],"人口"),
            (hist["gini"],COLORS["curve_gini"],"基尼")]); y+=62
        draw_chart_legend(px+10,y,[(hist["need"],COLORS["curve_need"],"需求"),
            (hist["money"],COLORS["curve_money"],"货币")]); y+=13
        draw_chart(px+10,y,pw-20,58,[(hist["need"],COLORS["curve_need"],"需求"),
            (hist["money"],COLORS["curve_money"],"货币")]); y+=62
        screen.blit(font_b.render("事件流",True,(180,220,255)),(px+10,y)); y+=15
        for line in list(feed)[-6:]:
            screen.blit(font_s.render(line[:34],True,(170,180,200)),(px+10,y)); y+=11
        y+=6
        if selected:
            a=selected
            if not a.alive:
                screen.blit(font.render("[已故] %s (%s)"%(a.name,a.aid),True,COLORS["agent_dead"]),(px+10,y)); y+=16
            else:
                screen.blit(font_b.render("%s (%s) gen%d"%(a.name,a.aid,a.generation),True,(255,255,150)),(px+10,y)); y+=16
                screen.blit(font.render("State: %s  Age: %d  Wealth: %.0f"%(a.state.value,a.age,a.wealth),True,COLORS["text"]),(px+10,y)); y+=14
                screen.blit(font.render("Energy: %.0f  Rep: %.0f  Know: %.1f"%(a.energy,a.reputation,a.knowledge),True,COLORS["text"]),(px+10,y)); y+=14
                ms=a.memory.stats()
                screen.blit(font.render("Mem: %d (S:%d L:%d)  Creat: %.1f"%(ms["total_memories"],ms["stm_count"],ms["ltm_count"],a.creativity),True,COLORS["text"]),(px+10,y)); y+=14
                for i,n in enumerate(FIVE_LAYER_NEEDS):
                    screen.blit(font_s.render(NEED_LABELS_CN[i],True,COLORS["text"]),(px+10,y))
                    draw_need_bar(px+50,y,a.needs[n],pw-75,h=7); y+=11
                y+=4
                inv_str=str(dict(a.inventory)) if a.inventory else "none"
                screen.blit(font_s.render("Items: "+inv_str,True,COLORS["text"]),(px+10,y)); y+=12
                if a.partner_id:
                    p=world.find_agent(a.partner_id); pn=p.name if p else "?"
                    screen.blit(font_s.render("配偶: %s  好友: %d  子女: %d"%(pn,len(a.friends),len(a.children_ids)),True,COLORS["text"]),(px+10,y)); y+=12
                recent=a.memory.recall(k=3)
                if recent:
                    screen.blit(font_s.render("最近记忆:",True,(180,200,255)),(px+10,y)); y+=11
                    for m in recent[:3]:
                        screen.blit(font_s.render("  "+m.content[:25],True,(160,180,200)),(px+10,y)); y+=10
        hy=WORLD_SIZE*CELL+5
        screen.blit(font_s.render(
            "SPACE暂停 | +/- 速度 | 点击选中 | P截图 S存档 R重置 H帮助 | 视觉开关已开: %s"%
            ("".join(k for k,v in [("W",show_heat),("F",show_graph),("E",show_eventfx),("N",show_daynight)] if v) or "无"),
            True,(150,150,170)),(10,hy))
        draw_legend(10,hy+20)
        if show_help:
            lines=["=== Second Reality v2.0 帮助 ===",
                "需求层级: 生理 > 安全 > 归属 > 尊重 > 自我实现",
                "行为: 休息/工作/社交/交易/学习/创造；已婚育龄者会主动与配偶会合",
                "经济: UBI/10t  税/30t  通胀/50t  债务下限  财富硬顶  劳动铸币(记账)",
                "记忆: STM->LTM 巩固 + 衰减；采集点写入记忆用于导航(无上帝视角)",
                "确定性: 同 seed + 同 config => 世界状态逐字节可复现 (--verify-determinism)",
                "视觉开关: W=财富热力  F=关系网  E=事件特效  N=昼夜色调  P=截图(存当前帧 PNG)",
                "面板: 热力底图 / 实时曲线(人口·基尼·需求·货币) / 事件流 / 鼠标悬停即看详情"]
            hh=len(lines)*15+12; hw=max(font.size(t)[0] for t in lines)+16
            box=pygame.Surface((hw,hh),pygame.SRCALPHA); box.fill((12,12,20,240))
            pygame.draw.rect(box,(120,120,150),(0,0,hw,hh),1)
            screen.blit(box,(8,hy+18))
            for i,line in enumerate(lines):
                screen.blit(font.render(line,True,(200,200,150)),(16,hy+24+i*15))

    def handle_click(pos):
        nonlocal selected
        mx,my=pos
        if mx<WORLD_SIZE*CELL and my<WORLD_SIZE*CELL:
            gx,gy=mx//CELL,my//CELL
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
        # 静默推演 N tick 后渲染一帧存图（无需显示器，配合 SDL_VIDEODRIVER=dummy）
        for _ in range(max_ticks or 600):
            note_events(world.tick()); sample_history()
        for _ in range(8): sample_history()
        del fx[:-8]   # 交互模式下由 ttl 自然衰减；静默推演时需手动裁剪，否则标记会全部叠在世界里
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
                elif ev.key==pygame.K_r: world=NohnWorld(config); selected=None; fx.clear(); feed.clear()  # 同 seed 重置 => 完全相同的世界
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
    ap=argparse.ArgumentParser(description="Second Reality v2.0 - Virtual World Model")
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
