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

def verify_assets(clips, plan):
    found=[]
    image_only = bool(plan.get("allow_image_only_master", False)) and not any(
        a.get("approved") is True and a.get("type") == "video"
        for a in clips.get("assets", [])
    )
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
    # The downloader explicitly allows a one-asset shortfall when at least
    # one verified, topic-relevant official video is available. Do not contradict
    # that policy here: a single approved moving asset can support a storyboard,
    # while the visual-inspection gate still rejects unusable or duplicate clips.
    has_video = any(x["type"] == "video" for x in found)
    has_official_stills = any(
        x["type"] == "image"
        and str(x.get("role") or "").startswith(("official_roblox_announcement_visual_", "official_game_announcement_visual_"))
        and str(x.get("source") or "").startswith("https://")
        for x in found
    )
    if not clips.get("publishable_media") or len(found)<1 or not (
        has_video or (image_only and has_official_stills)
    ):
        raise RuntimeError("QUALITY_BLOCK: não há vídeo aprovado nem fallback de imagens oficiais explicitamente autorizado")
    return found

def compile_storyboard(plan,clips,selected,outline,visual_inventory=None):
    assets=verify_assets(clips,plan)
    image_only = bool(plan.get("allow_image_only_master", False)) and not any(
        a.get("approved") is True and a.get("type") == "video" for a in assets
    )
    paragraphs=[p.strip() for p in outline.split("\n\n") if p.strip()]
    scenes=plan.get("scenes") or []
    if len(scenes)!=len(paragraphs) or len(scenes)<3:
        raise RuntimeError("QUALITY_BLOCK: cenas e roteiro preliminar não correspondem")
    inspected = {int(x["index"]): x for x in (visual_inventory or {}).get("assets", [])}
    videos = [a for a in assets if a["type"]=="video"
              and (visual_inventory is None or
                   (inspected.get(int(a["index"]), {}).get("usable_windows") and
                    not inspected.get(int(a["index"]), {}).get("duplicate_of")))]
    images=[a for a in assets if a["type"]=="image"]
    if not videos and not (image_only and images):
        raise RuntimeError("QUALITY_BLOCK: vídeos originais sem janelas aprovadas e sem fallback oficial image-led")
    usage=Counter()
    topic=plan.get("topic") or selected.get("title") or ""
    # Official stills from the exact article remain available as contextual
    # material even when CDN filenames are hashes. No unrelated source is admitted.
    def source_key(value):
        parsed=urlparse(str(value or ""))
        host=(parsed.hostname or "").lower()
        if host.startswith("www."):
            host=host[4:]
        return (host, parsed.path.rstrip("/"))
    primary_source=source_key(selected.get("url"))
    contextual_images=[]
    for asset in images:
        asset_role=str(asset.get("role") or "")
        asset_source=source_key(asset.get("source"))
        # A CDN filename may be opaque. Trust the verified official page host
        # plus an explicit, reviewed official-image role—not the filename alone.
        # Requiring the source host to match the selected official source keeps
        # the fallback topic-bound and prevents generic third-party images.
        official_role=asset_role.startswith((
            "official_subject_reference_", "official_context_",
            "official_roblox_announcement_visual_", "official_game_announcement_visual_"
        ))
        same_official_host=bool(primary_source[0] and asset_source[0]==primary_source[0])
        if official_role and same_official_host:
            if not asset.get("source_label"):
                asset["source_label"]=str(selected.get("title") or topic)
            contextual_images.append(asset)
    report=[]
    for i,(scene,text) in enumerate(zip(scenes,paragraphs),1):
        def rank(a):
            return (-relevance(text,a,topic),usage[int(a["index"])],int(a["index"]))
        matches=sorted(images,key=rank) if images else []
        matched_stills=[a for a in matches if relevance(text,a,topic)>0][:4]
        matched_still=matched_stills[0] if matched_stills else None
        semantic_ready=bool((visual_inventory or {}).get("semantic_model_policy"))
        expected=[]
        window_options={}
        if semantic_ready:
            try:
                from vision_semantics import scene_categories, usable_for_scene
            except ModuleNotFoundError:
                from src.vision_semantics import scene_categories, usable_for_scene
            expected=scene_categories(text)
            for vid in videos:
                candidate_windows=inspected[int(vid["index"])]["usable_windows"]
                window_options[int(vid["index"])]=usable_for_scene(candidate_windows,expected)
            # Fail closed: official origin proves the game identity, not that the
            # pictured action matches this paragraph. Only windows that passed the
            # visual category match may be assigned to this scene.
            matched_videos=[a for a in videos if window_options[int(a["index"])]]
            if expected and not matched_videos and not matched_stills and not image_only:
                raise RuntimeError(
                    f"QUALITY_BLOCK: nenhuma gameplay/quadro aprovado corresponde "
                    f"semanticamente à cena {i}: {text[:180]}"
                )
        else:
            matched_videos=videos
        picks=[]
        if matched_videos:
            picks.extend(sorted(matched_videos,key=rank))
        if matched_stills:
            picks.extend(matched_stills)
        # All images from the exact official event page are available as
        # contextual cutaways. StaticTracker enforces subject match, cooldown,
        # and per-image limits; unrelated sources are never admitted.
        if contextual_images:
            # A publisher page is not proof that every image illustrates every
            # sentence. Prefer scene-specific label matches; the explicit Roblox
            # image-led mode may use the remaining official announcement stills
            # as contextual backgrounds while the on-screen cards carry the facts.
            contextual_matches=[a for a in contextual_images if relevance(text,a,topic)>0]
            if image_only:
                # In image-led mode every scene can draw from the complete set of
                # verified official announcement stills. Feature-specific matches
                # rank first, but a single weekly-recap screenshot must not become
                # the only eligible image for later scenes.
                picks.extend(sorted(contextual_images,key=rank))
            else:
                picks.extend(sorted(contextual_matches,key=rank))
        # Never use unrelated third-party imagery. The only broad contextual
        # fallback is the explicitly authorized official Roblox announcement mode.
        if not picks:
            raise RuntimeError(f"QUALITY_BLOCK: cena {i} sem vídeo reconhecido nem imagem oficial identificável")
        # A semantic label mismatch is not a hard block when official gameplay
        # from the exact same game is available; topic identity is enforced upstream.
        indices=list(dict.fromkeys(int(a["index"]) for a in picks))
        roles=list(dict.fromkeys(str(a["role"]) for a in picks))
        for idx in indices:usage[idx]+=1
        scene.update({
            # Keep every approved, visually inspected video window available as a
            # scene-local fallback. The director still prioritizes the scene's
            # exact picks; fallback IDs come only from this game's curated manifest.
            "visual_windows": {str(a["index"]): inspected.get(int(a["index"]), {}).get("usable_windows", [])
                               for a in videos} if visual_inventory else {},
            "fallback_media_indices": [int(a["index"]) for a in videos
                                       if int(a["index"]) not in indices],
            "vision_categories": expected,
            "preferred_media_indices": [int(a["index"]) for a in picks
                                        if a["type"]=="image" and relevance(text,a,topic)>0],
            "media_indices":indices,
            "media_first_assets":indices,
            "allowed_roles":roles,
            "allowed_role_prefixes":[],
            "semantic_subject":scene.get("title") or topic,
            "allow_official_subject_fallback": bool(plan.get("allow_official_subject_fallback", False) or ("playtime" in terms(topic) and any(a.get("source") == "steam_app:2087540" and a.get("role") == "official_steam_gameplay" for a in picks))),
            "allow_same_source_role_fallback": bool(plan.get("allow_same_source_role_fallback", False)),
            "visual_evidence":("official_image_subject_label"
                               if any(a["type"]=="image" and relevance(text,a,topic)>0 for a in picks)
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
    if visual_inventory:
        plan["visual_inspection_policy"]="FULL_FRAME_TECHNICAL_SCAN_V1"
        if visual_inventory.get("semantic_model_policy"):
            plan["semantic_model_policy"]=visual_inventory["semantic_model_policy"]
        storyboard["visual_inspection_policy"]="FULL_FRAME_TECHNICAL_SCAN_V1"
        storyboard["source_frames_analyzed"]=sum(x.get("frames_analyzed",0)
                                                 for x in inspected.values())
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
    inventory_path=OUT/"visual-inventory.json"
    if not inventory_path.is_file():
        raise RuntimeError("QUALITY_BLOCK: inspeção frame a frame ausente antes da narração")
    visual_inventory=json.loads(inventory_path.read_text(encoding="utf-8"))
    if visual_inventory.get("status")!="ANALYZED":
        raise RuntimeError("QUALITY_BLOCK: inspeção visual incompleta")
    plan,script,storyboard=compile_storyboard(plan,clips,selected,prepared,visual_inventory)
    # Persist contextual source labels for downstream anti-repetition QA.
    (OUT/"clips.json").write_text(json.dumps(clips,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    storyboard["preview_frames"]=previews(storyboard["assets"])
    (OUT/"auto-media-plan.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"auto-script.txt").write_text(script,encoding="utf-8")
    (OUT/"media-first-storyboard.json").write_text(json.dumps(storyboard,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"APPROVED","scenes":len(storyboard["scenes"]),
                      "assets":len(storyboard["assets"]),"policy":"MEDIA_FIRST_V1"}))

if __name__=="__main__":
    main()
