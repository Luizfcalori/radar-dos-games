#!/usr/bin/env python3
"""Renderizador FFmpeg Radar dos Games: intro neon oficial + mídia + cards sincronizados + narração."""
import json, subprocess, sys
from pathlib import Path

def sh(cmd):
    print('+',' '.join(map(str,cmd)),flush=True); subprocess.run(cmd,check=True)

def esc(s):
    return s.replace('\\','\\\\').replace(':','\\:').replace("'","\\'")

def render(manifest_path):
    m=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    clips=[Path(x) for x in m['clips'] if Path(x).exists()]
    if not clips: raise RuntimeError('Nenhum clipe válido para renderizar')
    out=Path(m.get('output','output/master.mp4')); out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.parent/'normalized'; tmp.mkdir(exist_ok=True)
    norm=[]
    for i,c in enumerate(clips):
        p=tmp/f'{i:03}.mp4'; norm.append(p)
        sh(['ffmpeg','-y','-i',str(c),'-vf','scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30','-an','-c:v','libx264','-preset','veryfast','-crf','21',str(p)])
    lst=tmp/'concat.txt'; lst.write_text(''.join(f"file '{p.resolve()}'\n" for p in norm))
    visuals=tmp/'visuals.mp4'; sh(['ffmpeg','-y','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(visuals)])

    # Abertura aprovada: radar ativando -> controle/branding -> logo completo -> transição ao tema.
    intro=(
      "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.88:t=fill:enable='between(t,0,1.5)',"
      "drawtext=text='◉':x=(w-text_w)/2:y=(h-text_h)/2-90:fontsize=190:fontcolor=0x00F5B8:enable='between(t,0,1.5)',"
      "drawtext=text='RADAR ATIVANDO':x=(w-text_w)/2:y=h*0.72:fontsize=46:fontcolor=0x00F5B8:enable='between(t,0,1.5)',"
      "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.68:t=fill:enable='between(t,1.5,3)',"
      "drawtext=text='🎮':x=(w-text_w)/2:y=(h-text_h)/2-125:fontsize=180:fontcolor=white:enable='between(t,1.5,3)',"
      "drawtext=text='RADAR DOS GAMES':x=(w-text_w)/2:y=h*0.66:fontsize=72:fontcolor=white:borderw=3:bordercolor=0x00EFB0:enable='between(t,1.5,4.5)',"
      "drawtext=text='Notícias  •  Lançamentos  •  Gameplays':x=(w-text_w)/2:y=h*0.76:fontsize=34:fontcolor=0x55EFFF:enable='between(t,3,4.5)',"
      "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.42:t=fill:enable='between(t,4.5,6)',"
      "drawtext=text='ACE COMBAT 8':x=(w-text_w)/2:y=(h-text_h)/2-45:fontsize=92:fontcolor=white:borderw=4:bordercolor=black:enable='between(t,4.5,6)',"
      "drawtext=text='WINGS OF THEVE':x=(w-text_w)/2:y=(h-text_h)/2+70:fontsize=46:fontcolor=0x00F5B8:borderw=2:bordercolor=black:enable='between(t,4.5,6)'"
    )
    cards=m.get('cards') or [
      {'start':18,'end':25,'title':'ACE COMBAT 8','subtitle':'O retorno da franquia depois de 7 anos'},
      {'start':52,'end':59,'title':'UNREAL ENGINE 5','subtitle':'Nova geração de combate aéreo'},
      {'start':90,'end':97,'title':'JOKER FLIGHT','subtitle':'Esquadrão, campanha e novas missões'},
      {'start':128,'end':135,'title':'PS5 • XBOX SERIES • PC','subtitle':'Disponível nas plataformas atuais'},
      {'start':166,'end':173,'title':'MULTIPLAYER + CROSS-PLAY','subtitle':'Combate online e personalização'},
      {'start':204,'end':211,'title':'RADAR DOS GAMES','subtitle':'Like + inscrição para mais novidades'}
    ]
    vf=intro
    for c in cards:
        s,e=float(c['start']),float(c['end']); title=esc(c['title']); sub=esc(c.get('subtitle',''))
        vf += f",drawbox=x=70:y=h-245:w=1050:h=145:color=black@0.72:t=fill:enable='between(t,{s},{e})'"
        vf += f",drawbox=x=70:y=h-245:w=12:h=145:color=0x00F5B8:t=fill:enable='between(t,{s},{e})'"
        vf += f",drawtext=text='{title}':x=110:y=h-220:fontsize=48:fontcolor=white:borderw=1:bordercolor=black:enable='between(t,{s},{e})'"
        if sub:
            vf += f",drawtext=text='{sub}':x=110:y=h-158:fontsize=28:fontcolor=0x55EFFF:borderw=1:bordercolor=black:enable='between(t,{s},{e})'"
    # Assinatura discreta permanente depois da intro.
    vf += ",drawtext=text='RADAR DOS GAMES':x=w-tw-55:y=35:fontsize=26:fontcolor=white@0.78:borderw=1:bordercolor=black@0.5:enable='gte(t,6)'"
    sh(['ffmpeg','-y','-stream_loop','-1','-i',str(visuals),'-i',m['voice'],'-vf',vf,'-map','0:v','-map','1:a','-shortest','-c:v','libx264','-preset','medium','-crf','19','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)])
    print(out)

if __name__=='__main__': render(sys.argv[1])
