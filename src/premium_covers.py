#!/usr/bin/env python3
"""Gerador premium automático de 4 capas do Radar dos Games.

Objetivo:
- 1 thumbnail Master 1280x720;
- 3 capas Shorts 1080x1920;
- usar mídia oficial/aprovada do assunto como matéria-prima;
- identidade Radar fixa, composição gamer premium e alta legibilidade;
- tentar novamente automaticamente;
- usar thumbnail.py/short_cover.py somente como fallback técnico.
"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

OUT = Path("output")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
WHITE = (248, 249, 251)
GREEN = (57, 255, 20)
GREEN2 = (120, 255, 70)
BLACK = (4, 6, 10)
DARK = (6, 9, 15)

def fnt(size):
    return ImageFont.truetype(FONT, size)

def tokens(text):
    return {x.lower() for x in re.findall(r"[A-Za-zÀ-ÿ0-9]+", str(text or "")) if len(x) >= 3}

def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return {} if default is None else default
    return json.loads(p.read_text(encoding="utf-8"))

def clean_title(value):
    s = re.sub(r"(?i)\s*#shorts?\b", "", str(value or ""))
    s = re.sub(r"\s+", " ", s).strip(" -:|")
    return s.upper() or "RADAR DOS GAMES"

def score_asset(asset, query=""):
    if not asset.get("approved"):
        return -10**9
    role = str(asset.get("role") or "")
    ev = str(asset.get("relevance_evidence") or "")
    label = str(asset.get("source_label") or "")
    hay = f"{role} {ev} {label} {asset.get('source','')} {asset.get('url','')}"
    q = tokens(query)
    h = tokens(hay)
    overlap = len(q & h)
    s = overlap * 1_000_000
    if asset.get("type") == "image":
        s += 600_000
    else:
        s += 250_000
    if "official" in hay.lower() or "exact" in hay.lower():
        s += 500_000
    if "fallback" in hay.lower():
        s -= 400_000
    try:
        s += int(asset.get("width") or 0) * int(asset.get("height") or 0) // 100
    except Exception:
        pass
    return s

def assets():
    data = read_json(OUT / "clips.json", {"assets":[]})
    result = []
    for a in data.get("assets", []):
        p = Path(str(a.get("path") or ""))
        if a.get("approved") and p.exists() and p.stat().st_size > 20_000:
            result.append(a)

    # Resiliência: artifacts antigos podem não carregar output/media.
    # Nesse caso ainda mantemos o compositor premium usando frames do render
    # semanticamente correspondente, sem acionar o layout legado.
    master = OUT / "master.mp4"
    master_meta = read_json(OUT / "master-youtube.json", {})
    if master.exists() and master.stat().st_size > 100_000:
        result.append({
            "index": 9001, "approved": True, "type": "video", "path": str(master),
            "role": "premium_master_render_source",
            "source_label": master_meta.get("title",""),
            "relevance_evidence": "approved_master_render_semantic_source",
        })
    for i in range(1,4):
        p = OUT / "shorts" / f"short_{i}.mp4"
        meta = read_json(OUT / f"short-{i}-youtube.json", {})
        if p.exists() and p.stat().st_size > 100_000:
            result.append({
                "index": 9100+i, "approved": True, "type": "video", "path": str(p),
                "role": f"premium_short_{i}_render_source",
                "source_label": meta.get("title",""),
                "relevance_evidence": f"approved_short_{i}_render_semantic_source",
            })
    return result

def ffprobe_duration(path):
    try:
        return float(subprocess.check_output(
            ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(path)],
            text=True
        ).strip())
    except Exception:
        return 0.0

def materialize_asset(asset, key, seek_ratio=0.35):
    p = Path(asset["path"])
    if asset.get("type") == "image":
        return p
    dur = ffprobe_duration(p)
    seek = max(1.0, min((dur or 10) * seek_ratio, max(1.0, (dur or 10) - 0.5)))
    temp = OUT / "cover_sources" / f"{key}.jpg"
    temp.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg","-y","-v","error","-ss",f"{seek:.3f}","-i",str(p),
        "-frames:v","1","-q:v","2",str(temp)
    ], check=True)
    return temp

def pick_assets(query, count=3, prefer_indices=None):
    all_assets = assets()
    if prefer_indices:
        wanted = {int(x) for x in prefer_indices}
        preferred = [a for a in all_assets if int(a.get("index",-1)) in wanted]
    else:
        preferred = []
    ordered = sorted(preferred, key=lambda a: score_asset(a, query), reverse=True)
    ordered += [a for a in sorted(all_assets, key=lambda a: score_asset(a, query), reverse=True) if a not in ordered]
    return ordered[:count]

def short_scene_indices(short_no):
    manifest = read_json(OUT / "shorts" / "manifest.json", {"shorts":[]})
    plan = read_json(OUT / "auto-media-plan.json", {"scenes":[]})
    shorts = manifest.get("shorts", [])
    scenes = plan.get("scenes", [])
    if 1 <= short_no <= len(shorts):
        si = shorts[short_no-1].get("scene_index")
        if isinstance(si, int) and 0 <= si < len(scenes):
            return scenes[si].get("media_indices") or []
    return []

def crop_enhance(path, size, centering=(0.5,0.45), blur=0):
    with Image.open(path) as im:
        im = im.convert("RGB")
        im = ImageOps.fit(im, size, Image.Resampling.LANCZOS, centering=centering)
    im = ImageEnhance.Contrast(im).enhance(1.22)
    im = ImageEnhance.Color(im).enhance(1.18)
    im = ImageEnhance.Sharpness(im).enhance(1.08)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return im

def fit_font(draw, text, maxw, start, end):
    for size in range(start, end-1, -2):
        f = fnt(size)
        box = draw.textbbox((0,0), text, font=f, stroke_width=max(2,size//25))
        if box[2]-box[0] <= maxw:
            return f
    return fnt(end)

def wrap_words(draw, text, maxw, start, end, max_lines=3):
    words = clean_title(text).split()
    if not words:
        return ["RADAR DOS GAMES"], fnt(end)
    for size in range(start, end-1, -2):
        f = fnt(size)
        lines, cur = [], []
        for word in words:
            test = " ".join(cur+[word])
            if draw.textbbox((0,0),test,font=f,stroke_width=4)[2] <= maxw or not cur:
                cur.append(word)
            else:
                lines.append(" ".join(cur)); cur=[word]
        if cur: lines.append(" ".join(cur))
        if len(lines) <= max_lines:
            return lines, f
    return [" ".join(words[:max(1,len(words)//2)]), " ".join(words[max(1,len(words)//2):])], fnt(end)

def draw_brand_badge(draw, width, y, scale=1.0):
    text1, text2 = "RADAR DOS ", "GAMES"
    fs = int(31*scale)
    bf = fnt(fs)
    a = draw.textbbox((0,0),text1,font=bf)[2]
    b = draw.textbbox((0,0),text2,font=bf)[2]
    pad = int(20*scale)
    bw = a+b+pad*2
    bh = int(58*scale)
    x = (width-bw)//2
    draw.rounded_rectangle((x,y,x+bw,y+bh),radius=int(10*scale),fill=(3,6,10,238),outline=GREEN+(255,),width=max(3,int(4*scale)))
    ty = y + int(10*scale)
    draw.text((x+pad,ty),text1,font=bf,fill=WHITE+(255,),stroke_width=2,stroke_fill=BLACK+(255,))
    draw.text((x+pad+a,ty),text2,font=bf,fill=GREEN+(255,),stroke_width=2,stroke_fill=BLACK+(255,))
    return y+bh

def diagonal_panel(canvas, img, box, side="right"):
    x0,y0,x1,y1 = box
    panel = ImageOps.fit(img, (x1-x0,y1-y0), Image.Resampling.LANCZOS)
    mask = Image.new("L",(x1-x0,y1-y0),0)
    d = ImageDraw.Draw(mask)
    w,h = mask.size
    slant = min(100,w//4)
    if side == "right":
        d.polygon([(slant,0),(w,0),(w,h),(0,h)],fill=255)
    else:
        d.polygon([(0,0),(w-slant,0),(w,h),(0,h)],fill=255)
    canvas.paste(panel,(x0,y0),mask)

def master_cover(meta, variant=0):
    W,H = 1280,720
    title = clean_title(meta.get("title"))
    picked = pick_assets(title,3)
    if not picked:
        raise RuntimeError("sem mídia aprovada para capa Master")
    srcs = [materialize_asset(a,f"master_{variant}_{i}",0.28+0.18*i) for i,a in enumerate(picked)]
    bg = crop_enhance(srcs[0],(W,H),blur=15)
    bg = ImageEnhance.Brightness(bg).enhance(0.60)
    canvas = bg.convert("RGBA")

    hero = crop_enhance(srcs[0],(W,H),centering=(0.62 if variant==0 else 0.38,0.45))
    hero_mask = Image.new("L",(W,H),0)
    md = ImageDraw.Draw(hero_mask)
    md.polygon([(430,0),(W,0),(W,H),(300,H)],fill=235)
    hero_mask = hero_mask.filter(ImageFilter.GaussianBlur(2))
    canvas.paste(hero.convert("RGBA"),(0,0),hero_mask)

    if len(srcs) > 1:
        p2 = crop_enhance(srcs[1],(430,300))
        diagonal_panel(canvas,p2.convert("RGBA"),(820,30,1260,330),"right")
    if len(srcs) > 2:
        p3 = crop_enhance(srcs[2],(430,300))
        diagonal_panel(canvas,p3.convert("RGBA"),(760,375,1240,690),"left")

    shade = Image.new("RGBA",(W,H),(0,0,0,0))
    sd = ImageDraw.Draw(shade,"RGBA")
    for x in range(0,700,20):
        alpha = max(0,190-int(x/700*170))
        sd.rectangle((x,0,x+24,H),fill=(0,0,0,alpha))
    sd.rectangle((0,570,W,H),fill=(0,0,0,90))
    canvas = Image.alpha_composite(canvas,shade)

    ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov,"RGBA")
    draw_brand_badge(d,W,24,0.92)
    d.polygon([(38,126),(70,126),(48,360),(16,360)],fill=GREEN+(245,))
    d.line((34,672,720,672),fill=GREEN+(255,),width=8)

    lines, tf = wrap_words(d,title,700,92,48,3)
    y=250
    for i,line in enumerate(lines):
        fill = GREEN if i==len(lines)-1 else WHITE
        d.text((55,y+7),line,font=tf,fill=(0,0,0,220),stroke_width=9,stroke_fill=(0,0,0,230))
        d.text((48,y),line,font=tf,fill=fill+(255,),stroke_width=5,stroke_fill=BLACK+(255,))
        y += int(tf.size*1.03)

    sf=fnt(26)
    d.rounded_rectangle((48,596,670,648),radius=10,fill=(5,8,12,225),outline=GREEN+(230,),width=3)
    d.text((68,607),"NOTÍCIA • GAMEPLAY • CONTEXTO",font=sf,fill=WHITE+(245,))
    return Image.alpha_composite(canvas,ov).convert("RGB"), picked

def short_cover(meta, short_no, variant=0):
    W,H=1080,1920
    title=clean_title(meta.get("title"))
    idxs=short_scene_indices(short_no)
    picked=pick_assets(title,2,idxs)
    if not picked:
        raise RuntimeError(f"sem mídia aprovada para Short {short_no}")
    srcs=[materialize_asset(a,f"short{short_no}_{variant}_{i}",0.35+0.2*i) for i,a in enumerate(picked)]
    bg=crop_enhance(srcs[0],(W,H),centering=(0.5,0.38),blur=18)
    bg=ImageEnhance.Brightness(bg).enhance(0.56)
    canvas=bg.convert("RGBA")
    hero=crop_enhance(srcs[0],(W,1260),centering=(0.5,0.42))
    canvas.paste(hero.convert("RGBA"),(0,150))
    if len(srcs)>1:
        alt=crop_enhance(srcs[1],(W,620),centering=(0.5,0.45))
        mask=Image.new("L",(W,620),0); md=ImageDraw.Draw(mask)
        md.polygon([(0,180),(W,0),(W,620),(0,620)],fill=225)
        canvas.paste(alt.convert("RGBA"),(0,1050),mask)

    shade=Image.new("RGBA",(W,H),(0,0,0,0)); sd=ImageDraw.Draw(shade,"RGBA")
    sd.rectangle((0,0,W,160),fill=(3,7,12,225))
    for y in range(1050,H,20):
        alpha=min(220,60+int((y-1050)/(H-1050)*170))
        sd.rectangle((0,y,W,y+22),fill=(0,0,0,alpha))
    canvas=Image.alpha_composite(canvas,shade)

    ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov,"RGBA")
    draw_brand_badge(d,W,42,1.12)
    d.polygon([(55,1220),(80,1220),(50,1755),(25,1755)],fill=GREEN+(255,))
    lines,tf=wrap_words(d,title,900,112,60,4)
    y=1260
    for i,line in enumerate(lines):
        fill=GREEN if i==len(lines)-1 else WHITE
        d.text((98,y+8),line,font=tf,fill=(0,0,0,220),stroke_width=10,stroke_fill=(0,0,0,220))
        d.text((90,y),line,font=tf,fill=fill+(255,),stroke_width=6,stroke_fill=BLACK+(255,))
        y+=int(tf.size*1.04)
    d.line((90,1780,990,1780),fill=GREEN+(255,),width=9)
    bf=fnt(32)
    d.text((90,1810),"RADAR DOS GAMES • SHORTS",font=bf,fill=WHITE+(245,),stroke_width=2,stroke_fill=BLACK+(255,))
    return Image.alpha_composite(canvas,ov).convert("RGB"),picked

def save_checked(img,path,size):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    img.save(path,"JPEG",quality=95,subsampling=0,optimize=True,progressive=True)
    if not path.exists() or path.stat().st_size<30_000:
        raise RuntimeError(f"capa inválida/pequena: {path}")
    with Image.open(path) as check:
        if check.size!=size:
            raise RuntimeError(f"capa em resolução incorreta: {path} {check.size}")

def fallback():
    master=read_json(OUT/"master-youtube.json")
    title=master.get("title","RADAR DOS GAMES")
    subprocess.run(["python","src/thumbnail.py","output/master.mp4",title,"output/thumbnail.jpg"],check=True)
    for i in range(1,4):
        subprocess.run([
            "python","src/short_cover.py",
            f"output/shorts/short_{i}.mp4",
            f"output/short-{i}-youtube.json",
            f"output/shorts/short_{i}_cover.jpg",
            str(i)
        ],check=True)

def main():
    master=read_json(OUT/"master-youtube.json")
    shorts=[read_json(OUT/f"short-{i}-youtube.json") for i in range(1,4)]
    attempts=[]
    fallback_used=False
    selected_sources={}

    for variant in (0,1):
        try:
            img,src=master_cover(master,variant)
            save_checked(img,OUT/"thumbnail.jpg",(1280,720))
            selected_sources["master"]=[{"index":a.get("index"),"role":a.get("role"),"url":a.get("url")} for a in src]
            for i,meta in enumerate(shorts,1):
                img,src=short_cover(meta,i,variant)
                save_checked(img,OUT/f"shorts/short_{i}_cover.jpg",(1080,1920))
                selected_sources[f"short_{i}"]=[{"index":a.get("index"),"role":a.get("role"),"url":a.get("url")} for a in src]
            attempts.append({"variant":variant,"status":"APPROVED"})
            break
        except Exception as exc:
            attempts.append({"variant":variant,"status":"FAILED","error":str(exc)[:400]})
    else:
        fallback_used=True
        fallback()

    policy={
        "status":"APPROVED_WITH_FALLBACK" if fallback_used else "APPROVED_PREMIUM",
        "template_version":"radar-premium-auto-v1-2026-10-07",
        "policy":"official_exact_media_first; cinematic_montage; radar_brand_badge; huge_mobile_headline; neon_green_accents; master_plus_3_shorts; automatic_retry; legacy_fallback_only",
        "fallback_used":fallback_used,
        "attempts":attempts,
        "sources":selected_sources,
        "outputs":{
            "master":"output/thumbnail.jpg",
            "short_1":"output/shorts/short_1_cover.jpg",
            "short_2":"output/shorts/short_2_cover.jpg",
            "short_3":"output/shorts/short_3_cover.jpg"
        }
    }
    (OUT/"cover-suite-policy.json").write_text(json.dumps(policy,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(policy,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
