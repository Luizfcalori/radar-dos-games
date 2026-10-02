#!/usr/bin/env python3
"""Baixa URLs de mídia permitidas com fallbacks gratuitos e valida o arquivo real."""
import json, subprocess, sys
from pathlib import Path

def valid(p):
    if not p.exists() or p.stat().st_size < 500_000: return False
    try:
        subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name','-of','csv=p=0',str(p)],check=True,stdout=subprocess.DEVNULL)
        return True
    except Exception: return False

def attempt(url,dest,fmt,args=None):
    cmd=['yt-dlp','--no-playlist','--retries','3','--fragment-retries','3','--socket-timeout','20']+(args or [])+['-f',fmt,'--merge-output-format','mp4','-o',str(dest),url]
    try: subprocess.run(cmd,check=True); return valid(dest)
    except subprocess.CalledProcessError:
        dest.unlink(missing_ok=True); return False

def main(spec_path):
    spec=json.loads(Path(spec_path).read_text(encoding='utf-8')); out=Path('output/media'); out.mkdir(parents=True,exist_ok=True)
    clips=[]; errors=[]
    for i,item in enumerate(spec.get('media',[]),1):
        url=item['url']; dest=out/f'clip_{i:02}.mp4'
        routes=[
          ('bv*[height<=1080]+ba/b[height<=1080]',[]),
          ('b[height<=1080]/best',[]),
          ('bv*[height<=720]+ba/b[height<=720]', ['--extractor-args','youtube:player_client=android,web']),
          ('best', ['--extractor-args','youtube:player_client=android,web'])]
        ok=False
        for fmt,args in routes:
            if attempt(url,dest,fmt,args): ok=True; break
        if ok: clips.append(str(dest))
        else: errors.append({'url':url,'error':'all_free_download_routes_failed'})
    Path('output/clips.json').write_text(json.dumps({'clips':clips,'errors':errors},indent=2),encoding='utf-8')
    if not clips: raise RuntimeError('Nenhuma mídia válida baixada; '+json.dumps(errors))
    print(json.dumps({'clips':clips,'errors':errors}))
if __name__=='__main__': main(sys.argv[1])
