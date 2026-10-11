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
    # Concat MP4s can contain small timestamp gaps at cuts. If the exact
    # checkpoint has no decodable frame, try nearby frames rather than failing QA.
    attempts = [
        ["ffmpeg","-y","-v","error","-ss","{time}","-i",str(path),
         "-frames:v","1","-q:v","3",str(dest)],
        ["ffmpeg","-y","-v","error","-i",str(path),"-ss","{time}",
         "-frames:v","1","-q:v","3",str(dest)],
    ]
    errors = []
    total = duration(path)
    for offset in (0.0, -0.35, 0.35, -0.75, 0.75):
        ts = min(max(0.05, t + offset), max(0.05, total - 0.75))
        for template in attempts:
            cmd = [f"{ts:.3f}" if x == "{time}" else x for x in template]
            dest.unlink(missing_ok=True)
            proc = subprocess.run(cmd, text=True, capture_output=True)
            if proc.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
                try:
                    with Image.open(dest) as im:
                        im.verify()
                    return
                except Exception as exc:
                    errors.append(f"invalid image near {ts:.3f}s: {exc}")
            else:
                errors.append((proc.stderr or f"no frame produced near {ts:.3f}s (exit {proc.returncode})").strip())
    raise RuntimeError(f"FRAME_SAMPLE_FAILED at {t:.3f}s for {path}: {'; '.join(errors[-4:])}")

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
    # Never sample the exact final timestamp: MP4 duration is an exclusive boundary,\n    # and ffmpeg may return exit 0 without decoding a frame there. Keep every\n    # sample at least 0.75s before EOF while preserving evenly spaced checkpoints.\n    safe_end=max(0.25,d-0.75)\n    times=[min(safe_end,max(.25,d*(i+.5)/count)) for i in range(count)]
    # Rebuild checkpoints immediately before iteration; avoid an undefined local if earlier sampling setup changes.
    checkpoints = [min(safe_end, max(0.25, d * (i + 0.5) / count)) for i in range(count)]
    rows=[];bad=[]
    for i,t in enumerate(checkpoints,1):
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
