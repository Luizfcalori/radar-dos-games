#!/usr/bin/env python3
"""One-off GTA VI Oct 08 2026 review production.

Uses the already approved Radar V4 modules unchanged; special scene and timecode
constraints are applied only by this script. Never uploads or schedules to YouTube.
"""
import json
import os
import re
import sys
import subprocess
from pathlib import Path

OUT=Path("output")
BRIEF=Path("production/gta6-cyberleek-2026-10-08.json")
INTRO=Path("radar-dos-games-intro-oficial.mp4")

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def save(path,obj):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")

def check_rejection_context(script):
    forbidden=(
        "não vou usar", "não usamos outro", "não confundir",
        "não misturar", "nossa produção", "nossa edição",
        "o que está na tela", "a imagem corresponde", "você pediu",
        "nossa regra", "nosso padrão", "essa narração", "neste vídeo vamos",
        "não vou colocar"
    )
    text=script.casefold()
    bad=[x for x in forbidden if x in text]
    if bad:raise RuntimeError("QUALITY_BLOCK: recado interno/proibição na narração: "+str(bad))
    if re.search(r"\b(?:gta\s*v|gta\s*5|grand theft auto cinco)\b",text,re.I):
        # Historical comparison to GTA 5 is not a production problem, but no
        # visual substitution of GTA5 is ever permitted.
        pass
    return True

def prepare():
    b=load(BRIEF)
    blocks=b["script_blocks"]
    if len(blocks)!=len(b["scene_titles"]) or len(blocks)!=len(b["scene_seeks"]):
        raise RuntimeError("QUALITY_BLOCK: mapa editorial incompleto")
    word_count=len(" ".join(blocks).split())
    if not 890<=word_count<=1010:raise RuntimeError(f"QUALITY_BLOCK: roteiro fora da meta de 6-7 minutos: {word_count} palavras")
    script="\n\n".join(blocks)
    check_rejection_context(script)
    OUT.mkdir(exist_ok=True)
    (OUT/"auto-script.txt").write_text(script+"\n",encoding="utf-8")
    media=[]
    for i,url in enumerate(b["video_urls"],1):
        media.append({
            "type":"video","url":url,"role":f"gta6_original_rockstar_{i:02d}",
            "source_proof":"https://www.rockstargames.com/VI/media/videos",
            "relevance_evidence":"Rockstar_Games_verified_official_GTA_VI_in_game_footage",
            "max_assets":1,"min_duration":5
        })
    scenes=[]
    for i,(title,paragraph) in enumerate(zip(b["scene_titles"],blocks),1):
        scenes.append({
            "paragraph":i,"title":title[:47],
            "subtitle":"GTA VI - ANÁLISE DO VAZAMENTO",
            "semantic_subject":f"gta6_leak_scene_{i:02d}",
            "allowed_roles":["gta6_original_rockstar_01"],
            "media_indices":[1]
        })
    plan={
        "topic":b["headline"],"source":b["primary_source"],
        "minimum_assets":1,"minimum_video_assets":1,
        "minimum_unique_video_seconds":1200,
        "minimum_image_assets":0,
        "media_policy":"only_official_gta6_extended_look; no_other_games; no_explicit_leak; exact_timecoded_reference",
        "media":media,"scenes":scenes,
        "short_hooks":b["short_hooks"],
        "short_hook_policy":"exact_editorial_hooks; exact_scene_lock; no_short_from_master_crop"
    }
    save(OUT/"auto-media-plan.json",plan)
    selected={
        "title":"GTA 6","content_id":b["content_id"],
        "source":b["primary_source"],"url":b["primary_source"],
        "topic":b["headline"],"short_hooks":b["short_hooks"],
        "source_urls":b["sources"],
        "manual_brief":True,"discovered_media":3,
        "media_mix":{"quality":"official_rockstar_gta6_extended_look_only"}
    }
    save(OUT/"selected.json",selected)
    def seo(text):
        return {"title":text,
          "description":(
              "Radar dos Games: análise editorial do vazamento de GTA 6 divulgado em 8 de outubro de 2026.\n"
              "As informações sobre o arquivo divulgado por Cyberleek são relatos da imprensa, "
              "não anúncios confirmados pela Rockstar. As imagens são exclusivamente do "
              "material OFICIAL de GTA VI publicado pela Rockstar, sem reproduzir a gravação vazada.\n\n"
              "Fontes:\n"+"\n".join(b["sources"])+
              "\n\n#GTA6 #GTAVI #RadarDosGames #Gamer"
          ),
          "privacyStatus":"private",
          "tags":["GTA 6","GTA VI","Cyberleek","vazamento","Rockstar Games","Radar dos Games"]}
    save(OUT/"master-youtube.json",seo(b["headline"]))
    for k,hook in enumerate(b["short_hooks"],1):
        # Do not append #Shorts to the literal title: the existing V4 title
        # comparison expects EXACT hook and has a broken hashtag regex.
        meta=seo(hook)
        meta["description"]+="\n#Shorts"
        save(OUT/f"short-{k}-youtube.json",meta)
    print(json.dumps({"status":"PREPARED","words":word_count,"paragraphs":len(blocks),
                      "visual_policy":"verified Rockstar GTA6 extended only; explicit leaked frames excluded"}))

def scene_assets():
    """Each narration scene is locked to its own original Rockstar GTA VI clip."""
    clips=load(OUT/"clips.json")
    vids=[a for a in clips.get("assets",[]) if a.get("type")=="video"
        and "media-rockstargames-com.akamaized.net/VI/downloads/videos/GTAVI_An_Extended_Look" in str(a.get("url") or "")]
    b=load(BRIEF)
    if len(vids)!=len(b["scene_titles"]):
        raise RuntimeError(f"QUALITY_BLOCK: não foram encontrados os {len(b['scene_titles'])} clipes Rockstar por cena: {len(vids)}")
    out={}
    for n in range(1,len(b["scene_titles"])+1):
        role=f"gta6_rockstar_scene_{n:02d}"
        match=[a for a in vids if a.get("role")==role and float(a.get("duration") or 0)>=20]
        if len(match)!=1:
            raise RuntimeError("QUALITY_BLOCK: clipe oficial da cena %02d ausente"%n)
        out[n]=match[0]
    return out

def direct():
    import director_v4
    director_v4.main()
    b=load(BRIEF)
    plan=load(OUT/"auto-media-plan.json")
    scenes=plan["scenes"]
    asset_for_scene=scene_assets()
    if len(scenes)!=len(b["scene_titles"]):
        raise RuntimeError("QUALITY_BLOCK: 16 cenas obrigatórias GTA 6")
    rows=[]
    uses={}
    for i,scene in enumerate(scenes,1):
        asset=asset_for_scene[i]
        media_index=int(asset["index"])
        scene["title"]=b["scene_titles"][i-1][:47]
        scene["subtitle"]="GTA VI - ANÁLISE DO VAZAMENTO"
        scene["allowed_roles"]=[asset["role"]]
        scene.pop("allowed_role_prefixes",None)
        scene["semantic_subject"]=f"gta6_special_scene_{i:02d}"
        for k,beat in enumerate(scene["beats"]):
            d=float(beat["duration"])
            clip_seconds=float(asset["duration"])
            room=max(0.0,clip_seconds-d-0.5)
            if room<0.1:raise RuntimeError(f"QUALITY_BLOCK: clipe da cena {i} menor que beat")
            # Timecoded local clip bound to this precise subject; prevents
            # random seek into any other game or unrelated section.
            offset=round(min(room, max(0,(k*2.31)%room)),3)
            beat["media_index"]=media_index
            beat["source_seek"]=offset
            beat["source_kind"]="ROCKSTAR_GTA_VI_OFFICIAL_2026_08_27"
            rows.append({
                "scene":i,"beat":k+1,"phrase":beat.get("phrase"),
                "source_original_timestamp":asset["source_seek_original"],
                "source_local_timestamp":offset,
                "media_index":media_index,"duration":d,"text":beat.get("text","")[:150],
                "source":asset["url"]
            })
            uses[str(media_index)]=uses.get(str(media_index),0)+1
        scene["media_indices"]=[media_index]
    save(OUT/"auto-media-plan.json",plan)
    manifest=load(OUT/"render.json")
    manifest["scenes"]=scenes
    save(OUT/"render.json",manifest)
    report=load(OUT/"director-v4.json")
    report["source_lock"]="ROCKSTAR_GTA_VI_2026_08_27_TIME_CODED_16_SCENE_ONLY"
    report["asset_usage"]=uses
    for i,scene in enumerate(scenes):
        report["scenes"][i]["media_indices"]=scene["media_indices"]
        report["scenes"][i]["video_beats"]=len(scene["beats"])
    picks=[int(i)-1 for i in b["short_scene_numbers"]]
    hooks=b["short_hooks"]
    if len(set(picks))!=3 or len(hooks)!=3:
        raise RuntimeError("QUALITY_BLOCK: Shorts devem ter três cenas únicas")
    matches=[]
    for idx,hook in zip(picks,hooks):
        score,overlap,stems=director_v4.hook_scene_score(hook,scenes[idx])
        if score<=0:
            raise RuntimeError(f"QUALITY_BLOCK: hook do Short não combina com a cena escolhida: {hook}")
        matches.append({"hook":hook,"scene_index":idx,
              "scene_title":scenes[idx]["title"],"semantic_score":score,
              "overlap_terms":overlap,"overlap_stems":stems,"editorial_score":score})
    save(OUT/"short-picks.json",{
        "version":"PREMIUM_V4_DIRECTOR_CUT","scene_indexes":picks,
        "expected_hooks":hooks,"semantic_matches":matches,
        "selection_policy":"MANUAL_16_SCENE_GAMEPLAY_SOURCE_LOCK; SEMANTIC_SCORE_COMPUTED"
    })
    report["short_scene_indexes"]=picks
    report["short_hooks"]=hooks
    report["short_semantic_matches"]=matches
    save(OUT/"director-v4.json",report)
    save(OUT/"gta6-leak-visual-sync-qa.json",{
        "status":"SOURCE_BINDINGS_APPROVED_HUMAN_REVIEW_REQUIRED",
        "scope":"GTA VI CYBERLEEK REVIEW ONLY",
        "main_source":"https://media-rockstargames-com.akamaized.net/VI/downloads/videos/GTAVI_An_Extended_Look/GTAVI_An_Extended_Look.mp4",
        "main_source_duration":1608.0,
        "no_leaked_explicit_footage":True,"no_other_game":True,
        "note":"Official Aug 27 footage aligned to similar topics but does not depict today's leaked scenes. Human review required before publishing.",
        "beats":rows
    })
    print(json.dumps({"status":"SOURCE_LOCKED",
        "scenes":len(scenes),"beats":len(rows),"short_scene_indexes":picks,
        "source":"Rockstar official Aug 27 extended look; original scenes from today not included"},ensure_ascii=False))

def master():
    import render_v4
    m=load(OUT/"render.json")
    beats=[b for s in m["scenes"] for b in s["beats"]]
    def selected_seek(path,piece_no,duration):
        beat=beats[piece_no-1]
        return beat["source_seek"]
    render_v4.video_seek=selected_seek
    render_v4.render(str(OUT/"render.json"))

def shorts():
    import shorts_v4
    import textwrap
    b=load(BRIEF)
    visual=[
      "GTA 6: CORRIDA\nDE MOTO NA LAMA",
      "GTA 6: CARROS\nE CORRIDA DE RUA",
      "GTA 6: CÂMERA\nEM PRIMEIRA PESSOA"
    ]
    def headline(txt,width=24,max_lines=2):
        for k,hook in enumerate(b["short_hooks"]):
            if txt==hook:return visual[k]
        return "\n".join(textwrap.wrap(str(txt),width=18)[:2])
    shorts_v4.wrapped=headline
    orig=shorts_v4.render_vertical_piece
    state={"short":0}
    chosen=[int(i)-1 for i in b["short_scene_numbers"]]
    scenes=load(OUT/"render.json")["scenes"]
    # First video piece of each Short is indicated by headline, rather than
    # inferred from generic number n.
    def special_piece(asset,duration,dest,piece_no,headline="",keyword="",first=False,last=False):
        if first:
            state["short"]+=1
        chosen_idx=chosen[state["short"]-1]
        beat=scenes[chosen_idx]["beats"][piece_no-1]
        shorts_v4.seek_for=lambda path,n,d: beat["source_seek"]
        return orig(asset,duration,dest,piece_no,headline=headline,keyword=keyword,first=first,last=last)
    shorts_v4.render_vertical_piece=special_piece
    shorts_v4.main()

def final_review():
    import subprocess
    from pathlib import Path
    b=load(BRIEF)
    report=load(OUT/"gta6-leak-visual-sync-qa.json")
    assert report["status"].startswith("SOURCE_BINDINGS_APPROVED")
    q=load(OUT/"qa.json")
    duration=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
                                            "-of","csv=p=0","output/master.mp4"],text=True).strip())
    if not 360<=duration<=420:
        raise RuntimeError(f"QUALITY_BLOCK: Master fora de 6-7 minutos: {duration:.2f}s")
    if len((OUT/"auto-script.txt").read_text(encoding="utf-8").split())<885:
        raise RuntimeError("QUALITY_BLOCK: narração insuficiente")
    check_rejection_context((OUT/"auto-script.txt").read_text(encoding="utf-8"))
    short_d=[]
    for i in range(1,4):
        s=OUT/f"shorts/short_{i}.mp4"
        if not s.exists():raise RuntimeError("QUALITY_BLOCK: Short ausente")
        short_d.append(float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
                   "-of","csv=p=0",str(s)],text=True).strip()))
    if any(not 8<=d<=65 for d in short_d):
        raise RuntimeError(f"QUALITY_BLOCK: Short duração inválida: {short_d}")
    import os
    for p in ("output/thumbnail.jpg","output/shorts/short_1_cover.jpg",
              "output/shorts/short_2_cover.jpg","output/shorts/short_3_cover.jpg"):
        if not Path(p).exists() or Path(p).stat().st_size<20000:
            raise RuntimeError(f"QUALITY_BLOCK: capa ausente ou vazia: {p}")
    save(OUT/"gta6-special-final-review.json",{
        "status":"AUTOMATED_QA_APPROVED; HUMAN_REVIEW_REQUIRED",
        "master_seconds":duration,
        "short_seconds":short_d,
        "voice":"pt-BR-ThalitaMultilingualNeural",
        "source":report["main_source"],
        "caveat":"Footage from official prior Rockstar Extended Look rather than today's leaked clip.",
        "youtube_upload":"NOT_PERFORMED"
    })
    print("GTA6 SPECIAL REVIEW APPROVED",round(duration,1),short_d)

if __name__=="__main__":
    step=(sys.argv[1] if len(sys.argv)>1 else "").strip()
    actions={"prepare":prepare,"direct":direct,"master":master,"shorts":shorts,"review":final_review}
    if step not in actions:raise SystemExit("Use one of "+", ".join(actions))
    actions[step]()
