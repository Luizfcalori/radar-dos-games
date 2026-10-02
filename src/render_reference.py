#!/usr/bin/env python3
"""Radar dos Games reference renderer. Separate from legacy render.py."""
import json, subprocess, sys
from pathlib import Path

def run(c): print('+',' '.join(c),flush=True); subprocess.run(c,check=True)
def esc(s): return s.replace('\\','\\\\').replace(':','\\:').replace("'","\\'")
def main(p):
 m=json.loads(Path(p).read_text(encoding='utf-8')); out=Path(m['output']); out.parent.mkdir(parents=True,exist_ok=True)
 clips=[Path(x) for x in m['clips'] if Path(x).exists()]; tmp=out.parent/'refbuild'; tmp.mkdir(exist_ok=True)
 ns=[]
 for i,c in enumerate(clips):
  n=tmp/f'{i:03}.mp4'; ns.append(n); run(['ffmpeg','-y','-i',str(c),'-vf','scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=30','-an','-c:v','libx264','-crf','20','-preset','veryfast',str(n)])
 lst=tmp/'concat.txt'; lst.write_text(''.join("file '%s'\n"%x.resolve() for x in ns)); bg=tmp/'bg.mp4'; run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(bg)])
 # Reference language: real 5s intro asset if provided, otherwise FAIL. Never synthesize a fake intro.
 intro=m.get('intro')
 if not intro or not Path(intro).exists(): raise RuntimeError('INTRO_REAL_REQUIRED: supply extracted approved Radar intro asset')
 body=tmp/'body.mp4'
 vf="drawbox=x=0:y=0:w=iw:h=52:color=black@0.42:t=fill,drawtext=text='RADAR DOS GAMES':x=34:y=13:fontsize=25:fontcolor=white"
 vf+=",drawbox=x=w-245:y=10:w=215:h=34:color=0x00B979@0.92:t=fill,drawtext=text='ESPECIAL':x=w-215:y=17:fontsize=19:fontcolor=white"
 for c in m.get('cards',[]):
  s,e=c['start'],c['end']; t=esc(c['title']); sub=esc(c.get('subtitle',''))
  vf+=f",drawbox=x=45:y=h-190:w=850:h=118:color=black@0.68:t=fill:enable='between(t,{s},{e})'"
  vf+=f",drawbox=x=45:y=h-190:w=9:h=118:color=0x00D58A:t=fill:enable='between(t,{s},{e})'"
  vf+=f",drawtext=text='{t}':x=78:y=h-172:fontsize=39:fontcolor=white:enable='between(t,{s},{e})'"
  if sub: vf+=f",drawtext=text='{sub}':x=78:y=h-120:fontsize=23:fontcolor=0x00E69A:enable='between(t,{s},{e})'"
 vf+=",drawtext=text='Fonte: material oficial':x=w-tw-24:y=h-35:fontsize=16:fontcolor=white@0.8"
 run(['ffmpeg','-y','-stream_loop','-1','-i',str(bg),'-i',m['voice'],'-vf',vf,'-map','0:v','-map','1:a','-shortest','-c:v','libx264','-crf','19','-preset','medium','-c:a','aac','-b:a','192k',str(body)])
 # Intro is preserved exactly and body follows it. Audio narration begins with body, like reference package.
 intro_n=tmp/'intro.mp4'; run(['ffmpeg','-y','-i',intro,'-t','5','-vf','scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=30','-c:v','libx264','-crf','19','-preset','medium','-c:a','aac','-ar','48000','-ac','2',str(intro_n)])
 concat=tmp/'final.txt'; concat.write_text("file '%s'\nfile '%s'\n"%(intro_n.resolve(),body.resolve()))
 run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(out)])
if __name__=='__main__': main(sys.argv[1])
