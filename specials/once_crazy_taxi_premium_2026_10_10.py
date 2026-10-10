#!/usr/bin/env python3
"""Isolated Crazy Taxi editorial trial: reskin three already-QA'd informative
Shorts into approved RADAR_PREMIUM_CONVERSAO_V1 layout; do not edit production."""
import json
import subprocess
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path("crazy-taxi-premium-review")
ROOT.mkdir(exist_ok=True)
BASE=Path("output/shorts")
W,H=1080,1920
GREEN=(151,255,37)
WHITE=(245,248,253)
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BRIEF=Path("production/once-crazy-taxi-bgs-2026-10-10.json")
HOOKS=json.loads(BRIEF.read_text(encoding="utf-8"))["short_hooks"]
LABELS=[
    "MAPA BRASILEIRO • BGS 2026",
    "LOJAS REAIS NO NOVO MAPA",
    "ARCADE • CAMPANHA • MULTIPLAYER",
]

def cmd(*args):
    subprocess.run([str(a) for a in args],check=True,timeout=1800)

def probe(path):
    return json.loads(subprocess.check_output(
      ["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],
      text=True))

def font(size, regular=False):
    return ImageFont.truetype(REG if regular else FONT,size)

def centered(d,text,y,size,color=WHITE,regular=False):
    f=font(size,regular)
    x=(W-d.textbbox((0,0),text,font=f)[2])/2
    d.text((x,y),text,font=f,fill=color,stroke_width=1,stroke_fill=(0,0,0))

def fit_lines(d,title,y,maxwidth=944,maxlines=3):
    words=title.upper().split()
    for size in range(57,35,-2):
        f=font(size);lines=[];current=""
        for word in words:
            nxt=(current+" "+word).strip()
            if d.textbbox((0,0,nxt),font=f)[2] <= maxwidth:
                current=nxt
            else:
                if current:lines.append(current)
                current=word
        if current:lines.append(current)
        if len(lines)<=maxlines:
            for j,line in enumerate(lines):
                centered(d,line,y+j*(size+16),size,GREEN if j==len(lines)-1 else WHITE)
            return
    raise RuntimeError("QUALITY_BLOCK headline overflow: "+title)

def background():
    im=Image.new("RGB",(W,H),(5,18,31))
    d=ImageDraw.Draw(im)
    for y in range(H):
        v=y/H
        d.line((0,y,W,y),fill=(3,int(14+15*(1-v)),int(35+19*v)))
    for y in range(430,1430,95):
        d.line((0,y,W,y),fill=(17,65,57),width=2)
    for i in range(-6,12):
        d.line((i*145,440,(i+7)*145,1430),fill=(18,47,53),width=2)
    return im

def overlay(i):
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,124),fill=(3,10,28,253))
    d.line((0,124,W,124),fill=GREEN,width=4)
    d.rounded_rectangle((42,33,205,94),radius=13,fill=GREEN)
    d.text((64,44),"RDG",font=font(34),fill=(6,16,24))
    d.text((224,41),"RADAR",font=font(44),fill=WHITE)
    d.text((418,41),"DOS GAMES",font=font(44),fill=GREEN)
    d.rectangle((0,125,W,410),fill=(0,0,0,231))
    fit_lines(d,HOOKS[i],155)
    d.rounded_rectangle((69,587,1011,1141),radius=21,fill=None,outline=GREEN,width=7)
    d.rounded_rectangle((118,1198,962,1272),radius=16,fill=(5,12,26,242),outline=GREEN,width=3)
    centered(d,LABELS[i],1218,30,GREEN)
    d.rounded_rectangle((79,1445,1001,1560),radius=28,fill=GREEN)
    centered(d,"INSCREVA-SE AGORA",1468,51,(5,17,21))
    centered(d,"DEIXE O LIKE",1600,36,WHITE)
    d.rectangle((0,1743,W,H),fill=(3,9,22,253))
    centered(d,"RADAR DOS GAMES",1770,44,GREEN)
    centered(d,"GAMES  •  NOTÍCIAS  •  GAMEPLAY",1840,25,(183,200,213),regular=True)
    return im

def make_one(i,background_path):
    src=BASE/f"short_{i+1}.mp4"
    if not src.exists() or src.stat().st_size<200000:
        raise RuntimeError(f"QUALITY_BLOCK source Short {i+1} missing")
    info=probe(src); duration=float(info["format"]["duration"])
    a=[s for s in info["streams"] if s["codec_type"]=="audio"]
    v=[s for s in info["streams"] if s["codec_type"]=="video"]
    if not a or not v or (int(v[0]["width"]),int(v[0]["height"]))!=(1080,1920):
        raise RuntimeError(f"QUALITY_BLOCK invalid original Short {i+1}")
    ov=ROOT/f"overlay-{i+1}.png"; overlay(i).save(ov)
    out=ROOT/f"crazy-taxi-short-{i+1}-premium.mp4"
    filt=(
      "[0:v]crop=860:402:110:539,"
      "scale=900:506:force_original_aspect_ratio=decrease,"
      "pad=900:506:(ow-iw)/2:(oh-ih)/2:color=0x081420,"
      "fps=30,eq=contrast=1.025:saturation=0.94[fg];"
      "[1:v]format=rgba[base];"
      "[base][fg]overlay=x=90:y=612:shortest=1[mid];"
      "[2:v]format=rgba[ov];[mid][ov]overlay=0:0:shortest=1,"
      "format=yuv420p[out]"
    )
    cmd("ffmpeg","-y","-v","error","-i",src,
      "-loop","1","-i",background_path,"-loop","1","-i",ov,
      "-filter_complex",filt,"-map","[out]","-map","0:a:0",
      "-t",f"{duration:.3f}","-r","30",
      "-c:v","libx264","-preset","veryfast","-crf","21",
      "-pix_fmt","yuv420p","-c:a","copy","-movflags","+faststart",out)
    pr=probe(out); vs=[s for s in pr["streams"] if s["codec_type"]=="video"]
    aud=[s for s in pr["streams"] if s["codec_type"]=="audio"]
    if not vs or not aud or (int(vs[0]["width"]),int(vs[0]["height"]))!=(W,H) or vs[0]["r_frame_rate"]!="30/1":
        raise RuntimeError("QUALITY_BLOCK premium output invalid")
    if abs(float(pr["format"]["duration"])-duration)>0.18:
        raise RuntimeError("QUALITY_BLOCK output duration mismatch")
    frame=ROOT/f"short-{i+1}-frame.jpg"
    cmd("ffmpeg","-y","-v","error","-ss",f"{min(4.,duration/2):.2f}",
      "-i",out,"-frames:v","1","-q:v","3",frame)
    return {"short":i+1,"video":str(out),"frame":str(frame),
      "duration_s":round(duration,3),"headline":HOOKS[i],
      "layout":"RADAR_PREMIUM_CONVERSAO_V1",
      "cta":["INSCREVA-SE AGORA","DEIXE O LIKE","RADAR DOS GAMES"]}

def main():
    master=Path("output/master.mp4")
    if not master.exists() or master.stat().st_size<3000000:
        raise RuntimeError("QUALITY_BLOCK master missing")
    bg=ROOT/"background.png";background().save(bg)
    shorts=[make_one(i,bg) for i in range(3)]
    report={"topic":"Crazy Taxi: World Tour — Brasil BGS 2026",
        "master":str(master),"shorts":shorts,
        "platform_neutral":True,"published":False,
        "pipeline_modified":False,"basis":"Three classic QA-approved Shorts, visually reformatted for test",
        "voice":"Thalita Multilingual PT-BR (source soundtrack preserved)",
        "note":"The new promotional layout is used only for this standalone requested trial."}
    (ROOT/"production-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PREMIUM_REVIEW_READY",json.dumps(report,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
