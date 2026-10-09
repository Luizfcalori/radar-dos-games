#!/usr/bin/env python3
"""Fail-closed editorial anti-repetition policy for Radar Premium V4.

Check actual beat timelines, never merely metadata flags. Generic footage is
not evidence for an unrelated named subject. Preserve the approved visual style.
"""
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

MAX_STATIC_USES_MASTER=2
MAX_CURATED_STATIC_USES_MASTER=1
MAX_STATIC_TOTAL_SECONDS_MASTER=8.0
MAX_STATIC_BEAT_SECONDS=3.5
MAX_STATIC_USES_SHORT=1
MAX_STATIC_TOTAL_SECONDS_SHORT=3.5
STATIC_COOLDOWN_SCENES=3
STATIC_COOLDOWN_SECONDS=25.0
STOP={"arc","raiders","game","games","jogo","jogos","radar","dos","das","uma",
      "para","with","the","from","official","oficial","screen","screenshot",
      "image","images","media","frame","frozen","trail","update","novo",
      "nova","news","2026","16x9","1024x576","jpg","jpeg","png","webp",
      "gameplay","trailer","raider","raid","raiders","imagem","foto","shot",
      "pass","passe","passes","premium"}
ALIASES={
    "recompensas":"reward","recompensa":"reward","premios":"reward",
    "recompensar":"reward","premio":"reward","passes":"pass","passe":"pass",
    "visuais":"outfit","visual":"outfit","trajes":"outfit","traje":"outfit",
    "roupas":"outfit","roupa":"outfit","cosmeticos":"outfit","cosmetico":"outfit",
    "armas":"weapon","arma":"weapon","revolver":"weapon","fuzil":"weapon",
    "armamento":"weapon","weapon":"weapon","weapons":"weapon",
    "maquinas":"enemy","maquina":"enemy","inimigos":"enemy","inimigo":"enemy",
    "enemies":"enemy","enemy":"enemy",
    "neve":"snow","congelado":"snow","congelada":"snow","gelado":"snow",
    "frio":"snow","nevado":"snow","montanhas":"snow","snowy":"snow",
    "habilidades":"skill","habilidade":"skill","arvore":"skill",
    "movimentacao":"grappling","gancho":"grappling","corda":"grappling",
    "ganchos":"grappling","mobilidade":"grappling",
}
SPECIAL_NAMES={"bully","skulker","hydra","stiletto","bantam","frigate",
               "pendola","grappling","outpost","reward","tether"}


def tokens(s):
    n=unicodedata.normalize("NFKD",str(s or "").lower())
    n="".join(c for c in n if not unicodedata.combining(c))
    words=re.findall(r"[a-z][a-z0-9]{2,}",n)
    return {ALIASES.get(t,t) for t in words if t not in STOP}


def subject_label(asset):
    name=unquote(urlparse(str(asset.get("url") or "")).path).rsplit("/",1)[-1]
    name=re.sub(r"[_-](?:16x9|1024x576|600x200|500kb)\b"," ",name,flags=re.I)
    return str(asset.get("source_label") or "")+" "+name.replace("_"," ").replace("-"," ")


def match_score(phrase,asset):
    """Source labels are hints; exact named identities get priority."""
    if asset.get("type")!="image":
        return 0
    label=tokens(subject_label(asset))
    spoken=tokens(phrase)
    overlap=label & spoken
    named=overlap & SPECIAL_NAMES
    return len(named)*10+len(overlap)


def subject_ok(phrase,asset):
    """Never approve an unmatched official still just because it has game name."""
    return match_score(phrase,asset)>0


def static_limit(asset):
    if str(asset.get("role") or "").startswith("official_subject_reference_"):
        return MAX_CURATED_STATIC_USES_MASTER
    return MAX_STATIC_USES_MASTER


def asset_identity(asset):
    """Deduplicate downloaded aliases of the same picture."""
    path=Path(str(asset.get("path") or ""))
    if path.is_file():
        dig=hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""):
                dig.update(chunk)
        return "bytes:"+dig.hexdigest()
    return "url:"+str(asset.get("url") or asset.get("index") or "").split("?")[0]


class StaticTracker:
    def __init__(self):
        self.usage=defaultdict(lambda:{"count":0,"seconds":0.0,"scene":None,"end":None})
        self.previous=None

    def can_use(self,asset,phrase,scene_no,timeline_seconds,duration):
        if asset.get("type")!="image" or not subject_ok(phrase,asset):
            return False
        key=asset_identity(asset)
        row=self.usage[key]
        if duration>MAX_STATIC_BEAT_SECONDS+0.001:
            return False
        if row["count"]>=static_limit(asset):
            return False
        if row["seconds"]+duration>MAX_STATIC_TOTAL_SECONDS_MASTER+0.001:
            return False
        if row["scene"] is not None and scene_no-row["scene"]<STATIC_COOLDOWN_SCENES:
            return False
        if row["end"] is not None and timeline_seconds-row["end"]<STATIC_COOLDOWN_SECONDS:
            return False
        if self.previous==key:
            return False
        return True

    def record(self,asset,scene_no,timeline_seconds,duration):
        key=asset_identity(asset)
        if asset.get("type")=="image":
            row=self.usage[key]
            row["count"]+=1
            row["seconds"]+=duration
            row["scene"]=scene_no
            row["end"]=timeline_seconds+duration
        self.previous=key if asset.get("type")=="image" else None


def validate_master(scenes,assets):
    """Recheck timeline after director, including any footage-ratio substitutions."""
    tracker=StaticTracker()
    report=[]
    cursor=0.0
    for scene_no,scene in enumerate(scenes,1):
        for beat in scene.get("beats") or []:
            idx=int(beat["media_index"])
            asset=assets.get(idx)
            if not asset:
                raise RuntimeError(f"QUALITY_BLOCK: beat referencia asset desconhecido {idx}")
            d=float(beat["duration"])
            if d<=0:
                raise RuntimeError("QUALITY_BLOCK: beat sem duração")
            if asset["type"]=="image":
                if not tracker.can_use(asset,beat.get("text",""),scene_no,cursor,d):
                    raise RuntimeError(f"QUALITY_BLOCK: repetição ou tema incompatível para imagem {idx} na cena {scene_no}")
                report.append({"scene":scene_no,"image":idx,"seconds":round(d,3)})
            tracker.record(asset,scene_no,cursor,d)
            cursor+=d
    return {"status":"APPROVED","policy":"MASTER_STATIC_LIMITS_V1",
            "static_uses":report,"total_seconds":round(cursor,3)}


def validate_short(beats,assets):
    seen=set()
    seconds=defaultdict(float)
    for beat in beats:
        idx=int(beat["media_index"])
        asset=assets.get(idx)
        if not asset:
            raise RuntimeError(f"QUALITY_BLOCK: Short referencia asset ausente {idx}")
        if asset.get("type")!="image":
            continue
        key=asset_identity(asset)
        d=float(beat["duration"])
        if key in seen or d>MAX_STATIC_BEAT_SECONDS+0.001:
            raise RuntimeError(f"QUALITY_BLOCK: Short repete imagem {idx} ou excede 3,5s")
        if not subject_ok(beat.get("text",""),asset):
            raise RuntimeError(f"QUALITY_BLOCK: imagem {idx} desconectada da narração do Short")
        seconds[key]+=d
        if seconds[key]>MAX_STATIC_TOTAL_SECONDS_SHORT+0.001:
            raise RuntimeError(f"QUALITY_BLOCK: imagem {idx} domina o Short")
        seen.add(key)
    return {"status":"APPROVED","images_used":len(seen)}


def replace_short_repeats(scene,assets):
    """Rebuild a Short from approved source media without repeating stills."""
    from copy import deepcopy
    beats=deepcopy(scene.get("beats") or [])
    videos=[a for a in assets.values() if a.get("type")=="video"
            and int(a["index"]) in {int(x) for x in scene.get("media_first_assets",[])}]
    windows=scene.get("visual_windows") or {}
    used=set()
    for beat in beats:
        asset=assets[int(beat["media_index"])]
        d=float(beat["duration"])
        key=asset_identity(asset) if asset.get("type")=="image" else None
        if asset.get("type")=="image" and (
            key in used or d>MAX_STATIC_BEAT_SECONDS+0.001
            or not subject_ok(beat.get("text",""),asset)
        ):
            allowed=[a for a in videos if any(float(w["end"])-float(w["start"])>=d+.1
                     for w in windows.get(str(a["index"]),[]))]
            if not allowed:
                raise RuntimeError("QUALITY_BLOCK: Short sem gameplay compatível para substituir imagem repetida")
            pick=min(allowed,key=lambda a:int(a["index"]))
            beat["media_index"]=int(pick["index"])
            window=next(w for w in windows[str(pick["index"])]
                        if float(w["end"])-float(w["start"])>=d+.1)
            beat["source_window"]={"start":float(window["start"]),"end":float(window["end"])}
        elif key:
            used.add(key)
    validate_short(beats,assets)
    return beats


def qa_report(scenes,clips,shorts=None):
    assets={int(a["index"]):a for a in clips.get("assets") or [] if a.get("approved")}
    master=validate_master(scenes,assets)
    short_rows=[]
    for i,row in enumerate(shorts or [],1):
        b=row.get("media_beats")
        if not isinstance(b,list) or not b:
            raise RuntimeError(f"QUALITY_BLOCK: Short {i} sem mapa de mídias para anti-repetição")
        short_rows.append({"short":i,**validate_short(b,assets)})
    return {"status":"APPROVED","policy":"RADAR_ANTI_REPETITION_V1",
            "master":master,"shorts":short_rows}


if __name__=="__main__":
    plan=json.loads(Path(sys.argv[1] if len(sys.argv)>1 else "output/auto-media-plan.json").read_text())
    clips=json.loads(Path(sys.argv[2] if len(sys.argv)>2 else "output/clips.json").read_text())
    result=qa_report(plan.get("scenes") or [],clips)
    dest=Path("output/anti-repetition-qa.json")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False))
