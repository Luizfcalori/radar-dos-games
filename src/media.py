#!/usr/bin/env python3
"""Obtém assets oficiais/relevantes com fallbacks rápidos e gratuitos."""
import html,json,re,subprocess,sys,urllib.parse,urllib.request
from pathlib import Path

VIDEO_EXTS=('.mp4','.mov','.webm','.m4v')
IMAGE_EXTS=('.jpg','.jpeg','.png','.webp')

def probe_kind(p):
    if not p.exists() or p.stat().st_size < 20000:return None
    try:
        out=subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_type,codec_name,duration','-of','json',str(p)],stderr=subprocess.DEVNULL,timeout=12)
        data=json.loads(out);return 'video' if data.get('streams') else None
    except:return None

def req(url,data=None,referer=None):
    h={'User-Agent':'Mozilla/5.0 AppleWebKit/537.36 Chrome/129 Safari/537.36','Accept-Language':'pt-BR,pt;q=0.9,en;q=0.8','Accept':'*/*'}
    if referer:h['Referer']=referer
    return urllib.request.Request(url,data=data,headers=h)

def download(url,dest,referer=None):
    try:
        with urllib.request.urlopen(req(url,referer=referer),timeout=20) as r,open(dest,'wb') as f:
            f.write(r.read(120*1024*1024))
        if probe_kind(dest):return True
    except Exception as e: print('download failed',url,e)
    dest.unlink(missing_ok=True);return False

def discover(page):
    """Descobre arquivos de vídeo/imagem e embeds de vídeo em páginas oficiais."""
    try:
        with urllib.request.urlopen(req(page),timeout=20) as r:text=r.read(8*1024*1024).decode('utf-8','ignore')
    except Exception as e: print('page discovery failed',page,e);return []
    text=html.unescape(text).replace('\\/','/')
    vals=[]
    raws=[]
    raws += re.findall(r'(?:href|src|content|data-src|data-video|data-url|poster)=["\']([^"\']+)["\']',text,re.I)
    raws += re.findall(r'https?://[^"\'<>\\ ]+',text)
    # YouTube embeds/watch URLs hidden in JSON/iframes.
    raws += ['https://www.youtube.com/watch?v='+v for v in re.findall(r'(?:youtube\.com/embed/|youtu\.be/)([A-Za-z0-9_-]{6,})',text,re.I)]
    for raw in raws:
        u=urllib.parse.urljoin(page,raw.strip())
        clean=u.lower().split('?')[0]
        keep=clean.endswith(VIDEO_EXTS+IMAGE_EXTS) or 'youtube.com/watch' in u or 'youtu.be/' in u
        if keep and u not in vals:vals.append(u)
    # Prioriza vídeo real/embeds antes de imagens.
    vals.sort(key=lambda u:0 if (u.lower().split('?')[0].endswith(VIDEO_EXTS) or 'youtube.com/watch' in u or 'youtu.be/' in u) else 1)
    return vals[:60]

def ytdlp(url,dest):
    if 'youtube.com' not in url and 'youtu.be' not in url:return False
    # Channel URLs are allowed: yt-dlp resolves the newest suitable video only.
    args=['yt-dlp','--no-playlist','--playlist-end','1','--retries','1','--fragment-retries','1','--socket-timeout','15','-f','bv*[height<=1080]+ba/b[height<=1080]/best','--merge-output-format','mp4','-o',str(dest),url]
    try:
        subprocess.run(args,check=True,timeout=90)
        return bool(probe_kind(dest))
    except Exception as e: print('yt fallback failed',e);dest.unlink(missing_ok=True);return False

def main(path):
    spec=json.loads(Path(path).read_text(encoding='utf-8'));out=Path('output/media');out.mkdir(parents=True,exist_ok=True)
    assets=[];errors=[];seq=0
    for item in spec.get('media',[]):
        url=item['url'];role=item.get('role','');candidates=[];low=url.lower().split('?')[0]
        if low.endswith(VIDEO_EXTS+IMAGE_EXTS) or 'youtube.com' in url or 'youtu.be' in url:candidates=[url]
        else:candidates=discover(url)
        candidates.sort(key=lambda u:0 if (u.lower().split('?')[0].endswith(VIDEO_EXTS) or 'youtube.com' in u or 'youtu.be' in u) else 1)
        got=0
        for u in candidates[:18]:
            seq+=1;clean=u.lower().split('?')[0];isimg=clean.endswith(IMAGE_EXTS)
            dest=out/f'asset_{seq:02d}.{"jpg" if isimg else "mp4"}'
            ok=ytdlp(u,dest) if ('youtube.com' in u or 'youtu.be' in u) else download(u,dest,url)
            if ok:
                assets.append({'index':seq,'path':str(dest),'type':'image' if isimg else 'video','role':role,'url':u});got+=1
                if got>=4:break
        if not got:errors.append({'url':url,'error':'remote_media_unavailable_after_free_fallbacks'})
    minimum=int(spec.get('minimum_assets',2));videos=[a for a in assets if a['type']=='video']
    manifest={'assets':assets,'clips':[a['path'] for a in assets],'errors':errors,'publishable_media':len(assets)>=minimum and bool(videos),'generic_fallback':False,'official_assets':True,'minimum_assets':minimum,'video_assets':len(videos)}
    Path('output/clips.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    if len(assets)<minimum:raise RuntimeError(f'QUALITY_BLOCK: somente {len(assets)} assets relevantes; minimo {minimum}')
    if not videos:raise RuntimeError('QUALITY_BLOCK: nenhum trailer/gameplay em video; slideshow proibido')
    print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__':main(sys.argv[1])
