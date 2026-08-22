#!/usr/bin/env python3
"""Append NohnAgent class to virtual_world.py"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

agent_code = '''
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
        p={n:max(0,(100-v))*NEED_DECAY.get(n,0.5) for n,v in self.needs.items()}
        if self.energy<20: return AgentState.RESTING,{"reason":"low_energy"}
        if p["physiology"]>30:
            food=[x for x in self._perceived if x["type"]=="resource"
                  and x["res_type"] in ("food","water","fruit")]
            if food:
                food.sort(key=lambda x:x["dist"])
                return AgentState.WORKING,{"action":"gather","target":food[0]["pos"],"res_type":food[0]["res_type"]}
            return AgentState.WORKING,{"action":"seek_food"}
        if p["safety"]>30:
            if self.home_pos: return AgentState.RESTING,{"action":"go_home","target":(self.home_pos.x,self.home_pos.y)}
            return AgentState.IDLE,{"action":"seek_shelter"}
        if p["belonging"]>25:
            oa=[x for x in self._perceived if x["type"]=="agent"]
            if oa:
                oa.sort(key=lambda x:x["dist"])
                return AgentState.SOCIALIZING,{"action":"socialize","target_id":oa[0]["id"]}
            return AgentState.IDLE,{"action":"seek_company"}
        if p["esteem"]>25 and self.wealth>50:
            tt=[x for x in self._perceived if x["type"]=="agent" and x["id"]!=self.aid]
            if tt and random.random()<self.skills["trading"]:
                return AgentState.TRADING,{"action":"trade","target_id":random.choice(tt)["id"]}
            return AgentState.WORKING,{"action":"work"}
        if p["self_actualization"]>20 and self.energy>40:
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
            events.append(Event(eid=world.next_eid(),etype=EventType.REST,actor=self.aid,tick=world.tick,data=ai))
        elif ns==AgentState.WORKING:
            self.energy-=8; act=ai.get("action","work")
            if act=="gather":
                tx,ty=ai["target"]; self._move_toward(tx,ty,world)
                rt=ai.get("res_type","food"); g=min(2,int(self.skills["gathering"]*3))
                self.inventory[rt]=self.inventory.get(rt,0)+g
                if rt in ("food","water","fruit"): self.needs["physiology"]=min(100,self.needs["physiology"]+20)
                world.consume_resource(tx,ty,g)
                self.memory.remember("gathered_"+rt,0.4,"satisfied",["work","gather"])
            elif act=="seek_food": self._wander(world)
            else:
                self._wander(world); wage=5+int(self.skills["crafting"]*10)
                self.wealth+=wage; world._total_wealth_created+=wage
                self.needs["esteem"]=min(100,self.needs["esteem"]+3)
                self.memory.remember("worked_for_wage",0.3,"neutral",["work"])
            events.append(Event(eid=world.next_eid(),etype=EventType.PRODUCE,actor=self.aid,tick=world.tick,
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
                        target=tid,tick=world.tick,data={"action":"talk"}))
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
                            world._total_trades+=1
                            self.memory.remember("traded_"+rt,0.4,"satisfied",["trade"])
                            events.append(Event(eid=world.next_eid(),etype=EventType.TRADE,actor=self.aid,
                                target=tid,tick=world.tick,data={"price":price,"item":rt}))
            else: self._wander(world)
        elif ns==AgentState.LEARNING:
            self.energy-=5; sk=random.choice(list(self.skills.keys()))
            self.skills[sk]=min(1.0,self.skills[sk]+0.01*self.personality["openness"])
            self.knowledge+=random.uniform(0.2,0.8)
            self.needs["self_actualization"]=min(100,self.needs["self_actualization"]+8)
            self.memory.remember("learned_"+sk,0.5,"curious",["learning"])
            events.append(Event(eid=world.next_eid(),etype=EventType.PRODUCE,actor=self.aid,tick=world.tick,
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
            events.append(Event(eid=world.next_eid(),etype=EventType.PRODUCE,actor=self.aid,tick=world.tick,
                data={"action":"create","type":ct}))
        else:
            self.energy-=1; self._wander(world)
        for n in self.needs: self.needs[n]=max(0,self.needs[n]-NEED_DECAY.get(n,0.3))
        self.memory.consolidate(); self.memory.decay_memories()
        if self.needs["physiology"]<=0:
            self.alive=False; self.state=AgentState.DEAD; world._total_deaths+=1
            events.append(Event(eid=world.next_eid(),etype=EventType.DEATH,actor=self.aid,tick=world.tick,
                data={"cause":"starvation"}))
        return events

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
'''

with open("virtual_world.py", "a", encoding="utf-8") as f:
    f.write(agent_code)
print("NohnAgent class appended OK")
