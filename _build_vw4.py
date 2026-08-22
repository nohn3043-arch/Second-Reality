#!/usr/bin/env python3
"""Append GUI and main to virtual_world.py"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

gui_code = '''
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
        st="Tick: %d  %s"%(world.tick,"[PAUSED]"%() if paused else "[%d tps]"%speed)
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
            if max_ticks and world.tick>=max_ticks: running=False
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
    print("\\n=== Simulation Complete (%d ticks, %.1fs) ==="%(ticks,el))
    print("Population: %d alive / %d dead  Births: %d  Deaths: %d"%(s["alive"],s["dead"],s["births"],s["deaths"]))
    print("Wealth: %.0f total / %.1f avg  Created: %.0f  Trades: %d"%(s["total_wealth"],s["avg_wealth"],s["wealth_created"],s["total_trades"]))
    print("Money supply: %.0f  Inflation: %.4f  Violations: %d"%(s["money_supply"],s["inflation_rate"],s["violations"]))
    print("Knowledge: %.1f  Creativity: %.1f  Total memories: %d"%(s["avg_knowledge"],s["avg_creativity"],s["total_memory"]))
    needs_str="  ".join("%s=%.0f"%(NEED_LABELS_CN[i],s["avg_needs"][n]) for i,n in enumerate(FIVE_LAYER_NEEDS))
    print("Five-layer needs:",needs_str)
    print("\\nAudit Score: %.1f/100"%r["overall_score"])
    for dim,sc in r["dimensions"].items(): print("  %s: %.1f"%(dim,sc))
    return world

if __name__=="__main__":
    import sys
    if len(sys.argv)>1 and sys.argv[1]=="--headless":
        t=int(sys.argv[2]) if len(sys.argv)>2 else 1000
        run_headless(t,verbose=True)
    else:
        run_gui()
'''

with open("virtual_world.py", "a", encoding="utf-8") as f:
    f.write(gui_code)
print("GUI and main appended OK")
