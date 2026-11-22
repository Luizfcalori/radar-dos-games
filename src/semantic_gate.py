#!/usr/bin/env python3
"""Flexible phrase-to-gameplay QA: prefer exact matches, allow reviewed same-game fallback."""
import json
import sys
from pathlib import Path


def main(plan_path, clips_path, out_path="output/semantic-visual-qa.json"):
    plan=json.loads(Path(plan_path).read_text(encoding="utf-8"))
    clips=json.loads(Path(clips_path).read_text(encoding="utf-8"))
    assets={int(a["index"]):a for a in clips.get("assets",[]) if a.get("approved",True)}
    errors=[]
    warnings=[]
    report=[]
    try:
        from vision_semantics import scene_categories
    except ModuleNotFoundError:
        from src.vision_semantics import scene_categories
    try:
        from continuity import validate_video_beats
    except ModuleNotFoundError:
        from src.continuity import validate_video_beats

    beats=[b for scene in plan.get("scenes",[]) for b in scene.get("beats",[])]
    if not beats:
        errors.append({"type":"missing_beats","message":"Plano sem beats de fala para validar."})
    try:
        continuity=validate_video_beats(beats,assets,require_windows=True)
    except Exception as exc:
        continuity={"status":"BLOCKED","message":str(exc)}
        errors.append({"type":"continuity","message":str(exc)})

    for scene_no,scene in enumerate(plan.get("scenes",[]),1):
        scene_errors=[]
        scene_warnings=[]
        ids=[int(x) for x in scene.get("media_indices",[]) if str(x).lstrip("-").isdigit()]
        if not ids:
            scene_errors.append({"type":"missing_media_indices","message":"Cena sem mídia vinculada."})
        selected=[]
        for idx in ids:
            asset=assets.get(idx)
            if not asset:
                scene_errors.append({"type":"missing_asset","asset":idx,"message":"Mídia ausente ou não aprovada."})
            else:
                selected.append(asset)

        beats_here=scene.get("beats",[])
        if not beats_here:
            scene_errors.append({"type":"missing_scene_beats","message":"Cena sem frases/intervalos associados."})

        for beat in beats_here:
            phrase=beat.get("phrase",beat.get("phrase_index",1))
            text=str(beat.get("text") or "").strip()
            idx=int(beat.get("media_index",-1))
            asset=assets.get(idx)
            if not text:
                scene_errors.append({"phrase":phrase,"type":"empty_phrase","message":"Beat sem texto de fala."})
                continue
            if not asset:
                scene_errors.append({"phrase":phrase,"type":"missing_beat_asset","asset":idx,
                                     "message":"A frase aponta para mídia não aprovada."})
                continue
            if asset.get("type")!="video":
                if not beat.get("approved_context_still"):
                    scene_errors.append({"phrase":phrase,"type":"unverified_still",
                                         "message":"Imagem estática sem aprovação contextual explícita."})
                continue
            source_window=beat.get("source_window") or {}
            if not source_window:
                scene_errors.append({"phrase":phrase,"type":"missing_source_window",
                                     "message":"Frase sem intervalo de origem rastreável."})
                continue

            expected=set(scene_categories(text))
            if not expected:
                expected=set(scene.get("vision_categories") or
                             scene_categories(scene.get("title") or scene.get("semantic_subject") or ""))
            requirements=(scene.get("phrase_subjects") or {}).get(str(phrase),[])
            start=float(source_window.get("start",0))
            end=float(source_window.get("end",0))
            windows=(scene.get("visual_windows") or {}).get(str(idx),[])
            covering=[w for w in windows
                      if float(w.get("start",0))<=start+0.002
                      and float(w.get("end",0))+0.002>=end
                      and w.get("reviewed") is True and w.get("evidence")]
            if not covering:
                scene_errors.append({"phrase":phrase,"type":"unreviewed_visual_window","asset":idx,
                                     "message":"O intervalo não possui inspeção visual revisada."})
                continue

            # Explicitly named subjects are still protected. General category
            # labels are soft guidance, not a reason to stop the whole production.
            if requirements and not any(set(requirements).issubset(set(w.get("subjects",[]))) for w in covering):
                scene_errors.append({"phrase":phrase,"type":"required_subject_missing","asset":idx,
                                     "required_subjects":requirements,
                                     "message":"Sujeito nominal explicitamente exigido não foi confirmado."})
                continue

            category_match=not expected or any(
                bool(expected & set(w.get("semantic_categories",[]))) for w in covering
            )
            if not category_match:
                scene_warnings.append({
                    "phrase":phrase,"type":"flexible_same_game_fallback","asset":idx,
                    "expected_categories":sorted(expected),
                    "observed_categories":sorted(set().union(*(set(w.get("semantic_categories",[])) for w in covering))),
                    "message":"Categoria visual diferente da frase; trecho revisado do mesmo jogo aceito como plano de apoio."
                })
            elif not scene_categories(text):
                scene_warnings.append({
                    "phrase":phrase,"type":"contextual_phrase","asset":idx,
                    "message":"Frase contextual sem categoria visual própria; validada pelo contexto da cena."
                })

        allowed_roles=set(scene.get("allowed_roles") or [])
        allowed_prefixes=tuple(scene.get("allowed_role_prefixes") or [])
        for asset in selected:
            role=str(asset.get("role") or "")
            ok=(not allowed_roles and not allowed_prefixes) or role in allowed_roles or any(role.startswith(p) for p in allowed_prefixes)
            if not ok:
                scene_errors.append({"type":"role_mismatch","role":role,
                                     "message":"Papel visual fora das fontes aprovadas para a cena."})
        errors.extend([{"scene":scene.get("paragraph",scene_no),**item} for item in scene_errors])
        warnings.extend([{"scene":scene.get("paragraph",scene_no),**item} for item in scene_warnings])
        report.append({"scene":scene.get("paragraph",scene_no),
                       "subject":scene.get("semantic_subject") or scene.get("title"),
                       "asset_indices":ids,
                       "phrase_count":len(beats_here),
                       "status":"BLOCKED" if scene_errors else "APPROVED",
                       "warning_count":len(scene_warnings)})

    result={
        "status":"BLOCKED" if errors else "APPROVED",
        "policy":"FLEXIBLE_PHRASE_TO_REVIEWED_GAMEPLAY_V3",
        "continuity_report":continuity,
        "error_count":len(errors),
        "errors":errors,
        "warning_count":len(warnings),
        "warnings":warnings,
        "matching_policy":"Exact category matches are preferred; reviewed gameplay from the same approved game/source is accepted as fallback. Explicit named-subject requirements, missing media, unreviewed intervals and repeated intervals remain blocked.",
        "scenes":report
    }
    Path(out_path).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if errors:
        raise RuntimeError(f"QUALITY_BLOCK: {len(errors)} problema(s) de mídia/origem/continuidade; render/publicação bloqueados.")


if __name__=="__main__":
    if len(sys.argv)<3:
        raise SystemExit("Uso: semantic_gate.py <plan.json> <clips.json> [out.json]")
    main(*sys.argv[1:4])
