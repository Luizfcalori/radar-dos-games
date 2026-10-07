#!/usr/bin/env python3
"""Diretor editorial Premium V3 do Radar dos Games.

Transforma o plano editorial + assets já validados em um manifesto de render:
- preserva mapeamentos semânticos explícitos quando existirem;
- nunca usa asset reprovado;
- evita repetir o mesmo primeiro asset entre cenas quando há alternativa;
- prioriza vídeo contextual e intercala imagens oficiais;
- define ritmo de cortes por duração real da fala;
- escolhe 3 cenas fortes para Shorts.
"""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

TARGET_CUT_SECONDS = 4.2
MIN_CUT_SECONDS = 3.0
MAX_CUT_SECONDS = 6.0
MAX_SCENE_ASSETS = 4


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def role_allowed(scene, asset):
    role = str(asset.get("role") or "")
    allowed_roles = set(scene.get("allowed_roles") or [])
    prefixes = tuple(scene.get("allowed_role_prefixes") or [])
    if not allowed_roles and not prefixes:
        return True
    return role in allowed_roles or any(role.startswith(p) for p in prefixes)


def valid_explicit(scene, assets):
    chosen = []
    for raw in scene.get("media_indices") or []:
        try:
            idx = int(raw)
        except Exception:
            continue
        asset = assets.get(idx)
        if not asset or not asset.get("approved", True) or not role_allowed(scene, asset):
            continue
        if idx not in chosen:
            chosen.append(idx)
    return chosen


def cut_count(duration, target=TARGET_CUT_SECONDS):
    duration = max(0.1, float(duration))
    if duration <= MAX_CUT_SECONDS:
        return 1
    minimum = max(1, math.ceil(duration / MAX_CUT_SECONDS))
    maximum = max(minimum, math.floor(duration / MIN_CUT_SECONDS))
    desired = max(1, round(duration / target))
    return max(minimum, min(8, maximum, desired))


def generic_subject(plan, scene, scene_no):
    value = scene.get("semantic_subject")
    if value:
        return str(value)
    topic = str(plan.get("topic") or "radar_dos_games")
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
    return f"{slug or 'radar_dos_games'}_scene_{scene_no:02d}"


def candidate_assets(scene, assets):
    vals = [a for a in assets.values() if a.get("approved", True) and role_allowed(scene, a)]
    return vals or [a for a in assets.values() if a.get("approved", True)]


def choose_assets(scene, assets, usage, previous_first, wanted):
    explicit = valid_explicit(scene, assets)
    has_semantic_rules = bool(scene.get("allowed_roles") or scene.get("allowed_role_prefixes") or scene.get("semantic_subject"))
    if explicit and has_semantic_rules:
        return explicit[:MAX_SCENE_ASSETS]

    candidates = candidate_assets(scene, assets)
    candidates.sort(
        key=lambda a: (
            0 if a.get("type") == "video" else 1,
            usage[int(a["index"])],
            int(a["index"]),
        )
    )
    ids = [int(a["index"]) for a in candidates]
    if previous_first in ids and len(ids) > 1 and ids[0] == previous_first:
        ids = ids[1:] + ids[:1]

    selected = []
    for idx in ids:
        if idx not in selected:
            selected.append(idx)
        if len(selected) >= wanted:
            break
    return selected


def hook_score(scene, idx, total):
    text = f"{scene.get('title','')} {scene.get('subtitle','')}".upper()
    score = 0
    for token, points in (
        ("CONFIRM", 4), ("NOV", 3), ("GAMEPLAY", 3), ("IMPACTO", 3),
        ("LANÇ", 2), ("DATA", 2), ("MUD", 2), ("AGORA", 2), ("RADAR", 1),
    ):
        if token in text:
            score += points
    if idx == 0:
        score += 3
    if idx == total - 1:
        score += 1
    score += max(0, 2 - abs(idx - (total // 2)))
    return score


def pick_shorts(scenes):
    if not scenes:
        return [0, 0, 0]
    ranked = sorted(range(len(scenes)), key=lambda i: (-hook_score(scenes[i], i, len(scenes)), i))
    picked = []
    for idx in ranked:
        if all(abs(idx - old) >= 2 for old in picked) or len(scenes) < 5:
            picked.append(idx)
        if len(picked) == 3:
            break
    for idx in range(len(scenes)):
        if idx not in picked:
            picked.append(idx)
        if len(picked) == 3:
            break
    while len(picked) < 3:
        picked.append(picked[-1] if picked else 0)
    return picked[:3]


def main(plan_path="output/auto-media-plan.json", clips_path="output/clips.json"):
    plan = read_json(plan_path)
    clips = read_json(clips_path)
    timings = read_json("output/voice-timings.json")
    segments = timings.get("segments") or []
    scenes = plan.get("scenes") or []
    if len(segments) != len(scenes):
        raise RuntimeError(f"QUALITY_BLOCK: Premium V3 recebeu {len(segments)} blocos de voz para {len(scenes)} cenas")

    assets = {
        int(a["index"]): a
        for a in clips.get("assets", [])
        if a.get("approved", True)
    }
    if not assets:
        raise RuntimeError("QUALITY_BLOCK: Premium V3 sem assets aprovados")

    generic_roles = all(str(a.get("role") or "").startswith("official_context_") for a in assets.values())
    usage = Counter()
    previous_first = None
    report = []

    for i, (scene, timing) in enumerate(zip(scenes, segments), 1):
        scene["semantic_subject"] = generic_subject(plan, scene, i)
        if generic_roles and not scene.get("allowed_roles") and not scene.get("allowed_role_prefixes"):
            scene["allowed_role_prefixes"] = ["official_context_"]

        duration = float(timing.get("duration") or 0)
        cuts = cut_count(duration)
        available = len(candidate_assets(scene, assets))
        wanted = max(1, min(MAX_SCENE_ASSETS, available, max(2, math.ceil(cuts / 2))))
        ids = choose_assets(scene, assets, usage, previous_first, wanted)
        if not ids:
            raise RuntimeError(f"QUALITY_BLOCK: cena {i} sem mídia elegível no Premium V3")

        scene["media_indices"] = ids
        scene["editing"] = {
            "version": "PREMIUM_V3",
            "cut_target_seconds": TARGET_CUT_SECONDS,
            "min_cut_seconds": MIN_CUT_SECONDS,
            "max_cut_seconds": MAX_CUT_SECONDS,
            "planned_cuts": cuts,
            "motion_profile": "subtle_non_destructive",
            "card_once_per_scene": True,
            "pattern_interrupt_max_seconds": 6.0,
        }
        for idx in ids:
            usage[idx] += 1
        previous_first = ids[0]

        report.append({
            "scene": i,
            "semantic_subject": scene["semantic_subject"],
            "duration": round(duration, 3),
            "planned_cuts": cuts,
            "media_indices": ids,
            "roles": [assets[idx].get("role") for idx in ids],
        })

    plan["premium_version"] = "PREMIUM_V3"
    plan["director_policy"] = (
        "semantic_scene_mapping; video_first_when_relevant; 3-6s_visual_cadence; "
        "non_destructive_motion; no_unapproved_assets; no_generic_cross_topic_fill"
    )
    Path(plan_path).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    picks = pick_shorts(scenes)
    Path("output/short-picks.json").write_text(
        json.dumps({"version": "PREMIUM_V3", "scene_indexes": picks}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest = {
        "premium_version": "PREMIUM_V3",
        "assets": list(assets.values()),
        "voice": "output/voice.mp3",
        "voice_timings": "output/voice-timings.json",
        "intro": "radar-dos-games-intro-oficial.mp4",
        "scenes": scenes,
        "output": "output/master.mp4",
    }
    Path("output/render.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {
        "status": "APPROVED",
        "version": "PREMIUM_V3",
        "target_cut_seconds": TARGET_CUT_SECONDS,
        "short_scene_indexes": picks,
        "asset_usage": {str(k): v for k, v in sorted(usage.items())},
        "scenes": report,
    }
    Path("output/director-v3.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    args = sys.argv[1:]
    main(*(args[:2]))
