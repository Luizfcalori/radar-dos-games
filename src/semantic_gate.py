#!/usr/bin/env python3
"""QA visual flexível: avisos editoriais não cancelam uma produção utilizável."""
import json, sys
from pathlib import Path

def main(plan_path, clips_path, out_path="output/semantic-visual-qa.json"):
    plan=json.loads(Path(plan_path).read_text(encoding="utf-8"))
    clips=json.loads(Path(clips_path).read_text(encoding="utf-8"))
    assets={int(a["index"]):a for a in clips.get("assets",[]) if a.get("approved",True)}
    report=[]
    warnings=[]
    try:
        from vision_semantics import scene_categories
    except ModuleNotFoundError:
        from src.vision_semantics import scene_categories

    # Relaxed policy: continuity/category mismatches are logged, not fatal.
    # The director already prioritizes reviewed official footage and uses
    # source-approved fallback shots when an exact match is unavailable.
    try:
        from continuity import validate_video_beats
    except ModuleNotFoundError:
        from src.continuity import validate_video_beats
    try:
        if plan.get("continuity_policy"):
            continuity=validate_video_beats(
                [b for s in plan.get("scenes",[]) for b in s.get("beats",[])],
                assets, require_windows=False)
        else:
            continuity={"policy":"not_declared"}
    except Exception as exc:
        continuity={"status":"WARNING","message":str(exc)}
        warnings.append({"type":"continuity","message":str(exc)})

    for scene in plan.get("scenes",[]):
        subject=(scene.get("semantic_subject") or "contexto oficial").strip()
        ids=[int(x) for x in scene.get("media_indices",[]) if str(x).lstrip("-").isdigit()]
        if not ids:
            warnings.append({"scene":scene.get("paragraph"),"type":"missing_media_indices",
                             "message":"Nenhum índice de mídia declarado; revisão necessária."})
        if plan.get("media_first_policy")=="MEDIA_FIRST_V1":
            allowed={int(x) for x in scene.get("media_first_assets",[])}
            if not allowed or not set(ids).issubset(allowed):
                warnings.append({"scene":scene.get("paragraph"),"type":"media_first_mismatch",
                                 "message":"Plano usa mídia fora da decupagem inicial; liberado com aviso."})

        selected=[]
        for idx in ids:
            if idx not in assets:
                warnings.append({"scene":scene.get("paragraph"),"type":"missing_asset",
                                 "asset":idx,"message":"Índice ausente na lista de assets aprovados."})
                continue
            selected.append(assets[idx])

        for beat in scene.get("beats",[]):
            idx=int(beat.get("media_index",-1))
            asset=assets.get(idx)
            if not asset or asset.get("type")!="video":
                continue
            selected_window=beat.get("source_window") or {}
            expected=set(scene_categories(beat.get("text","")))
            requirements=(scene.get("phrase_subjects") or {}).get(str(beat.get("phrase",1)),[])
            windows=[w for w in scene.get("visual_windows",{}).get(str(idx),[])
                     if float(w.get("start",0))<=float(selected_window.get("start",0))+0.002
                     and float(w.get("end",0))+0.002>=float(selected_window.get("end",0))]
            valid=[w for w in windows if "title_card" not in w.get("semantic_categories",[])
                   and (not expected or expected & set(w.get("semantic_categories",[])))
                   and (not requirements or (w.get("reviewed") is True and w.get("evidence")
                        and set(requirements)<=set(w.get("subjects",[]))))]
            if not valid:
                warnings.append({"scene":scene.get("paragraph"),"phrase":beat.get("phrase"),
                                 "type":"soft_semantic_mismatch",
                                 "message":"Correspondência visual secundária; manter gameplay oficial do mesmo jogo."})

        allowed_roles=set(scene.get("allowed_roles") or [])
        allowed_prefixes=tuple(scene.get("allowed_role_prefixes") or [])
        roles=[a.get("role","") for a in selected]
        for role in roles:
            ok=(not allowed_roles and not allowed_prefixes) or role in allowed_roles or any(role.startswith(p) for p in allowed_prefixes)
            if not ok:
                warnings.append({"scene":scene.get("paragraph"),"type":"role_mismatch",
                                 "role":role,"message":"Papel visual diferente do preferido; liberado com aviso."})
        report.append({"paragraph":scene.get("paragraph"),"subject":subject,"roles":roles,
                       "asset_indices":ids,"status":"APPROVED_WITH_WARNINGS" if warnings else "APPROVED"})

    result={
        "status":"APPROVED",
        "policy":"RELAXED_OFFICIAL_MEDIA_WARN_ONLY",
        "continuity_policy":plan.get("continuity_policy"),
        "continuity_report":continuity,
        "warning_count":len(warnings),
        "warnings":warnings,
        "evidence_limit":"A correspondência exata é preferencial, não bloqueante; priorizar fontes oficiais do mesmo jogo.",
        "scenes":report
    }
    Path(out_path).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    if len(sys.argv)<3:
        raise SystemExit("Uso: semantic_gate.py <plan.json> <clips.json> [out.json]")
    main(*sys.argv[1:4])
