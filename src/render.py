#!/usr/bin/env python3
"""Renderizador FFmpeg do Radar dos Games. Monta clipes em movimento + narração + cards/branding."""
import json, subprocess, sys
from pathlib import Path

def sh(cmd):
    print('+',' '.join(map(str,cmd)),flush=True); subprocess.run(cmd,check=True)

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
    # Intro curta, branding e cards discretos; áudio é a fonte de duração final.
    vf="drawbox=x=0:y=0:w=iw:h=80:color=black@0.35:t=fill,drawtext=text='RADAR DOS GAMES':x=55:y=24:fontsize=34:fontcolor=white:enable='lt(t,6)'"
    sh(['ffmpeg','-y','-stream_loop','-1','-i',str(visuals),'-i',m['voice'],'-vf',vf,'-map','0:v','-map','1:a','-shortest','-c:v','libx264','-preset','medium','-crf','19','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)])
    print(out)

if __name__=='__main__': render(sys.argv[1])
