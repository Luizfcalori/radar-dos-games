#!/usr/bin/env python3
"""Obtém mídia permitida sem deixar a produção parar por bloqueios do YouTube."""
import json, subprocess, sys, urllib.request
from pathlib import Path


def valid(p):
    if not p.exists() or p.stat().st_size < 100_000: return False
    try:
        subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name','-of','csv=p=0',str(p)],check=True,stdout=subprocess.DEVNULL)
        return True
    except Exception: return False


def direct(url,dest):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=30) as r, open(dest,'wb') as f:
            while True:
                b=r.read(1024*1024)
                if not b: break
                f.write(b)
        return valid(dest)
    except Exception as e:
        print('direct failed:',e); dest.unlink(missing_ok=True); return False


def ytdlp(url,dest):
    # Uma única tentativa curta. YouTube em runner de datacenter pode exigir login/bot check.
    cmd=['yt-dlp','--no-playlist','--retries','1','--fragment-retries','1','--socket-timeout','15','-f','b[height<=1080]/best','--merge-output-format','mp4','-o',str(dest),url]
    try: subprocess.run(cmd,check=True); return valid(dest)
    except subprocess.CalledProcessError:
        dest.unlink(missing_ok=True); return False


def generated(dest,title='RADAR DOS GAMES'):
    # Fallback 100% local/gratuito: fundo animado para manter voz e produção funcionando.
    safe=title.replace("'","").replace(':',' -')[:80]
    vf=("drawbox=x=0:y=0:w=iw:h=ih:color=0x071426:t=fill,"
        "drawgrid=width=120:height=120:thickness=2:color=white@0.06,"
        "drawtext=text='RADAR DOS GAMES':x=(w-text_w)/2:y=h*0.38:fontsize=72:fontcolor=white,"
        f"drawtext=text='{safe}':x=(w-text_w)/2:y=h*0.52:fontsize=42:fontcolor=white")
    subprocess.run(['ffmpeg','-y','-f','lavfi','-i','color=c=0x071426:s=1920x1080:r=30:d=12','-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','20',str(dest)],check=True)
    return valid(dest)


def main(spec_path):
    spec=json.loads(Path(spec_path).read_text(encoding='utf-8')); out=Path('output/media'); out.mkdir(parents=True,exist_ok=True)
    clips=[]; errors=[]
    for i,item in enumerate(spec.get('media',[]),1):
        url=item['url']; dest=out/f'clip_{i:02}.mp4'; ok=False
        if url.lower().split('?')[0].endswith(('.mp4','.mov','.webm')): ok=direct(url,dest)
        if not ok: ok=ytdlp(url,dest)
        if ok: clips.append(str(dest))
        else: errors.append({'url':url,'error':'remote_media_unavailable'})
    if not clips:
        dest=out/'fallback_generated.mp4'
        generated(dest,spec.get('title','ACE COMBAT 8 - WINGS OF THEVE'))
        clips.append(str(dest)); errors.append({'fallback':'generated_local_visual','status':'used'})
    Path('output/clips.json').write_text(json.dumps({'clips':clips,'errors':errors},indent=2),encoding='utf-8')
    print(json.dumps({'clips':clips,'errors':errors}))
if __name__=='__main__': main(sys.argv[1])
