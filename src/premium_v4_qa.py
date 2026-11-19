#!/usr/bin/env python3
"""Quality gate for Premium V4 Master plus three narrated Master-derived Shorts."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

def load(path):
    p=Path(path)
    if not p.exists():
        raise RuntimeError(f"QUALITY_BLOCK: arquivo ausente {path}")
    return json.loads(p.read_text(encoding="utf-8"))

def norm(value):
    value=re.sub(r"(?i)\s*#shorts?\b","",str(value or ""))
    return re.sub(r"\s+"," ",value).strip().casefold()

def norm_short_title(value):
    return norm(value)


def probe(path):
    data=json.loads(subprocess.check_output([
        "ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)
    ],text=True))
    streams=data.get("streams") or []
    video=next((s for s in streams if s.get("codec_type")=="video"),None)
    audio=next((s for s in streams if s.get("codec_type")=="audio"),None)
    return data,video,audio,float((data.get("format") or {}).get("duration") or 0)

def main():
    storyboard=load("output/media-first-storyboard.json")
    script=Path("output/auto-script.txt")
    if not script.exists():
        raise RuntimeError("QUALITY_BLOCK: roteiro definitivo ausente")
    actual=hashlib.sha256(script.read_bytes()).hexdigest()
    if storyboard.get("policy")!="MEDIA_FIRST_V1" or storyboard.get("status")!="APPROVED" or storyboard.get("script_sha256")!=actual:
        raise RuntimeError("QUALITY_BLOCK: roteiro ou decupagem media-first inválidos")

    plan=load("output/auto-media-plan.json")
    clips=load("output/clips.json")
    semantic=load("output/semantic-visual-qa.json")
    render=load("output/qa.json")
    shorts=load("output/shorts/manifest.json")
    picks=load("output/short-picks.json")
    frames=load("output/visual-frame-qa.json")
    timings=load("output/voice-timings.json")

    if plan.get("premium_version")!="PREMIUM_V4_DIRECTOR_CUT":
        raise RuntimeError("QUALITY_BLOCK: plano não está no padrão Premium V4")
    if semantic.get("status")!="APPROVED":
        raise RuntimeError("QUALITY_BLOCK: gate semântico fala/imagem não aprovado")
    if render.get("standard")!="radar-dos-games-premium-v4-director-cut":
        raise RuntimeError("QUALITY_BLOCK: render Master fora do padrão Premium V4")
    if render.get("editing_policy")!="phrase_level_beats; variable_pacing; selective_keyword_overlays":
        raise RuntimeError("QUALITY_BLOCK: política de edição do Master ausente")
    if frames.get("status")!="APPROVED":
        raise RuntimeError("QUALITY_BLOCK: QA visual por frames não aprovado")
    if timings.get("source")!="paragraph_boundaries+tts_word_boundaries":
        raise RuntimeError("QUALITY_BLOCK: timings de narração não são confiáveis")
    if not clips.get("publishable_media"):
        raise RuntimeError("QUALITY_BLOCK: pacote de mídia não está publicável")

    video_assets=int(clips.get("video_assets") or 0)
    unique_video_seconds=float(clips.get("unique_video_seconds") or 0)
    required_videos=max(1,int(plan.get("minimum_video_assets") or 0))
    required_unique=max(15.0,float(plan.get("minimum_unique_video_seconds") or 0))
    if video_assets<required_videos:
        raise RuntimeError(f"QUALITY_BLOCK: gameplay/vídeo oficial ausente ({video_assets}/{required_videos})")
    if unique_video_seconds<required_unique:
        raise RuntimeError(f"QUALITY_BLOCK: somente {unique_video_seconds:.1f}s de vídeo oficial único; mínimo {required_unique:.1f}s")

    plan_scenes=plan.get("scenes") or []
    if len(plan_scenes)<3:
        raise RuntimeError("QUALITY_BLOCK: menos de três cenas editoriais aprovadas")
    asset_map={int(a["index"]):a for a in clips.get("assets",[]) if a.get("approved")}
    body_seconds=moving_seconds=0.0
    video_scene_count=0
    for i,scene in enumerate(plan_scenes,1):
        title=str(scene.get("title") or "").strip()
        if not title or re.fullmatch(r"(DESTAQUE\s*\d*|CENA\s*\d+.*)",title,re.I):
            raise RuntimeError(f"QUALITY_BLOCK: headline genérica/ausente na cena {i}: {title}")
        has_video=False
        for beat in scene.get("beats") or []:
            duration=float(beat.get("duration") or 0)
            body_seconds+=duration
            asset=asset_map.get(int(beat.get("media_index") or 0),{})
            if asset.get("type")=="video":
                moving_seconds+=duration
                has_video=True
        video_scene_count+=int(has_video)
    moving_ratio=moving_seconds/body_seconds if body_seconds else 0.0
    if moving_ratio<0.35:
        raise RuntimeError(f"QUALITY_BLOCK: gameplay em movimento ocupa {moving_ratio:.1%}; mínimo 35%")
    if video_scene_count<min(3,len(plan_scenes)):
        raise RuntimeError(f"QUALITY_BLOCK: gameplay presente em somente {video_scene_count} cenas")

    rendered_scenes=render.get("scenes") or []
    if len(rendered_scenes)!=len(plan_scenes):
        raise RuntimeError("QUALITY_BLOCK: cenas do Master divergem do plano editorial")
    for row in rendered_scenes:
        avg=float(row.get("average_beat_seconds") or 0)
        if not 0.05<=avg<=10.10 or row.get("phrase_level") is not True or int(row.get("beats") or 0)<1:
            raise RuntimeError(f"QUALITY_BLOCK: cadência/edição inválida na cena {row.get('scene')}")

    master=Path("output/master.mp4")
    if not master.exists():
        raise RuntimeError("QUALITY_BLOCK: Master final ausente")
    _,master_video,master_audio,master_duration=probe(master)
    if not master_video or not master_audio or master_duration<=0:
        raise RuntimeError("QUALITY_BLOCK: Master sem vídeo ou áudio/narração")

    rows=shorts.get("shorts") or []
    hooks=[str(x or "").strip() for x in (picks.get("expected_hooks") or [])]
    indexes=[int(x) for x in (picks.get("scene_indexes") or [])]
    if len(rows)!=3 or len(hooks)!=3 or len(indexes)!=3 or any(not x for x in hooks):
        raise RuntimeError("QUALITY_BLOCK: são obrigatórios exatamente 3 Shorts, 3 hooks e 3 cenas")
    if shorts.get("source_policy")!="master_timeline_crops_preserve_original_audio":
        raise RuntimeError("QUALITY_BLOCK: Shorts não foram derivados da timeline do Master")
    if shorts.get("audio_policy")!="mandatory_original_master_audio; no_an; no_silent_rebuild":
        raise RuntimeError("QUALITY_BLOCK: política de áudio original dos Shorts ausente")

    ranges=[]
    short_report=[]
    for i,(row,hook,scene_index) in enumerate(zip(rows,hooks,indexes),1):
        if norm(row.get("title"))!=norm(hook) or norm(row.get("approved_hook"))!=norm(hook):
            raise RuntimeError(f"QUALITY_BLOCK: hook do Short {i} diverge do hook aprovado")
        if int(row.get("scene_index",-1))!=scene_index:
            raise RuntimeError(f"QUALITY_BLOCK: Short {i} não corresponde à cena selecionada")
        if row.get("source")!="output/master.mp4" or row.get("render_policy")!="direct_master_timeline_crop_with_original_narration":
            raise RuntimeError(f"QUALITY_BLOCK: Short {i} não é corte direto do Master")
        if row.get("boundary_policy")!="complete_master_voice_segment":
            raise RuntimeError(f"QUALITY_BLOCK: Short {i} não respeita limite de fala")
        start=float(row.get("start") or 0)
        _,v,a,d=probe(row["path"])
        if not v or not a:
            raise RuntimeError(f"QUALITY_BLOCK: Short {i} sem vídeo ou trilha de áudio")
        if d<30:
            raise RuntimeError(f"QUALITY_BLOCK: Short {i} tem {d:.1f}s; mínimo 30s")
        if (int(v.get("width") or 0),int(v.get("height") or 0))!=(1080,1920):
            raise RuntimeError(f"QUALITY_BLOCK: Short {i} não está em 1080x1920")
        if start<0 or start+d>master_duration+0.5:
            raise RuntimeError(f"QUALITY_BLOCK: Short {i} está fora da timeline do Master")
        ranges.append((start,start+d))
        short_report.append({"index":i,"duration":round(d,3),"audio":"present","source":"master_timeline"})

    for i,(left,right) in enumerate(ranges):
        for j,(other_left,other_right) in enumerate(ranges[i+1:],i+1):
            if min(right,other_right)-max(left,other_left)>1.0:
                raise RuntimeError(f"QUALITY_BLOCK: Shorts {i+1} e {j+1} usam o mesmo trecho da timeline")

    sound=render.get("sound_design") or {}
    if sound.get("voice_chain")!="compression+loudnorm+limiter" or sound.get("editorial_sfx")!="subtle_generated_impacts":
        raise RuntimeError("QUALITY_BLOCK: cadeia de áudio cinematográfica do Master ausente")
    if render.get("cinematic_profile")!="RADAR_CINEMATIC_V1":
        raise RuntimeError("QUALITY_BLOCK: tratamento cinematográfico do Master ausente")
    if sound.get("music_bed")!="approved_bed_with_voice_ducking":
        raise RuntimeError("QUALITY_BLOCK: Master sem trilha aprovada e ducking")

    result={
        "status":"APPROVED","version":"PREMIUM_V4_MASTER_CUTS",
        "master_audio":"APPROVED","master_visual_qa":"APPROVED",
        "semantic_visual_sync":"APPROVED","phrase_level_direction":"APPROVED",
        "sound_design":"APPROVED","master_derived_shorts":"APPROVED",
        "short_audio_streams":"3/3","short_hooks_exact":"APPROVED",
        "short_scene_mapping":"APPROVED","real_headlines":"APPROVED",
        "approved_short_hooks":hooks,"shorts":short_report,
        "gameplay_moving_footage":"APPROVED","video_assets":video_assets,
        "unique_video_seconds":round(unique_video_seconds,3),
        "moving_footage_ratio":round(moving_ratio,4),
        "video_scene_count":video_scene_count,
    }
    Path("output/premium-v4-qa.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
