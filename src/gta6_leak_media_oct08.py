#!/usr/bin/env python3
"""Acquire GTA VI-only time-bounded excerpts from Rockstar's official MP4.

One-off 2026-10-08 analysis only. All scenes have distinct assets with labeled
source timestamps; footage is the August 27 extended look, NOT today's leak.
Downloads narrow HTTP ranges; never downloads or stores the 14 GB entire video.
If source access fails, fail closed instead of replacing it with another game.
"""
import json
import subprocess
from pathlib import Path

SRC="https://media-rockstargames-com.akamaized.net/VI/downloads/videos/GTAVI_An_Extended_Look/GTAVI_An_Extended_Look.mp4"
REF="https://www.rockstargames.com/VI/media/videos"
HEADERS="User-Agent: Mozilla/5.0 AppleWebKit/537.36 Chrome/129 Safari/537.36\r\nReferer: https://www.rockstargames.com/\r\nOrigin: https://www.rockstargames.com\r\n"
OUT=Path("output/media")
W,H=960,540
VF=f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,fps=30,format=yuv420p"

def clip(source,start,duration,path):
    commands=[
        ["ffmpeg","-hide_banner","-y","-nostdin","-loglevel","error",
         "-headers",HEADERS,"-ss",str(start),"-i",source,"-t",str(duration),
         "-map","0:v:0","-an","-vf",VF,
         "-c:v","libx264","-preset","veryfast","-crf","24","-movflags","+faststart",str(path)],
        ["ffmpeg","-hide_banner","-y","-nostdin","-loglevel","error",
         "-headers",HEADERS,"-i",source,"-ss",str(start),"-t",str(duration),
         "-map","0:v:0","-an","-vf",VF,
         "-c:v","libx264","-preset","veryfast","-crf","24","-movflags","+faststart",str(path)]
    ]
    for idx,cmd in enumerate(commands):
        try:
            subprocess.run(cmd,check=True,timeout=125 if idx==0 else 180)
            q=subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
                            "-of","csv=p=0",str(path)],text=True,timeout=20).strip()
            if float(q)>=20:return float(q)
        except Exception as e:
            print(f"official CDN extract failure {start}s route {idx}: {str(e)[:250]}",flush=True)
        path.unlink(missing_ok=True)
    raise RuntimeError(f"QUALITY_BLOCK: clipe Rockstar oficial inacessível em {start}s")

def main():
    b=json.loads(Path("production/gta6-cyberleek-2026-10-08.json").read_text(encoding="utf-8"))
    plan_path=Path("output/auto-media-plan.json")
    plan=json.loads(plan_path.read_text(encoding="utf-8"))
    scenes=plan["scenes"]
    if len(scenes)!=len(b["scene_seeks"]) or len(scenes)!=16:
        raise RuntimeError("QUALITY_BLOCK: cena/timecode ausente")
    OUT.mkdir(parents=True,exist_ok=True)
    assets=[]
    for n,start in enumerate(b["scene_seeks"],1):
        if not 0<=float(start)<1560:raise RuntimeError(f"QUALITY_BLOCK: tempo fora do original {start}")
        dest=OUT/f"rockstar_gta6_scene_{n:02d}.mp4"
        try:
            dur=clip(SRC,round(float(start),2),32,dest)
        except Exception:
            # No generic media fallback. Preserve only approved original footage.
            raise
        role=f"gta6_rockstar_scene_{n:02d}"
        item={
            "index":n,"path":str(dest),"type":"video","role":role,
            "url":SRC,"source":REF,
            "source_seek_original":start,
            "source_label":f"GTA VI Extended Look 2026-08-27 {start}s",
            "relevance_evidence":"Rockstar_first_party_official_game_inengine_footage",
            "approved":True,"duration":dur,"width":W,"height":H
        }
        assets.append(item)
        scenes[n-1]["allowed_roles"]=[role]
        scenes[n-1]["media_indices"]=[n]
        print(f"OFFICIAL GTA VI CLIP {n:02d} SOURCE AT {start}s DURATION {dur:.1f}s",flush=True)
    plan["media"]=[]
    plan["minimum_assets"]=len(assets)
    plan["minimum_video_assets"]=len(assets)
    plan["minimum_unique_video_seconds"]=250
    plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf-8")
    seconds=sum(a["duration"] for a in assets)
    if seconds<250:raise RuntimeError("QUALITY_BLOCK: pouco movimento GTA VI")
    clips={
        "assets":assets,"clips":[a["path"] for a in assets],"errors":[],
        "publishable_media":True,"generic_fallback":False,"official_assets":True,
        "minimum_assets":len(assets),"video_assets":len(assets),"image_assets":0,
        "unique_video_seconds":round(seconds,2),"minimum_video_assets":len(assets),
        "minimum_unique_video_seconds":250,"minimum_image_assets":0,
        "semantic_policy":"first_party_exact_gta_vi_extended_look_2026-08-27; timecoded_clips; no_other_game; no_leak_nudity"
    }
    Path("output/clips.json").write_text(json.dumps(clips,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":"APPROVED_SOURCE","gta6_clips":len(assets),"seconds":round(seconds,2),"original_url":SRC},ensure_ascii=False))

if __name__=="__main__":main()
