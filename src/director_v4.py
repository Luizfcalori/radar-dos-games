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
MIN_MOVING_FOOTAGE_RATIO = 0.35
MIN_VIDEO_SCENES = 3

HOOK_TOKENS = (
    "confirm", "novo", "nova", "revel", "agora", "lanç", "data", "primeir",
    "surpresa", "mud", "cheg", "volt", "exclusiv", "grátis", "gratis",
)

SHORT_STOP = {
    "radar","games","game","battlefield","shorts","short","dos","das","de","do","da",
    "em","no","na","nos","nas","e","o","a","os","as","um","uma","para","por","com",
    "que","voce","você","vai","vem","agora","mais","sobre"
}

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

def headline_from_text(text, scene_no):
    """Fallback semântico de segurança: barras nunca podem sair como DESTAQUE X."""
    raw=str(text or "").strip()
    low=norm(raw)
    rules=[
        ("lancamento" in low and ("data" in low or re.search(r"\b20\d{2}\b",low)), "DATA DE LANÇAMENTO"),
        ("playstation" in low and "xbox" in low, "PLATAFORMAS CONFIRMADAS"),
        ("jason" in low and "lucia" in low, "JASON E LUCIA"),
        ("jason" in low and "lucia" not in low, "QUEM É JASON"),
        ("lucia" in low and "jason" not in low, "QUEM É LUCIA"),
        ("vice city" in low and "leonida" in low, "LEONIDA ALÉM DE VICE CITY"),
        ("gameplay" in low or "imagens de jogo" in low or "capturado inteiramente" in low, "GAMEPLAY E IMAGENS DE JOGO"),
        ("pre carga" in low, "PRÉ-CARGA E LANÇAMENTO"),
        ("standard" in low and "ultimate" in low, "EDIÇÕES E BÔNUS"),
        ("musica" in low or "faixas" in low, "TRILHA SONORA"),
        ("xbox cloud" in low or "cloud gaming" in low, "XBOX CLOUD: FATO OU RUMOR"),
        ("streaming" in low and "pc" in low, "STREAMING NÃO É VERSÃO DE PC"),
        ("comenta" in low or "queremos saber" in low, "SUA VEZ NO RADAR"),
    ]
    for ok,title in rules:
        if ok:return title
    first=re.split(r"[.!?]",raw,maxsplit=1)[0]
    words=[w for w in re.findall(r"[A-Za-zÀ-ÿ0-9'’-]+",first) if len(w)>2]
    title=" ".join(words[:7]).upper()[:48].rstrip(" -:|")
    return title or "CONTEXTO OFICIAL"


def role_allowed(scene, asset):
    role=str(asset.get("role") or "")
    roles=set(scene.get("allowed_roles") or [])
    prefixes=tuple(scene.get("allowed_role_prefixes") or [])
    if not roles and not prefixes:
        return True
    return role in roles or any(role.startswith(p) for p in prefixes)

def eligible(scene, assets):
    # Restrict MEDIA_FIRST_V1 scenes to the exact clip IDs approved during
    # decupagem. Different Steam clips may share a role and must not become
    # interchangeable merely because their source/type labels match.
    planned=scene.get("media_first_assets")
    if planned is not None:
        approved_ids={int(v) for v in planned}
        vals=[a for a in assets.values()
              if a.get("approved",True)
              and int(a["index"]) in approved_ids
              and role_allowed(scene,a)]
        if not vals or any(idx not in assets for idx in approved_ids):
            raise RuntimeError(f"QUALITY_BLOCK: cena {scene.get('title')} sem mídia da decupagem; fallback proibido")
        return vals
    vals=[a for a in assets.values() if a.get("approved",True) and role_allowed(scene,a)]
    if vals:
        return vals
    return [a for a in assets.values() if a.get("approved",True)]

def phrase_asset_match(phrase, asset):
    """Ground exact proper-noun media selection in official source labeling."""
    from urllib.parse import unquote, urlparse
    source=str(asset.get("source_label") or "")
    filename=unquote(urlparse(str(asset.get("url") or "")).path).rsplit("/",1)[-1]
    label_words=set(norm(source+" "+filename.replace("_"," ").replace("-"," ")).split())
    phrase_words=set(norm(phrase).split())
    stop={"arc", "raiders", "games", "gameplay", "official", "screen",
          "screenshot", "media", "image", "trailer", "frozen", "trail"}
    return len({w for w in label_words if len(w)>=4 and w not in stop} & phrase_words)


def choose(scene, assets, usage, previous, count, phrase_text=""):
    vals=eligible(scene,assets)
    preferred={int(x) for x in scene.get("preferred_media_indices") or []}
    vals.sort(key=lambda a:(
        -phrase_asset_match(phrase_text,a),
        0 if int(a["index"]) in preferred else 1,
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

def canonical_hook_tokens(text):
    """Normalize obvious Portuguese equivalents without matching game names."""
    aliases={
        "gratis":"free_trial","gratuito":"free_trial","gratuita":"free_trial",
        "gratuitamente":"free_trial","gratuidade":"free_trial",
        "congelado":"snowy","congelada":"snowy","neve":"snowy",
        "nevado":"snowy","nevada":"snowy","gelado":"snowy",
        "gelada":"snowy","frio":"snowy","fria":"snowy",
        "12":"doze",
    }
    return [aliases.get(t,t) for t in norm(text).split()]


def hook_terms(text):
    generic=SHORT_STOP | {"arc","raiders","jogo","jogos","novo","nova",
                          "novos","novas","frozen","trail","atualizacao"}
    return {token for token in canonical_hook_tokens(text)
            if len(token)>=3 and token not in generic}


def scene_short_text(scene):
    # A beat is an editorial cut, NOT a new phrase; count each sentence once.
    seen=set()
    lines=[str(scene.get("title") or ""),str(scene.get("subtitle") or "")]
    for b in scene.get("beats") or []:
        text=str(b.get("text") or "")
        key=(b.get("phrase"),text)
        if text and key not in seen:
            seen.add(key)
            lines.append(text)
    return " ".join(lines)


def hook_scene_score(hook, scene):
    hook_set=hook_terms(hook)
    scene_text=scene_short_text(scene)
    tokens=canonical_hook_tokens(scene_text)
    scene_set=set(tokens)
    overlap=sorted(hook_set & scene_set)
    # Specific terms are more valuable than common channel/game adjectives.
    counts=Counter(tokens)
    score=sum(20+min(2,counts[x]-1)*4 for x in overlap)
    first_words=set(tokens[:75])
    score+=sum(12 for x in overlap if x in first_words)
    # Substring stems help grammatical inflections only for meaningful terms.
    hook_stems={x[:6] for x in hook_set if len(x)>=6}
    scene_stems={x[:6] for x in scene_set if len(x)>=6}
    stem_overlap=sorted(hook_stems & scene_stems)
    score+=sum(2 for x in stem_overlap if not any(x==t[:6] for t in overlap))
    return score, overlap, stem_overlap


def pick_shorts_for_hooks(scenes, hooks):
    if len(hooks) != 3:
        raise RuntimeError(f"QUALITY_BLOCK: Diretor V4 exige exatamente 3 hooks aprovados; recebeu {len(hooks)}")
    def scene_duration(scene):
        return sum(float(b.get("duration") or 0) for b in (scene.get("beats") or []))
    eligible_indexes=[i for i,s in enumerate(scenes) if 8.0 <= scene_duration(s) <= 60.0]
    pool=eligible_indexes if len(eligible_indexes)>=3 else list(range(len(scenes)))
    picks=[]
    matches=[]
    for hook in hooks:
        ranked=[]
        for idx in pool:
            if idx in picks:
                continue
            score,overlap,stems=hook_scene_score(hook,scenes[idx])
            ranked.append((score,short_score(scenes[idx],idx,len(scenes)),-idx,idx,overlap,stems))
        if not ranked:
            raise RuntimeError(f"QUALITY_BLOCK: sem cena disponível para o hook aprovado: {hook}")
        ranked.sort(reverse=True)
        score,editorial_score,_,idx,overlap,stems=ranked[0]
        if score <= 0:
            raise RuntimeError(f"QUALITY_BLOCK: hook sem correspondência semântica com a narração: {hook}")
        picks.append(idx)
        matches.append({
            "hook":hook,
            "scene_index":idx,
            "scene_title":scenes[idx].get("title"),
            "semantic_score":score,
            "overlap_terms":overlap,
            "overlap_stems":stems,
            "editorial_score":editorial_score,
        })
    return picks,matches

def main(plan_path="output/auto-media-plan.json", clips_path="output/clips.json"):
    plan=load(plan_path); clips=load(clips_path); timings=load("output/voice-timings.json")
    scenes=plan.get("scenes") or []; segments=timings.get("segments") or []
    if len(scenes)!=len(segments):
        raise RuntimeError(f"QUALITY_BLOCK: V4 recebeu {len(segments)} blocos de voz para {len(scenes)} cenas")
    assets={int(a["index"]):a for a in clips.get("assets",[]) if a.get("approved",True)}
    if not assets: raise RuntimeError("QUALITY_BLOCK: V4 sem assets aprovados")

    try:
        from repetition_policy import StaticTracker, match_score, validate_master
    except ModuleNotFoundError:
        from src.repetition_policy import StaticTracker, match_score, validate_master

    generic=all(str(a.get("role") or "").startswith("official_context_") for a in assets.values())
    usage=Counter(); previous=None; scene_report=[]; phrase_total=0
    static_tracker=StaticTracker(); timeline_seconds=0.0

    for i,(scene,segment) in enumerate(zip(scenes,segments),1):
        if generic and not scene.get("allowed_roles") and not scene.get("allowed_role_prefixes"):
            scene["allowed_role_prefixes"]=["official_context_"]
        scene["semantic_subject"]=scene.get("semantic_subject") or f"scene_{i:02d}"
        current_title=str(scene.get("title") or "").strip()
        if not current_title or re.fullmatch(r"DESTAQUE\s*\d*", current_title, re.I):
            scene["title"]=headline_from_text(segment.get("text",""),i)
        if re.fullmatch(r"DESTAQUE\s*\d*", str(scene.get("title") or "").strip(), re.I):
            raise RuntimeError(f"QUALITY_BLOCK: headline genérica proibida na cena {i}: {scene.get('title')}")

        rows=phrases_for_paragraph(timings,i,segment)
        beats=[]; scene_ids=[]
        for phrase in rows:
            duration=float(phrase.get("duration") or 0)
            target=phrase_target(phrase.get("text",""))
            count=beat_count(duration,target)
            beat_duration=duration/count if count else duration
            allowed=eligible(scene,assets)
            for n in range(count):
                phrase_text=phrase.get("text","")
                # A source-specific still appears only when its labeled subject is
                # mentioned in THIS phrase; never fill generic footage with posters.
                stills=[a for a in allowed
                        if static_tracker.can_use(a,phrase_text,i,timeline_seconds,beat_duration)]
                videos=[a for a in allowed if a.get("type")=="video" and (
                    plan.get("visual_inspection_policy")!="FULL_FRAME_TECHNICAL_SCAN_V1"
                    or any(float(w["end"])-float(w["start"])>=beat_duration+.10
                           for w in (scene.get("visual_windows") or {}).get(str(a["index"]),[]))
                )]
                # Visual specificity wins once (Bully / rewards / weapon);
                # otherwise moving footage is the default. No recycled stills.
                stills.sort(key=lambda a:(-match_score(phrase_text,a),usage[int(a["index"])],
                                          int(a["index"])))
                videos.sort(key=lambda a:(int(a["index"])==previous,
                                         usage[int(a["index"])],int(a["index"])))
                if stills and (n==0 or not videos):
                    picked=stills[0]
                elif videos:
                    picked=videos[0]
                elif stills:
                    picked=stills[0]
                else:
                    raise RuntimeError(
                        f"QUALITY_BLOCK: cena {i} frase {phrase.get('sentence')} "
                        "sem mídia inédita e correspondente; pesquisar mais material")
                asset_id=int(picked["index"])
                static_tracker.record(picked,i,timeline_seconds,beat_duration)
                timeline_seconds+=beat_duration
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

    def footage_stats():
        total=0.0; moving=0.0; video_scenes=0
        for scene in scenes:
            has_video=False
            for beat in scene.get("beats") or []:
                d=float(beat.get("duration") or 0)
                total+=d
                asset=assets.get(int(beat.get("media_index") or 0),{})
                if asset.get("type")=="video":
                    moving+=d;has_video=True
            if has_video:video_scenes+=1
        return total,moving,video_scenes

    video_assets=[a for a in assets.values() if a.get("type")=="video" and a.get("approved",True)]
    if not video_assets:
        raise RuntimeError("QUALITY_BLOCK: Master sem gameplay/vídeo oficial em movimento")

    # Cada cena que aceita vídeo recebe pelo menos um beat em movimento.
    for scene in scenes:
        vids=[a for a in eligible(scene,assets) if a.get("type")=="video"]
        beats=scene.get("beats") or []
        if vids and beats and not any(assets.get(int(b.get("media_index") or 0),{}).get("type")=="video" for b in beats):
            pick=min(vids,key=lambda a:(usage[int(a["index"])],int(a["index"])))
            beats[0]["media_index"]=int(pick["index"]);usage[int(pick["index"])]+=1

    # Se ainda houver pouca gameplay/footage, converte beats de imagem permitidos
    # até atingir o piso editorial do Radar.
    total,moving,video_scenes=footage_stats()
    target=total*MIN_MOVING_FOOTAGE_RATIO
    if moving<target:
        for scene in scenes:
            vids=[a for a in eligible(scene,assets) if a.get("type")=="video"]
            if not vids:continue
            for beat in scene.get("beats") or []:
                if moving>=target:break
                old=assets.get(int(beat.get("media_index") or 0),{})
                if old.get("type")=="video":continue
                pick=min(vids,key=lambda a:(usage[int(a["index"])],int(a["index"])))
                beat["media_index"]=int(pick["index"]);usage[int(pick["index"])]+=1
                moving+=float(beat.get("duration") or 0)
            if moving>=target:break

    # Bind every video beat to an actual non-black timeline window.
    # This runs AFTER footage-ratio adjustments so those substitutions are
    # subject to the same restrictions as the director's original selections.
    source_usage=Counter()
    for scene in scenes:
        windows_by_id=scene.get("visual_windows") or {}
        for beat in scene.get("beats") or []:
            idx=int(beat["media_index"])
            if assets.get(idx, {}).get("type") != "video":
                continue
            if plan.get("visual_inspection_policy") != "FULL_FRAME_TECHNICAL_SCAN_V1":
                continue
            windows=[w for w in windows_by_id.get(str(idx), [])
                     if float(w["end"])-float(w["start"]) >= float(beat["duration"])+0.10]
            if not windows:
                raise RuntimeError(f"QUALITY_BLOCK: vídeo {idx} sem janela limpa para beat de {beat['duration']}s")
            window=windows[source_usage[idx] % len(windows)]
            source_usage[idx]+=1
            beat["source_window"]={"start":float(window["start"]), "end":float(window["end"])}
        scene["media_indices"]=list(dict.fromkeys(int(b["media_index"]) for b in (scene.get("beats") or [])))

    # Fail before rendering costly footage if substitutions reintroduced
    # repeated stills or captions unrelated to the narration.
    repetition_qa=validate_master(scenes,assets)

    total,moving,video_scenes=footage_stats()
    moving_ratio=(moving/total) if total else 0.0
    if moving_ratio+1e-9<MIN_MOVING_FOOTAGE_RATIO:
        raise RuntimeError(f"QUALITY_BLOCK: gameplay/footage em movimento {moving_ratio:.1%}; mínimo {MIN_MOVING_FOOTAGE_RATIO:.0%}")
    if video_scenes<min(MIN_VIDEO_SCENES,len(scenes)):
        raise RuntimeError(f"QUALITY_BLOCK: gameplay presente em somente {video_scenes} cenas")

    scene_report=[]
    for i,scene in enumerate(scenes,1):
        beats=scene.get("beats") or []
        scene_report.append({
            "scene":i,
            "title":scene.get("title"),
            "phrases":len({int(b.get("phrase") or 1) for b in beats}),
            "beats":len(beats),
            "media_indices":scene.get("media_indices") or [],
            "video_beats":sum(1 for b in beats if assets.get(int(b.get("media_index") or 0),{}).get("type")=="video"),
            "avg_beat_seconds":round(sum(float(b.get("duration") or 0) for b in beats)/max(1,len(beats)),3),
        })

    hooks=[str(x or "").strip() for x in (plan.get("short_hooks") or []) if str(x or "").strip()]
    picks,short_matches=pick_shorts_for_hooks(scenes,hooks)

    plan["premium_version"]="PREMIUM_V4_DIRECTOR_CUT"
    plan["director_policy"]="phrase_level_semantic_direction; variable_pacing; selective_keyword_overlays; independent_shorts; pro_score_gate"
    Path(plan_path).write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf-8")

    Path("output/short-picks.json").write_text(json.dumps({
        "version":"PREMIUM_V4_DIRECTOR_CUT",
        "scene_indexes":picks,
        "expected_hooks":hooks,
        "semantic_matches":short_matches,
        "selection_policy":"exact_approved_hook_to_semantically_matching_scene; unique_scenes; block_zero_overlap",
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
        "short_hooks":hooks,
        "short_semantic_matches":short_matches,
        "asset_usage":{str(k):v for k,v in sorted(usage.items())},
        "moving_footage_seconds":round(moving,3),
        "body_seconds":round(total,3),
        "moving_footage_ratio":round(moving_ratio,4),
        "video_scenes":video_scenes,
        "headline_policy":"semantic_real_headline_no_DESTAQUE_X",
        "gameplay_policy":"official_video_required; moving_footage_ratio_gte_35pct",
        "scenes":scene_report,
    }
    Path("output/anti-repetition-director.json").write_text(
        json.dumps(repetition_qa,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    Path("output/director-v4.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    args=sys.argv[1:]
    main(*(args[:2]))
