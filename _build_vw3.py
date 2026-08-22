#!/usr/bin/env python3
"""Append NohnWorld class to virtual_world.py"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

world_code = '''
class NohnWorld:
    NAMES=["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Eta","Theta",
           "Iota","Kappa","Lambda","Mu","Nu","Xi","Omicron","Pi",
           "Rho","Sigma","Tau","Upsilon","Phi","Chi","Psi","Omega"]
    def __init__(self, config=None):
        self.config=config or WorldConfig(); self.size=self.config.world_size; self.tick=0
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
            "amount":random.randint(3,15),"regen_rate":random.uniform(0.05,0.2)})
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
        self.event_log.append(Event(eid=self.next_eid(),etype=EventType.BIRTH,actor=aid,tick=self.tick,
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
        for a in alive: a.receive_ubi(UBI_DAILY); a.last_ubi_tick=self.tick
        self.event_log.append(Event(eid=self.next_eid(),etype=EventType.UBI,actor="SYSTEM",tick=self.tick,
            data={"cycle":self._ubi_cycle,"amount_per":UBI_DAILY}))
    def _collect_taxes(self):
        alive=[a for a in self.agents if a.alive]
        total=sum(a.pay_tax(a.wealth*TAX_RATE) for a in alive)
        self.reserve.collect_tax(total)
        self.event_log.append(Event(eid=self.next_eid(),etype=EventType.TAX,actor="SYSTEM",tick=self.tick,
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
                ev.append(Event(eid=self.next_eid(),etype=EventType.DEATH,actor=a.aid,tick=self.tick,
                    data={"cause":"old_age","age":a.age}))
        return ev
    def _regenerate_resources(self):
        for r in self.resources:
            if r["amount"]<15 and random.random()<r["regen_rate"]: r["amount"]+=1
        if random.random()<0.1 and len(self.resources)<self.size*self.size*0.05: self._spawn_resource()
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
                ev.append(Event(eid=self.next_eid(),etype=EventType.VIOLATION,actor=a.aid,tick=self.tick,
                    data={"rule":"debt_limit"}))
                a.wealth=max(a.wealth,self.config.debt_limit*0.5)
            if a.wealth>self.config.max_wealth:
                a.violations+=1; excess=a.wealth-self.config.max_wealth; tax=excess*WEALTH_HARDCAP_TAX
                a.wealth-=tax; self.reserve.collect_tax(tax)
                ev.append(Event(eid=self.next_eid(),etype=EventType.VIOLATION,actor=a.aid,tick=self.tick,
                    data={"rule":"wealth_hardcap","penalty":tax}))
        return ev
    def tick(self):
        self.tick+=1; te=[]; alive=[a for a in self.agents if a.alive]
        for a in alive:
            a.age+=1; a.perceive(self); d=a.think(self); te.extend(a.act(d,self))
        self._regenerate_resources(); self._build_houses()
        te.extend(self._check_reproduction()); te.extend(self._check_deaths()); te.extend(self._compliance_check())
        if self.tick%10==0: self._distribute_ubi()
        if self.tick%30==0: self._collect_taxes()
        if self.tick%50==0: self._apply_inflation()
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
        return {"tick":self.tick,"alive":len(alive),"dead":len([a for a in self.agents if not a.alive]),
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
        return {"tick":self.tick,"config":self.config.__dict__,
            "agents":[a.to_dict() for a in self.agents],"resources":self.resources,
            "buildings":self.buildings,"stats":self.get_stats(),
            "reserve":{"money_supply":self.reserve.money_supply,"treasury":self.reserve.treasury,
                "total_ubi":self.reserve.total_ubi_distributed,"total_tax":self.reserve.total_tax_collected}}
    def save_state(self, fp):
        with open(fp,'w',encoding='utf-8') as f: json.dump(self.export_state(),f,ensure_ascii=False,indent=2,default=str)
'''

with open("virtual_world.py", "a", encoding="utf-8") as f:
    f.write(world_code)
print("NohnWorld class appended OK")
