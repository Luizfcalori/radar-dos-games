#!/usr/bin/env python3
"""QA visual por amostragem de frames do Master Premium V4."""
import json
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageStat

OUT=Path("output/frame-qa")
OUT.mkdir(parents=True,exist_ok=True)

def duration(path):
    return float(subprocess.check_output([
        "ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(path)
    ],text=True).strip())

def sample(path,t,dest):
    # Some MP4s with concat/copy timestamps can return exit code 0 without
    # writing a frame when seeking before input. Retry with accurate input seek.
    attempts = [
        ["ffmpeg","-y","-v","error","-ss",f"{t:.3f}","-i",str(path),
         "-frames:v","1","-q:v","3",str(dest)],
        ["ffmpeg","-y","-v","error","-i",str(path),"-ss",f"{t:.3f}",
         "-frames:v","1","-q:v","3",str(dest)],
    ]
    errors = []
    for cmd in attempts:
        dest.unlink(missing_ok=True)
        proc = subprocess.run(cmd, text=True, capture_output=True)
        if proc.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
            try:
                with Image.open(dest) as im:
                    im.verify()
                return
            except Exception as exc:
                errors.append(f"invalid image: {exc}")
        else:
            errors.append((proc.stderr or f"no frame produced (exit {proc.returncode})").strip())
    raise RuntimeError(f"FRAME_SAMPLE_FAILED at {t:.3f}s for {path}: {'; '.join(errors)}")

def metrics(path):
    with Image.open(path).convert("RGB") as im:
        thumb=im.resize((160,90))
        stat=ImageStat.Stat(thumb)
        mean=sum(stat.mean)/3
        rms=sum(stat.rms)/3
        # Percentual quase preto.
        px=list(thumb.getdata())
        dark=sum(1 for r,g,b in px if max(r,g,b)<18)/len(px)
        # Contraste simples por desvio médio dos canais.
        std=sum(math.sqrt(max(0,v)) for v in stat.var)/3
        return {"mean":round(mean,2),"rms":round(rms,2),"std":round(std,2),"dark_ratio":round(dark,4)}

def main():
    master=Path("output/master.mp4")
    if not master.exists():raise RuntimeError("QUALITY_BLOCK: master ausente para frame QA")
    d=duration(master)
    count=10 if d>=80 else 8
    times=[max(.25,d*(i+.5)/count) for i in range(count)]
    rows=[];bad=[]
    for i,t in enumerate(times,1):
        p=OUT/f"frame_{i:02d}.jpg"; sample(master,t,p); m=metrics(p)
        status="APPROVED"
        if m["dark_ratio"]>.90 or m["mean"]<12 or m["std"]<7:
            status="REVIEW"; bad.append(i)
        rows.append({"index":i,"time":round(t,3),"path":str(p),**m,"status":status})
    # Um frame de transição muito escuro é tolerado; padrão repetido não.
    status="APPROVED" if len(bad)<=1 else "BLOCKED"
    result={
        "status":status,
        "policy":"multi_point_frame_sampling; blank_or_near_black_detection; low_detail_detection",
        "sample_count":len(rows),"flagged_frames":bad,"frames":rows,
    }
    Path("output/visual-frame-qa.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if status!="APPROVED":raise RuntimeError(f"QUALITY_BLOCK: frame QA reprovou frames {bad}")

if __name__=="__main__":main()
