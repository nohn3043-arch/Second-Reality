#!/usr/bin/env python3
"""Build virtual_world.py v2.0 from parts"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

parts = []

parts.append('''#!/usr/bin/env python3
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
NEED_DECAY = {"physiology":0.5,"safety":0.3,"belonging":0.4,"esteem":0.3,"self_actualization":0.2}
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
    world_size:int=60; initial_agents:int=30; initial_resources:int=80; initial_buildings:int=8
    initial_money_supply:float=10000.0; inflation_rate:float=INFLATION_RATE
    debt_limit:float=DEBT_LIMIT; max_wealth:float=MAX_WEALTH; max_ticks:int=0
''')

parts.append('''
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
''')

parts.append('''
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
''')

with open("virtual_world.py", "w", encoding="utf-8") as f:
    for p in parts:
        f.write(p)
print("Parts 1-3 written OK")
