#!/usr/bin/env python3
"""Renderizador Radar dos Games Premium V4 — Director Cut."""
import json
import math
import struct
import subprocess
import sys
import wave
from pathlib import Path

FPS=30; W=1920; H=1080
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
IMAGE_EXTENSIONS={".jpg",".jpeg",".png",".webp"}
WATERMARK_X="w-tw-44"; WATERMARK_Y=30; WATERMARK_SIZE=23
CARD_X=62; CARD_Y=850; CARD_W=1240; CARD_H=138
CARD_BG="black@0.68"; CARD_ACCENT="0x00DCC8@0.96"
TITLE_X=102; TITLE_Y=869; SUBTITLE_X=102; SUBTITLE_Y=927
VOICE_CHAIN="acompressor=threshold=-20dB:ratio=2.4:attack=12:release=140,loudnorm=I=-16:LRA=6:TP=-1.2,alimiter=limit=0.92"

def sh(cmd):
    print("+"," ".join(map(str,cmd)),flush=True)
    subprocess.run(cmd,check=True)

def esc(text):
    return str(text).replace("\\","\\\\").replace(":","\\:").replace("'","\\'").replace("%","\\%")

def probe_duration(path):
    try:
        return float(subprocess.check_output([
            "ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(path)
        ],text=True).strip())
    except Exception:
        return 0.0

def has_audio(path):
    try:
        out=subprocess.check_output([
            "ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=codec_type","-of","csv=p=0",str(path)
        ],text=True).strip()
        return bool(out)
    except Exception:
        return False

def asset_map(items):
    out={}
    for pos,item in enumerate(items,1):
        if isinstance(item,str):
            p=Path(item)
            out[pos]={"index":pos,"path":item,"type":"image" if p.suffix.lower() in IMAGE_EXTENSIONS else "video","approved":True}
        else:
            out[int(item.get("index",pos))]=item
    return out

def is_image(asset):
    p=Path(asset["path"])
    return asset.get("type")=="image" or p.suffix.lower() in IMAGE_EXTENSIONS

def video_seek(path,piece_no,duration):
    total=probe_duration(path)
    room=total-duration-.35
    if room<=.2:return 0.0
    return round((piece_no*5.83)%room,3)

def render_piece(asset,duration,dest,piece_no,card=None,keyword="",scene_first=False):
    path=Path(asset["path"])
    if not path.exists():raise RuntimeError(f"Asset ausente: {path}")
    image_mode=is_image(asset)
    if image_mode:
        inp=["-loop","1","-i",str(path)]
    else:
        seek=video_seek(path,piece_no,duration)
        inp=["-stream_loop","-1"]
        if seek>0:inp += ["-ss",f"{seek:.3f}"]
        inp += ["-i",str(path)]

    # Movimento sempre preserva a fonte completa. Fundo preenche sem crop no foreground.
    drift_x=6+(piece_no%3)*2
    drift_y=3+(piece_no%2)*2
    if image_mode:
        base=(
            f"[0:v]fps={FPS},split=2[bg0][fg0];"
            f"[bg0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            "boxblur=28:14,eq=brightness=-0.19:saturation=0.88[bg];"
            f"[fg0]scale={W-90}:{H-54}:force_original_aspect_ratio=decrease,setsar=1[fg];"
            f"[bg][fg]overlay=x='(W-w)/2+{drift_x}*sin(t*0.55)':y='(H-h)/2+{drift_y}*cos(t*0.41)',"
        )
    else:
        base=(
            f"[0:v]fps={FPS},split=2[bg0][fg0];"
            f"[bg0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            "boxblur=28:14,eq=brightness=-0.19:saturation=0.90[bg];"
            f"[fg0]scale={W}:{H}:force_original_aspect_ratio=decrease,setsar=1[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
        )

    filters=[
        f"drawtext=fontfile='{FONT}':text='RADAR DOS GAMES':x={WATERMARK_X}:y={WATERMARK_Y}:"
        f"fontsize={WATERMARK_SIZE}:fontcolor=white@0.70:borderw=1:bordercolor=black@0.55:expansion=none"
    ]
    if scene_first and card:
        title=esc(card.get("title","")); subtitle=esc(card.get("subtitle",""))
        end=max(1.0,min(duration-.12,4.8))
        en=f"between(t,0.28,{end:.3f})"
        filters += [
            f"drawbox=x={CARD_X}:y={CARD_Y}:w={CARD_W}:h={CARD_H}:color={CARD_BG}:t=fill:enable='{en}'",
            f"drawbox=x={CARD_X}:y={CARD_Y}:w=10:h={CARD_H}:color={CARD_ACCENT}:t=fill:enable='{en}'",
            f"drawtext=fontfile='{FONT}':text='{title}':x={TITLE_X}:y={TITLE_Y}:fontsize=40:fontcolor=white:"
            f"borderw=2:bordercolor=black@0.65:expansion=none:enable='{en}'",
        ]
        if subtitle:
            filters.append(
                f"drawtext=fontfile='{FONT}':text='{subtitle}':x={SUBTITLE_X}:y={SUBTITLE_Y}:fontsize=25:"
                f"fontcolor=0x7FE8FF:borderw=1:bordercolor=black@0.7:expansion=none:enable='{en}'"
            )

    if keyword:
        k=esc(keyword[:24])
        filters += [
            "drawbox=x=72:y=112:w=520:h=70:color=black@0.72:t=fill:enable='between(t,0.18,1.75)'",
            f"drawtext=fontfile='{FONT}':text='{k}':x=96:y=127:fontsize=34:fontcolor=0xF4FF00:"
            "borderw=2:bordercolor=black@0.75:expansion=none:enable='between(t,0.18,1.75)'",
        ]

    # Pequeno dip apenas na abertura de nova cena; cortes internos continuam secos.
    if scene_first and piece_no>1:
        filters.append("fade=t=in:st=0:d=0.10")

    fc=base+",".join(filters)+",format=yuv420p[v]"
    sh([
        "ffmpeg","-y","-v","error",*inp,"-t",f"{duration:.3f}",
        "-filter_complex",fc,"-map","[v]","-an","-r",str(FPS),
        "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",str(dest)
    ])

def make_sfx_track(duration_seconds,events,dest):
    """Cria impactos curtíssimos e discretos nos pontos editoriais fortes."""
    rate=48000
    frames=max(1,int(math.ceil(duration_seconds*rate)))
    samples=[0.0]*frames
    for event in events:
        start=max(0,int(float(event.get("time",0))*rate))
        intensity=max(1,min(4,int(event.get("intensity",1))))
        span=int(rate*(0.11+0.02*intensity))
        amp=0.018+0.006*intensity
        for n in range(span):
            idx=start+n
            if idx>=frames:break
            t=n/rate
            env=math.exp(-22*t)
            freq=760-360*(n/max(1,span))
            samples[idx]+=amp*env*math.sin(2*math.pi*freq*t)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(dest),"wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        chunk=bytearray()
        for value in samples:
            v=max(-1.0,min(1.0,value))
            chunk += struct.pack("<h",int(v*32767))
        wf.writeframes(bytes(chunk))

def mix_voice_sfx(visuals,voice,sfx,dest):
    sh([
        "ffmpeg","-y","-v","error","-i",str(visuals),"-i",str(voice),"-i",str(sfx),
        "-filter_complex",
        f"[1:a]{VOICE_CHAIN}[voice];[2:a]volume=0.72[sfx];[voice][sfx]amix=inputs=2:weights='1 0.55':normalize=0,alimiter=limit=0.92[a]",
        "-map","0:v:0","-map","[a]","-shortest","-c:v","copy",
        "-c:a","aac","-b:a","192k","-ar","48000","-ac","2",str(dest)
    ])

def normalize_intro(src,dest,limit_seconds=0):
    cmd=["ffmpeg","-y","-v","error","-i",str(src)]
    if limit_seconds and limit_seconds>0:
        cmd += ["-t",f"{limit_seconds:.3f}"]
    vf=f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,fps={FPS},setsar=1,format=yuv420p"
    af="aresample=48000"
    if limit_seconds and limit_seconds>0.35:
        af += f",afade=t=out:st={max(0,limit_seconds-.18):.3f}:d=.18"
    cmd += ["-vf",vf,"-af",af,"-c:v","libx264","-preset","veryfast","-crf","20",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-ar","48000","-ac","2",str(dest)]
    sh(cmd)

def trim_av(src,dest,start=0,duration=0):
    cmd=["ffmpeg","-y","-v","error"]
    if start>0:cmd += ["-ss",f"{start:.3f}"]
    cmd += ["-i",str(src)]
    if duration>0:cmd += ["-t",f"{duration:.3f}"]
    cmd += ["-vf",f"fps={FPS},format=yuv420p","-af","aresample=48000",
            "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",
            "-c:a","aac","-b:a","192k","-ar","48000","-ac","2",str(dest)]
    sh(cmd)

def concat_av(paths,dest,tmp):
    listing=tmp/"final-v4.txt"
    listing.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in paths),encoding="utf-8")
    sh(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(listing),
        "-c","copy","-movflags","+faststart",str(dest)])

def render(manifest_path):
    m=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    out=Path(m.get("output","output/master.mp4")); out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.parent/"director_v4"; tmp.mkdir(parents=True,exist_ok=True)
    intro=Path(m["intro"])
    if not intro.exists():raise RuntimeError("QUALITY_BLOCK: intro oficial ausente")
    timings=json.loads(Path(m["voice_timings"]).read_text(encoding="utf-8"))
    scenes=m.get("scenes") or []; assets=asset_map(m.get("assets") or [])
    if len(scenes)!=len(timings.get("segments") or []):
        raise RuntimeError("QUALITY_BLOCK: V4 cenas/timings incompatíveis")

    pieces=[]; qa_scenes=[]; global_piece=0; cursor=0.0; sfx_events=[]
    for scene_no,scene in enumerate(scenes,1):
        beats=scene.get("beats") or []
        if not beats:raise RuntimeError(f"QUALITY_BLOCK: V4 cena {scene_no} sem beats")
        scene_paths=[]; sequence=[]
        for beat_no,beat in enumerate(beats,1):
            idx=int(beat["media_index"])
            if idx not in assets or not assets[idx].get("approved",True):
                raise RuntimeError(f"QUALITY_BLOCK: V4 cena {scene_no} asset {idx} inválido")
            d=float(beat.get("duration") or 0)
            if d<=0:raise RuntimeError(f"QUALITY_BLOCK: V4 beat sem duração cena {scene_no}")
            global_piece+=1
            p=tmp/f"scene_{scene_no:02d}_beat_{beat_no:02d}.mp4"
            render_piece(
                assets[idx],d,p,global_piece,
                card={"title":scene.get("title",""),"subtitle":scene.get("subtitle","")},
                keyword=beat.get("keyword_overlay",""),
                scene_first=(beat_no==1),
            )
            pieces.append(p); scene_paths.append(str(p)); sequence.append(idx)
            if (beat_no==1 and scene_no>1) or int(beat.get("intensity",0))>=2:
                sfx_events.append({"time":round(cursor,3),"intensity":max(1,int(beat.get("intensity",1)))})
            cursor+=d

        qa_scenes.append({
            "scene":scene_no,
            "semantic_subject":scene.get("semantic_subject"),
            "phrase_level":True,
            "beats":len(beats),
            "sequence":sequence,
            "distinct_assets":len(set(sequence)),
            "average_beat_seconds":round(sum(float(b["duration"]) for b in beats)/len(beats),3),
            "keyword_overlays":sum(1 for b in beats if b.get("keyword_overlay")),
            "pieces":scene_paths,
        })

    listing=tmp/"visuals.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in pieces),encoding="utf-8")
    visuals=tmp/"body_visuals.mp4"
    sh(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(listing),"-c","copy",str(visuals)])

    sfx=tmp/"editorial-sfx.wav"
    make_sfx_track(cursor,sfx_events,sfx)
    body=tmp/"body_av.mp4"
    mix_voice_sfx(visuals,Path(m["voice"]),sfx,body)

    intro_norm=tmp/"intro-sting.mp4"
    intro_limit=float(m.get("intro_sting_seconds") or 0)
    normalize_intro(intro,intro_norm,intro_limit)

    cold=float(m.get("cold_open_seconds") or 0)
    final_parts=[]
    if cold>=2.0 and cold < probe_duration(body)-1:
        cold_p=tmp/"cold-open.mp4"; rest_p=tmp/"body-rest.mp4"
        trim_av(body,cold_p,0,cold)
        trim_av(body,rest_p,cold,0)
        final_parts=[cold_p,intro_norm,rest_p]
        timeline="cold_open_then_intro_sting_then_body"
    else:
        final_parts=[intro_norm,body]
        timeline="intro_sting_then_body"
    concat_av(final_parts,out,tmp)

    probe=json.loads(subprocess.check_output([
        "ffprobe","-v","error","-show_entries","format=duration,size",
        "-show_entries","stream=codec_type,width,height,r_frame_rate","-of","json",str(out)
    ],text=True))
    qa={
        "master":str(out),
        "standard":"radar-dos-games-premium-v4-director-cut",
        "premium_version":"PREMIUM_V4_DIRECTOR_CUT",
        "voice":timings.get("voice"),
        "semantic_timing_source":timings.get("source"),
        "timeline_policy":timeline,
        "cold_open_seconds":cold,
        "intro_sting_seconds":round(probe_duration(intro_norm),3),
        "framing_policy":"full_source_visible; blurred_background_fill; no_destructive_crop",
        "motion_policy":"subtle_non_destructive; phrase_level",
        "sound_design":{
            "voice_chain":"compression+loudnorm+limiter",
            "editorial_sfx":"subtle_generated_impacts",
            "sfx_events":len(sfx_events),
            "music_bed":"not_forced_without_approved_licensed_asset",
        },
        "editing_policy":"phrase_level_beats; variable_pacing; selective_keyword_overlays",
        "scenes":qa_scenes,
        "probe":probe,
    }
    Path("output/qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"master":str(out),"version":"V4","scenes":len(qa_scenes),"sfx_events":len(sfx_events)},ensure_ascii=False))

if __name__=="__main__":
    render(sys.argv[1])
