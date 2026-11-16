# -*- coding: utf-8 -*-
"""即梦生成资产的后处理：assets_src/（原始下载） -> assets/（渲染用）。

1) 地面纹理：裁掉水印角与透视/渐晕边缘，LANCZOS 重采样到 448×448。
2) 建筑/道具/角色立绘：白底 floodfill 抠透明（阈值只吃纯白背景，保留画好的落地软阴影），
   按 alpha bbox 裁紧，缩到目标宽度。

运行：python demo/make_assets.py
"""
import os
from PIL import Image, ImageDraw, ImageChops

HERE=os.path.dirname(os.path.abspath(__file__))
SRC=os.path.join(HERE,"assets_src")
DST=os.path.join(HERE,"assets")

# (x0,y0,x1,y1) 保留区比例：避开右下水印与上缘透视渐晕；土路只取下半平坦区
TEX_CROPS={
    "tex_grass":  ("tex_grass_v2.png",(0.00,0.06,0.90,0.86)),
    "tex_forest": ("tex_forest.png",  (0.00,0.04,0.90,0.88)),
    "tex_rock":   ("tex_rock.png",    (0.00,0.04,0.90,0.88)),
    "tex_road":   ("tex_road.png",    (0.00,0.52,0.88,0.86)),
    "tex_plaza":  ("tex_plaza.png",   (0.00,0.07,0.90,0.88)),
    "tex_sea":    ("tex_sea.png",     (0.00,0.06,0.92,0.86)),
}
BLD_WIDTH={"bld_house":64,"bld_market":60,"bld_workshop":64,"bld_garden":64,"bld_library":64}
PROP_WIDTH={"prop_pine":36,"prop_oak":40,"prop_bush":26,"prop_rock":28}
CHAR_KEYS=("iris","geat","marduk","elfia","filia","abraham","mingil","edric","ayas")
NPC_KEYS=("sword","knight","mage","warrior","merchant","noble")
CHAR_HEIGHT=52
TEX_SIZE=448


def make_textures():
    os.makedirs(DST,exist_ok=True)
    for out,(src,(x0,y0,x1,y1)) in TEX_CROPS.items():
        path=os.path.join(SRC,src)
        if not os.path.exists(path):
            print("tex %-10s SKIP（缺 %s，等待生成）"%(out,src)); continue
        im=Image.open(path).convert("RGB")
        W,H=im.size
        im=im.crop((int(W*x0),int(H*y0),int(W*x1),int(H*y1)))
        im=im.resize((TEX_SIZE,TEX_SIZE),Image.LANCZOS)
        im.save(os.path.join(DST,out+".png"))
        print("tex %-10s <- %s %s"%(out,src,im.size))


def cutout(name,target_w,target_h=None):
    path=os.path.join(SRC,name+".png")
    if not os.path.exists(path):
        print("bld %-12s SKIP（缺 %s，等待生成）"%(name,name+".png")); return
    im=Image.open(path).convert("RGBA")
    im=im.resize((1024,1024),Image.LANCZOS)          # 抠图在 1024 上做，足够 64px 落地
    W,H=im.size
    seeds=[(3,3),(W-4,3),(3,H-4),(W-4,H-4),(W//2,3),(3,H//2),(W-4,H//2)]
    for sx,sy in seeds:
        if im.getpixel((sx,sy))[3]>0 and min(im.getpixel((sx,sy))[:3])>=200:
            ImageDraw.floodfill(im,(sx,sy),(255,255,255,0),thresh=60)
    bbox=im.split()[3].getbbox()
    if bbox is None:
        print("bld %-12s FAIL: 全透明"%(name,)); return
    pad=8
    box=(max(0,bbox[0]-pad),max(0,bbox[1]-pad),min(W,bbox[2]+pad),min(H,bbox[3]+pad))
    im=im.crop(box)
    w,h=im.size
    if target_h:                                  # 角色按身高归一，避免高矮不齐
        th=target_h; tw=max(1,round(w*th/h))
    else:
        tw=target_w; th=max(1,round(h*tw/w))
    im=im.resize((tw,th),Image.LANCZOS)
    im.save(os.path.join(DST,name+".png"))
    print("bld %-12s %s  (from bbox %s)"%(name,im.size,bbox))


def glow_cutout(name):
    """黑底辉光资产（天穹裂痕）：max(r,g,b) 作 alpha——黑底全透、亮芯不透明。"""
    path=os.path.join(SRC,name+".png")
    if not os.path.exists(path):
        print("sky %-10s SKIP（缺 %s，等待生成）"%(name,name)); return
    im=Image.open(path).convert("RGB")
    r,g,b=im.split()
    im.putalpha(ImageChops.lighter(ImageChops.lighter(r,g),b))
    os.makedirs(DST,exist_ok=True)
    im.save(os.path.join(DST,name+".png"))
    print("sky %-10s %s"%(name,im.size))


if __name__=="__main__":
    make_textures()
    for name,tw in BLD_WIDTH.items():
        cutout(name,tw)
    for name,tw in PROP_WIDTH.items():
        cutout(name,tw)
    for k in CHAR_KEYS:
        cutout("char_"+k,None,target_h=CHAR_HEIGHT)
    for k in NPC_KEYS:
        cutout("npc_"+k,None,target_h=CHAR_HEIGHT)
    glow_cutout("sky_rift")
    print("done ->",DST)
