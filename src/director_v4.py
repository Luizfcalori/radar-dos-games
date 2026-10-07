#!/usr/bin/env python3
"""Radar dos Games Premium V4 — Director Cut.

Direção por frase sobre a base semântica do V3:
- preserva papéis/roles explícitos de fluxos STRICT;
- cada sentença recebe um ou mais beats visuais;
- ritmo varia com o conteúdo (impacto mais rápido, explicação respira);
- evita repetir o primeiro asset entre frases quando existe alternativa;
- produz mapa para Shorts independentes; o Master sempre começa pela intro oficial completa.
"""
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

MIN_BEAT = 1.65
NORMAL_TARGET = 3.6
CALM_TARGET = 4.7
HOOK_TARGET = 2.25
MAX_BEAT = 5.8
MAX_ASSETS_PER_SCENE = 5

HOOK_TOKENS = (
    "confirm", "novo", "nova", "revel", "agora", "lanç", "data", "primeir",
    "surpresa", "mud", "cheg", "volt", "exclusiv", "grátis", "gratis",
)

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def norm(text):
    value=unicodedata.normalize("NFKD", str(text or ""))
    value="".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9 ]+", " ", value.lower())

def intensity(text):
    low=norm(text)
    hits=sum(1 for x in HOOK_TOKENS if x in low)
    if "!" in str(text) or "?" in str(text):
        hits+=1
    if re.search(r"\b\d{4}\b|\b\d+[%xX]\b", str(text)):
        hits+=1
    return min(4,hits)

def keyword_overlay(text):
    raw=str(text or "")
    candidates=[]
    for pat in (
        r"\b(?:20\d{2}|\d{1,3}%|\d+[xX])\b",
        r"\b(?:CONFIRMAD[OA]S?|NOV[OA]S?|LANÇAMENTO|GAMEPLAY|TRAILER|GRÁTIS|DATA|AGORA)\b",
    ):
        candidates += re.findall(pat, raw, re.I)
    if candidates:
        return candidates[0].upper()
    words=[w for w in re.findall(r"[A-Za-zÀ-ÿ0-9'-]+", raw) if len(w)>=6]
    return (words[0].upper() if words else "")[:24]

def role_allowed(scene, asset):
    role=str(asset.get("role") or "")
    roles=set(scene.get("allowed_roles") or [])
    prefixes=tuple(scene.get("allowed_role_prefixes") or [])
    if not roles and not prefixes:
        return True
    return role in roles or any(role.startswith(p) for p in prefixes)

def eligible(scene, assets):
    vals=[a for a in assets.values() if a.get("approved",True) and role_allowed(scene,a)]
    if vals:
        return vals
    return [a for a in assets.values() if a.get("approved",True)]

def choose(scene, assets, usage, previous, count):
    vals=eligible(scene,assets)
    vals.sort(key=lambda a:(
        0 if a.get("type")=="video" else 1,
        usage[int(a["index"])],
        int(a["index"]),
    ))
    ids=[int(a["index"]) for a in vals]
    if previous in ids and len(ids)>1 and ids[0]==previous:
        ids=ids[1:]+ids[:1]
    result=[]
    for idx in ids:
        if idx not in result:
            result.append(idx)
        if len(result)>=max(1,count):
            break
    return result

def phrase_target(text):
    level=intensity(text)
    if level>=2:
        return HOOK_TARGET
    if len(str(text).split())>=22:
        return CALM_TARGET
    return NORMAL_TARGET

def beat_count(duration, target):
    d=max(.1,float(duration))
    if d<=MAX_BEAT:
        return 1
    desired=max(1,round(d/target))
    minimum=max(1,math.ceil(d/MAX_BEAT))
    maximum=max(minimum,math.floor(d/MIN_BEAT))
    return max(minimum,min(6,maximum,desired))

def phrases_for_paragraph(timings, paragraph, segment):
    rows=[p for p in timings.get("phrases",[]) if int(p.get("paragraph",0))==paragraph]
    if rows:
        return rows
    return [{
        "paragraph":paragraph,"sentence":1,
        "start":segment.get("start",0),"end":segment.get("end",0),
        "duration":segment.get("duration",0),"text":segment.get("text",""),
    }]

def short_score(scene, index, total):
    score=intensity(f"{scene.get('title','')} {scene.get('subtitle','')}")*5
    beats=scene.get("beats") or []
    score+=sum(intensity(b.get("text","")) for b in beats)*2
    score+=min(5,len(beats))
    if index==0: score+=5
    if index==total-1: score+=2
    return score

def pick_shorts(scenes):
    def scene_duration(scene):
        return sum(float(b.get("duration") or 0) for b in (scene.get("beats") or []))
    eligible_indexes=[i for i,s in enumerate(scenes) if 8.0 <= scene_duration(s) <= 60.0]
    pool=eligible_indexes if len(eligible_indexes)>=3 else list(range(len(scenes)))
    ranked=sorted(pool,key=lambda i:(-short_score(scenes[i],i,len(scenes)),i))
    picks=[]
    for idx in ranked:
        if all(abs(idx-old)>=2 for old in picks) or len(scenes)<5:
            picks.append(idx)
        if len(picks)==3: break
    for idx in range(len(scenes)):
        if idx not in picks:picks.append(idx)
        if len(picks)==3:break
    return (picks+[0,0,0])[:3]

def main(plan_path="output/auto-media-plan.json", clips_path="output/clips.json"):
    plan=load(plan_path); clips=load(clips_path); timings=load("output/voice-timings.json")
    scenes=plan.get("scenes") or []; segments=timings.get("segments") or []
    if len(scenes)!=len(segments):
        raise RuntimeError(f"QUALITY_BLOCK: V4 recebeu {len(segments)} blocos de voz para {len(scenes)} cenas")
    assets={int(a["index"]):a for a in clips.get("assets",[]) if a.get("approved",True)}
    if not assets: raise RuntimeError("QUALITY_BLOCK: V4 sem assets aprovados")

    generic=all(str(a.get("role") or "").startswith("official_context_") for a in assets.values())
    usage=Counter(); previous=None; scene_report=[]; phrase_total=0

    for i,(scene,segment) in enumerate(zip(scenes,segments),1):
        if generic and not scene.get("allowed_roles") and not scene.get("allowed_role_prefixes"):
            scene["allowed_role_prefixes"]=["official_context_"]
        scene["semantic_subject"]=scene.get("semantic_subject") or f"scene_{i:02d}"

        rows=phrases_for_paragraph(timings,i,segment)
        beats=[]; scene_ids=[]
        for phrase in rows:
            duration=float(phrase.get("duration") or 0)
            target=phrase_target(phrase.get("text",""))
            count=beat_count(duration,target)
            ids=choose(scene,assets,usage,previous,min(MAX_ASSETS_PER_SCENE,max(1,count)))
            if not ids: raise RuntimeError(f"QUALITY_BLOCK: V4 cena {i} frase {phrase.get('sentence')} sem mídia")
            beat_duration=duration/count if count else duration
            for n in range(count):
                asset_id=ids[n%len(ids)]
                beats.append({
                    "phrase":int(phrase.get("sentence") or 1),
                    "text":phrase.get("text",""),
                    "start":round(float(phrase.get("start") or 0)+(beat_duration*n),3),
                    "end":round(float(phrase.get("start") or 0)+(beat_duration*(n+1)),3),
                    "duration":round(beat_duration,3),
                    "media_index":asset_id,
                    "transition":"hard_cut" if n else ("micro_dip" if i>1 else "opening_after_full_intro"),
                    "keyword_overlay":keyword_overlay(phrase.get("text","")) if n==0 and intensity(phrase.get("text",""))>=1 else "",
                    "intensity":intensity(phrase.get("text","")),
                })
                scene_ids.append(asset_id); usage[asset_id]+=1; previous=asset_id

        scene["media_indices"]=list(dict.fromkeys(scene_ids))
        scene["beats"]=beats
        scene["editing"]={
            "version":"PREMIUM_V4_DIRECTOR_CUT",
            "phrase_level":True,
            "variable_pacing":True,
            "card_once_per_scene":True,
            "motion_profile":"subtle_non_destructive",
            "transition_policy":"hard_cut_inside_subject; micro_dip_on_scene_change",
        }
        phrase_total+=len(rows)
        scene_report.append({
            "scene":i,"phrases":len(rows),"beats":len(beats),
            "media_indices":scene["media_indices"],
            "avg_beat_seconds":round(sum(float(b["duration"]) for b in beats)/max(1,len(beats)),3),
        })

    picks=pick_shorts(scenes)

    plan["premium_version"]="PREMIUM_V4_DIRECTOR_CUT"
    plan["director_policy"]="phrase_level_semantic_direction; variable_pacing; selective_keyword_overlays; independent_shorts; pro_score_gate"
    Path(plan_path).write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf-8")

    Path("output/short-picks.json").write_text(json.dumps({
        "version":"PREMIUM_V4_DIRECTOR_CUT","scene_indexes":picks
    },ensure_ascii=False,indent=2),encoding="utf-8")

    manifest={
        "premium_version":"PREMIUM_V4_DIRECTOR_CUT",
        "assets":list(assets.values()),
        "voice":"output/voice.mp3",
        "voice_timings":"output/voice-timings.json",
        "intro":"radar-dos-games-intro-oficial.mp4",
        "intro_policy":"full_intro_first",
        "cold_open_seconds":0.0,
        "scenes":scenes,
        "output":"output/master.mp4",
    }
    Path("output/render.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

    result={
        "status":"APPROVED","version":"PREMIUM_V4_DIRECTOR_CUT",
        "phrase_count":phrase_total,
        "intro_policy":"full_intro_first",
        "cold_open_seconds":0.0,
        "short_scene_indexes":picks,
        "asset_usage":{str(k):v for k,v in sorted(usage.items())},
        "scenes":scene_report,
    }
    Path("output/director-v4.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    args=sys.argv[1:]
    main(*(args[:2]))
