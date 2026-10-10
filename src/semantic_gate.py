#!/usr/bin/env python3
"""Gate semântico global: a mídia de cada cena deve corresponder ao assunto narrado."""
import json, sys
from pathlib import Path

def main(plan_path, clips_path, out_path="output/semantic-visual-qa.json"):
    plan=json.loads(Path(plan_path).read_text(encoding="utf-8"))
    clips=json.loads(Path(clips_path).read_text(encoding="utf-8"))
    assets={int(a["index"]):a for a in clips.get("assets",[]) if a.get("approved")}
    report=[]
    try:
        from continuity import validate_video_beats
        from vision_semantics import scene_categories
    except ModuleNotFoundError:
        from src.continuity import validate_video_beats
        from src.vision_semantics import scene_categories
    if plan.get("continuity_policy"):
        validate_video_beats([b for s in plan.get("scenes",[]) for b in s.get("beats",[])],assets)

    for scene in plan.get("scenes",[]):
        subject=(scene.get("semantic_subject") or "").strip()
        if not subject:
            raise RuntimeError(f"QUALITY_BLOCK: cena {scene.get('paragraph')} sem semantic_subject")
        ids=[int(x) for x in scene.get("media_indices",[])]
        if not ids:
            raise RuntimeError(f"QUALITY_BLOCK: cena {scene.get('paragraph')} sem media_indices")
        if plan.get("media_first_policy")=="MEDIA_FIRST_V1":
            allowed={int(x) for x in scene.get("media_first_assets",[])}
            if not allowed or not set(ids).issubset(allowed):
                raise RuntimeError(f"QUALITY_BLOCK: cena fora da decupagem: {scene.get('paragraph')}")
            for beat in scene.get("beats") or []:
                if int(beat["media_index"]) not in allowed:
                    raise RuntimeError("QUALITY_BLOCK: frase com vídeo diferente da decupagem")
        if plan.get("continuity_policy"):
            for beat in scene.get("beats",[]):
                idx=int(beat["media_index"])
                if assets[idx].get("type")!="video":continue
                selected_window=beat["source_window"]
                expected=set(scene_categories(beat.get("text","")))
                requirements=(scene.get("phrase_subjects") or {}).get(str(beat.get("phrase",1)),[])
                windows=[w for w in scene.get("visual_windows",{}).get(str(idx),[])
                         if float(w["start"])<=float(selected_window["start"])+0.002
                         and float(w["end"])+0.002>=float(selected_window["end"])]
                verified_context=set(scene.get("verified_source_fallback_categories") or ())
                valid=[w for w in windows if "title_card" not in w.get("semantic_categories",[])
                       and (not expected or expected & set(w.get("semantic_categories",[]))
                            or verified_context & set(w.get("semantic_categories",[])))
                       and (not requirements or (w.get("reviewed") is True and w.get("evidence")
                            and set(requirements)<=set(w.get("subjects",[]))))]
                if not valid:raise RuntimeError("QUALITY_BLOCK: fala sem evidência visual no intervalo escolhido")
        selected=[]
        for idx in ids:
            if idx not in assets:
                raise RuntimeError(f"QUALITY_BLOCK: cena {scene.get('paragraph')} aponta para asset ausente {idx}")
            selected.append(assets[idx])

        allowed_roles=set(scene.get("allowed_roles") or [])
        allowed_prefixes=tuple(scene.get("allowed_role_prefixes") or [])
        roles=[a.get("role","") for a in selected]
        for role in roles:
            ok=(not allowed_roles and not allowed_prefixes) or role in allowed_roles or any(role.startswith(p) for p in allowed_prefixes)
            if not ok:
                raise RuntimeError(
                    f"QUALITY_BLOCK: cena {scene.get('paragraph')} ({subject}) recebeu mídia errada: {role}; "
                    f"allowed_roles={sorted(allowed_roles)} allowed_prefixes={allowed_prefixes}"
                )
        report.append({
            "paragraph":scene.get("paragraph"),
            "subject":subject,
            "roles":roles,
            "asset_indices":ids,
            "status":"APPROVED"
        })

    result={
        "status":"APPROVED",
        "policy":"EVERY_SCENE_MUST_MATCH_NARRATION_SUBJECT",
        "continuity_policy":plan.get("continuity_policy"),
        "evidence_limit":"Broad category classification is a suggestion; exact object names need reviewed shot evidence",
        "scenes":report
    }
    Path(out_path).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    if len(sys.argv)<3:
        raise SystemExit("Uso: semantic_gate.py <plan.json> <clips.json> [out.json]")
    main(*sys.argv[1:4])
