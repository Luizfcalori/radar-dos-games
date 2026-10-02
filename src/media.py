#!/usr/bin/env python3
"""Obtém mídia relevante; nunca libera fallback genérico como conteúdo publicável."""
import json, subprocess, sys, urllib.request
from pathlib import Path

def valid_video(p):
    if not p.exists() or p.stat().st_size < 100_000: return False
    try:
        subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name','-of','csv=p=0',str(p)],check=True,stdout=subprocess.DEVNULL); return True
    except Exception: return False

def direct(url,dest):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.bandainamcoent.com/'})
        with urllib.request.urlopen(req,timeout=30) as r, open(dest,'wb') as f:
            while True:
                b=r.read(1024*1024)
                if not b: break
                f.write(b)
        return valid_video(dest)
    except Exception as e:
        print('direct failed:',e); dest.unlink(missing_ok=True); return False

def ytdlp(url,dest):
    cmd=['yt-dlp','--no-playlist','--retries','1','--fragment-retries','1','--socket-timeout','15','-f','b[height<=1080]/best','--merge-output-format','mp4','-o',str(dest),url]
    try: subprocess.run(cmd,check=True); return valid_video(dest)
    except subprocess.CalledProcessError: dest.unlink(missing_ok=True); return False

def main(spec_path):
    spec=json.loads(Path(spec_path).read_text(encoding='utf-8')); out=Path('output/media'); out.mkdir(parents=True,exist_ok=True)
    clips=[]; errors=[]
    for i,item in enumerate(spec.get('media',[]),1):
        url=item['url']; dest=out/f'clip_{i:02}.mp4'; ok=False
        if url.lower().split('?')[0].endswith(('.mp4','.mov','.webm')): ok=direct(url,dest)
        if not ok: ok=ytdlp(url,dest)
        if ok: clips.append(str(dest))
        else: errors.append({'url':url,'error':'remote_media_unavailable'})
    manifest={'clips':clips,'errors':errors,'publishable_media':bool(clips),'generic_fallback':False}
    Path('output/clips.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    if not clips:
        raise RuntimeError('QUALITY_BLOCK: nenhuma midia visual relevante obtida; fallback generico proibido')
    print(json.dumps(manifest))
if __name__=='__main__': main(sys.argv[1])
