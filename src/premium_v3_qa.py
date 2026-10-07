#!/usr/bin/env python3
"""Quality gate bloqueante do padrão Radar dos Games Premium V3."""
import json
from pathlib import Path

MIN_AVG_CUT = 2.4
MAX_AVG_CUT = 6.4


def load(path):
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"QUALITY_BLOCK: arquivo ausente: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    plan = load("output/auto-media-plan.json")
    director = load("output/director-v3.json")
    semantic = load("output/semantic-visual-qa.json")
    render_qa = load("output/qa.json")
    shorts = load("output/shorts/manifest.json")

    assert plan.get("premium_version") == "PREMIUM_V3", plan.get("premium_version")
    assert director.get("status") == "APPROVED", director
    assert director.get("version") == "PREMIUM_V3", director
    assert semantic.get("status") == "APPROVED", semantic
    assert render_qa.get("standard") == "radar-dos-games-premium-v3", render_qa.get("standard")

    scene_reports = render_qa.get("scenes") or []
    plan_scenes = plan.get("scenes") or []
    assert scene_reports and len(scene_reports) == len(plan_scenes), (len(scene_reports), len(plan_scenes))

    cadence = []
    previous_first = None
    repeated_first = 0
    for idx, (scene, row) in enumerate(zip(plan_scenes, scene_reports), 1):
        assert scene.get("semantic_subject"), f"cena {idx} sem semantic_subject"
        ids = [int(x) for x in scene.get("media_indices") or []]
        assert ids, f"cena {idx} sem media_indices"
        assert row.get("all_assets_explicit") is True, row
        cuts = int(row.get("cut_count") or len(row.get("sequence") or []))
        duration = float(row.get("voice_duration") or 0)
        assert cuts >= 1 and duration > 0, (idx, cuts, duration)
        avg = duration / cuts
        if duration >= 7:
            assert MIN_AVG_CUT <= avg <= MAX_AVG_CUT, (idx, duration, cuts, avg)
        first = (row.get("sequence") or [None])[0]
        if previous_first is not None and first == previous_first and len(ids) > 1:
            repeated_first += 1
        previous_first = first
        cadence.append({"scene": idx, "seconds": round(duration, 3), "cuts": cuts, "avg_cut": round(avg, 3)})

    assert repeated_first <= 1, f"repetição visual excessiva entre cenas: {repeated_first}"

    short_rows = shorts.get("shorts") or []
    assert len(short_rows) == 3, len(short_rows)
    for row in short_rows:
        assert row.get("boundary_policy") in {"voice_segment_complete", "silence_boundary_fallback"}, row
        assert float(row.get("duration") or 0) >= 8, row

    result = {
        "status": "APPROVED",
        "version": "PREMIUM_V3",
        "semantic_visual_sync": "APPROVED",
        "visual_cadence": "APPROVED",
        "non_destructive_motion": render_qa.get("motion_policy"),
        "shorts_semantic_boundaries": "APPROVED",
        "shorts_count": 3,
        "cadence": cadence,
    }
    Path("output/premium-v3-qa.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
