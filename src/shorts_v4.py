#!/usr/bin/env python3
"""Gera 3 Shorts Premium V4 como peças independentes, não como crop do Master."""
import colorsys
import json
import math
import struct
import subprocess
import sys
import textwrap
import wave
from pathlib import Path

W=1080; H=1920; FPS=30
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
IMAGE_EXT={".jpg",".jpeg",".png",".webp"}
VOICE_CHAIN="acompressor=threshold=-20dB:ratio=2.4:attack=12:release=140,loudnorm=I=-16:LRA=6:TP=-1.2,alimiter=limit=0.92"

def sh(cmd):
    print("+"," ".join(map(str,cmd)),flush=True); subprocess.run(cmd,check=True)

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def esc(text):
    return str(text).replace("\\","\\\\").replace(":","\\:").replace("'","\\'").replace("%","\\%").replace("\n","\\n")

def wrapped(text,width=24,max_lines=2):
    clean=" ".join(str(text or "").upper().split())
    lines=textwrap.wrap(clean,width=width,break_long_words=False,break_on_hyphens=False)
    if len(lines)>max_lines:
        lines=lines[:max_lines]
        lines[-1]=textwrap.shorten(lines[-1],width=width,placeholder="…")
    return "\n".join(lines)

def probe_duration(path):
    return float(subprocess.check_output([
        "ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(path)
    ],text=True).strip())

def is_image(asset):
    return asset.get("type")=="image" or Path(asset["path"]).suffix.lower() in IMAGE_EXT

def seek_for(path,n,duration):
    try:total=probe_duration(path)
    except:return 0.0
    room=total-duration-.25
    if room<=.1:return 0.0
    return round((n*4.77)%room,3)

def accent_from_asset(path,image_mode,seek=0):
    try:
        cmd=["ffmpeg","-v","error"]
        if not image_mode and seek>0:cmd += ["-ss",f"{seek:.3f}"]
        cmd += ["-i",str(path),"-frames:v","1","-vf","scale=48:48","-f","rawvideo","-pix_fmt","rgb24","pipe:1"]
        raw=subprocess.check_output(cmd)
        buckets={}
        for i in range(0,len(raw)-2,3):
            r,g,b=raw[i],raw[i+1],raw[i+2]
            h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
            if s<.34 or v<.3:continue
            key=int(h*12)%12; rec=buckets.setdefault(key,[0,0,0,0])
            weight=s*(.5+v); rec[0]+=r*weight; rec[1]+=g*weight; rec[2]+=b*weight; rec[3]+=weight
        if not buckets:return "0x00DCC8"
        rec=max(buckets.values(),key=lambda x:x[3]); w=rec[3]
        r,g,b=[max(0,min(255,round(x/w))) for x in rec[:3]]
        return f"0x{r:02X}{g:02X}{b:02X}"
    except:return "0x00DCC8"

def render_vertical_piece(asset,duration,dest,piece_no,headline="",keyword="",first=False,last=False):
    path=Path(asset["path"]); image_mode=is_image(asset)
    if image_mode: inp=["-loop","1","-i",str(path)]
    else:
        seek=seek_for(path,piece_no,duration); inp=["-stream_loop","-1"]
        if seek>0:inp += ["-ss",f"{seek:.3f}"]
        inp += ["-i",str(path)]
    accent=accent_from_asset(path,image_mode,0)
    fg_scale="940:1040"
    base=(
        f"[0:v]fps={FPS},split=2[bg0][fg0];"
        f"[bg0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:15,"
        "eq=brightness=-0.20:saturation=0.86[bg];"
        f"[fg0]scale={fg_scale}:force_original_aspect_ratio=decrease,setsar=1[fg];"
        f"[bg]drawbox=x=0:y=0:w={W}:h=118:color=0x020A23@0.96:t=fill[canvas];"
        f"[canvas][fg]overlay=x='(W-w)/2+5*sin(t*.65)':y='510+(1040-h)/2+4*cos(t*.47)'[tmp];"
    )
    filters=[
        f"drawtext=fontfile='{FONT}':text='RADAR DOS GAMES':x=42:y=54:fontsize=32:fontcolor=white:"
        "borderw=2:bordercolor=black@0.7:expansion=none",
        f"drawbox=x=72:y=440:w=936:h=1120:color={accent}@0.22:t=3",
    ]
    if first:
        h=esc(wrapped(headline,23,2))
        filters += [
            "drawbox=x=56:y=150:w=968:h=270:color=black@0.86:t=fill:enable='between(t,0,3.0)'",
            f"drawtext=fontfile='{FONT}':text='{h}':x=(w-text_w)/2:y=205:fontsize=55:fontcolor=white:"
            "borderw=2:bordercolor=black@0.8:line_spacing=12:expansion=none:enable='between(t,0,3.0)'",
        ]
    if keyword:
        k=esc(keyword[:22])
        filters += [
            "drawbox=x=190:y=1575:w=700:h=72:color=black@0.80:t=fill:enable='between(t,0.15,1.65)'",
            f"drawtext=fontfile='{FONT}':text='{k}':x=(w-text_w)/2:y=1590:fontsize=36:fontcolor=0xF4FF00:"
            "borderw=2:bordercolor=black@0.8:expansion=none:enable='between(t,0.15,1.65)'",
        ]
    if last:
        start=max(0.0,duration-2.2)
        filters += [
            f"drawbox=x=165:y=1685:w=750:h=96:color=black@0.86:t=fill:enable='gte(t,{start:.3f})'",
            f"drawtext=fontfile='{FONT_REG}':text='VÍDEO COMPLETO NO RADAR DOS GAMES':x=(w-text_w)/2:y=1715:"
            f"fontsize=28:fontcolor=white:borderw=1:bordercolor=black@0.8:expansion=none:enable='gte(t,{start:.3f})'",
        ]
    fc=base+",".join(filters)+",format=yuv420p[v]"
    sh(["ffmpeg","-y","-v","error",*inp,"-t",f"{duration:.3f}","-filter_complex",fc,
        "-map","[v]","-an","-r",str(FPS),"-c:v","libx264","-preset","veryfast","-crf","20",
        "-pix_fmt","yuv420p",str(dest)])
    return accent

def sfx_track(duration,events,dest):
    rate=48000; frames=max(1,int(math.ceil(duration*rate))); samples=[0.0]*frames
    for when,intensity in events:
        start=int(max(0,when)*rate); span=int(rate*.12); amp=.022+.004*min(4,intensity)
        for n in range(span):
            idx=start+n
            if idx>=frames:break
            t=n/rate; env=math.exp(-24*t); freq=720-300*(n/max(1,span))
            samples[idx]+=amp*env*math.sin(2*math.pi*freq*t)
    with wave.open(str(dest),"wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        data=bytearray()
        for x in samples:data += struct.pack("<h",int(max(-1,min(1,x))*32767))
        wf.writeframes(bytes(data))

def concat_visuals(paths,dest,tmp):
    listing=tmp/"visuals.txt"
    listing.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in paths),encoding="utf-8")
    sh(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(listing),"-c","copy",str(dest)])

def approved_music_bed():
    for p in (Path("assets/audio/radar-bed.mp3"),Path("assets/audio/radar-bed.wav"),Path("assets/audio/radar-bed.m4a")):
        if p.exists() and p.stat().st_size>20000:return p
    return None

def mix_audio(visuals,voice,sfx,dest):
    bed=approved_music_bed()
    if bed:
        sh(["ffmpeg","-y","-v","error","-i",str(visuals),"-i",str(voice),"-i",str(sfx),"-stream_loop","-1","-i",str(bed),
            "-filter_complex",f"[1:a]{VOICE_CHAIN},asplit=2[vmain][vsc];[2:a]volume=.68[s];[3:a]volume=.10[bed];"
            "[bed][vsc]sidechaincompress=threshold=.015:ratio=12:attack=18:release=240[ducked];"
            "[vmain][ducked][s]amix=inputs=3:weights='1 .55 .45':normalize=0,alimiter=limit=.92[a]",
            "-map","0:v:0","-map","[a]","-shortest","-c:v","copy","-c:a","aac","-b:a","160k","-ar","48000","-ac","2",
            "-movflags","+faststart",str(dest)])
        return "approved_bed_with_voice_ducking"
    sh(["ffmpeg","-y","-v","error","-i",str(visuals),"-i",str(voice),"-i",str(sfx),
        "-filter_complex",f"[1:a]{VOICE_CHAIN}[v];[2:a]volume=.68[s];[v][s]amix=inputs=2:weights='1 .5':normalize=0,alimiter=limit=.92[a]",
        "-map","0:v:0","-map","[a]","-shortest","-c:v","copy","-c:a","aac","-b:a","160k","-ar","48000","-ac","2",
        "-movflags","+faststart",str(dest)])
    return "ducking_ready_no_approved_bed"

def main():
    manifest=load("output/render.json"); timings=load("output/voice-timings.json"); picks=load("output/short-picks.json")
    scenes=manifest.get("scenes") or []; assets={int(a["index"]):a for a in manifest.get("assets") or []}
    segments=timings.get("segments") or []; indexes=[int(x) for x in picks.get("scene_indexes") or []]
    if len(indexes)!=3:raise RuntimeError("QUALITY_BLOCK: V4 precisa de 3 cenas de Short")
    out=Path("output/shorts"); out.mkdir(parents=True,exist_ok=True)
    report=[]

    for short_no,scene_index in enumerate(indexes,1):
        scene=scenes[scene_index]; seg=segments[scene_index]; beats=scene.get("beats") or []
        if not beats:raise RuntimeError(f"QUALITY_BLOCK: Short {short_no} sem beats V4")
        tmp=out/f"v4_{short_no}"; tmp.mkdir(exist_ok=True)
        pieces=[]; events=[]; cursor=0.0; accents=[]
        for n,beat in enumerate(beats,1):
            idx=int(beat["media_index"]); asset=assets[idx]; d=float(beat["duration"])
            p=tmp/f"piece_{n:02d}.mp4"
            accents.append(render_vertical_piece(
                asset,d,p,n,headline=scene.get("title",""),
                keyword=beat.get("keyword_overlay",""),
                first=n==1,last=n==len(beats),
            ))
            pieces.append(p)
            if n>1 or int(beat.get("intensity",0))>=2:events.append((cursor,max(1,int(beat.get("intensity",1)))))
            cursor+=d

        visuals=tmp/"visuals.mp4"; concat_visuals(pieces,visuals,tmp)
        sfx=tmp/"sfx.wav"; sfx_track(cursor,events,sfx)
        voice=Path(seg["file"])
        if not voice.exists():raise RuntimeError(f"QUALITY_BLOCK: áudio da cena {scene_index+1} ausente")
        dest=out/f"short_{short_no}.mp4"; music_policy=mix_audio(visuals,voice,sfx,dest)
        report.append({
            "index":short_no,"path":str(dest),"scene_index":scene_index,
            "duration":round(probe_duration(dest),3),
            "boundary_policy":"independent_scene_voice_complete",
            "render_policy":"rebuilt_from_source_assets_not_master_crop",
            "title":scene.get("title"),"subtitle":scene.get("subtitle"),
            "beats":len(beats),"accent":accents[0] if accents else "0x00DCC8",
            "music_bed":music_policy,
        })

    payload={
        "standard":"radar-dos-games-shorts-premium-v4-director-cut",
        "premium_version":"PREMIUM_V4_DIRECTOR_CUT",
        "source_policy":"independent_rebuild_from_approved_assets",
        "resolution":[W,H],"fps":FPS,
        "hook_policy":"headline_first_frame; phrase_level_visuals; selective_keywords",
        "sound_design":"compression+loudnorm+limiter+subtle_editorial_sfx",
        "shorts":report,
    }
    (out/"manifest.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False))

if __name__=="__main__":
    main()
