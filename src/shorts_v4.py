#!/usr/bin/env python3
"""Gera exatamente 3 Shorts como cortes verticais do Master, preservando o áudio original."""
import json
import subprocess
import sys
from pathlib import Path

SHORTS_LAYOUT_ID = "RADAR_PREMIUM_MASTER_CROP_V1"
SOURCE_POLICY = "master_timeline_crops_preserve_original_audio"
RENDER_POLICY = "direct_master_timeline_crop_with_original_narration"
AUDIO_POLICY = "mandatory_original_master_audio; no_an; no_silent_rebuild"

def probe(path):
    raw=subprocess.check_output([
        "ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)
    ],text=True)
    data=json.loads(raw)
    streams=data.get("streams") or []
    return {
        "duration":float((data.get("format") or {}).get("duration") or 0),
        "video":any(x.get("codec_type")=="video" for x in streams),
        "audio":any(x.get("codec_type")=="audio" for x in streams),
    }

def main():
    master=Path("output/master.mp4")
    if not master.exists():
        raise RuntimeError("QUALITY_BLOCK: Master ausente; Shorts devem ser cortes do Master.")
    master_info=probe(master)
    if not master_info["video"] or not master_info["audio"]:
        raise RuntimeError("QUALITY_BLOCK: Master precisa conter vídeo e narração/áudio antes dos Shorts.")

    # shorts.py corta o próprio Master nos limites das falas do voice-timings,
    # faz o enquadramento 9:16 e mapeia também 0:a?; não reconstrói cenas mudas.
    subprocess.run([sys.executable,"src/shorts.py",str(master)],check=True)

    manifest_path=Path("output/shorts/manifest.json")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    picks_path=Path("output/short-picks.json")
    picks=json.loads(picks_path.read_text(encoding="utf-8")) if picks_path.exists() else {}
    hooks=[" ".join(str(x or "").split()).strip() for x in (picks.get("expected_hooks") or [])]
    shorts=manifest.get("shorts") or []
    if len(shorts)!=3:
        raise RuntimeError(f"QUALITY_BLOCK: esperados exatamente 3 Shorts; encontrados {len(shorts)}")
    if hooks and len(hooks)!=3:
        raise RuntimeError("QUALITY_BLOCK: short-picks precisa fornecer exatamente 3 hooks.")

    for i,item in enumerate(shorts):
        path=Path(item["path"])
        info=probe(path)
        if not info["video"] or not info["audio"]:
            raise RuntimeError(f"QUALITY_BLOCK: Short {i+1} sem trilha de áudio; publicação bloqueada.")
        if info["duration"]<20:
            raise RuntimeError(f"QUALITY_BLOCK: Short {i+1} curto/incompleto ({info['duration']:.1f}s).")
        item["duration"]=round(info["duration"],3)
        item["audio_validation"]="audio_stream_present_from_master"
        item["source"]="output/master.mp4"
        item["render_policy"]="direct_master_timeline_crop_with_original_narration"
        item["boundary_policy"]="complete_master_voice_segment"
        if hooks:
            item["approved_hook"]=hooks[i]
    manifest.update({
        "standard":"radar-dos-games-shorts-premium-v4-master-cuts",
        "premium_version":"PREMIUM_V4_MASTER_CUTS",
        "layout_profile":SHORTS_LAYOUT_ID,
        "source_policy":SOURCE_POLICY,
        "render_policy":"vertical_reframe_of_master_with_original_narration_music_and_sfx",
        "audio_policy":AUDIO_POLICY,
        "shorts":shorts,
    })
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False))

if __name__=="__main__":
    main()
