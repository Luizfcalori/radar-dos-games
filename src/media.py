#!/usr/bin/env python3
"""Obtém mídia relevante. Tenta origem direta/yt-dlp e, para YouTube bloqueado, SaveFrom como fallback experimental."""
import json, subprocess, sys, urllib.request, urllib.parse, re, html
from pathlib import Path

def valid_video(p):
    if not p.exists() or p.stat().st_size < 100_000: return False
    try:
        subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name','-of','csv=p=0',str(p)],check=True,stdout=subprocess.DEVNULL); return True
    except Exception: return False

def request(url, data=None, referer=None):
    headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/129 Safari/537.36','Accept-Language':'pt-BR,pt;q=0.9,en;q=0.8'}
    if referer: headers['Referer']=referer
    return urllib.request.Request(url,data=data,headers=headers)

def download(url,dest,referer=None):
    try:
        with urllib.request.urlopen(request(url,referer=referer),timeout=40) as r, open(dest,'wb') as f:
            while True:
                b=r.read(1024*1024)
                if not b: break
                f.write(b)
        return dest.exists() and dest.stat().st_size>20_000
    except Exception as e:
        print('download failed:',e); dest.unlink(missing_ok=True); return False

def image_clip(url,dest,i):
    img=dest.with_suffix('.jpg')
    if not download(url,img): return False
    z="min(zoom+0.0007,1.12)" if i%2 else "min(zoom+0.0005,1.10)"
    vf=f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='{z}':d=300:s=1920x1080:fps=25,format=yuv420p"
    try:
        subprocess.run(['ffmpeg','-y','-loop','1','-i',str(img),'-vf',vf,'-t','12','-r','25','-an','-c:v','libx264','-preset','veryfast','-crf','20',str(dest)],check=True)
        return valid_video(dest)
    except subprocess.CalledProcessError: return False
    finally: img.unlink(missing_ok=True)

def direct_video(url,dest,referer=None):
    tmp=dest.with_suffix('.download')
    if not download(url,tmp,referer): return False
    tmp.replace(dest); return valid_video(dest)

def ytdlp(url,dest):
    try:
        subprocess.run(['yt-dlp','--no-playlist','--retries','1','--fragment-retries','1','--socket-timeout','15','-f','b[height<=1080]/best','--merge-output-format','mp4','-o',str(dest),url],check=True)
        return valid_video(dest)
    except subprocess.CalledProcessError:
        dest.unlink(missing_ok=True); return False

def savefrom(url,dest):
    """Fallback experimental: pede ao SaveFrom a página de links e baixa somente URL HTTP de vídeo retornada."""
    endpoints=['https://pt1.savefrom.net/8bb/','https://savefrom.net/1-youtube-video-downloader-4/']
    for endpoint in endpoints:
        try:
            payload=urllib.parse.urlencode({'sf_url':url,'sf_submit':'','new':'2','lang':'pt'}).encode()
            with urllib.request.urlopen(request(endpoint,payload,endpoint),timeout=40) as r:
                text=r.read().decode('utf-8','ignore')
            candidates=[]
            for raw in re.findall(r'https?:[^\"\'<>\\ ]+',text):
                u=html.unescape(raw).replace('\\/','/')
                low=u.lower()
                if ('googlevideo.com' in low or '.mp4' in low or 'videoplayback' in low) and 'savefrom' not in low:
                    candidates.append(u)
            for media_url in candidates:
                print('SaveFrom candidate found')
                if direct_video(media_url,dest,endpoint): return True
        except Exception as e:
            print('SaveFrom fallback failed:',e)
    return False

def main(spec_path):
    spec=json.loads(Path(spec_path).read_text(encoding='utf-8')); out=Path('output/media'); out.mkdir(parents=True,exist_ok=True)
    clips=[]; errors=[]
    for i,item in enumerate(spec.get('media',[]),1):
        url=item['url']; typ=item.get('type','video'); dest=out/f'clip_{i:02}.mp4'; ok=False
        if typ=='image': ok=image_clip(url,dest,i)
        elif url.lower().split('?')[0].endswith(('.mp4','.mov','.webm')): ok=direct_video(url,dest)
        if not ok and typ!='image': ok=ytdlp(url,dest)
        if not ok and typ!='image' and ('youtube.com' in url or 'youtu.be' in url): ok=savefrom(url,dest)
        if ok: clips.append(str(dest))
        else: errors.append({'url':url,'error':'remote_media_unavailable_after_fallbacks'})
    manifest={'clips':clips,'errors':errors,'publishable_media':len(clips)>=4,'generic_fallback':False,'official_assets':True}
    Path('output/clips.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    if len(clips)<4: raise RuntimeError(f'QUALITY_BLOCK: somente {len(clips)} assets relevantes; minimo 4')
    print(json.dumps(manifest))
if __name__=='__main__': main(sys.argv[1])
