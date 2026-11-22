#!/usr/bin/env python3
"""Fail-closed phrase-to-frame semantic QA for every Radar production."""
import json
import sys
from pathlib import Path


def main(plan_path, clips_path, out_path="output/semantic-visual-qa.json"):
    plan=json.loads(Path(plan_path).read_text(encoding="utf-8"))
    clips=json.loads(Path(clips_path).read_text(encoding="utf-8"))
    assets={int(a["index"]):a for a in clips.get("assets",[]) if a.get("approved",True)}
    errors=[]
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
                # Still images are allowed only as explicit contextual inserts.
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
            requirements=(scene.get("phrase_subjects") or {}).get(str(phrase),[])
            if not expected and not requirements:
                scene_errors.append({"phrase":phrase,"type":"unclassifiable_phrase",
                                     "message":"A frase não descreve uma categoria visual verificável nem tem sujeito nominal validado; reescreva-a ou associe quadro oficial específico."})
                continue
            start=float(source_window.get("start",0))
            end=float(source_window.get("end",0))
            windows=(scene.get("visual_windows") or {}).get(str(idx),[])
            covering=[w for w in windows
                      if float(w.get("start",0))<=start+0.002
                      and float(w.get("end",0))+0.002>=end
                      and w.get("reviewed") is True and w.get("evidence")]
            valid=[]
            for window in covering:
                categories=set(window.get("semantic_categories",[]))
                subjects=set(window.get("subjects",[]))
                if "title_card" in categories:
                    continue
                if expected and not (expected & categories):
                    continue
                if requirements and not set(requirements).issubset(subjects):
                    continue
                valid.append(window)
            if not valid:
                scene_errors.append({
                    "phrase":phrase,"type":"phrase_visual_mismatch","asset":idx,
                    "expected_categories":sorted(expected),
                    "source_window":{"start":start,"end":end},
                    "message":"O quadro/trecho selecionado não tem evidência visual revisada que corresponda à frase."
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
        report.append({"scene":scene.get("paragraph",scene_no),
                       "subject":scene.get("semantic_subject") or scene.get("title"),
                       "asset_indices":ids,
                       "phrase_count":len(beats_here),
                       "status":"BLOCKED" if scene_errors else "APPROVED"})

    result={
        "status":"BLOCKED" if errors else "APPROVED",
        "policy":"STRICT_PHRASE_TO_REVIEWED_FRAME_MATCH_V2",
        "continuity_report":continuity,
        "error_count":len(errors),
        "errors":errors,
        "warning_count":0,
        "warnings":[],
        "evidence_limit":"Aprovação exige categoria visual correspondente e janela revisada rastreável; fonte oficial do mesmo jogo, isoladamente, não comprova a cena.",
        "scenes":report
    }
    Path(out_path).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if errors:
        raise RuntimeError(f"QUALITY_BLOCK: {len(errors)} divergência(s) entre fala e gameplay; render/publicação bloqueados.")


if __name__=="__main__":
    if len(sys.argv)<3:
        raise SystemExit("Uso: semantic_gate.py <plan.json> <clips.json> [out.json]")
    main(*sys.argv[1:4])
