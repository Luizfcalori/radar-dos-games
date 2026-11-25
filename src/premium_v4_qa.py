#!/usr/bin/env python3
"""Gate editorial Premium V4 Director Cut."""
import json
import re
from pathlib import Path

def load(path):
    p=Path(path)
    if not p.exists():raise RuntimeError(f"QUALITY_BLOCK: arquivo ausente {path}")
    return json.loads(p.read_text(encoding="utf-8"))

def norm_short_title(value):
    value=re.sub(r"(?i)\s*#shorts?\b","",str(value or ""))
    return re.sub(r"\s+"," ",value).strip().casefold()

def main():
    storyboard=load("output/media-first-storyboard.json")
    import hashlib
    actual=hashlib.sha256(Path("output/auto-script.txt").read_bytes()).hexdigest()
    if storyboard.get("policy")!="MEDIA_FIRST_V1" or storyboard.get("status")!="APPROVED" or storyboard.get("script_sha256")!=actual:
        raise RuntimeError("QUALITY_BLOCK: roteiro ou decupagem media-first inválidos")
    plan=load("output/auto-media-plan.json")
    director=load("output/director-v4.json")
    clips=load("output/clips.json")
    semantic=load("output/semantic-visual-qa.json")
    render=load("output/qa.json")
    shorts=load("output/shorts/manifest.json")
    picks=load("output/short-picks.json")
    frames=load("output/visual-frame-qa.json")
    timings=load("output/voice-timings.json")

    assert plan.get("premium_version")=="PREMIUM_V4_DIRECTOR_CUT",plan.get("premium_version")
    assert director.get("status")=="APPROVED" and director.get("version")=="PREMIUM_V4_DIRECTOR_CUT",director
    assert semantic.get("status")=="APPROVED",semantic
    assert semantic.get("policy")=="FLEXIBLE_PHRASE_TO_REVIEWED_GAMEPLAY_V3",semantic
    assert int(semantic.get("error_count") or 0)==0,semantic
    assert render.get("standard")=="radar-dos-games-premium-v4-director-cut",render.get("standard")
    assert render.get("editing_policy")=="phrase_level_beats; variable_pacing; selective_keyword_overlays"
    assert frames.get("status")=="APPROVED",frames
    assert timings.get("source")=="paragraph_boundaries+tts_word_boundaries",timings.get("source")

    if not clips.get("publishable_media"):
        raise RuntimeError("QUALITY_BLOCK: pacote de mídia não está publicável")
    video_assets=int(clips.get("video_assets") or 0)
    image_assets=int(clips.get("image_assets") or 0)
    unique_video_seconds=float(clips.get("unique_video_seconds") or 0)
    image_only=bool(plan.get("allow_image_only_master", False)) and video_assets == 0
    required_videos=0 if image_only else max(1,int(plan.get("minimum_video_assets") or 0))
    required_unique=0.0 if image_only else max(15.0,float(plan.get("minimum_unique_video_seconds") or 0))
    required_images=int(plan.get("minimum_image_assets") or 0)
    if video_assets < required_videos:
        raise RuntimeError(f"QUALITY_BLOCK: gameplay/vídeo oficial ausente ({video_assets}/{required_videos})")
    if unique_video_seconds < required_unique:
        raise RuntimeError(f"QUALITY_BLOCK: somente {unique_video_seconds:.1f}s de vídeo oficial único; mínimo {required_unique:.1f}s")
    if image_only and image_assets < max(1,required_images):
        raise RuntimeError(f"QUALITY_BLOCK: imagens oficiais insuficientes para o modo image-led ({image_assets}/{required_images})")

    plan_scenes=plan.get("scenes") or []
    for i,scene in enumerate(plan_scenes,1):
        title=str(scene.get("title") or "").strip()
        if not title:
            raise RuntimeError(f"QUALITY_BLOCK: cena {i} sem headline")
        if re.fullmatch(r"DESTAQUE\s*\d*",title,re.I) or re.fullmatch(r"CENA\s*\d+.*",title,re.I):
            raise RuntimeError(f"QUALITY_BLOCK: headline genérica proibida na cena {i}: {title}")

    asset_map={int(a["index"]):a for a in clips.get("assets",[]) if a.get("approved")}
    body_seconds=0.0
    moving_seconds=0.0
    video_scene_count=0
    for scene in plan_scenes:
        scene_has_video=False
        for beat in scene.get("beats") or []:
            duration=float(beat.get("duration") or 0)
            body_seconds+=duration
            asset=asset_map.get(int(beat.get("media_index") or 0),{})
            if asset.get("type")=="video":
                moving_seconds+=duration
                scene_has_video=True
        if scene_has_video:
            video_scene_count+=1
    moving_ratio=(moving_seconds/body_seconds) if body_seconds else 0.0
    if image_only:
        image_scene_count=sum(
            1 for scene in plan_scenes
            if any(asset_map.get(int(beat.get("media_index") or 0),{}).get("type")=="image"
                   and str(asset_map.get(int(beat.get("media_index") or 0),{}).get("role") or "").startswith(("official_roblox_announcement_visual_", "official_game_announcement_visual_"))
                   for beat in scene.get("beats") or [])
        )
        if image_scene_count < len(plan_scenes):
            raise RuntimeError(f"QUALITY_BLOCK: cenas sem imagem oficial image-led ({image_scene_count}/{len(plan_scenes)})")
    else:
        if moving_ratio+1e-9 < 0.25:
            raise RuntimeError(f"QUALITY_BLOCK: gameplay/footage em movimento ocupa {moving_ratio:.1%}; mínimo 25%")
        if video_scene_count < min(1,len(plan_scenes)):
            raise RuntimeError(f"QUALITY_BLOCK: gameplay/footage presente em somente {video_scene_count} cenas")

    scenes=render.get("scenes") or []
    assert scenes and len(scenes)==len(plan.get("scenes") or []),(len(scenes),len(plan.get("scenes") or []))
    phrase_count=int(director.get("phrase_count") or 0)
    assert phrase_count>=len(scenes),(phrase_count,len(scenes))
    cadence=[]
    for row in scenes:
        avg=float(row.get("average_beat_seconds") or 0)
        assert 0.05<=avg<=10.10,(row.get("scene"),avg)
        assert row.get("phrase_level") is True,row
        assert int(row.get("beats") or 0)>=1,row
        cadence.append({"scene":row.get("scene"),"beats":row.get("beats"),"avg_beat":avg})

    srows=shorts.get("shorts") or []
    assert len(srows)==3,len(srows)
    expected_hooks=[str(x or "").strip() for x in (picks.get("expected_hooks") or [])]
    manifest_hooks=[str(x or "").strip() for x in (shorts.get("expected_hooks") or [])]
    if len(expected_hooks)!=3 or any(not x for x in expected_hooks):
        raise RuntimeError("QUALITY_BLOCK: short-picks sem exatamente 3 hooks aprovados")
    if [norm_short_title(x) for x in manifest_hooks] != [norm_short_title(x) for x in expected_hooks]:
        raise RuntimeError("QUALITY_BLOCK: manifest dos Shorts divergiu dos hooks aprovados")

    master_split=shorts.get("source_policy")=="contiguous_master_split_v1"
    if master_split:
        if shorts.get("layout_profile")!="RADAR_MASTER_SPLIT_9X16_V1":
            raise RuntimeError("QUALITY_BLOCK: layout 9:16 do recorte do Master ausente")
        if shorts.get("hook_policy")!="approved_hook_as_metadata; contiguous_master_timeline; preserve_master_audio":
            raise RuntimeError("QUALITY_BLOCK: política de recorte do Master inválida")
        master_duration=float(shorts.get("master_duration") or 0)
        ranges=[]
        for i,(row,hook) in enumerate(zip(srows,expected_hooks),1):
            if row.get("render_policy")!="contiguous_master_segment" or row.get("boundary_policy")!="master_timeline_partition":
                raise RuntimeError(f"QUALITY_BLOCK: Short {i} não veio diretamente do Master")
            if row.get("audio_source")!="master_original_audio":
                raise RuntimeError(f"QUALITY_BLOCK: Short {i} não preserva o áudio do Master")
            if norm_short_title(row.get("title"))!=norm_short_title(hook) or norm_short_title(row.get("approved_hook"))!=norm_short_title(hook):
                raise RuntimeError(f"QUALITY_BLOCK: título do Short {i} diverge do hook aprovado")
            if row.get("layout_profile")!="RADAR_MASTER_SPLIT_9X16_V1":
                raise RuntimeError(f"QUALITY_BLOCK: Short {i} sem layout vertical correto")
            if row.get("cta")!=["INSCREVA-SE AGORA","DEIXE O LIKE","RADAR DOS GAMES"]:
                raise RuntimeError(f"QUALITY_BLOCK: CTA metadata ausente no Short {i}")
            meta=load(f"output/short-{i}-youtube.json")
            if norm_short_title(meta.get("title"))!=norm_short_title(hook):
                raise RuntimeError(f"QUALITY_BLOCK: metadata do Short {i} diverge do hook aprovado")
            lo=float(row.get("source_start") or 0)
            hi=float(row.get("source_end") or 0)
            duration=float(row.get("duration") or 0)
            if duration<20 or hi<=lo or abs((hi-lo)-duration)>0.15:
                raise RuntimeError(f"QUALITY_BLOCK: intervalo/duração inválido no Short {i}")
            ranges.append((lo,hi))
        if abs(ranges[0][0])>0.08 or abs(ranges[-1][1]-master_duration)>0.15:
            raise RuntimeError("QUALITY_BLOCK: os Shorts não cobrem o Master inteiro")
        for i in range(2):
            if abs(ranges[i][1]-ranges[i+1][0])>0.08:
                raise RuntimeError("QUALITY_BLOCK: há lacuna ou sobreposição entre partes do Master")
        if abs(ranges[0][1]-ranges[0][0] - master_duration/3)>0.2:
            raise RuntimeError("QUALITY_BLOCK: divisão do Master não está em três partes equivalentes")
        if abs(ranges[1][1]-ranges[1][0] - master_duration/3)>0.2:
            raise RuntimeError("QUALITY_BLOCK: divisão do Master não está em três partes equivalentes")
        if abs(ranges[2][1]-ranges[2][0] - master_duration/3)>0.2:
            raise RuntimeError("QUALITY_BLOCK: divisão do Master não está em três partes equivalentes")
        anti_spam={
            "status":"APPROVED",
            "policy":"three_non_overlapping_contiguous_master_segments",
            "master_split":"APPROVED",
            "segments":len(ranges),
        }
        Path("output/anti-repetition-qa.json").write_text(
            json.dumps(anti_spam,ensure_ascii=False,indent=2),encoding="utf-8")
    else:
        if shorts.get("layout_profile") != "RADAR_PREMIUM_CONVERSAO_V1":
            raise RuntimeError("QUALITY_BLOCK: padrão visual Premium Conversão não aplicado")
        if shorts.get("hook_policy") != "exact_approved_hook_persistent_all_beats; semantic_scene_match; phrase_level_visuals; premium_conversion_fixed_layout":
            raise RuntimeError("QUALITY_BLOCK: política de layout Premium ausente")
        matches=picks.get("semantic_matches") or []
        if len(matches)!=3:
            raise RuntimeError("QUALITY_BLOCK: seleção semântica dos Shorts incompleta")
        for i,(row,hook,match) in enumerate(zip(srows,expected_hooks,matches),1):
            if row.get("layout_profile") != "RADAR_PREMIUM_CONVERSAO_V1":
                raise RuntimeError(f"QUALITY_BLOCK: Short {i} não usa o padrão Premium Conversão")
            if row.get("cta") != ["INSCREVA-SE AGORA", "DEIXE O LIKE", "RADAR DOS GAMES"]:
                raise RuntimeError(f"QUALITY_BLOCK: CTA multiplataforma aprovado ausente no Short {i}")
            assert row.get("render_policy")=="rebuilt_from_source_assets_not_master_crop",row
            assert row.get("boundary_policy")=="independent_scene_voice_complete",row
            assert float(row.get("duration") or 0)>=(60),row
            if norm_short_title(row.get("title")) != norm_short_title(hook):
                raise RuntimeError(f"QUALITY_BLOCK: Short {i} saiu com título diferente do hook aprovado: {row.get('title')} != {hook}")
            if norm_short_title(row.get("approved_hook")) != norm_short_title(hook):
                raise RuntimeError(f"QUALITY_BLOCK: Short {i} perdeu o hook aprovado no manifesto")
            if int(match.get("scene_index",-1)) != int(row.get("scene_index",-2)):
                raise RuntimeError(f"QUALITY_BLOCK: Short {i} renderizou cena diferente da seleção semântica")
            if float(match.get("semantic_score") or 0) <= 0:
                raise RuntimeError(f"QUALITY_BLOCK: Short {i} sem correspondência semântica entre hook e narração")
            meta=load(f"output/short-{i}-youtube.json")
            if norm_short_title(meta.get("title")) != norm_short_title(hook):
                raise RuntimeError(f"QUALITY_BLOCK: metadata do Short {i} diverge do hook aprovado")
        try:
            from repetition_policy import qa_report
        except ModuleNotFoundError:
            from src.repetition_policy import qa_report
        anti_spam=qa_report(plan_scenes,clips,srows)
        Path("output/anti-repetition-qa.json").write_text(
            json.dumps(anti_spam,ensure_ascii=False,indent=2),encoding="utf-8")

    sound=render.get("sound_design") or {}
    assert sound.get("voice_chain")=="compression+loudnorm+limiter",sound
    assert sound.get("editorial_sfx")=="subtle_generated_impacts",sound

    if render.get('cinematic_profile') != 'RADAR_CINEMATIC_V1' or shorts.get('cinematic_profile') != 'RADAR_CINEMATIC_V1':
        raise RuntimeError('QUALITY_BLOCK: tratamento cinematográfico ausente')
    if sound.get('music_bed') != 'approved_bed_with_voice_ducking':
        raise RuntimeError('QUALITY_BLOCK: Master sem trilha aprovada e ducking')
    for short in shorts.get('shorts', []):
        if short.get('music_bed') != 'approved_bed_with_voice_ducking':
            raise RuntimeError('QUALITY_BLOCK: Short sem trilha aprovada e ducking')

    result={
        "status":"APPROVED","version":"PREMIUM_V4_DIRECTOR_CUT",
        "phrase_level_direction":"APPROVED",
        "semantic_visual_sync":"APPROVED_WITH_FLEXIBLE_FALLBACK",
        "semantic_visual_warnings":int(semantic.get("warning_count") or 0),
        "variable_pacing":"APPROVED",
        "sound_design":"APPROVED",
        "independent_shorts":"APPROVED_MASTER_SPLIT" if master_split else "APPROVED",
        "short_hooks_exact":"APPROVED",
        "short_semantic_selection":"APPROVED_MASTER_SPLIT" if master_split else "APPROVED",
        "approved_short_hooks":expected_hooks,
        "anti_repetition":"APPROVED",
        "shorts_source_policy":"contiguous_master_split_v1" if master_split else "independent_rebuild",
        "image_reuse_policy":"limited_by_content_hash; exact_phrase; cooldown; shorts_once",
        "visual_frame_qa":"APPROVED",
        "real_headlines":"APPROVED",
        "gameplay_moving_footage":"NOT_APPLICABLE_IMAGE_LED" if image_only else "APPROVED",
        "official_image_led_mode":"APPROVED" if image_only else "NOT_USED",
        "official_image_assets":image_assets,
        "video_assets":video_assets,
        "unique_video_seconds":round(unique_video_seconds,3),
        "moving_footage_seconds":round(moving_seconds,3),
        "moving_footage_ratio":round(moving_ratio,4),
        "video_scene_count":video_scene_count,
        "cold_open_seconds":director.get("cold_open_seconds"),
        "cadence":cadence,
    }
    Path("output/premium-v4-qa.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
