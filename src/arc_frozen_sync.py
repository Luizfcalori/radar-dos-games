#!/usr/bin/env python3
"""Curadoria por frase exclusiva de ARC Raiders: Frozen Trail; demais pautas inalteradas."""
from collections import defaultdict
import json
from pathlib import Path

TITLES = [
    "FROZEN TRAIL 2.0 JÁ DISPONÍVEL",
    "TESTE GRATUITO: 8 A 12 DE OUTUBRO",
    "NOVO MAPA: PENDOLA PASS",
    "NEVASCA, EMPEROR E EXTRAÇÃO",
    "A FRIGATE E O NOVO DESAFIO",
    "NOVOS INIMIGOS: BULLY, SKULKER E HYDRA",
    "NOVAS ARMAS: STILETTO E BANTAM",
    "GADGETS: GRAPPLING HOOK E TETHER",
    "OUTPOST E ARMAS AMPLIFICADAS",
    "ÁRVORE DE HABILIDADES REFORMULADA",
    "REWARD PASS E RECOMPENSAS",
    "MUDANÇAS DE COMBATE E MATCHMAKING",
    "A NOVA FRONTEIRA CONGELADA",
    "QUAL NOVIDADE VOCÊ VAI EXPLORAR?"
]
TOKENS = {
    "map": ("2-1-1024x576",),
    "bully": ("ar_bumper_arc_bully",),
    "skulker": ("ar_bumper_arc_skulker",),
    "hydra": ("ar_bumper_arc_hydra",),
    "outpost": ("ar_bumper_location_outposts",),
    "amplified": ("ar_bumper_amplified-weapons",),
    "stiletto": ("ar_bumper_weapon_stiletto",),
    "bantam": ("ar_bumper_weapon_bantam",),
    "grapple": ("ar_bumper_gadgets_grapplinghook",),
    "tether": ("ar_bumper_gadgets_tetherlauncher",),
    "harmonica": ("ar_bumper_instrument_harmonica",),
}
# Restringe a seleção de cada cena ao seu tema.
SCENE_CHOICES = {
    1: ("video",), 2: ("video",), 3: ("map","video"),
    4: ("video","map"), 5: ("video",),
    6: ("bully","skulker","hydra"),
    7: ("stiletto","bantam"),
    8: ("grapple","tether","harmonica"),
    9: ("outpost","amplified"),
    10: ("video",), 11: ("video",), 12: ("video",),
    13: ("video","map"), 14: ("video",)
}
MATCHES = {
    "bully": ("bully",), "skulker": ("skulker",),
    "hydra": ("hydra",), "stiletto": ("stiletto",),
    "bantam": ("bantam",), "outpost": ("outpost",),
    "amplified weapons": ("amplified",),
    "grappling hook": ("grapple",),
    "tether launcher": ("tether",),
    "gaita": ("harmonica",), "harmonica": ("harmonica",),
    "pendola pass": ("map",)
}

def curate(scenes, assets):
    if len(scenes)!=len(TITLES):
        raise RuntimeError("QUALITY_BLOCK: Frozen Trail exige 14 blocos de narração")
    available={"video": sorted(
        (a for a in assets.values() if a.get("type")=="video"),
        key=lambda a:int(a["index"]))}
    for key,tokens in TOKENS.items():
        available[key]=[a for a in assets.values()
            if a.get("type")=="image" and any(
                token in str(a.get("url","")).lower() for token in tokens)]
    required=("map","bully","skulker","hydra","stiletto","bantam","grapple","tether","outpost","amplified")
    for key in required:
        if not available.get(key):
            raise RuntimeError(f"QUALITY_BLOCK: Frozen Trail sem imagem oficial de {key}")
    if not available["video"]:
        raise RuntimeError("QUALITY_BLOCK: Frozen Trail sem vídeo oficial")
    qa=[]
    for scene_no,scene in enumerate(scenes,1):
        scene["title"]=TITLES[scene_no-1]
        scene["semantic_subject"]=f"arc_frozen_trail_{scene_no:02d}"
        options=SCENE_CHOICES[scene_no]
        grouped=defaultdict(list)
        for beat in scene.get("beats") or []:
            grouped[int(beat.get("phrase") or 1)].append(beat)
        updated=[]
        for phrase_no,old_beats in sorted(grouped.items()):
            text=str(old_beats[0].get("text") or "")
            low=text.casefold()
            named=[]
            for phrase,keys in MATCHES.items():
                if phrase in low:
                    for key in keys:
                        if key in options and key not in named:
                            named.append(key)
            if named and scene_no in (6,7,8,9):
                choices=named
            else:
                choices=list(options)
                if scene_no in (3,4,13) and phrase_no%2==0:
                    choices.reverse()
            count=max(len(old_beats),len(named)) if named and scene_no in (6,7,8,9) else len(old_beats)
            duration=sum(float(b.get("duration") or 0) for b in old_beats)
            if duration<=0:raise RuntimeError("QUALITY_BLOCK: frase sem duração")
            start=float(old_beats[0].get("start") or 0)
            for idx in range(count):
                key=choices[idx%len(choices)]
                pool=available.get(key) or []
                if not pool:raise RuntimeError(f"QUALITY_BLOCK: mídia exata não disponível: {key}")
                asset=pool[idx%len(pool)]
                d=duration/count
                beat=dict(old_beats[min(idx,len(old_beats)-1)])
                beat.update(
                    start=round(start+idx*d,3),
                    end=round(start+(idx+1)*d,3),
                    duration=round(d,3),
                    media_index=int(asset["index"]),
                    semantic_asset_label=key,
                    text=text
                )
                if idx>0:beat["keyword_overlay"]=""
                updated.append(beat)
                qa.append({"scene":scene_no,"phrase":phrase_no,
                    "role":key,"asset_index":int(asset["index"]),
                    "source":asset.get("url"),"text":text[:120]})
        scene["beats"]=updated
        scene["media_indices"]=list(dict.fromkeys(x["media_index"] for x in updated))
        scene["allowed_roles"]=list(dict.fromkeys(assets[i]["role"] for i in scene["media_indices"]))
        scene.pop("allowed_role_prefixes",None)
        if not updated:raise RuntimeError(f"QUALITY_BLOCK: cena {scene_no} sem cortes")
    for scene_no,allowed in ((2,{"video"}),(3,{"map","video"}),(6,{"bully","skulker","hydra"}),(7,{"stiletto","bantam"})):
        observed={b["semantic_asset_label"] for b in scenes[scene_no-1]["beats"]}
        if not observed<=allowed:
            raise RuntimeError(f"QUALITY_BLOCK: material incorreto na cena {scene_no}: {observed-allowed}")
    for key in ("bully","skulker","hydra"):
        if not any(b["semantic_asset_label"]==key for b in scenes[5]["beats"]):
            raise RuntimeError(f"QUALITY_BLOCK: inimigo {key} ausente do Short 3")
    Path("output/arc-visual-sync-qa.json").write_text(json.dumps({
        "status":"APPROVED",
        "scope":"ARC RAIDERS FROZEN TRAIL ONLY",
        "policy":"named_asset_per_sentence; topic_locked_scenes; fail_closed",
        "beats":qa
    },ensure_ascii=False,indent=2),encoding="utf-8")
