#!/usr/bin/env python3
"""Baixa apenas URLs de mídia explicitamente fornecidas/permitidas para a produção."""
import json, subprocess, sys
from pathlib import Path

def main(spec_path):
 spec=json.loads(Path(spec_path).read_text(encoding='utf-8')); out=Path('output/media'); out.mkdir(parents=True,exist_ok=True)
 clips=[]
 for i,item in enumerate(spec.get('media',[]),1):
  url=item['url']; dest=out/f'clip_{i:02}.mp4'
  # yt-dlp é usado como transportador; a lista deve ser composta por material autorizado/oficial permitido para uso.
  subprocess.run(['yt-dlp','--no-playlist','-f','bv*[height<=1080]+ba/b[height<=1080]','--merge-output-format','mp4','-o',str(dest),url],check=True)
  clips.append(str(dest))
 Path('output/clips.json').write_text(json.dumps({'clips':clips},indent=2),encoding='utf-8')
 print(json.dumps({'clips':clips}))
if __name__=='__main__': main(sys.argv[1])
