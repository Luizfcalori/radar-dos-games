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
from itertools import combinations
from pathlib import Path
from PIL import ImageFont

try:
    from cinematic import COLOR_FILTER, mix as cinematic_mix, write_credit
except ModuleNotFoundError:
    from src.cinematic import COLOR_FILTER, mix as cinematic_mix, write_credit

W=1080; H=1920; FPS=30
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
IMAGE_EXT={".jpg",".jpeg",".png",".webp"}

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
        if not buckets:return "0xFFFFFF"
        rec=max(buckets.values(),key=lambda x:x[3]); w=rec[3]
        r,g,b=[max(0,min(255,round(x/w))) for x in rec[:3]]
        return f"0x{r:02X}{g:02X}{b:02X}"
    except:return "0xFFFFFF"

SHORTS_LAYOUT_ID = "RADAR_SHORTS_CLASSIC_V1"

def title_layout(headline):
    """Pixel-accurate fail-closed short title layout, no cropped text."""
    words=" ".join(str(headline or "").upper().split()).split()
    if not words:
        raise RuntimeError("QUALITY_BLOCK: Shorts sem título")
    for fontsize in (52,50,48,46,44,42,40,38):
        font=ImageFont.truetype(FONT,fontsize)
        for count in (1,2,3):
            candidates=[]
            for cuts in combinations(range(1,len(words)),count-1):
                p=(0,)+cuts+(len(words),)
                lines=[" ".join(words[p[i]:p[i+1]]) for i in range(count)]
                widths=[font.getlength(line) for line in lines]
                if max(widths)>940:
                    continue
                # Balanced full hook: no ellipsis and no oversized headline.
                score=(max(widths)-min(widths))**2
                candidates.append((score,lines))
            if candidates:
                lines=min(candidates,key=lambda x:x[0])[1]
                assert " ".join(lines)==" ".join(words)
                return {"lines":lines,"fontsize":fontsize,"max_width":940}
    raise RuntimeError(f"QUALITY_BLOCK: título de Short não cabe no layout: {headline}")



def classic_short_filter(headline, accent):
    """Approved 02/10 layout, retained on every V4 beat (08/10 GTA6 reference)."""
    title=title_layout(headline)
    base_y=155 if len(title["lines"])<=2 else 141
    spacing=70 if len(title["lines"])<=2 else 66
    headline_filters=",".join(
        f"drawtext=fontfile='{FONT}':text='{esc(line)}':x=(w-text_w)/2:"
        f"y={base_y+i*spacing}:fontsize={title['fontsize']}:"
        "fontcolor=white:borderw=2:bordercolor=black@0.7:expansion=none"
        for i,line in enumerate(title["lines"])
    )
    # Keep the approved source image entirely visible inside the framed central panel.
    # Apply the cinematic grade BEFORE text and overlays so branding stays crisp.
    return (
        f"[0:v]fps={FPS},split=2[base][fg0];"
        f"[base]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        "boxblur=28:14,eq=brightness=-0.18:saturation=0.85[bg];"
        "[fg0]scale=900:600:force_original_aspect_ratio=decrease,setsar=1[fg];"
        "[bg]drawbox=x=0:y=0:w=1080:h=112:color=0x020A23@0.98:t=fill,"
        "drawbox=x=0:y=112:w=1080:h=285:color=black@0.96:t=fill,"
        "drawbox=x=25:y=470:w=1030:h=535:color=0x020A23@0.94:t=fill,"
        f"drawbox=x=96:y=525:w=888:h=430:color={accent}@0.96:t=8,"
        f"drawbox=x=110:y=539:w=860:h=402:color={accent}@0.42:t=3[canvas];"
        "[canvas][fg]overlay=x='(W-w)/2+5*sin(t*0.70)':"
        "y='575+(430-h)/2+4*cos(t*0.55)',"
        f"{COLOR_FILTER}[tmp];"
        f"[tmp]drawtext=fontfile='{FONT}':text='RADAR DOS GAMES':x=48:y=55:fontsize=32:"
        "fontcolor=white:borderw=2:bordercolor=black@0.7:expansion=none,"
        f"{headline_filters},"
        "drawbox=x=170:y=1040:w=740:h=64:color=black@0.86:t=fill,"
        f"drawtext=fontfile='{FONT}':text='CONFIRA O CONTEÚDO COMPLETO':"
        f"x=(w-text_w)/2:y=1053:fontsize=30:fontcolor={accent}:"
        "borderw=1:bordercolor=black@0.8:expansion=none,"
        "drawbox=x=250:y=1505:w=580:h=58:color=black@0.86:t=fill,"
        f"drawtext=fontfile='{FONT_REG}':text='VÍDEO COMPLETO NO CANAL':"
        "x=(w-text_w)/2:y=1517:fontsize=29:fontcolor=white:"
        "borderw=1:bordercolor=black@0.8:expansion=none,"
        "drawbox=x=245:y=1569:w=590:h=64:color=black@0.9:t=fill,"
        f"drawtext=fontfile='{FONT}':text='RADAR DOS GAMES':"
        "x=(w-text_w)/2:y=1580:fontsize=36:fontcolor=0xF4FF00:"
        "borderw=1:bordercolor=black@0.9:expansion=none,format=yuv420p[v]"
    )


def render_vertical_piece(asset, duration, dest, piece_no, headline="", keyword="", first=False, last=False, source_window=None):
    """Maintain the full classic layout throughout EVERY beat, no timed title/CTA."""
    path = Path(asset["path"])
    image_mode = is_image(asset)
    if image_mode:
        inp = ["-loop", "1", "-i", str(path)]
    else:
        seek = float(source_window["start"]) if source_window else seek_for(path, piece_no, duration)
        if source_window and seek+duration>float(source_window["end"])+0.01:
            raise RuntimeError("QUALITY_BLOCK: Short extrapolou janela visual aprovada")
        inp = ["-stream_loop", "-1"]
        if seek > 0:
            inp += ["-ss", f"{seek:.3f}"]
        inp += ["-i", str(path)]

    accent = accent_from_asset(path, image_mode, 0)
    # keyword, first and last remain accepted for pipeline compatibility. No
    # transient graphics may cover the approved permanent title, media or CTA.
    fc = classic_short_filter(headline, accent)
    sh(["ffmpeg", "-y", "-v", "error", *inp, "-t", f"{duration:.3f}", "-filter_complex", fc,
        "-map", "[v]", "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "20", "-pix_fmt", "yuv420p", str(dest)])
    return accent


def sfx_track(duration,events,dest):
    rate=48000; frames=max(1,int(math.ceil(duration*rate))); samples=[0.0]*frames
    for when,intensity in events:
        start=int(max(0,when)*rate); span=int(rate*.32); amp=.022+.004*min(4,intensity)
        for n in range(span):
            idx=start+n
            if idx>=frames:break
            t=n/rate; env=math.exp(-24*t); freq=55-15*(n/max(1,span))
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

def mix_audio(visuals,voice,sfx,dest):
    return cinematic_mix(visuals,voice,sfx,dest)

def main():
    manifest=load("output/render.json"); timings=load("output/voice-timings.json"); picks=load("output/short-picks.json")
    scenes=manifest.get("scenes") or []; assets={int(a["index"]):a for a in manifest.get("assets") or []}
    segments=timings.get("segments") or []; indexes=[int(x) for x in picks.get("scene_indexes") or []]
    expected_hooks=[" ".join(str(x or "").split()).strip() for x in (picks.get("expected_hooks") or [])]
    if len(indexes)!=3:raise RuntimeError("QUALITY_BLOCK: V4 precisa de 3 cenas de Short")
    if len(expected_hooks)!=3 or any(not x for x in expected_hooks):
        raise RuntimeError("QUALITY_BLOCK: V4 precisa de 3 hooks aprovados e não vazios")
    out=Path("output/shorts"); out.mkdir(parents=True,exist_ok=True)
    report=[]

    for short_no,scene_index in enumerate(indexes,1):
        scene=scenes[scene_index]; seg=segments[scene_index]; beats=scene.get("beats") or []
        hook=expected_hooks[short_no-1]
        if not beats:raise RuntimeError(f"QUALITY_BLOCK: Short {short_no} sem beats V4")
        tmp=out/f"v4_{short_no}"; tmp.mkdir(exist_ok=True)
        pieces=[]; events=[]; cursor=0.0; accents=[]
        for n,beat in enumerate(beats,1):
            idx=int(beat["media_index"]); asset=assets[idx]; d=float(beat["duration"])
            p=tmp/f"piece_{n:02d}.mp4"
            accents.append(render_vertical_piece(
                asset,d,p,n,headline=hook,
                keyword=beat.get("keyword_overlay",""),
                first=n==1,last=n==len(beats),
                source_window=beat.get("source_window"),
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
            "title":hook,
            "approved_hook":hook,
            "scene_title":scene.get("title"),
            "subtitle":scene.get("subtitle"),
            "beats":len(beats),"accent":accents[0] if accents else "0xFFFFFF",
            "music_bed":music_policy,
            "layout_profile":SHORTS_LAYOUT_ID,
            "title_layout":title_layout(hook),
        })

    payload={
        "standard":"radar-dos-games-shorts-premium-v4-director-cut",
        "premium_version":"PREMIUM_V4_DIRECTOR_CUT",
        "cinematic_profile":"RADAR_CINEMATIC_V1",
        "layout_profile":SHORTS_LAYOUT_ID,
        "color_filter":COLOR_FILTER,
        "source_policy":"independent_rebuild_from_approved_assets",
        "resolution":[W,H],"fps":FPS,
        "hook_policy":"exact_approved_hook_persistent_all_beats; semantic_scene_match; phrase_level_visuals; classic_fixed_layout",
        "expected_hooks":expected_hooks,
        "sound_design":"compression+loudnorm+limiter+subtle_editorial_sfx",
        "shorts":report,
    }
    (out/"manifest.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False))

if __name__=="__main__":
    main()
