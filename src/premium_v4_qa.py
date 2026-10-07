#!/usr/bin/env python3
"""Gate editorial Premium V4 Director Cut."""
import json
import re
from pathlib import Path

def load(path):
    p=Path(path)
    if not p.exists():raise RuntimeError(f"QUALITY_BLOCK: arquivo ausente {path}")
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    plan=load("output/auto-media-plan.json")
    director=load("output/director-v4.json")
    clips=load("output/clips.json")
    semantic=load("output/semantic-visual-qa.json")
    render=load("output/qa.json")
    shorts=load("output/shorts/manifest.json")
    frames=load("output/visual-frame-qa.json")
    timings=load("output/voice-timings.json")

    assert plan.get("premium_version")=="PREMIUM_V4_DIRECTOR_CUT",plan.get("premium_version")
    assert director.get("status")=="APPROVED" and director.get("version")=="PREMIUM_V4_DIRECTOR_CUT",director
    assert semantic.get("status")=="APPROVED",semantic
    assert render.get("standard")=="radar-dos-games-premium-v4-director-cut",render.get("standard")
    assert render.get("editing_policy")=="phrase_level_beats; variable_pacing; selective_keyword_overlays"
    assert frames.get("status")=="APPROVED",frames
    assert "sentence_estimates" in str(timings.get("source","")),timings.get("source")

    if not clips.get("publishable_media"):
        raise RuntimeError("QUALITY_BLOCK: pacote de mídia não está publicável")
    video_assets=int(clips.get("video_assets") or 0)
    unique_video_seconds=float(clips.get("unique_video_seconds") or 0)
    required_videos=max(1,int(plan.get("minimum_video_assets") or 0))
    required_unique=max(15.0,float(plan.get("minimum_unique_video_seconds") or 0))
    if video_assets < required_videos:
        raise RuntimeError(f"QUALITY_BLOCK: gameplay/vídeo oficial ausente ({video_assets}/{required_videos})")
    if unique_video_seconds < required_unique:
        raise RuntimeError(f"QUALITY_BLOCK: somente {unique_video_seconds:.1f}s de vídeo oficial único; mínimo {required_unique:.1f}s")

    plan_scenes=plan.get("scenes") or []
    for i,scene in enumerate(plan_scenes,1):
        title=str(scene.get("title") or "").strip()
        if not title:
            raise RuntimeError(f"QUALITY_BLOCK: cena {i} sem headline")
        if re.fullmatch(r"DESTAQUE\s*\d*",title,re.I) or re.fullmatch(r"CENA\s*\d+.*",title,re.I):
            raise RuntimeError(f"QUALITY_BLOCK: headline genérica proibida na cena {i}: {title}")

    asset_map={int(a["index"]):a for a in clips.get("assets",[]) if a.get("approved")}
    body_seconds=0.0
    moving_seconds=0.0
    video_scene_count=0
    for scene in plan_scenes:
        scene_has_video=False
        for beat in scene.get("beats") or []:
            duration=float(beat.get("duration") or 0)
            body_seconds+=duration
            asset=asset_map.get(int(beat.get("media_index") or 0),{})
            if asset.get("type")=="video":
                moving_seconds+=duration
                scene_has_video=True
        if scene_has_video:
            video_scene_count+=1
    moving_ratio=(moving_seconds/body_seconds) if body_seconds else 0.0
    if moving_ratio+1e-9 < 0.35:
        raise RuntimeError(f"QUALITY_BLOCK: gameplay/footage em movimento ocupa {moving_ratio:.1%}; mínimo 35%")
    if video_scene_count < min(3,len(plan_scenes)):
        raise RuntimeError(f"QUALITY_BLOCK: gameplay/footage presente em somente {video_scene_count} cenas")

    scenes=render.get("scenes") or []
    assert scenes and len(scenes)==len(plan.get("scenes") or []),(len(scenes),len(plan.get("scenes") or []))
    phrase_count=int(director.get("phrase_count") or 0)
    assert phrase_count>=len(scenes),(phrase_count,len(scenes))
    cadence=[]
    for row in scenes:
        avg=float(row.get("average_beat_seconds") or 0)
        assert 1.35<=avg<=6.10,(row.get("scene"),avg)
        assert row.get("phrase_level") is True,row
        assert int(row.get("beats") or 0)>=1,row
        cadence.append({"scene":row.get("scene"),"beats":row.get("beats"),"avg_beat":avg})

    srows=shorts.get("shorts") or []
    assert len(srows)==3,len(srows)
    for row in srows:
        assert row.get("render_policy")=="rebuilt_from_source_assets_not_master_crop",row
        assert row.get("boundary_policy")=="independent_scene_voice_complete",row
        assert float(row.get("duration") or 0)>=8,row

    sound=render.get("sound_design") or {}
    assert sound.get("voice_chain")=="compression+loudnorm+limiter",sound
    assert sound.get("editorial_sfx")=="subtle_generated_impacts",sound

    result={
        "status":"APPROVED","version":"PREMIUM_V4_DIRECTOR_CUT",
        "phrase_level_direction":"APPROVED",
        "semantic_visual_sync":"APPROVED",
        "variable_pacing":"APPROVED",
        "sound_design":"APPROVED",
        "independent_shorts":"APPROVED",
        "visual_frame_qa":"APPROVED",
        "real_headlines":"APPROVED",
        "gameplay_moving_footage":"APPROVED",
        "video_assets":video_assets,
        "unique_video_seconds":round(unique_video_seconds,3),
        "moving_footage_seconds":round(moving_seconds,3),
        "moving_footage_ratio":round(moving_ratio,4),
        "video_scene_count":video_scene_count,
        "cold_open_seconds":director.get("cold_open_seconds"),
        "cadence":cadence,
    }
    Path("output/premium-v4-qa.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
