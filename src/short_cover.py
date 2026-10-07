#!/usr/bin/env python3
"""Gerador oficial de capas verticais 1080x1920 do Radar dos Games.

Padrão aprovado em 06/10/2026:
- identidade verde Radar fixa;
- badge RADAR DOS GAMES no topo;
- arte oficial do jogo como protagonista;
- composição gamer de alto impacto;
- headline enorme branca + verde neon;
- painel inferior metálico/escuro com subtítulo;
- visual consistente com a thumbnail Master.
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

W,H=1080,1920
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
WHITE=(247,248,250)
GREEN=(57,255,20)
GREEN_DARK=(18,105,22)
BLACK=(5,7,11)
NAVY=(2,10,35)

def font(n): return ImageFont.truetype(FONT,n)

def clean(s):
    s=re.sub(r"\s+"," ",str(s or "")).strip()
    s=re.sub(r"(?i)\s*#shorts?\b","",s).strip()
    return s.upper() or "RADAR DOS GAMES"

def fit(draw,text,maxw,start=92,end=44):
    for size in range(start,end-1,-2):
        f=font(size)
        if draw.textbbox((0,0),text,font=f,stroke_width=4)[2] <= maxw:
            return f
    return font(end)

def approved_image(index:int, preferred_role=None):
    p=Path("output/clips.json")
    if not p.exists(): return None, None
    try: data=json.loads(p.read_text(encoding="utf-8"))
    except Exception: return None, None
    imgs=[]
    for a in data.get("assets",[]):
        if not (a.get("approved") and a.get("type")=="image"):
            continue
        if preferred_role and a.get("role") != preferred_role:
            continue
        fp=Path(str(a.get("path") or ""))
        if fp.exists() and fp.stat().st_size>20000:
            imgs.append((fp,a))
    if not imgs: return None, None
    return imgs[(max(index,1)-1)%len(imgs)]

def frame(video:Path,out:Path):
    tmp=out.with_suffix(".source.jpg")
    subprocess.run(["ffmpeg","-y","-v","error","-ss","2.0","-i",str(video),"-frames:v","1","-q:v","2",str(tmp)],check=True)
    return tmp

def split_title(title):
    title=clean(title)
    if ":" in title:
        a,b=[x.strip() for x in title.split(":",1)]
        return a[:30],b[:44]
    words=title.split()
    if len(words)<=3: return title,"DESTAQUE DO RADAR DOS GAMES"
    return " ".join(words[:3])[:30]," ".join(words[3:])[:44]

def compose(src:Path,title:str):
    with Image.open(src) as im:
        im=im.convert("RGB")
        bg=ImageOps.fit(im,(W,H),method=Image.Resampling.LANCZOS,centering=(0.5,0.45))
    bg=ImageEnhance.Contrast(bg).enhance(1.23)
    bg=ImageEnhance.Color(bg).enhance(1.14)
    canvas=bg.convert("RGBA")

    shade=Image.new("RGBA",(W,H),(0,0,0,0))
    sd=ImageDraw.Draw(shade,"RGBA")
    sd.rectangle((0,0,W,145),fill=(NAVY[0],NAVY[1],NAVY[2],245))
    sd.rectangle((0,1190,W,H),fill=(0,0,0,112))
    for i in range(16):
        p=i*20
        sd.rectangle((p,p,W-p,H-p),outline=(0,0,0,10+i*3),width=24)
    canvas=Image.alpha_composite(canvas,shade)

    ov=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(ov,"RGBA")

    # Badge superior
    badge=(270,30,810,125)
    d.rounded_rectangle(badge,radius=14,fill=(4,7,12,242),outline=GREEN+(245,),width=5)
    bf=font(38)
    a,b="RADAR DOS ","GAMES"
    aw=d.textbbox((0,0),a,font=bf)[2]; bw=d.textbbox((0,0),b,font=bf)[2]
    x=(W-aw-bw)//2
    d.text((x,54),a,font=bf,fill=WHITE+(255,),stroke_width=2,stroke_fill=BLACK+(255,))
    d.text((x+aw,54),b,font=bf,fill=GREEN+(255,),stroke_width=2,stroke_fill=BLACK+(255,))

    head,sub=split_title(title)

    # Painel inferior metálico
    panel=(70,1280,1010,1690)
    d.rounded_rectangle(panel,radius=22,fill=(8,11,16,235),outline=(145,151,160,230),width=4)
    d.rounded_rectangle((82,1292,998,1678),radius=18,outline=GREEN+(240,),width=5)
    d.rectangle((82,1330,96,1640),fill=GREEN+(255,))

    hf=fit(d,head,820,98,54)
    sf=fit(d,sub,820,68,40)
    hb=d.textbbox((0,0),head,font=hf,stroke_width=5)
    sx=120
    d.text((sx,1360),head,font=hf,fill=WHITE+(255,),stroke_width=6,stroke_fill=(0,0,0,240))
    d.text((sx,1485),sub,font=sf,fill=GREEN+(255,),stroke_width=5,stroke_fill=(0,0,0,235))

    small=font(30)
    d.text((120,1620),"RADAR DOS GAMES • SHORTS",font=small,fill=WHITE+(235,),stroke_width=2,stroke_fill=(0,0,0,200))
    d.line((0,H-16,W,H-16),fill=GREEN+(255,),width=8)
    return Image.alpha_composite(canvas,ov).convert("RGB")

def main():
    if len(sys.argv) not in (4,5,6):
        raise SystemExit("uso: short_cover.py SHORT.mp4 META.json SAIDA.jpg [INDICE] [ROLE_PREFERIDA]")
    video=Path(sys.argv[1]); meta=Path(sys.argv[2]); out=Path(sys.argv[3]); idx=int(sys.argv[4]) if len(sys.argv)>=5 else 1
    preferred_role=sys.argv[5] if len(sys.argv)==6 else None
    out.parent.mkdir(parents=True,exist_ok=True)
    data=json.loads(meta.read_text(encoding="utf-8"))
    source,asset=approved_image(idx,preferred_role)
    tmp=None
    if source is None:
        tmp=frame(video,out); source=tmp; asset=None
    img=compose(source,data.get("title",""))
    img.save(out,"JPEG",quality=95,subsampling=0,optimize=True)
    if tmp: tmp.unlink(missing_ok=True)
    with Image.open(out) as check:
        if check.size!=(W,H): raise RuntimeError(f"QUALITY_BLOCK: cover size {check.size}")
    policy={
      "status":"APPROVED",
      "policy":"radar_short_cover_v1_green; official_image_first; top_brand_badge; huge_white_green_headline; metallic_lower_panel; neon_green_brand_accents; 9:16",
      "template_version":"radar-short-cover-v1-green-2026-10-06",
      "output":str(out),"size":[W,H],"index":idx,"title":data.get("title"),
      "preferred_role":preferred_role,
      "source_path":str(source),
      "source_role":(asset or {}).get("role"),
      "source_url":(asset or {}).get("url")
    }
    out.with_name(out.stem+"-policy.json").write_text(json.dumps(policy,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(policy,ensure_ascii=False))

if __name__=="__main__": main()
