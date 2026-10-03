#!/usr/bin/env python3
"""Aquisição de mídia com prova de relevância por jogo e QA semântico."""
import html,json,re,subprocess,sys,urllib.parse,urllib.request
from pathlib import Path

VIDEO_EXTS=('.mp4','.mov','.webm','.m4v')
IMAGE_EXTS=('.jpg','.jpeg','.png','.webp')
LOW_VALUE_TOKENS=(
    'logo','favicon','icon','ogp_','store_banner','store-banner','header','footer','nav_','social','share',
    '/intro.mp4','/intro-sp.mp4','/ptcl.mp4','splash','loading','background-loop'
)

def probe_info(p):
    if not p.exists() or p.stat().st_size < 20000:return None
    try:
        out=subprocess.check_output([
            'ffprobe','-v','error','-select_streams','v:0',
            '-show_entries','stream=codec_type,codec_name,width,height:format=duration',
            '-of','json',str(p)
        ],stderr=subprocess.DEVNULL,timeout=15)
        data=json.loads(out); streams=data.get('streams') or []
        if not streams:return None
        dur=float((data.get('format') or {}).get('duration') or 0)
        s=streams[0]
        return {'duration':round(dur,3),'width':int(s.get('width') or 0),'height':int(s.get('height') or 0),'codec':s.get('codec_name')}
    except:return None

def req(url,referer=None):
    h={'User-Agent':'Mozilla/5.0 AppleWebKit/537.36 Chrome/129 Safari/537.36','Accept-Language':'pt-BR,pt;q=0.9,en;q=0.8','Accept':'*/*'}
    if referer:h['Referer']=referer
    return urllib.request.Request(url,headers=h)

def download(url,dest,referer=None):
    try:
        with urllib.request.urlopen(req(url,referer),timeout=30) as r,open(dest,'wb') as f:
            while True:
                chunk=r.read(1024*1024)
                if not chunk:break
                f.write(chunk)
                if f.tell()>500*1024*1024:break
        info=probe_info(dest)
        if info:return info
    except Exception as e: print('download failed',url,e)
    dest.unlink(missing_ok=True);return None

def gdrive_download(url,dest):
    m=re.search(r'/file/d/([^/]+)',url) or re.search(r'[?&]id=([^&]+)',url)
    file_id=m.group(1) if m else url
    try:
        subprocess.run([sys.executable,'-m','gdown',file_id,'-O',str(dest)],check=True,timeout=300)
        info=probe_info(dest)
        if info:return info
    except Exception as e: print('gdrive id download failed',file_id,e)
    dest.unlink(missing_ok=True)
    if m:
        for direct in [
            'https://drive.usercontent.google.com/download?id='+file_id+'&export=download&confirm=t',
            'https://drive.google.com/uc?export=download&confirm=t&id='+file_id,
        ]:
            info=download(direct,dest,'https://drive.google.com/')
            if info:return info
    return None

def ytdlp(url,dest):
    if 'youtube.com' not in url and 'youtu.be' not in url:return None
    args=['yt-dlp','--no-playlist','--playlist-end','1','--retries','1','--fragment-retries','1','--socket-timeout','15',
          '-f','bv*[height<=1080]+ba/b[height<=1080]/best','--merge-output-format','mp4','-o',str(dest),url]
    try:
        subprocess.run(args,check=True,timeout=100)
        return probe_info(dest)
    except Exception as e: print('yt fallback failed',e);dest.unlink(missing_ok=True);return None

def discover(page,allow_images=False):
    try:
        with urllib.request.urlopen(req(page),timeout=20) as r:text=r.read(10*1024*1024).decode('utf-8','ignore')
    except Exception as e: print('page discovery failed',page,e);return []
    text=html.unescape(text).replace('\\/','/')
    raws=[]
    raws += re.findall(r'(?:href|src|content|data-src|data-video|data-url|poster)=["\']([^"\']+)["\']',text,re.I)
    raws += re.findall(r'https?://[^"\'<>\\ ]+',text)
    raws += ['https://www.youtube.com/watch?v='+v for v in re.findall(r'(?:youtube\.com/embed/|youtu\.be/)([A-Za-z0-9_-]{6,})',text,re.I)]
    vals=[]
    for raw in raws:
        u=urllib.parse.urljoin(page,raw.strip()); low=u.lower(); clean=low.split('?')[0]
        is_video=clean.endswith(VIDEO_EXTS) or 'drive.google.com/file/d/' in low or 'youtube.com/watch' in low or 'youtu.be/' in low
        is_image=clean.endswith(IMAGE_EXTS)
        if is_video or (allow_images and is_image):
            if u not in vals:vals.append(u)
    vals.sort(key=lambda u:0 if ('drive.google.com/file/d/' in u.lower() or u.lower().split('?')[0].endswith(VIDEO_EXTS)) else (1 if ('youtube.com' in u or 'youtu.be/' in u) else 2))
    return vals[:100]

def steam_candidates(app_id,wanted):
    """Assets do app exato da Steam. A listagem é controlada pelo publisher e amarrada ao app_id."""
    api=f'https://store.steampowered.com/api/appdetails?appids={int(app_id)}&cc=us&l=english'
    try:
        with urllib.request.urlopen(req(api),timeout=25) as r:data=json.loads(r.read().decode('utf-8','ignore'))
        root=data.get(str(app_id),{})
        if not root.get('success'):return []
        d=root.get('data') or {}; out=[]
        if wanted=='video':
            for movie in d.get('movies') or []:
                mp4=(movie.get('mp4') or {})
                u=mp4.get('max') or mp4.get('480')
                if u:out.append((u,'steam_exact_app_trailer',movie.get('name','')))
        elif wanted=='image':
            for s in d.get('screenshots') or []:
                u=s.get('path_full') or s.get('path_thumbnail')
                if u:out.append((u,'steam_exact_app_screenshot',str(s.get('id',''))))
        return out
    except Exception as e:
        print('steam discovery failed',app_id,e);return []

def blocked_candidate(url,item):
    low=url.lower()
    blocked=list(LOW_VALUE_TOKENS)+[str(x).lower() for x in item.get('blocked_tokens',[])]
    return next((tok for tok in blocked if tok and tok in low),None)

def main(path):
    spec=json.loads(Path(path).read_text(encoding='utf-8'));out=Path('output/media');out.mkdir(parents=True,exist_ok=True)
    assets=[];errors=[];seq=0;seen=set()
    for item in spec.get('media',[]):
        wanted=item.get('type','video');role=item.get('role','');max_assets=int(item.get('max_assets',4));candidates=[]
        if item.get('steam_app_id'):
            candidates=[(u,evidence,label) for u,evidence,label in steam_candidates(item['steam_app_id'],wanted)]
            source=f"steam_app:{item['steam_app_id']}"
        else:
            url=item['url'];source=url;low=url.lower().split('?')[0]
            if low.endswith(VIDEO_EXTS+IMAGE_EXTS) or 'drive.google.com/file/d/' in url.lower() or 'youtube.com' in url or 'youtu.be' in url:
                candidates=[(url,'direct_source','')]
            else:
                allow_images=bool(item.get('allow_images_from_page',False) and wanted=='image')
                candidates=[(u,'official_page_discovery','') for u in discover(url,allow_images=allow_images)]
        got=0
        for u,evidence,label in candidates[:40]:
            if u in seen:continue
            low=u.lower();clean=low.split('?')[0];isimg=clean.endswith(IMAGE_EXTS);isdrive='drive.google.com/file/d/' in low
            if wanted=='video' and isimg:continue
            if wanted=='image' and not isimg:continue
            blocked=blocked_candidate(u,item)
            if blocked:
                print('relevance reject',blocked,u);continue
            seq+=1;dest=out/f'asset_{seq:02d}.{"jpg" if isimg else "mp4"}'
            if isimg:
                try:
                    with urllib.request.urlopen(req(u,source if source.startswith('http') else None),timeout=25) as r,open(dest,'wb') as f:f.write(r.read(50*1024*1024))
                    ok=dest.exists() and dest.stat().st_size>20000;info={'duration':0,'width':0,'height':0,'codec':'image'} if ok else None
                except Exception as e: print('image download failed',u,e);info=None
            elif isdrive:info=gdrive_download(u,dest)
            elif 'youtube.com' in low or 'youtu.be' in low:info=ytdlp(u,dest)
            else:info=download(u,dest,source if source.startswith('http') else None)
            if not info:
                dest.unlink(missing_ok=True);continue
            if wanted=='video':
                min_d=float(item.get('min_duration',8))
                if float(info.get('duration',0))<min_d:
                    print('duration reject',info.get('duration'),u);dest.unlink(missing_ok=True);continue
            seen.add(u)
            assets.append({
                'index':seq,'path':str(dest),'type':'image' if isimg else 'video','role':role,'url':u,
                'source':source,'relevance_evidence':evidence,'source_label':label,'approved':True,
                'duration':float(info.get('duration',0)),'width':int(info.get('width',0)),'height':int(info.get('height',0))
            })
            got+=1
            if got>=max_assets:break
        if not got:errors.append({'source':source,'role':role,'error':'no_approved_relevant_media'})
    minimum=int(spec.get('minimum_assets',2));videos=[a for a in assets if a['type']=='video'];images=[a for a in assets if a['type']=='image']
    unique_video_seconds=round(sum(float(a.get('duration',0)) for a in videos),3)
    min_videos=int(spec.get('minimum_video_assets',1));min_secs=float(spec.get('minimum_unique_video_seconds',0));min_images=int(spec.get('minimum_image_assets',0))
    manifest={'assets':assets,'clips':[a['path'] for a in assets],'errors':errors,'publishable_media':False,'generic_fallback':False,'official_assets':True,
              'minimum_assets':minimum,'video_assets':len(videos),'image_assets':len(images),'unique_video_seconds':unique_video_seconds,
              'minimum_video_assets':min_videos,'minimum_unique_video_seconds':min_secs,'minimum_image_assets':min_images,
              'semantic_policy':'exact_source_only; no_generic_page_images; reject_logo_banner_store_intro; explicit_scene_assets_only'}
    manifest['publishable_media']=len(assets)>=minimum and len(videos)>=min_videos and unique_video_seconds>=min_secs and len(images)>=min_images
    Path('output/clips.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    if len(assets)<minimum:raise RuntimeError(f'QUALITY_BLOCK: somente {len(assets)} assets aprovados; minimo {minimum}')
    if len(videos)<min_videos:raise RuntimeError(f'QUALITY_BLOCK: somente {len(videos)} videos aprovados; minimo {min_videos}')
    if unique_video_seconds<min_secs:raise RuntimeError(f'QUALITY_BLOCK: apenas {unique_video_seconds}s de video unico aprovado; minimo {min_secs}s')
    if len(images)<min_images:raise RuntimeError(f'QUALITY_BLOCK: somente {len(images)} imagens aprovadas; minimo {min_images}')
    print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__':main(sys.argv[1])
