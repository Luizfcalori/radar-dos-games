#!/usr/bin/env python3
"""Explore publicly mirrored GTA VI Oct 8 leak for SFW editorial clips.

One-off diagnostic. Never publishes, never outputs the original 25 min recording
as deliverable. Prevent unverified/nude segments from being fed into production.
"""
import json,subprocess,sys,urllib.request,time
from pathlib import Path

OUT=Path("output/gta6-thirdparty-probe")
OUT.mkdir(parents=True,exist_ok=True)
MIRRORS=[
 "https://b.imgur.gg/JmuFZ5b-video.mp4",
 "https://x.com/saintyvesxx/status/2108179313157644742",
 "https://x.com/CYBERLEEK_off/status/2108155110534840618"
]
MAX_FILE=450*1024*1024

def info(path):
 p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration,size:stream=codec_name,width,height",
 "-of","json",str(path)],capture_output=True,text=True,timeout=25)
 if p.returncode:return None
 try:return json.loads(p.stdout)
 except:return None

def get_one(url,target):
 target.unlink(missing_ok=True)
 if "x.com" in url:
  p=subprocess.run(["yt-dlp","--no-playlist","--socket-timeout","18","--retries","1",
       "--max-filesize","450M","-f","best[height<=720]/best","--merge-output-format","mp4",
       "--output",str(target),url],capture_output=True,text=True,timeout=145)
  if p.returncode: print("YT_DLP_FAILED",url,p.stderr[-500:],flush=True)
  files=list(OUT.glob(target.stem+"*"))
  for f in files:
   if f.is_file() and f.stat().st_size>100000:
    if f!=target:f.rename(target)
    break
 else:
  try:
   request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 Chrome/129.0","Referer":"https://www.reddit.com/"})
   with urllib.request.urlopen(request,timeout=25) as conn,target.open("wb") as f:
    length=conn.headers.get("Content-Length")
    if length and int(length)>MAX_FILE:raise RuntimeError("too large")
    while True:
     block=conn.read(1048576)
     if not block:break
     f.write(block)
     if f.tell()>MAX_FILE:raise RuntimeError("max bytes")
  except Exception as e:
   print("DIRECT_DOWNLOAD_FAILED",url,type(e).__name__,str(e)[:400],flush=True)
   target.unlink(missing_ok=True)
   return None
 if target.exists() and target.stat().st_size>100000:
  return info(target)
 return None

def frame(path,at,index):
 dest=OUT/f"sample_{index:02d}.jpg"
 try:
  p=subprocess.run(["ffmpeg","-y","-v","error","-ss",str(at),"-i",str(path),
        "-frames:v","1","-vf","scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2:color=black",
        str(dest)],timeout=35,check=True)
  return str(dest)
 except Exception as e:print("FRAME_FAILED",at,str(e)[:200],flush=True);return None

def main():
 report={"status":"NO_SAFE_MEDIA_VERIFIED","candidates":[],"provenance":"unconfirmed third-party mirroring of Oct 8 2026 gameplay","stage":"diagnostic_only"}
 chosen=None
 for n,url in enumerate(MIRRORS):
  p=OUT/("source_%d.mp4"%n)
  try:res=get_one(url,p)
  except Exception as e:res=None;print("SOURCE_ERROR",str(e)[:300],flush=True)
  if res:
   dur=float(res.get("format",{}).get("duration") or 0)
   report["candidates"].append({"url":url,"duration":dur,"bytes":p.stat().st_size,
      "status":"FETCHED_UNREVIEWED","file":str(p)})
   if dur>=150:
    chosen=(url,p,dur)
    break
  report["candidates"].append({"url":url,"status":"UNAVAILABLE"})
 if chosen:
  url,p,dur=chosen
  # Sample opening and race only. Review manually before using any excerpts.
  times=[6,25,45,65,85,105,125,145,165,185,205,225]
  samples=[{"timestamp":t,"frame":frame(p,t,i)} for i,t in enumerate(times) if t<dur-1]
  report.update({"status":"FOOTAGE_FETCHED_REQUIRES_VISUAL_SAFETY_REVIEW","source":url,
     "duration":dur,"safe_verified":False,"preview_frames":samples,
     "allowed_for_render":False,
     "review_instruction":"Visual inspection must exclude all explicit nudity. Never enable rendering on source download alone."})
  # Keep only compact frames in artifact, not the entire copyrighted leaked video.
  p.unlink(missing_ok=True)
 (OUT/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
 print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":main()
