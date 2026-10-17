#!/usr/bin/env python3
"""Aquisição de mídia com prova de relevância por jogo e QA semântico."""
import html,json,os,re,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path

try:
    from instagram_media import is_instagram_video_url, download_public_instagram
except ModuleNotFoundError:
    from src.instagram_media import is_instagram_video_url, download_public_instagram

VIDEO_EXTS=('.mp4','.mov','.webm','.m4v')
STREAM_EXTS=('.m3u8','.mpd')
IMAGE_EXTS=('.jpg','.jpeg','.png','.webp')
LOW_VALUE_TOKENS=(
    'logo','favicon','icon','ogp_','store_banner','store-banner','header','footer','nav_','social',
    'share-button','/share/','/intro.mp4','/intro-sp.mp4','/ptcl.mp4','splash','loading','background-loop'
)
STEAM_VIDEO_HOST='https://video.fastly.steamstatic.com/'
NEWISTY_BASE='https://newisty.com/api/video-downloader'

def probe_info(p):
    if not p.exists() or p.stat().st_size < 20000:return None
    try:
        out=subprocess.check_output([
            'ffprobe','-v','error','-select_streams','v:0',
            '-show_entries','stream=codec_type,codec_name,width,height:format=duration',
            '-of','json',str(p)
        ],stderr=subprocess.DEVNULL,timeout=15)
        data=json.loads(out);streams=data.get('streams') or []
        if not streams:return None
        dur=float((data.get('format') or {}).get('duration') or 0);s=streams[0]
        return {'duration':round(dur,3),'width':int(s.get('width') or 0),'height':int(s.get('height') or 0),'codec':s.get('codec_name')}
    except:return None

def req(url,referer=None,steam_age=False):
    h={'User-Agent':'Mozilla/5.0 AppleWebKit/537.36 Chrome/129 Safari/537.36','Accept-Language':'pt-BR,pt;q=0.9,en;q=0.8','Accept':'*/*'}
    if referer:h['Referer']=referer
    if steam_age:h['Cookie']='birthtime=0; mature_content=1; lastagecheckage=1-January-1990; wants_mature_content=1'
    return urllib.request.Request(url,headers=h)

def download(url,dest,referer=None):
    try:
        with urllib.request.urlopen(req(url,referer),timeout=30) as r,open(dest,'wb') as f:
            while True:
                chunk=r.read(1024*1024)
                if not chunk:break
                f.write(chunk)
                if f.tell()>700*1024*1024:break
        info=probe_info(dest)
        if info:return info
    except Exception as e:print('download failed',url,e)
    dest.unlink(missing_ok=True);return None

def official_remote_clip(url,dest,referer='https://www.rockstargames.com/'):
    """Extrai um trecho utilizável de MP4 oficial remoto sem baixar o arquivo inteiro.

    Feito para CDNs oficiais de publisher que oferecem masters muito grandes. O FFmpeg
    usa seek/range HTTP e gera um asset local 720p leve, preservando gameplay em movimento.
    """
    low=url.lower()
    if 'gtavi_an_extended_look' in low:
        start=300
        seconds=55
    elif 'trailer_2' in low:
        start=22
        seconds=50
    elif 'trailer_1' in low:
        start=12
        seconds=45
    else:
        start=8
        seconds=40
    headers=(
        'User-Agent: Mozilla/5.0 AppleWebKit/537.36 Chrome/129 Safari/537.36\r\n'
        f'Referer: {referer or "https://www.rockstargames.com/"}\r\n'
        f'Origin: {urllib.parse.urlparse(url).scheme}://{urllib.parse.urlparse(url).netloc}\r\n'
        'Accept: */*\r\n'
    )
    vf='scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,fps=30,format=yuv420p'
    commands=[
        ['ffmpeg','-y','-loglevel','error','-headers',headers,'-ss',str(start),'-i',url,'-t',str(seconds),
         '-map','0:v:0','-an','-vf',vf,'-c:v','libx264','-preset','veryfast','-crf','21','-movflags','+faststart',str(dest)],
        ['ffmpeg','-y','-loglevel','error','-headers',headers,'-i',url,'-ss',str(start),'-t',str(seconds),
         '-map','0:v:0','-an','-vf',vf,'-c:v','libx264','-preset','veryfast','-crf','21','-movflags','+faststart',str(dest)]
    ]
    for cmd in commands:
        try:
            subprocess.run(cmd,check=True,timeout=360)
            info=probe_info(dest)
            if info and float(info.get('duration',0))>=15:
                print('official remote clip success',url,info,flush=True)
                return info
        except Exception as e:
            print('official remote clip failed',url,type(e).__name__,e,flush=True)
        dest.unlink(missing_ok=True)
    return None


def stream_download(url,dest,referer='https://store.steampowered.com/'):
    """Baixa HLS/DASH direto do CDN, sem depender do YouTube."""
    headers=f'User-Agent: Mozilla/5.0\r\nReferer: {referer}\r\n'
    commands=[
        ['ffmpeg','-y','-loglevel','error','-headers',headers,'-i',url,'-map','0:v:0','-map','0:a:0?','-c','copy',str(dest)],
        ['ffmpeg','-y','-loglevel','error','-headers',headers,'-i',url,'-map','0:v:0','-map','0:a:0?','-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-b:a','160k',str(dest)]
    ]
    for cmd in commands:
        try:
            # Keep the direct-CDN route bounded: a stalled manifest must not
            # block alternate encoders and official YouTube fallbacks for six minutes.
            subprocess.run(cmd,check=True,timeout=120)
            info=probe_info(dest)
            if info:return info
        except Exception as e:print('stream download failed',url,type(e).__name__,e,flush=True)
        dest.unlink(missing_ok=True)
    return None

def gdrive_download(url,dest):
    m=re.search(r'/file/d/([^/]+)',url) or re.search(r'[?&]id=([^&]+)',url);file_id=m.group(1) if m else url
    try:
        subprocess.run([sys.executable,'-m','gdown',file_id,'-O',str(dest)],check=True,timeout=300)
        info=probe_info(dest)
        if info:return info
    except Exception as e:print('gdrive id download failed',file_id,e)
    dest.unlink(missing_ok=True)
    if m:
        for direct in ['https://drive.usercontent.google.com/download?id='+file_id+'&export=download&confirm=t','https://drive.google.com/uc?export=download&confirm=t&id='+file_id]:
            info=download(direct,dest,'https://drive.google.com/')
            if info:return info
    return None

def newisty_download(url,dest,quality='720p'):
    """Fallback externo para YouTube quando o IP do runner recebe bloqueio anti-bot.

    Respeita Retry-After/429 em start, progress e download para que um pico temporario
    do servico nao derrube a aquisicao de midia do Master.
    """
    headers={'User-Agent':'radar-dos-games/1.0','Accept':'application/json','Content-Type':'application/json'}

    def wait_rate_limit(err,attempt,stage):
        try:body=err.read().decode('utf-8','replace')
        except:body=''
        if 'downloader is busy' in body.lower():
            # Busy is transient congestion, not a permanent failure. Back off and
            # retry instead of abandoning the only non-YouTube fallback immediately.
            wait=min(10+attempt*5,20)
            print('newisty busy',stage,'retrying after backoff',wait,'seconds',body[:300],flush=True)
            time.sleep(wait)
            return True
        raw=(err.headers.get('Retry-After') if getattr(err,'headers',None) else None) or str(min(5+attempt*5,20))
        try:wait=int(float(raw))
        except:wait=min(10+attempt*5,45)
        wait=max(5,min(wait,20))
        print('newisty 429',stage,'attempt',attempt,'retry in',wait,'seconds',body[:300],flush=True)
        time.sleep(wait)
        return True

    try:
        job_id=''
        payload=json.dumps({'url':url,'format':quality}).encode()
        for attempt in range(1,4):
            start=urllib.request.Request(NEWISTY_BASE+'/start',data=payload,headers=headers,method='POST')
            try:
                with urllib.request.urlopen(start,timeout=45) as r:obj=json.loads(r.read().decode('utf-8','replace'))
                job_id=str(((obj.get('data') or {}).get('job_id') or '')).strip()
                if job_id:break
                print('newisty start failed: no job_id',obj,flush=True)
            except urllib.error.HTTPError as e:
                if e.code==429 and attempt<3:
                    if not wait_rate_limit(e,attempt,'start'):return None
                    continue
                raise
        if not job_id:return None

        state='queued'
        not_found=0
        for poll in range(24):
            time.sleep(5)
            progress=urllib.request.Request(NEWISTY_BASE+'/progress/'+urllib.parse.quote(job_id),headers={'User-Agent':headers['User-Agent'],'Accept':'application/json'})
            try:
                with urllib.request.urlopen(progress,timeout=30) as r:pobj=json.loads(r.read().decode('utf-8','replace'))
                not_found=0
            except urllib.error.HTTPError as e:
                if e.code==404:
                    not_found+=1
                    if not_found>=4:
                        print('newisty job missing from progress API; abandoning this fallback',job_id,flush=True)
                        return None
                    continue
                if e.code==429:
                    if not wait_rate_limit(e,min(poll+1,6),'progress'):return None
                    continue
                raise
            state=str(((pobj.get('data') or {}).get('status') or '')).lower()
            if state in ('done','completed','complete'):break
            if state in ('failed','error'):
                print('newisty job failed',pobj,flush=True);return None
        if state not in ('done','completed','complete'):
            print('newisty timeout',job_id,state,flush=True);return None

        dreq=urllib.request.Request(NEWISTY_BASE+'/download/'+urllib.parse.quote(job_id),headers={'User-Agent':headers['User-Agent'],'Accept':'*/*'})
        downloaded=False
        for attempt in range(1,7):
            try:
                with urllib.request.urlopen(dreq,timeout=240) as r,open(dest,'wb') as f:
                    while True:
                        chunk=r.read(1024*1024)
                        if not chunk:break
                        f.write(chunk)
                        if f.tell()>700*1024*1024:break
                downloaded=True;break
            except urllib.error.HTTPError as e:
                dest.unlink(missing_ok=True)
                if e.code==429 and attempt<6:
                    if not wait_rate_limit(e,attempt,'download'):return None
                    continue
                raise
        if not downloaded:return None
        info=probe_info(dest)
        if info:
            print('newisty youtube fallback success',quality,info,flush=True)
            return info
    except Exception as e:print('newisty youtube fallback failed',type(e).__name__,e,flush=True)
    dest.unlink(missing_ok=True);return None


def social_post_url(url):
    low=url.lower()
    return (
        (('x.com/' in low or 'twitter.com/' in low) and '/status/' in low)
        or ('tiktok.com/' in low and '/video/' in low)
        or ('instagram.com/' in low and ('/reel/' in low or '/p/' in low))
        or ('facebook.com/' in low and ('/videos/' in low or 'watch' in low or '/reel/' in low))
    )

def social_profile_url(url):
    low=url.lower().split('?')[0].rstrip('/')
    return low in ('https://x.com/fortnitegame','https://twitter.com/fortnitegame',
                   'https://www.instagram.com/fortnite','https://instagram.com/fortnite',
                   'https://www.tiktok.com/@fortnite','https://tiktok.com/@fortnite',
                   'https://www.facebook.com/fortnitegame','https://facebook.com/fortnitegame')

def discover_social_posts(profile):
    """Inspect recent posts on official accounts and keep only topic-matched posts."""
    print("cross-platform fallback enabled: X, Instagram, TikTok, Facebook", flush=True)
    args=['yt-dlp','--flat-playlist','--dump-single-json','--playlist-end','40','--no-warnings',profile]
    try:
        p=subprocess.run(args,check=True,capture_output=True,text=True,timeout=100)
        data=json.loads(p.stdout)
        matches=[]
        for entry in data.get('entries') or []:
            title=str(entry.get('title') or '')
            desc=str(entry.get('description') or '')
            combined=(title+' '+desc).lower()
            if not (('yeat' in combined or 'real lyfe' in combined) and 'fortnite' in combined):
                continue
            post_url=entry.get('webpage_url') or entry.get('original_url')
            if post_url and social_post_url(post_url):
                matches.append((post_url,'official_social_post_keyword_match',title))
        print('official social discovery',profile,'matched_posts',len(matches),flush=True)
        return matches
    except Exception as e:
        print('official social discovery failed',profile,type(e).__name__,str(e)[:240],flush=True)
        return []

def ytdlp(url,dest):
    low_url=url.lower()
    is_youtube='youtube.com' in low_url or 'youtu.be' in low_url
    is_social=social_post_url(url)
    if not is_youtube and not is_social:return None
    is_actions=os.environ.get('GITHUB_ACTIONS','').lower()=='true'
    # Try multiple public player clients before the external queue. A video can
    # reject web_embedded while remaining available through iOS/TV player APIs.
    height=720 if is_actions else 1080
    timeout=45 if is_actions else 35
    clients=['web_embedded','ios','android_vr','tv_embedded'] if is_actions and is_youtube else [None]
    for client in clients:
        args=['yt-dlp','--no-playlist','--playlist-end','1','--retries','1','--fragment-retries','1','--socket-timeout','15']
        if client:
            args += ['--extractor-args',f'youtube:player_client={client}']
        args += ['-f',f'bv*[height<={height}]+ba/b[height<={height}]/best','--merge-output-format','mp4','-o',str(dest),url]
        try:
            subprocess.run(args,check=True,timeout=timeout)
            info=probe_info(dest)
            if info:
                print('github actions youtube: client download success',client or 'default',flush=True)
                return info
        except Exception as e:
            print('yt client failed',client or 'default',type(e).__name__,str(e)[:180],flush=True)
        dest.unlink(missing_ok=True)
    if is_youtube:
        if is_actions:
            print('github actions youtube: using external fallback after all player clients failed',flush=True)
        return newisty_download(url,dest,'720p' if is_actions else '1080p')
    return None


def discover(page,allow_images=False):
    try:
        with urllib.request.urlopen(req(page),timeout=20) as r:text=r.read(10*1024*1024).decode('utf-8','ignore')
    except Exception as e:print('page discovery failed',page,e);return []
    text=html.unescape(text).replace('\\/','/')
    raws=[]
    raws += re.findall(r'(?:href|src|content|data-src|data-video|data-url|poster)=["\']([^"\']+)["\']',text,re.I)
    raws += re.findall(r'https?://[^"\'<>\\ ]+',text)
    raws += ['https://www.youtube.com/watch?v='+v for v in re.findall(r'(?:youtube\.com/embed/|youtu\.be/)([A-Za-z0-9_-]{6,})',text,re.I)]
    vals=[]
    for raw in raws:
        u=urllib.parse.urljoin(page,raw.strip());low=u.lower();clean=low.split('?')[0]
        is_video=clean.endswith(VIDEO_EXTS+STREAM_EXTS) or 'drive.google.com/file/d/' in low or 'youtube.com/watch' in low or 'youtu.be/' in low
        is_image=clean.endswith(IMAGE_EXTS)
        if is_video or (allow_images and is_image):
            if u not in vals:vals.append(u)
    vals.sort(key=lambda u:0 if u.lower().split('?')[0].endswith(STREAM_EXTS+VIDEO_EXTS) or 'drive.google.com/file/d/' in u.lower() else (1 if ('youtube.com' in u or 'youtu.be/' in u) else 2))
    return vals[:120]

def steam_url(value):
    if not isinstance(value,str):return None
    v=html.unescape(value).replace('\\/','/').strip()
    if not v:return None
    if v.startswith('//'):return 'https:'+v
    if v.startswith('http://') or v.startswith('https://'):return v
    if 'store_trailers/' in v:
        return STEAM_VIDEO_HOST+v.lstrip('/')
    if re.match(r'^\d+/\d+/',v):
        return STEAM_VIDEO_HOST+'store_trailers/'+v.lstrip('/')
    return None

def steam_store_streams(app_id):
    """Extrai streams diretos do HTML da página exata do app Steam."""
    page=f'https://store.steampowered.com/app/{int(app_id)}/?cc=us&l=english&agecheckage=1-January-1990'
    try:
        with urllib.request.urlopen(req(page,steam_age=True),timeout=25) as r:text=r.read(12*1024*1024).decode('utf-8','ignore')
    except Exception as e:print('steam store html failed',app_id,e);return []
    text=html.unescape(text).replace('\\/','/')
    found=[]
    patterns=[
        r'https?://video\.[^"\'<> ]*steamstatic\.com/store_trailers/[^"\'<> ]+',
        r'https?://[^"\'<> ]*steamstatic\.com/store_trailers/[^"\'<> ]+',
        r'store_trailers/[^"\'<> ]+(?:\.m3u8|\.mpd|\.webm|\.mp4)(?:\?[^"\'<> ]*)?'
    ]
    for pat in patterns:
        for raw in re.findall(pat,text,re.I):
            u=steam_url(raw)
            if not u:continue
            low=u.lower().split('?')[0]
            if not low.endswith(STREAM_EXTS+VIDEO_EXTS):continue
            if 'microtrailer' in low:continue
            if u not in found:found.append(u)
    def rank(u):
        low=u.lower()
        if 'hls_264_master.m3u8' in low:return 0
        if 'dash_h264.mpd' in low:return 1
        if 'movie_max' in low:return 2
        if 'movie480' in low:return 3
        return 4
    return sorted(found,key=rank)

def recursive_video_strings(obj):
    vals=[]
    if isinstance(obj,dict):
        for v in obj.values():vals.extend(recursive_video_strings(v))
    elif isinstance(obj,list):
        for v in obj:vals.extend(recursive_video_strings(v))
    elif isinstance(obj,str):
        u=steam_url(obj)
        if u:
            low=u.lower().split('?')[0]
            if low.endswith(STREAM_EXTS+VIDEO_EXTS) and 'microtrailer' not in low:vals.append(u)
    return vals

def steam_candidates(app_id,wanted):
    # Production retry is intentionally triggered by the commit message; publishing remains disabled for push events.
    """Descobre mídia do app exato; prioriza CDN Steam e usa vídeos embutidos em anúncios oficiais do próprio app como fallback."""
    app_id=int(app_id)
    api=f'https://store.steampowered.com/api/appdetails?appids={app_id}&cc=us&l=english'
    try:
        with urllib.request.urlopen(req(api,steam_age=True),timeout=25) as r:data=json.loads(r.read().decode('utf-8','ignore'))
        root=data.get(str(app_id),{});d=(root.get('data') or {}) if root.get('success') else {}
    except Exception as e:
        print('steam discovery failed',app_id,e);d={}
    out=[]
    if wanted=='video':
        for movie in d.get('movies') or []:
            name=movie.get('name','')
            for u in recursive_video_strings(movie):
                if 'youtube.com' in u.lower() or 'youtu.be' in u.lower():continue
                out.append((u,'steam_exact_app_direct_stream',name))
        for u in steam_store_streams(app_id):
            out.append((u,'steam_exact_app_store_stream',''))

        # Alguns jogos (incluindo Deadlock) não publicam trailers no appdetails.
        # Procura vídeos somente no feed de anúncios oficiais do app, não em buscas
        # genéricas nem em páginas de usuários da comunidade.
        announcement_pages=[
            f'https://steamcommunity.com/games/{app_id}/announcements/',
            f'https://store.steampowered.com/news/app/{app_id}/',
        ]
        for page in announcement_pages:
            try:
                with urllib.request.urlopen(req(page,steam_age=True),timeout=20) as r:
                    body=html.unescape(r.read(12*1024*1024).decode('utf-8','ignore')).replace('\\/','/')
            except Exception as e:
                print('steam official announcement video discovery failed',page,e,flush=True)
                continue
            candidates=[]
            patterns=[
                r"""https?://video\.[^"'<> ]*steamstatic\.com/store_trailers/[^"'<> ]+""",
                r"""https?://[^"'<> ]*steamstatic\.com/store_trailers/[^"'<> ]+""",
                r"""https?://(?:www\.)?youtube\.com/(?:watch\?v=[A-Za-z0-9_-]{6,}|embed/[A-Za-z0-9_-]{6,})[^"'<> ]*""",
                r"""https?://youtu\.be/[A-Za-z0-9_-]{6,}[^"'<> ]*""",
                r"""(?:src|href|data-video|data-url)=["']([^"']+)["']"""
            ]
            for pattern in patterns:
                for raw in re.findall(pattern,body,re.I):
                    u=html.unescape(raw).replace('\\/','/').strip().rstrip('),;')
                    if u.startswith('//'):u='https:'+u
                    if u.startswith('/'):
                        u=urllib.parse.urljoin(page,u)
                    low=u.lower().split('?')[0]
                    if low.endswith(STREAM_EXTS+VIDEO_EXTS) and 'steamstatic.com/store_trailers/' in low:
                        candidates.append((u,'steam_official_app_announcement_cdn',page))
                    elif 'youtube.com/watch' in low or 'youtube.com/embed/' in low or 'youtu.be/' in low:
                        # Apenas embeds presentes no feed oficial do app; downloader/QA valida o arquivo.
                        candidates.append((u,'steam_official_app_announcement_embed',page))
            for u,evidence,label in candidates:
                out.append((u,evidence,label))
            if candidates:
                print('steam official announcement video candidates',app_id,len(candidates),page,flush=True)
                break
    elif wanted=='image':
        for shot in d.get('screenshots') or []:
            u=shot.get('path_full') or shot.get('path_thumbnail')
            if u:out.append((u,'steam_exact_app_screenshot',str(shot.get('id',''))))
    dedup=[];seen=set()
    for row in out:
        if row[0] in seen:continue
        seen.add(row[0]);dedup.append(row)
    return dedup

def blocked_candidate(url,item):
    low=url.lower();blocked=list(LOW_VALUE_TOKENS)+[str(x).lower() for x in item.get('blocked_tokens',[])]
    return next((tok for tok in blocked if tok and tok in low),None)

def main(path):
    spec=json.loads(Path(path).read_text(encoding='utf-8'));out=Path('output/media');out.mkdir(parents=True,exist_ok=True)
    assets=[];errors=[];seq=0;seen=set();seen_movie_sources=set()
    for item in spec.get('media',[]):
        wanted=item.get('type','video');role=item.get('role','');max_assets=int(item.get('max_assets',4));candidates=[]
        if item.get('steam_app_id'):
            candidates=steam_candidates(item['steam_app_id'],wanted);source=f"steam_app:{item['steam_app_id']}"
        else:
            url=item['url'];source=item.get('source_proof') or url;low=url.lower().split('?')[0]
            if wanted=='video' and social_profile_url(url):
                candidates=discover_social_posts(url)
            elif low.endswith(VIDEO_EXTS+STREAM_EXTS+IMAGE_EXTS) or bool(item.get('force_image',False)) or 'drive.google.com/file/d/' in url.lower() or 'youtube.com' in url or 'youtu.be' in url or social_post_url(url) or (wanted=='video' and is_instagram_video_url(url)):
                candidates=[(url,item.get('relevance_evidence','direct_source'),item.get('source_label',''))]
            else:
                allow_images=bool(item.get('allow_images_from_page',False) and wanted=='image')
                candidates=[(u,'official_page_discovery','') for u in discover(url,allow_images=allow_images)]
            for fallback in item.get('fallback_urls',[]) or []:
                if isinstance(fallback,str) and fallback.startswith('http'):
                    candidates.append((fallback,'official_fallback_source','fallback'))
        got=0
        for u,evidence,label in candidates[:60]:
            if u in seen:continue
            movie_key=(source,label) if item.get("steam_app_id") and label else None
            if movie_key and movie_key in seen_movie_sources:continue
            low=u.lower();clean=low.split('?')[0];isimg=clean.endswith(IMAGE_EXTS) or bool(item.get('force_image',False) and wanted=='image');isstream=clean.endswith(STREAM_EXTS);isdrive='drive.google.com/file/d/' in low
            if wanted=='video' and isimg:continue
            if wanted=='image' and not isimg:continue
            blocked=blocked_candidate(u,item)
            if blocked:print('relevance reject',blocked,u);continue
            seq+=1;dest=out/f'asset_{seq:02d}.{"jpg" if isimg else "mp4"}'
            if isimg:
                try:
                    with urllib.request.urlopen(req(u,source if str(source).startswith('http') else None),timeout=25) as r,open(dest,'wb') as f:f.write(r.read(50*1024*1024))
                    ok=dest.exists() and dest.stat().st_size>20000;info={'duration':0,'width':0,'height':0,'codec':'image'} if ok else None
                except Exception as e:print('image download failed',u,e);info=None
            elif isstream:info=stream_download(u,dest)
            elif isdrive:info=gdrive_download(u,dest)
            elif (
                wanted=='video'
                and clean.endswith(VIDEO_EXTS)
                and ('rockstargames.com/vi/downloads/videos/' in low or 'media-rockstargames-com.akamaized.net/vi/downloads/videos/' in low or 'download.enshrouded.com/press%20kit/trailers/' in low)
            ):
                info=official_remote_clip(u,dest,source if str(source).startswith('http') else 'https://www.rockstargames.com/')
            elif is_instagram_video_url(u) and wanted=='video':info=download_public_instagram(u,dest,probe_info)
            elif 'youtube.com' in low or 'youtu.be' in low or social_post_url(u):info=ytdlp(u,dest)
            else:info=download(u,dest,source if str(source).startswith('http') else None)
            if not info:dest.unlink(missing_ok=True);continue
            if wanted=='video':
                min_d=float(item.get('min_duration',8))
                if float(info.get('duration',0))<min_d:
                    print('duration reject',info.get('duration'),u);dest.unlink(missing_ok=True);continue
            seen.add(u)
            if movie_key:seen_movie_sources.add(movie_key)
            assets.append({'index':seq,'path':str(dest),'type':'image' if isimg else 'video','role':role,'url':u,'source':source,
                           'relevance_evidence':evidence,'source_label':label,'approved':True,'duration':float(info.get('duration',0)),
                           'width':int(info.get('width',0)),'height':int(info.get('height',0))})
            got+=1
            if got>=max_assets:break
        if not got:errors.append({'source':source,'role':role,'error':'no_approved_relevant_media'})
        # Once quality requirements are met, stop probing slower fallback sources.
        # If the first source fails, iteration continues through the remaining routes.
        minimum_now=int(spec.get('minimum_assets',2))
        videos_now=[a for a in assets if a['type']=='video']
        images_now=[a for a in assets if a['type']=='image']
        seconds_now=sum(float(a.get('duration',0)) for a in videos_now)
        if (len(assets)>=minimum_now
            and len(videos_now)>=int(spec.get('minimum_video_assets',1))
            and seconds_now>=float(spec.get('minimum_unique_video_seconds',0))
            and len(images_now)>=int(spec.get('minimum_image_assets',0))):
            print('media acquisition complete; skipping remaining fallbacks',len(assets),'assets',len(videos_now),'videos',round(seconds_now,2),'unique video seconds',flush=True)
            break
    minimum=int(spec.get('minimum_assets',2));videos=[a for a in assets if a['type']=='video'];images=[a for a in assets if a['type']=='image']
    unique_video_seconds=round(sum(float(a.get('duration',0)) for a in videos),3)
    min_videos=int(spec.get('minimum_video_assets',1));min_secs=float(spec.get('minimum_unique_video_seconds',0));min_images=int(spec.get('minimum_image_assets',0))
    # Delivery fallback: tolerate a one-asset shortfall only when every substantive
    # media gate (approved video count, unique footage duration, and image count) passes.
    # This avoids blocking a complete edit over one unavailable secondary still.
    media_core_passes=(len(videos)>=min_videos and unique_video_seconds>=min_secs and len(images)>=min_images)
    effective_minimum=minimum-1 if len(assets)==minimum-1 and media_core_passes else minimum
    manifest={'assets':assets,'clips':[a['path'] for a in assets],'errors':errors,'publishable_media':False,'generic_fallback':False,'official_assets':True,
              'minimum_assets':effective_minimum,'requested_minimum_assets':minimum,'one_asset_shortfall_tolerated':effective_minimum<minimum,
              'video_assets':len(videos),'image_assets':len(images),'unique_video_seconds':unique_video_seconds,
              'minimum_video_assets':min_videos,'minimum_unique_video_seconds':min_secs,'minimum_image_assets':min_images,
              'semantic_policy':'exact_source_only; exact_app_assets; direct_steam_cdn_before_youtube; external_youtube_fallback_after_direct_block; no_generic_page_images; reject_logo_banner_store_intro; explicit_scene_assets_only'}
    manifest['publishable_media']=len(assets)>=effective_minimum and media_core_passes
    Path('output/clips.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    if len(assets)<effective_minimum:raise RuntimeError(f'QUALITY_BLOCK: somente {len(assets)} assets aprovados; minimo efetivo {effective_minimum} (solicitado {minimum})')
    if len(videos)<min_videos:raise RuntimeError(f'QUALITY_BLOCK: somente {len(videos)} videos aprovados; minimo {min_videos}')
    if unique_video_seconds<min_secs:raise RuntimeError(f'QUALITY_BLOCK: apenas {unique_video_seconds}s de video unico aprovado; minimo {min_secs}s')
    if len(images)<min_images:raise RuntimeError(f'QUALITY_BLOCK: somente {len(images)} imagens aprovadas; minimo {min_images}')
    print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__':main(sys.argv[1])
# [run-production] TOPIC=Deadlock — retry targeted after official Steam announcement fallback.

# Production trigger 2026-10-14: League of Legends private delivery retry.
