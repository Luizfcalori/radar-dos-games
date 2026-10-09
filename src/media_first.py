#!/usr/bin/env python3
"""Media-first storyboard: bind narration scenes to files actually downloaded.

This is evidence-based editorial ordering, NOT automatic recognition of objects
in video frames. Asset filenames and source labels are only contextual clues.
"""
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlparse

OUT=Path("output")
STOP=set(("radar dos games videogame jogo jogos game games video videos "
          "trailer gameplay official oficial imagem imagens media assets source news "
          "para com uma mais sobre quando como esta esse essa novo nova pela pelo "
          "entre conforme quem ainda tambem anuncio confirmado detalhes").split())

def terms(text):
    s=unicodedata.normalize("NFKD",str(text or "").lower())
    s="".join(c for c in s if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z][a-z0-9]{2,}",s)
            if w not in STOP and not re.fullmatch(r"[a-f0-9]{16,}",w)}

def label(asset):
    name=unquote(urlparse(str(asset.get("url") or "")).path).rsplit("/",1)[-1]
    return " ".join([str(asset.get("source_label") or ""),
                     name.replace("-"," ").replace("_"," ")])

def relevance(paragraph,asset,topic):
    return len((terms(paragraph)-terms(topic)) & terms(label(asset)))

def verify_assets(clips):
    found=[]
    for asset in clips.get("assets") or []:
        if not asset.get("approved"):continue
        if asset.get("type") not in ("video","image"):continue
        file=Path(asset["path"])
        if not file.is_file() or file.stat().st_size==0:
            raise RuntimeError(f"QUALITY_BLOCK: mídia aprovada ausente: {file}")
        if not asset.get("role") or not asset.get("source"):
            raise RuntimeError("QUALITY_BLOCK: mídia sem identificação da fonte")
        if asset["type"]=="video" and float(asset.get("duration") or 0)<1:
            raise RuntimeError("QUALITY_BLOCK: arquivo de vídeo sem duração válida")
        found.append(asset)
    if not clips.get("publishable_media") or len(found)<2 or not any(
        x["type"]=="video" for x in found
    ):
        raise RuntimeError("QUALITY_BLOCK: não há mídia em movimento aprovada suficiente")
    return found

def compile_storyboard(plan,clips,selected,outline):
    assets=verify_assets(clips)
    paragraphs=[p.strip() for p in outline.split("\n\n") if p.strip()]
    scenes=plan.get("scenes") or []
    if len(scenes)!=len(paragraphs) or len(scenes)<3:
        raise RuntimeError("QUALITY_BLOCK: cenas e roteiro preliminar não correspondem")
    videos=[a for a in assets if a["type"]=="video"]
    images=[a for a in assets if a["type"]=="image"]
    usage=Counter()
    topic=plan.get("topic") or selected.get("title") or ""
    report=[]
    for i,(scene,text) in enumerate(zip(scenes,paragraphs),1):
        def rank(a):
            return (-relevance(text,a,topic),usage[int(a["index"])],int(a["index"]))
        picks=[min(videos,key=rank)]
        if images:
            picks.append(min(images,key=rank))
        indices=[int(a["index"]) for a in picks]
        roles=list(dict.fromkeys(str(a["role"]) for a in picks))
        for idx in indices:usage[idx]+=1
        scene.update({
            "media_indices":indices,
            "media_first_assets":indices,
            "allowed_roles":roles,
            "allowed_role_prefixes":[],
            "semantic_subject":scene.get("title") or topic,
            "visual_evidence":("filename_or_label" if relevance(text,picks[0],topic)
                               else "source_level_only"),
        })
        report.append({"scene":i,"media_indices":indices,"roles":roles,
                       "visual_evidence":scene["visual_evidence"],
                       "paragraph_excerpt":text[:160]})
    # Definitive narration is assembled only after the real file inventory.
    # Keep manually researched claims unchanged; no fabricated shot descriptions.
    script="\n\n".join(paragraphs)+"\n"
    storyboard={
        "status":"APPROVED","policy":"MEDIA_FIRST_V1",
        "order":["research_outline","download","verified_shotlist",
                 "final_script","thalita_voice","director_v4","semantic_gate"],
        "note":"Source/filename clues are NOT proof of scene objects or actions",
        "manual_script_preserved":bool(selected.get("manual_brief")),
        "assets":[{"index":int(a["index"]),"type":a["type"],"role":a["role"],
                   "path":a["path"],"source":a["source"],"url":a.get("url"),
                   "duration":a.get("duration")} for a in assets],
        "script_sha256":hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "scenes":report,
    }
    plan["media_first_policy"]="MEDIA_FIRST_V1"
    return plan,script,storyboard

def previews(assets):
    """Optional contact frames retained for visual review, not automated semantic proof."""
    folder=OUT/"media-first-frames"
    folder.mkdir(parents=True,exist_ok=True)
    results={}
    for a in assets:
        if a["type"]!="video":continue
        dest=folder/f"asset_{a['index']}.jpg"
        seconds=min(5,max(0,float(a.get("duration") or 0)/2))
        try:
            subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{seconds:.2f}",
                            "-i",a["path"],"-frames:v","1","-vf","scale=480:-2",
                            str(dest)],check=True,timeout=30)
            if dest.is_file() and dest.stat().st_size>1000:
                results[str(a["index"])]=str(dest)
        except (OSError,subprocess.SubprocessError):
            pass
    return results

def main():
    plan=json.loads((OUT/"auto-media-plan.json").read_text(encoding="utf-8"))
    clips=json.loads((OUT/"clips.json").read_text(encoding="utf-8"))
    selected=json.loads((OUT/"selected.json").read_text(encoding="utf-8"))
    outline=(OUT/"auto-script-outline.txt").read_text(encoding="utf-8")
    # Preserve the existing voice-editor cleanup, but execute it BEFORE binding
    # scene-to-file roles and SHA so voice no longer modifies the approved script.
    from voice import prepare_narration
    prepared=prepare_narration(outline)
    plan,script,storyboard=compile_storyboard(plan,clips,selected,prepared)
    storyboard["preview_frames"]=previews(storyboard["assets"])
    (OUT/"auto-media-plan.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"auto-script.txt").write_text(script,encoding="utf-8")
    (OUT/"media-first-storyboard.json").write_text(json.dumps(storyboard,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"APPROVED","scenes":len(storyboard["scenes"]),
                      "assets":len(storyboard["assets"]),"policy":"MEDIA_FIRST_V1"}))

if __name__=="__main__":
    main()
