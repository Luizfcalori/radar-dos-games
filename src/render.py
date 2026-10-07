#!/usr/bin/env python3
"""Renderizador editorial Radar dos Games no padrão visual aprovado."""
import json
import math
import subprocess
import sys
from pathlib import Path

FPS=30; W=1920; H=1080
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
WATERMARK_X="w-tw-44"; WATERMARK_Y=30; WATERMARK_SIZE=24
CARD_X=62; CARD_Y=850; CARD_W=1240; CARD_H=138; CARD_ACCENT_W=10
CARD_BG="black@0.68"; CARD_ACCENT="0x00DCC8@0.96"; CARD_IN=0.45; CARD_MAX_SECONDS=5.8; CARD_END_MARGIN=0.15
TITLE_X=102; TITLE_Y=869; TITLE_SIZE=40; SUBTITLE_X=102; SUBTITLE_Y=927; SUBTITLE_SIZE=25; SUBTITLE_COLOR="0x7FE8FF"
AUDIO_NORMALIZE="loudnorm=I=-16:LRA=7:TP=-1.5"
IMAGE_EXTENSIONS={".jpg",".jpeg",".png",".webp"}

def sh(cmd):
    print('+',' '.join(map(str,cmd)),flush=True);subprocess.run(cmd,check=True)

def esc(text):
    return str(text).replace('\\','\\\\').replace(':','\\:').replace("'","\\'").replace('%','\\%')

def asset_map(items):
    result={}
    for pos,item in enumerate(items,1):
        if isinstance(item,str):
            p=Path(item);result[pos]={'index':pos,'path':item,'type':'image' if p.suffix.lower() in IMAGE_EXTENSIONS else 'video','approved':True}
        else:
            result[int(item.get('index',pos))]=item
    return result

def is_video(asset):
    p=Path(asset['path']);return asset.get('type','image')!='image' and p.suffix.lower() not in IMAGE_EXTENSIONS

def ordered_scene_indices(indices,assets):
    return sorted(indices,key=lambda idx:0 if is_video(assets[idx]) else 1)

def strict_scene_indices(raw_indices,assets):
    """Nunca injeta mídia fora da lista explícita da cena."""
    chosen=[]
    for idx in raw_indices:
        if idx in assets and idx not in chosen and assets[idx].get('approved',True):chosen.append(idx)
    return chosen

def scene_sequence(indices,cuts=4):
    """Cortes usando somente assets aprovados da própria cena."""
    if not indices:return []
    if len(indices)>=cuts:return indices[:cuts]
    return [indices[i%len(indices)] for i in range(cuts)]

def cut_count_for_duration(duration,target=4.2,min_cut=3.0,max_cut=6.0):
    """Ritmo Premium V3: mudança visual em média a cada 3-6 segundos."""
    duration=max(0.1,float(duration))
    if duration<=max_cut:return 1
    minimum=max(1,math.ceil(duration/max_cut))
    maximum=max(minimum,math.floor(duration/min_cut))
    desired=max(1,round(duration/target))
    return max(minimum,min(8,maximum,desired))

def media_duration(path):
    try:return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(path)],text=True).strip())
    except:return 0.0

def video_seek_offset(path,piece_no,piece_duration):
    total=media_duration(path);max_seek=total-piece_duration-0.75
    if max_seek<=1:return 0.0
    return round((piece_no*7.37)%max_seek,3)

def render_piece(asset,duration,dest,card=None,piece_no=0,motion_profile='subtle_non_destructive'):
    path=Path(asset['path']);typ=asset.get('type','image')
    if not path.exists():raise RuntimeError(f'Asset ausente: {path}')
    image_mode=typ=='image' or path.suffix.lower() in IMAGE_EXTENSIONS
    if image_mode:
        input_args=['-loop','1','-i',str(path)]
    else:
        seek=video_seek_offset(path,piece_no,duration);input_args=['-stream_loop','-1']
        if seek>0:input_args+=['-ss',f'{seek:.3f}']
        input_args+=['-i',str(path)]
    if image_mode and motion_profile=='subtle_non_destructive':
        base=(f'[0:v]fps={FPS},split=2[bg0][fg0];'
              f'[bg0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:14,eq=brightness=-0.18:saturation=0.88[bg];'
              f'[fg0]scale={W-80}:{H-50}:force_original_aspect_ratio=decrease,setsar=1[fg];'
              f"[bg][fg]overlay=x='(W-w)/2+8*sin(t*0.65)':y='(H-h)/2+5*cos(t*0.43)',")
    else:
        base=(f'[0:v]fps={FPS},split=2[bg0][fg0];'
              f'[bg0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:14,eq=brightness=-0.18:saturation=0.88[bg];'
              f'[fg0]scale={W}:{H}:force_original_aspect_ratio=decrease,setsar=1[fg];'
              f'[bg][fg]overlay=(W-w)/2:(H-h)/2,')
    filters=[f"drawtext=fontfile='{FONT}':text='RADAR DOS GAMES':x={WATERMARK_X}:y={WATERMARK_Y}:fontsize={WATERMARK_SIZE}:fontcolor=white@0.72:borderw=1:bordercolor=black@0.55:expansion=none"]
    if card:
        show_end=max(1.2,min(duration-CARD_END_MARGIN,CARD_MAX_SECONDS));title=esc(card.get('title',''));subtitle=esc(card.get('subtitle',''));enable=f'between(t,{CARD_IN:.2f},{show_end:.3f})'
        filters += [
            f"drawbox=x={CARD_X}:y={CARD_Y}:w={CARD_W}:h={CARD_H}:color={CARD_BG}:t=fill:enable='{enable}'",
            f"drawbox=x={CARD_X}:y={CARD_Y}:w={CARD_ACCENT_W}:h={CARD_H}:color={CARD_ACCENT}:t=fill:enable='{enable}'",
            f"drawtext=fontfile='{FONT}':text='{title}':x={TITLE_X}:y={TITLE_Y}:fontsize={TITLE_SIZE}:fontcolor=white:borderw=2:bordercolor=black@0.65:expansion=none:enable='{enable}'"
        ]
        if subtitle:filters.append(f"drawtext=fontfile='{FONT}':text='{subtitle}':x={SUBTITLE_X}:y={SUBTITLE_Y}:fontsize={SUBTITLE_SIZE}:fontcolor={SUBTITLE_COLOR}:borderw=1:bordercolor=black@0.7:expansion=none:enable='{enable}'")
    fc=base+','.join(filters)+',format=yuv420p[v]'
    sh(['ffmpeg','-y','-v','error',*input_args,'-t',f'{duration:.3f}','-filter_complex',fc,'-map','[v]','-an','-r',str(FPS),'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',str(dest)])

def normalize_intro(src,dest):
    sh(['ffmpeg','-y','-v','error','-i',str(src),'-vf',f'scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,fps={FPS},setsar=1,format=yuv420p','-af','aresample=48000','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2',str(dest)])

def render(manifest_path):
    m=json.loads(Path(manifest_path).read_text(encoding='utf-8'));out=Path(m.get('output','output/master.mp4'));out.parent.mkdir(parents=True,exist_ok=True);tmp=out.parent/'editorial';tmp.mkdir(exist_ok=True)
    intro=Path(m['intro'])
    if not intro.exists():raise RuntimeError('QUALITY_BLOCK: intro oficial real ausente')
    timings=json.loads(Path(m['voice_timings']).read_text(encoding='utf-8'));voice_segments=timings.get('segments',[]);scenes=m.get('scenes',[])
    if len(voice_segments)!=len(scenes):raise RuntimeError(f'QUALITY_BLOCK: {len(voice_segments)} blocos de voz para {len(scenes)} cenas')
    assets=asset_map(m.get('assets') or m.get('clips') or [])
    rejected=[idx for idx,a in assets.items() if not a.get('approved',True)]
    pieces=[];qa_scenes=[];global_piece_no=0
    for scene_no,(timing,scene) in enumerate(zip(voice_segments,scenes),1):
        duration=float(timing['duration']);raw_indices=[int(x) for x in scene.get('media_indices',[])]
        if not raw_indices:raise RuntimeError(f'Cena {scene_no} sem mídia contextual explícita')
        missing=[x for x in raw_indices if x not in assets]
        if missing:raise RuntimeError(f'Cena {scene_no} aponta para assets ausentes: {missing}')
        bad=[x for x in raw_indices if not assets[x].get('approved',True)]
        if bad:raise RuntimeError(f'QUALITY_BLOCK: cena {scene_no} contém assets não aprovados: {bad}')
        strict=strict_scene_indices(raw_indices,assets);indices=ordered_scene_indices(strict,assets)
        editing=scene.get('editing') or {};target=float(editing.get('cut_target_seconds',4.2))
        cuts=int(editing.get('planned_cuts') or cut_count_for_duration(duration,target))
        sequence=scene_sequence(indices,cuts)
        if not sequence:raise RuntimeError(f'Cena {scene_no} sem sequência de mídia aprovada')
        per_piece=duration/len(sequence);scene_piece_paths=[]
        for j,idx in enumerate(sequence):
            global_piece_no+=1;piece_duration=duration-per_piece*j if j==len(sequence)-1 else per_piece;p=tmp/f'scene_{scene_no:02d}_{j+1:02d}.mp4'
            render_piece(assets[idx],piece_duration,p,card={'title':scene.get('title',''),'subtitle':scene.get('subtitle','')} if j==0 else None,piece_no=global_piece_no,motion_profile=editing.get('motion_profile','subtle_non_destructive'))
            pieces.append(p);scene_piece_paths.append(str(p))
        qa_scenes.append({'scene':scene_no,'voice_start':timing.get('start'),'voice_end':timing.get('end'),'voice_duration':round(duration,3),'media_indices_explicit':raw_indices,'sequence':sequence,'cut_count':len(sequence),'average_cut_seconds':round(duration/len(sequence),3),'distinct_assets_in_scene':len(set(sequence)),'all_assets_explicit':set(sequence).issubset(set(raw_indices)),'gameplay_first':bool(indices and is_video(assets[indices[0]])),'motion_profile':editing.get('motion_profile','subtle_non_destructive'),'semantic_subject':scene.get('semantic_subject'),'title':scene.get('title'),'pieces':scene_piece_paths})
    concat_visuals=tmp/'visuals.txt';concat_visuals.write_text(''.join(f"file '{p.resolve()}'\n" for p in pieces),encoding='utf-8');visuals=tmp/'body_visuals.mp4'
    sh(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(concat_visuals),'-c','copy',str(visuals)])
    body=tmp/'body_av.mp4';sh(['ffmpeg','-y','-v','error','-i',str(visuals),'-i',m['voice'],'-map','0:v:0','-map','1:a:0','-shortest','-c:v','copy','-af',AUDIO_NORMALIZE,'-c:a','aac','-b:a','192k','-ar','48000','-ac','2',str(body)])
    intro_norm=tmp/'intro.mp4';normalize_intro(intro,intro_norm);final_list=tmp/'final.txt';final_list.write_text(f"file '{intro_norm.resolve()}'\nfile '{body.resolve()}'\n",encoding='utf-8')
    sh(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(final_list),'-c','copy','-movflags','+faststart',str(out)])
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size','-show_entries','stream=codec_type,width,height,r_frame_rate','-of','json',str(out)],text=True)
    qa={'master':str(out),'standard':'radar-dos-games-premium-v3','premium_version':m.get('premium_version','PREMIUM_V3'),'intro_source':str(intro),'intro_audio_preserved':True,'voice':timings.get('voice'),'semantic_timing_source':timings.get('source'),'framing_policy':'full_source_visible; blurred_background_fill; no_destructive_crop','motion_policy':'subtle_non_destructive_on_images; source_fully_visible','media_policy':'ONLY explicit approved scene assets; never auto-fill from global pool; varied seek only inside approved videos','rejected_global_assets':rejected,'scenes':qa_scenes,'card_style':{'x':CARD_X,'y':CARD_Y,'w':CARD_W,'h':CARD_H,'title_x':TITLE_X,'title_y':TITLE_Y,'subtitle_x':SUBTITLE_X,'subtitle_y':SUBTITLE_Y,'shadow_attached_to_text':True},'probe':json.loads(probe)}
    Path('output/qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'master':str(out),'scenes':len(qa_scenes),'intro':str(intro)},ensure_ascii=False))
if __name__=='__main__':render(sys.argv[1])
