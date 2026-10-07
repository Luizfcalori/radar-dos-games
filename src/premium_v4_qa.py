#!/usr/bin/env python3
"""Gate editorial Premium V4 Director Cut."""
import json
from pathlib import Path

def load(path):
    p=Path(path)
    if not p.exists():raise RuntimeError(f"QUALITY_BLOCK: arquivo ausente {path}")
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    plan=load("output/auto-media-plan.json")
    director=load("output/director-v4.json")
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
        "cold_open_seconds":director.get("cold_open_seconds"),
        "cadence":cadence,
    }
    Path("output/premium-v4-qa.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
