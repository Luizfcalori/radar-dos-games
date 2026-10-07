#!/usr/bin/env python3
"""PRO_SCORE objetivo do Radar dos Games. Bloqueia liberação abaixo de 85/100."""
import json
from pathlib import Path

THRESHOLD=85

def load(path):
    p=Path(path)
    if not p.exists():return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    semantic=load("output/semantic-visual-qa.json")
    v4=load("output/premium-v4-qa.json")
    render=load("output/qa.json")
    shorts=load("output/shorts/manifest.json")
    frames=load("output/visual-frame-qa.json")
    covers=load("output/cover-qa.json")

    components={}
    components["semantic"]=25 if semantic.get("status")=="APPROVED" else 0
    components["direction_and_pacing"]=20 if v4.get("status")=="APPROVED" else 0

    sound=render.get("sound_design") or {}
    sound_score=0
    if sound.get("voice_chain")=="compression+loudnorm+limiter":sound_score+=9
    if sound.get("editorial_sfx")=="subtle_generated_impacts":sound_score+=4
    if int(sound.get("sfx_events") or 0)>0:sound_score+=2
    components["audio"]=min(15,sound_score)

    rows=shorts.get("shorts") or []
    independent=len(rows)==3 and all(r.get("render_policy")=="rebuilt_from_source_assets_not_master_crop" for r in rows)
    components["shorts"]=15 if independent else (8 if len(rows)==3 else 0)

    components["visual_frames"]=10 if frames.get("status")=="APPROVED" else 0
    cover_ok=covers.get("premium_cover_qa")=="APPROVED"
    fallback=bool(covers.get("fallback_used"))
    components["covers"]=10 if cover_ok and not fallback else (7 if cover_ok else 0)
    components["voice_identity"]=5 if render.get("voice")=="pt-BR-ThalitaMultilingualNeural" else 0

    total=sum(components.values())
    recommendations=[]
    if components["semantic"]<25:recommendations.append("refazer mapeamento fala-imagem")
    if components["direction_and_pacing"]<20:recommendations.append("refazer direção/cadência")
    if components["audio"]<13:recommendations.append("revisar sound design/masterização")
    if components["shorts"]<15:recommendations.append("reconstruir Shorts independentes")
    if components["visual_frames"]<10:recommendations.append("revisar frames sinalizados")
    if components["covers"]<10:recommendations.append("regenerar capas sem fallback")

    result={
        "status":"APPROVED" if total>=THRESHOLD else "BLOCKED",
        "pro_score":total,"threshold":THRESHOLD,
        "components":components,"recommendations":recommendations,
        "policy":"publish_only_if_pro_score_gte_85",
    }
    Path("output/pro-score.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if total<THRESHOLD:raise RuntimeError(f"QUALITY_BLOCK: PRO_SCORE {total}/{THRESHOLD}")

if __name__=="__main__":main()
