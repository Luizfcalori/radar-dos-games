#!/usr/bin/env python3
"""Create exactly three consecutive 9:16 segments from the approved Master render."""
import json
import subprocess
from pathlib import Path

OUT=Path("output")
MASTER=OUT/"master.mp4"
DEST=OUT/"shorts"
LAYOUT="RADAR_MASTER_SPLIT_9X16_V1"
HOOK_POLICY="approved_hook_as_metadata; contiguous_master_timeline; preserve_master_audio"


def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)
    ],text=True))


def duration(path):
    return float(probe(path)["format"]["duration"])


def run(cmd):
    print("+"," ".join(map(str,cmd)),flush=True)
    subprocess.run(cmd,check=True)


def main():
    if not MASTER.is_file() or MASTER.stat().st_size<1_000_000:
        raise RuntimeError("QUALITY_BLOCK: Master final ausente ou inválido")
    master_info=probe(MASTER)
    master_duration=float(master_info["format"]["duration"])
    video=next((x for x in master_info["streams"] if x.get("codec_type")=="video"),None)
    audio=next((x for x in master_info["streams"] if x.get("codec_type")=="audio"),None)
    if not video or not audio:
        raise RuntimeError("QUALITY_BLOCK: Master precisa conter vídeo e áudio")
    if int(video.get("width",0))!=1920 or int(video.get("height",0))!=1080:
        raise RuntimeError("QUALITY_BLOCK: Master não está em 1920x1080")
    segment_length=master_duration/3.0
    if segment_length<20:
        raise RuntimeError(f"QUALITY_BLOCK: Master tem apenas {master_duration:.1f}s; três partes precisam ter ao menos 20s cada")

    picks=json.loads((OUT/"short-picks.json").read_text(encoding="utf-8"))
    hooks=[str(x or "").strip() for x in (picks.get("expected_hooks") or [])]
    if len(hooks)!=3 or any(not x for x in hooks):
        raise RuntimeError("QUALITY_BLOCK: são necessários exatamente três hooks aprovados")
    master_meta=json.loads((OUT/"master-youtube.json").read_text(encoding="utf-8"))
    render=json.loads((OUT/"qa.json").read_text(encoding="utf-8"))
    music=(render.get("sound_design") or {}).get("music_bed")
    if music!="approved_bed_with_voice_ducking":
        raise RuntimeError("QUALITY_BLOCK: trilha/ducking do Master não foi aprovada")

    DEST.mkdir(parents=True,exist_ok=True)
    for old in DEST.glob("short_*.mp4"):
        old.unlink()
    rows=[]
    for i,hook in enumerate(hooks,1):
        start=(i-1)*segment_length
        end=master_duration if i==3 else i*segment_length
        expected=end-start
        dest=DEST/f"short_{i}.mp4"
        vf=(
            "[0:v]split=2[bgsrc][fgsrc];"
            "[bgsrc]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=28:14,eq=brightness=-0.18:saturation=0.85[bg];"
            "[fgsrc]scale=1080:608:force_original_aspect_ratio=decrease,"
            "pad=1080:608:(ow-iw)/2:(oh-ih)/2:color=0x081420,setsar=1[fg];"
            "[bg][fg]overlay=0:(H-h)/2,format=yuv420p[v]"
        )
        run([
            "ffmpeg","-y","-v","error","-ss",f"{start:.6f}","-i",str(MASTER),
            "-t",f"{expected:.6f}","-filter_complex",vf,"-map","[v]","-map","0:a:0",
            "-c:v","libx264","-preset","veryfast","-crf","18","-r","30",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-ar","48000",
            "-movflags","+faststart",str(dest)
        ])
        info=probe(dest)
        actual=float(info["format"]["duration"])
        out_video=next(x for x in info["streams"] if x.get("codec_type")=="video")
        if (int(out_video.get("width",0)),int(out_video.get("height",0)))!=(1080,1920):
            raise RuntimeError(f"QUALITY_BLOCK: resolução incorreta no Short {i}")
        if actual<20 or abs(actual-expected)>0.25:
            raise RuntimeError(f"QUALITY_BLOCK: duração do Short {i} divergiu do trecho Master ({actual:.3f}/{expected:.3f})")
        if not any(x.get("codec_type")=="audio" for x in info["streams"]):
            raise RuntimeError(f"QUALITY_BLOCK: áudio ausente no Short {i}")
        meta_path=OUT/f"short-{i}-youtube.json"
        if not meta_path.is_file():
            raise RuntimeError(f"QUALITY_BLOCK: metadata do Short {i} ausente")
        meta=json.loads(meta_path.read_text(encoding="utf-8"))
        if " ".join(str(meta.get("title") or "").split()).casefold()!=" ".join(hook.split()).casefold():
            raise RuntimeError(f"QUALITY_BLOCK: título do Short {i} não corresponde ao hook aprovado")
        rows.append({
            "index":i,"path":str(dest),"title":hook,"approved_hook":hook,
            "duration":round(actual,3),"source_start":round(start,6),"source_end":round(end,6),
            "scene_index":int(((picks.get("semantic_matches") or [{}]*3)[i-1]).get("scene_index",i-1)),
            "render_policy":"contiguous_master_segment",
            "boundary_policy":"master_timeline_partition",
            "audio_source":"master_original_audio",
            "layout_profile":LAYOUT,
            "cta":["INSCREVA-SE AGORA","DEIXE O LIKE","RADAR DOS GAMES"],
            "music_bed":music,
            "media_beats":[],
        })

    manifest={
        "standard":"radar-dos-games-shorts-from-master-v1",
        "premium_version":"PREMIUM_V4_DIRECTOR_CUT",
        "cinematic_profile":"RADAR_CINEMATIC_V1",
        "layout_profile":LAYOUT,
        "hook_policy":HOOK_POLICY,
        "source_policy":"contiguous_master_split_v1",
        "master_path":str(MASTER),
        "master_duration":round(master_duration,6),
        "resolution":[1080,1920],"fps":30,
        "audio_policy":"preserve_master_original_audio_per_segment",
        "expected_hooks":hooks,
        "shorts":rows,
    }
    (DEST/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
