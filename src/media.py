#!/usr/bin/env python3
"""Obtém assets oficiais/relevantes com fallbacks rápidos e gratuitos."""
import html,json,re,subprocess,sys,urllib.parse,urllib.request
from pathlib import Path

def valid_visual(p):
    if not p.exists() or p.stat().st_size < 20000:return False
    try:
        subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name','-of','csv=p=0',str(p)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=12);return True
    except:return False

def req(url,data=None,referer=None):
    h={'User-Agent':'Mozilla/5.0 AppleWebKit/537.36 Chrome/129 Safari/537.36','Accept-Language':'pt-BR,pt;q=0.9,en;q=0.8'}
    if referer:h['Referer']=referer
    return urllib.request.Request(url,data=data,headers=h)

def download(url,dest,referer=None):
    try:
        with urllib.request.urlopen(req(url,referer=referer),timeout=15) as r,open(dest,'wb') as f:
            f.write(r.read(80*1024*1024))
        if valid_visual(dest):return True
    except Exception as e: print('download failed',url,e)
    dest.unlink(missing_ok=True);return False

def discover(page):
    """Descobre mídia direta em páginas oficiais sem depender de YouTube."""
    try:
        with urllib.request.urlopen(req(page),timeout=15) as r:text=r.read(4*1024*1024).decode('utf-8','ignore')
    except Exception as e: print('page discovery failed',page,e);return []
    vals=[]
    # href/src/content, JSON-LD e URLs absolutas/relativas
    for raw in re.findall(r'(?:href|src|content)=["\']([^"\']+)["\']',text,re.I)+re.findall(r'https?:\\?/\\?/[^"\'<> ]+',text):
        u=html.unescape(raw).replace('\\/','/')
        u=urllib.parse.urljoin(page,u)
        clean=u.lower().split('?')[0]
        if clean.endswith(('.mp4','.mov','.webm','.jpg','.jpeg','.png','.webp')) and u not in vals: vals.append(u)
    return vals[:30]

def ytdlp(url,dest):
    # somente URLs reais do YouTube; páginas comuns nunca entram neste loop caro
    if 'youtube.com' not in url and 'youtu.be' not in url:return False
    for client in ['tv_embedded','web_embedded']:
        dest.unlink(missing_ok=True)
        try:
            subprocess.run(['yt-dlp','--no-playlist','--retries','0','--fragment-retries','0','--socket-timeout','10','--extractor-args',f'youtube:player_client={client}','-f','bv*[height<=1080]+ba/b[height<=1080]/best','--merge-output-format','mp4','-o',str(dest),url],check=True,timeout=45)
            if valid_visual(dest):return True
        except Exception as e: print('yt fallback failed',client,e)
    return False

def main(path):
    spec=json.loads(Path(path).read_text(encoding='utf-8'));out=Path('output/media');out.mkdir(parents=True,exist_ok=True)
    assets=[];errors=[];seq=0
    for item in spec.get('media',[]):
        url=item['url'];role=item.get('role','');typ=item.get('type','video');candidates=[]
        low=url.lower().split('?')[0]
        if low.endswith(('.mp4','.mov','.webm','.jpg','.jpeg','.png','.webp')): candidates=[url]
        elif 'youtube.com' in url or 'youtu.be' in url: candidates=[url]
        else: candidates=discover(url)
        # prioriza vídeo, depois imagens oficiais
        candidates.sort(key=lambda u:0 if u.lower().split('?')[0].endswith(('.mp4','.mov','.webm')) else 1)
        got=0
        for u in candidates[:12]:
            seq+=1;ext=u.lower().split('?')[0].rsplit('.',1)[-1];isimg=ext in ('jpg','jpeg','png','webp')
            dest=out/f'asset_{seq:02d}.{"jpg" if isimg else "mp4"}'
            ok=ytdlp(u,dest) if ('youtube.com' in u or 'youtu.be' in u) else download(u,dest,url)
            if ok:
                assets.append({'index':seq,'path':str(dest),'type':'image' if isimg else 'video','role':role,'url':u});got+=1
                if got>=4:break
        if not got: errors.append({'url':url,'error':'remote_media_unavailable_after_free_fallbacks'})
    minimum=int(spec.get('minimum_assets',2));manifest={'assets':assets,'clips':[a['path'] for a in assets],'errors':errors,'publishable_media':len(assets)>=minimum,'generic_fallback':False,'official_assets':True,'minimum_assets':minimum}
    Path('output/clips.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    if len(assets)<minimum:raise RuntimeError(f'QUALITY_BLOCK: somente {len(assets)} assets relevantes; minimo {minimum}')
    print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__':main(sys.argv[1])
