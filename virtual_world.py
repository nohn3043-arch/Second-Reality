#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Second Reality v2.0 - Virtual World Model
Aligned with system/ layer: 5-layer needs + memory + compliant economy + perceive/think/act
Self-contained: pure in-memory simulation, runs GUI/headless standalone
"""
import random, math, time, json
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

@dataclass
class Memory:
    content:str; importance:float=0.5; emotion:str="neutral"; age:int=0
    tags:List[str]=field(default_factory=list); in_ltm:bool=False

class MemoryVault:
    def __init__(self, stm_cap=MEM_STM, ltm_cap=MEM_LTM, consolidation=MEM_CONSOL, decay=MEM_DECAY):
        self.stm=[]; self.ltm=[]; self.stm_cap=stm_cap; self.ltm_cap=ltm_cap
        self.consolidation_rate=consolidation; self.decay_rate=decay; self.tick=0
    def remember(self, content, importance=0.5, emotion="neutral", tags=None):
        self.stm.insert(0, Memory(content=content,importance=importance,emotion=emotion,tags=tags or []))
        if len(self.stm)>self.stm_cap: self.stm=self.stm[:self.stm_cap]
    def consolidate(self):
        rem=[]
        for m in self.stm:
            m.age+=1
            if m.importance>=self.consolidation_rate and len(self.ltm)<self.ltm_cap:
                m.in_ltm=True; self.ltm.append(m)
            elif m.importance>=self.decay_rate*2: rem.append(m)
        self.stm=rem
    def decay_memories(self):
        self.tick+=1
        if self.tick%MEM_DECAY_INT!=0: return
        self.ltm=[m for m in self.ltm if m.importance>self.decay_rate]
        for m in self.ltm: m.importance*=(1-self.decay_rate)
    def recall(self, k=5, tag=None):
        c=list(self.stm)+list(self.ltm)
        if tag: c=[m for m in c if tag in m.tags]
        c.sort(key=lambda m:m.importance, reverse=True)
        return c[:k]
    def stats(self):
        return {"stm_count":len(self.stm),"ltm_count":len(self.ltm),"total_memories":len(self.stm)+len(self.ltm)}

class EconomicReserve:
    def __init__(self, initial_supply=10000.0, ubi_amount=UBI_DAILY, tax_rate=TAX_RATE,
                 inflation_rate=INFLATION_RATE, debt_limit=DEBT_LIMIT):
        self.money_supply=initial_supply; self.treasury=0.0; self.ubi_amount=ubi_amount
        self.tax_rate=tax_rate; self.inflation_rate=inflation_rate; self.debt_limit=debt_limit
        self.total_ubi_distributed=0.0; self.total_tax_collected=0.0
    def distribute_ubi(self, pop):
        t=self.ubi_amount*pop; self.money_supply+=t; self.total_ubi_distributed+=t; return t
    def collect_tax(self, amt): self.treasury+=amt; self.total_tax_collected+=amt
    def apply_inflation(self): self.money_supply*=(1+self.inflation_rate)
    def grant(self, amt): self.money_supply+=amt

@dataclass
class NohnAgent:
    aid:str; name:str; pos:Position
    needs:Dict[str,float]=field(default_factory=lambda:{"physiology":100.0,"safety":100.0,
        "belonging":100.0,"esteem":100.0,"self_actualization":50.0})
    energy:float=100.0; wealth:float=100.0
    state:AgentState=AgentState.IDLE; alive:bool=True
    age:int=0; generation:int=0
    personality:Dict[str,float]=field(default_factory=lambda:{"openness":random.uniform(0.3,0.9),
        "conscientiousness":random.uniform(0.3,0.9),"extraversion":random.uniform(0.2,0.9),
        "agreeableness":random.uniform(0.3,0.9),"neuroticism":random.uniform(0.1,0.7)})
    skills:Dict[str,float]=field(default_factory=lambda:{"gathering":random.uniform(0.3,0.8),
        "crafting":random.uniform(0.2,0.7),"social":random.uniform(0.2,0.8),
        "trading":random.uniform(0.2,0.7),"learning":random.uniform(0.2,0.7),
        "creating":random.uniform(0.1,0.6)})
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
        if p["belonging"]>35:
            oa=[x for x in self._perceived if x["type"]=="agent"]
            if oa:
                oa.sort(key=lambda x:x["dist"])
                return AgentState.SOCIALIZING,{"action":"socialize","target_id":oa[0]["id"]}
            return AgentState.IDLE,{"action":"seek_company"}
        if p["esteem"]>35 and self.wealth>50:
            tt=[x for x in self._perceived if x["type"]=="agent" and x["id"]!=self.aid]
            if tt and random.random()<self.skills["trading"]:
                return AgentState.TRADING,{"action":"trade","target_id":random.choice(tt)["id"]}
            return AgentState.WORKING,{"action":"work"}
        if p["self_actualization"]>30 and self.energy>40:
            if random.random()<self.personality["openness"]*self.skills["creating"]:
                return AgentState.CREATING,{"action":"create"}
            if random.random()<self.skills["learning"]:
                return AgentState.LEARNING,{"action":"learn"}
        if self.energy>30 and random.random()<0.6: return AgentState.WORKING,{"action":"work"}
        return AgentState.IDLE,{"action":"wander"}

    def act(self, decision, world):
        if not self.alive: return []
        ns,ai=decision; self.state=ns; events=[]
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
                self.memory.remember("gathered_"+rt,0.4,"satisfied",["work","gather"])
            elif act=="seek_food":
                nearest=self._find_nearest_food(world)
                if nearest: self._move_toward(nearest[0],nearest[1],world)
                else: self._wander(world)
            else:
                self._wander(world); wage=5+int(self.skills["crafting"]*10)
                self.wealth+=wage; world._wc+=wage
                self.needs["esteem"]=min(100,self.needs["esteem"]+3)
                if random.random()<0.3: self.needs["physiology"]=min(100,self.needs["physiology"]+10)
                self.memory.remember("worked_for_wage",0.3,"neutral",["work"])
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
                    if random.random()<0.2:
                        k=random.uniform(0.1,0.5); self.knowledge+=k; o.knowledge+=k*0.8
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
                        rt=random.choice(list(o.inventory.keys())); price=random.randint(5,20)
                        if self.wealth>=price:
                            self.wealth-=price; o.wealth+=price
                            self.inventory[rt]=self.inventory.get(rt,0)+1; o.inventory[rt]-=1
                            if o.inventory[rt]<=0: del o.inventory[rt]
                            self.needs["esteem"]=min(100,self.needs["esteem"]+5)
                            o.needs["esteem"]=min(100,o.needs["esteem"]+3)
                            world._wt+=1
                            self.memory.remember("traded_"+rt,0.4,"satisfied",["trade"])
                            events.append(Event(eid=world.next_eid(),etype=EventType.TRADE,actor=self.aid,
                                target=tid,tick=world._tick,data={"price":price,"item":rt}))
            else: self._wander(world)
        elif ns==AgentState.LEARNING:
            self.energy-=5; sk=random.choice(list(self.skills.keys()))
            self.skills[sk]=min(1.0,self.skills[sk]+0.01*self.personality["openness"])
            self.knowledge+=random.uniform(0.2,0.8)
            self.needs["self_actualization"]=min(100,self.needs["self_actualization"]+8)
            self.memory.remember("learned_"+sk,0.5,"curious",["learning"])
            events.append(Event(eid=world.next_eid(),etype=EventType.PRODUCE,actor=self.aid,tick=world._tick,
                data={"action":"learn","skill":sk}))
        elif ns==AgentState.CREATING:
            self.energy-=10; ct=random.choice(["craft","art","idea"])
            self.creativity+=random.uniform(0.3,1.0)*self.personality["openness"]
            self.knowledge+=random.uniform(0.1,0.4)
            self.needs["self_actualization"]=min(100,self.needs["self_actualization"]+15)
            self.needs["esteem"]=min(100,self.needs["esteem"]+5)
            if ct=="craft" and random.random()<0.5:
                item=random.choice(["tool","artwork","book"]); self.inventory[item]=self.inventory.get(item,0)+1
            self.memory.remember("created_"+ct,0.7,"inspired",["creation"])
            events.append(Event(eid=world.next_eid(),etype=EventType.PRODUCE,actor=self.aid,tick=world._tick,
                data={"action":"create","type":ct}))
        else:
            self.energy-=1; self._wander(world)
        for n in self.needs: self.needs[n]=max(0,self.needs[n]-NEED_DECAY.get(n,0.3))
        self.memory.consolidate(); self.memory.decay_memories()
        if self.needs["physiology"]<=0:
            self.alive=False; self.state=AgentState.DEAD; world._wd+=1
            events.append(Event(eid=world.next_eid(),etype=EventType.DEATH,actor=self.aid,tick=world._tick,
                data={"cause":"starvation"}))
        return events

    def _find_nearest_food(self, world):
        best=None; best_d=999
        for r in world.resources:
            if r["amount"]<=0 or r["type"] not in ("food","water","fruit"): continue
            d=math.hypot(r["pos"][0]-self.pos.x, r["pos"][1]-self.pos.y)
            if d<best_d: best_d=d; best=r["pos"]
        return best

    def _move_toward(self,tx,ty,world):
        dx,dy=tx-self.pos.x,ty-self.pos.y; d=math.hypot(dx,dy)
        if d>0:
            s=min(1.0,d); self.pos.x+=int(round(dx/d*s)); self.pos.y+=int(round(dy/d*s))
        self.pos.x=max(0,min(world.size-1,self.pos.x)); self.pos.y=max(0,min(world.size-1,self.pos.y))
    def _wander(self,world):
        self.pos.x=max(0,min(world.size-1,self.pos.x+random.choice([-1,0,1])))
        self.pos.y=max(0,min(world.size-1,self.pos.y+random.choice([-1,0,1])))
    def receive_ubi(self,amt):
        self.wealth+=amt; self.needs["safety"]=min(100,self.needs["safety"]+3)
    def pay_tax(self,amt):
        paid=min(self.wealth,amt); self.wealth-=paid; return paid
    def to_dict(self):
        d=asdict(self); d["pos"]={"x":self.pos.x,"y":self.pos.y}; d["state"]=self.state.value
        if self.home_pos: d["home_pos"]={"x":self.home_pos.x,"y":self.home_pos.y}
        d["memory_stats"]=self.memory.stats(); del d["_perceived"]; return d

class NohnWorld:
    NAMES=["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Eta","Theta",
           "Iota","Kappa","Lambda","Mu","Nu","Xi","Omicron","Pi",
           "Rho","Sigma","Tau","Upsilon","Phi","Chi","Psi","Omega"]
    def __init__(self, config=None):
        self.config=config or WorldConfig(); self.size=self.config.world_size; self._tick=0
        self.agents=[]; self.resources=[]; self.buildings=[]; self.events=[]; self.event_log=[]
        self.reserve=EconomicReserve(initial_supply=self.config.initial_money_supply,
            inflation_rate=self.config.inflation_rate,debt_limit=self.config.debt_limit)
        self._eid=0; self._wc=0.0; self._wt=0; self._wd=0; self._wb=0; self._ubi_cycle=0
        self._used_names=set(); self._init_world()
    def _init_world(self):
        for _ in range(self.config.initial_resources): self._spawn_resource()
        for _ in range(self.config.initial_buildings):
            self.buildings.append({"type":random.choice(["house","market","workshop","garden","library"]),
                "pos":(random.randint(0,self.size-1),random.randint(0,self.size-1)),"age":0})
        for _ in range(self.config.initial_agents): self._spawn_agent()
    def _spawn_resource(self):
        rt=random.choices(["food","water","wood","stone","herb","ore","fruit"],weights=[30,25,15,10,8,7,5])[0]
        self.resources.append({"type":rt,"pos":(random.randint(0,self.size-1),random.randint(0,self.size-1)),
            "amount":random.randint(8,25),"regen_rate":random.uniform(0.15,0.4)})
    def _gen_name(self):
        avail=[n for n in self.NAMES if n not in self._used_names]
        n=random.choice(avail) if avail else "Resident"+str(len(self._used_names))
        self._used_names.add(n); return n
    def _spawn_agent(self, parent_ids=None, pos=None):
        name=self._gen_name()
        pos=pos or Position(random.randint(0,self.size-1),random.randint(0,self.size-1))
        gen=0
        if parent_ids:
            ps=[a for a in self.agents if a.aid in parent_ids]
            if ps: gen=max(p.generation for p in ps)+1
        aid="A%04d"%len(self.agents)
        a=NohnAgent(aid=aid,name=name,pos=pos,generation=gen,wealth=random.uniform(50,150))
        if parent_ids:
            for pid in parent_ids:
                p=self.find_agent(pid)
                if p: p.children_ids.append(aid); p.wealth-=20; a.wealth+=10
            a.needs["belonging"]=80
        self.agents.append(a); self._wb+=1
        self.event_log.append(Event(eid=self.next_eid(),etype=EventType.BIRTH,actor=aid,tick=self._tick,
            data={"parent_ids":list(parent_ids) if parent_ids else [],"generation":gen}))
        return a
    def spawn_agent(self, pos=None): return self._spawn_agent(pos=pos)
    def next_eid(self):
        eid="E%06d"%self._eid; self._eid+=1; return eid
    def find_agent(self, aid):
        for a in self.agents:
            if a.aid==aid: return a
        return None
    def consume_resource(self,x,y,amt):
        for r in self.resources:
            if r["pos"]==(x,y) and r["amount"]>0: r["amount"]=max(0,r["amount"]-amt); return
    def _distribute_ubi(self):
        self._ubi_cycle+=1; alive=[a for a in self.agents if a.alive]
        self.reserve.distribute_ubi(len(alive))
        for a in alive: a.receive_ubi(UBI_DAILY); a.last_ubi_tick=self._tick
        self.event_log.append(Event(eid=self.next_eid(),etype=EventType.UBI,actor="SYSTEM",tick=self._tick,
            data={"cycle":self._ubi_cycle,"amount_per":UBI_DAILY}))
    def _collect_taxes(self):
        alive=[a for a in self.agents if a.alive]
        total=sum(a.pay_tax(a.wealth*TAX_RATE) for a in alive)
        self.reserve.collect_tax(total)
        self.event_log.append(Event(eid=self.next_eid(),etype=EventType.TAX,actor="SYSTEM",tick=self._tick,
            data={"total_collected":total}))
    def _apply_inflation(self): self.reserve.apply_inflation()
    def _check_reproduction(self):
        ev=[]; alive=[a for a in self.agents if a.alive]
        for a in alive:
            if not a.partner_id and a.age>20 and a.needs["belonging"]>70:
                for b in alive:
                    if b.aid!=a.aid and b.alive and not b.partner_id and b.age>18 and b.needs["belonging"]>70:
                        if math.hypot(a.pos.x-b.pos.x,a.pos.y-b.pos.y)<=2 and random.random()<0.02:
                            a.partner_id=b.aid; b.partner_id=a.aid
                            ev.append(Event(eid=self.next_eid(),etype=EventType.MARRIAGE,actor=a.aid,target=b.aid,tick=self.tick))
                            break
            if (a.partner_id and a.alive and 22<a.age<60 and a.needs["physiology"]>60
                    and a.needs["safety"]>50 and a.wealth>80):
                p=self.find_agent(a.partner_id)
                if p and p.alive and math.hypot(a.pos.x-p.pos.x,a.pos.y-p.pos.y)<=2 and random.random()<0.01:
                    self._spawn_agent(parent_ids=(a.aid,p.aid),
                        pos=Position((a.pos.x+p.pos.x)//2,(a.pos.y+p.pos.y)//2))
        return ev
    def _check_deaths(self):
        ev=[]
        for a in self.agents:
            if a.alive and a.age>80 and random.random()<0.05:
                a.alive=False; a.state=AgentState.DEAD; self._wd+=1
                ev.append(Event(eid=self.next_eid(),etype=EventType.DEATH,actor=a.aid,tick=self._tick,
                    data={"cause":"old_age","age":a.age}))
        return ev
    def _regenerate_resources(self):
        for r in self.resources:
            if r["amount"]<25 and random.random()<r["regen_rate"]: r["amount"]+=2
        if random.random()<0.15 and len(self.resources)<self.size*self.size*0.08: self._spawn_resource()
    def _build_houses(self):
        for a in self.agents:
            if a.alive and not a.home_pos and a.wealth>200 and random.random()<0.005:
                a.home_pos=Position(a.pos.x,a.pos.y)
                self.buildings.append({"type":"house","pos":(a.pos.x,a.pos.y),"owner":a.aid,"age":0})
                a.wealth-=100; a.needs["safety"]=min(100,a.needs["safety"]+20)
    def _compliance_check(self):
        ev=[]
        for a in self.agents:
            if not a.alive: continue
            if a.wealth<self.config.debt_limit:
                a.violations+=1
                ev.append(Event(eid=self.next_eid(),etype=EventType.VIOLATION,actor=a.aid,tick=self._tick,
                    data={"rule":"debt_limit"}))
                a.wealth=max(a.wealth,self.config.debt_limit*0.5)
            if a.wealth>self.config.max_wealth:
                a.violations+=1; excess=a.wealth-self.config.max_wealth; tax=excess*WEALTH_HARDCAP_TAX
                a.wealth-=tax; self.reserve.collect_tax(tax)
                ev.append(Event(eid=self.next_eid(),etype=EventType.VIOLATION,actor=a.aid,tick=self._tick,
                    data={"rule":"wealth_hardcap","penalty":tax}))
        return ev
    def tick(self):
        self._tick+=1; te=[]; alive=[a for a in self.agents if a.alive]
        for a in alive:
            a.age+=1; a.perceive(self); d=a.think(self); te.extend(a.act(d,self))
        self._regenerate_resources(); self._build_houses()
        te.extend(self._check_reproduction()); te.extend(self._check_deaths()); te.extend(self._compliance_check())
        if self._tick%10==0: self._distribute_ubi()
        if self._tick%30==0: self._collect_taxes()
        if self._tick%50==0: self._apply_inflation()
        for b in self.buildings: b["age"]+=1
        self.events.extend(te); self.event_log.extend(te)
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
            "wealth_created":self._wc,"total_trades":self._wt,"avg_needs":an,
            "avg_knowledge":sum(a.knowledge for a in alive)/len(alive) if alive else 0,
            "avg_creativity":sum(a.creativity for a in alive)/len(alive) if alive else 0,
            "total_memory":sum(a.memory.stats()["total_memories"] for a in alive),
            "resources":len(self.resources),"buildings":len(self.buildings),
            "money_supply":self.reserve.money_supply,"inflation_rate":self.reserve.inflation_rate,
            "ubi_cycles":self._ubi_cycle,"violations":sum(a.violations for a in self.agents)}
    def get_audit_report(self):
        s=self.get_stats(); alive=s["alive"]; n=s["avg_needs"]
        dims={}
        dims["physiology"]=min(100,n["physiology"]*1.2)
        dims["safety"]=min(100,n["safety"]*1.1)
        dims["belonging"]=min(100,n["belonging"]*1.1)
        dims["esteem"]=min(100,n["esteem"])
        dims["self_actualization"]=min(100,n["self_actualization"]*1.5)
        dims["economy"]=max(0,100-s["violations"]*5)
        dims["sustainability"]=max(0,100-abs(s["inflation_rate"]-0.02)*500)
        overall=sum(dims.values())/len(dims)
        return {"overall_score":overall,"dimensions":dims,"stats":s}
    def export_state(self):
        return {"tick":self._tick,"config":self.config.__dict__,
            "agents":[a.to_dict() for a in self.agents],"resources":self.resources,
            "buildings":self.buildings,"stats":self.get_stats(),
            "reserve":{"money_supply":self.reserve.money_supply,"treasury":self.reserve.treasury,
                "total_ubi":self.reserve.total_ubi_distributed,"total_tax":self.reserve.total_tax_collected}}
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
    "bar_bg":(50,50,65),"panel":(25,25,40)}

def run_gui(tps=10, max_ticks=None):
    import pygame
    pygame.init()
    screen=pygame.display.set_mode((WW,WH))
    pygame.display.set_caption("Second Reality v2.0 - Virtual World")
    try:
        font=pygame.font.SysFont("microsoftyahei,simhei,arial",12)
        font_b=pygame.font.SysFont("microsoftyahei,simhei,arial",13,bold=True)
        font_s=pygame.font.SysFont("microsoftyahei,simhei,arial",10)
    except:
        font=pygame.font.Font(None,14); font_b=pygame.font.Font(None,16); font_s=pygame.font.Font(None,11)
    clock=pygame.time.Clock()
    config=WorldConfig(world_size=WORLD_SIZE,initial_agents=30,initial_resources=80,initial_buildings=8)
    world=NohnWorld(config)
    running=True; paused=False; speed=tps; selected=None; show_help=False

    def draw_world():
        pygame.draw.rect(screen,COLORS["bg"],(0,0,WORLD_SIZE*CELL,WORLD_SIZE*CELL))
        for x in range(0,WORLD_SIZE*CELL+1,CELL):
            pygame.draw.line(screen,COLORS["grid"],(x,0),(x,WORLD_SIZE*CELL))
        for y in range(0,WORLD_SIZE*CELL+1,CELL):
            pygame.draw.line(screen,COLORS["grid"],(0,y),(WORLD_SIZE*CELL,y))
        for r in world.resources:
            if r["amount"]<=0: continue
            rx,ry=r["pos"]; c=COLORS.get(r["type"],(128,128,128))
            sz=max(2,min(CELL-2,int(r["amount"]/2)))
            pygame.draw.circle(screen,c,(rx*CELL+CELL//2,ry*CELL+CELL//2),sz//2+1)
        for b in world.buildings:
            bx,by=b["pos"]; c=COLORS.get(b["type"],(128,128,128))
            rect=pygame.Rect(bx*CELL+1,by*CELL+1,CELL-2,CELL-2)
            pygame.draw.rect(screen,c,rect); pygame.draw.rect(screen,(0,0,0),rect,1)
        for a in world.agents:
            cx,cy=a.pos.x*CELL+CELL//2,a.pos.y*CELL+CELL//2
            if not a.alive:
                pygame.draw.line(screen,COLORS["agent_dead"],(cx-3,cy-3),(cx+3,cy+3),1)
                pygame.draw.line(screen,COLORS["agent_dead"],(cx-3,cy+3),(cx+3,cy-3),1)
                continue
            c=COLORS.get("agent_"+a.state.value,COLORS["agent_idle"])
            pygame.draw.circle(screen,c,(cx,cy),CELL//2-1)
            pygame.draw.circle(screen,(0,0,0),(cx,cy),CELL//2-1,1)
            if a.partner_id:
                p=world.find_agent(a.partner_id)
                if p and p.alive:
                    pygame.draw.line(screen,(255,150,200,60),(cx,cy),
                        (p.pos.x*CELL+CELL//2,p.pos.y*CELL+CELL//2),1)
            if selected and a.aid==selected.aid:
                pygame.draw.circle(screen,(255,255,100),(cx,cy),CELL//2+2,2)

    def draw_need_bar(x,y,val,w=150,h=8):
        pygame.draw.rect(screen,COLORS["bar_bg"],(x,y,w,h))
        bc=COLORS["need_high"] if val>60 else (COLORS["need_mid"] if val>30 else COLORS["need_low"])
        pygame.draw.rect(screen,bc,(x,y,int(w*val/100),h))

    def draw_stats():
        px=WORLD_SIZE*CELL; pw=WW-px
        pygame.draw.rect(screen,COLORS["panel"],(px,0,pw,WH))
        pygame.draw.line(screen,(60,60,80),(px,0),(px,WH),2)
        y=8
        s=world.get_stats()
        screen.blit(font_b.render("Second Reality v2.0",True,(255,220,100)),(px+10,y)); y+=20
        st="Tick: %d  %s"%(world._tick,"[PAUSED]" if paused else "[%d tps]"%speed)
        screen.blit(font.render(st,True,COLORS["text"]),(px+10,y)); y+=18
        screen.blit(font.render("Pop: %d alive / %d dead  B:%d D:%d"%(s["alive"],s["dead"],s["births"],s["deaths"]),True,COLORS["text"]),(px+10,y)); y+=16
        screen.blit(font.render("Wealth: %.0f total / %.1f avg"%(s["total_wealth"],s["avg_wealth"]),True,COLORS["text"]),(px+10,y)); y+=14
        screen.blit(font.render("Money: %.0f  Infl: %.4f  Viol: %d"%(s["money_supply"],s["inflation_rate"],s["violations"]),True,COLORS["text"]),(px+10,y)); y+=14
        screen.blit(font.render("Trades: %d  Created: %.0f  Mem: %d"%(s["total_trades"],s["wealth_created"],s["total_memory"]),True,COLORS["text"]),(px+10,y)); y+=14
        screen.blit(font.render("Know: %.1f  Creat: %.1f  Bldg: %d"%(s["avg_knowledge"],s["avg_creativity"],s["buildings"]),True,COLORS["text"]),(px+10,y)); y+=20
        screen.blit(font_b.render("Five-Layer Needs (avg)",True,(180,220,255)),(px+10,y)); y+=18
        for i,n in enumerate(FIVE_LAYER_NEEDS):
            screen.blit(font_s.render(NEED_LABELS_CN[i],True,COLORS["text"]),(px+10,y))
            draw_need_bar(px+50,y,s["avg_needs"][n],pw-75); y+=14
        y+=8
        if selected:
            a=selected
            if not a.alive:
                screen.blit(font.render("[DECEASED] %s (%s)"%(a.name,a.aid),True,COLORS["agent_dead"]),(px+10,y)); y+=16
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
                    screen.blit(font_s.render("Partner: %s  Friends: %d  Children: %d"%(pn,len(a.friends),len(a.children_ids)),True,COLORS["text"]),(px+10,y)); y+=12
                recent=a.memory.recall(k=3)
                if recent:
                    screen.blit(font_s.render("Recent memories:",True,(180,200,255)),(px+10,y)); y+=11
                    for m in recent[:3]:
                        screen.blit(font_s.render("  "+m.content[:25],True,(160,180,200)),(px+10,y)); y+=10
        hy=WORLD_SIZE*CELL+5
        screen.blit(font_s.render("SPACE=pause | +/-=speed | CLICK=select | S=save | H=help | R=reset",True,(150,150,170)),(10,hy))
        if show_help:
            lines=["=== Second Reality v2.0 Help ===",
                "Five-layer needs: Physiology > Safety > Belonging > Esteem > Self-Actualization",
                "Behaviors: Rest/Work/Socialize/Trade/Learn/Create",
                "Economy: UBI/10t  Tax/30t  Inflation/50t  Debt limit  Wealth hardcap",
                "New: Memory system (STM->LTM), Learning & Creation, Compliance audit",
                "Colors: W=idle Y=work P=social B=rest C=trade V=learn R=create"]
            for i,line in enumerate(lines):
                screen.blit(font.render(line,True,(200,200,150)),(10,hy+16+i*15))

    def handle_click(pos):
        nonlocal selected
        mx,my=pos
        if mx<WORLD_SIZE*CELL and my<WORLD_SIZE*CELL:
            gx,gy=mx//CELL,my//CELL
            for a in world.agents:
                if a.alive and a.pos.x==gx and a.pos.y==gy:
                    selected=a; return
            selected=None

    while running:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            elif ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_SPACE: paused=not paused
                elif ev.key in (pygame.K_EQUALS,pygame.K_PLUS,pygame.K_KP_PLUS): speed=min(60,speed+5)
                elif ev.key in (pygame.K_MINUS,pygame.K_KP_MINUS): speed=max(1,speed-5)
                elif ev.key==pygame.K_s: world.save_state("second_reality_save.json"); print("Saved")
                elif ev.key==pygame.K_h: show_help=not show_help
                elif ev.key==pygame.K_r: world=NohnWorld(config); selected=None
            elif ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1: handle_click(ev.pos)
        if not paused:
            world.tick()
            if max_ticks and world._tick>=max_ticks: running=False
        draw_world(); draw_stats(); pygame.display.flip(); clock.tick(speed)
    pygame.quit()
    return world

def run_headless(ticks=1000, verbose=False):
    config=WorldConfig(world_size=60,initial_agents=30,initial_resources=80,initial_buildings=8)
    world=NohnWorld(config)
    t0=time.time()
    for i in range(ticks):
        world.tick()
        if verbose and (i+1)%100==0:
            s=world.get_stats()
            print("Tick %d: Pop=%d AvgW=%.1f Phys=%.0f Safe=%.0f Know=%.1f"%(
                i+1,s["alive"],s["avg_wealth"],s["avg_needs"]["physiology"],s["avg_needs"]["safety"],s["avg_knowledge"]))
    el=time.time()-t0; s=world.get_stats(); r=world.get_audit_report()
    print("\n=== Simulation Complete (%d ticks, %.1fs) ==="%(ticks,el))
    print("Population: %d alive / %d dead  Births: %d  Deaths: %d"%(s["alive"],s["dead"],s["births"],s["deaths"]))
    print("Wealth: %.0f total / %.1f avg  Created: %.0f  Trades: %d"%(s["total_wealth"],s["avg_wealth"],s["wealth_created"],s["total_trades"]))
    print("Money supply: %.0f  Inflation: %.4f  Violations: %d"%(s["money_supply"],s["inflation_rate"],s["violations"]))
    print("Knowledge: %.1f  Creativity: %.1f  Total memories: %d"%(s["avg_knowledge"],s["avg_creativity"],s["total_memory"]))
    needs_str="  ".join("%s=%.0f"%(NEED_LABELS_CN[i],s["avg_needs"][n]) for i,n in enumerate(FIVE_LAYER_NEEDS))
    print("Five-layer needs:",needs_str)
    print("\nAudit Score: %.1f/100"%r["overall_score"])
    for dim,sc in r["dimensions"].items(): print("  %s: %.1f"%(dim,sc))
    return world

if __name__=="__main__":
    import sys
    if len(sys.argv)>1 and sys.argv[1]=="--headless":
        t=int(sys.argv[2]) if len(sys.argv)>2 else 1000
        run_headless(t,verbose=True)
    else:
        run_gui()
