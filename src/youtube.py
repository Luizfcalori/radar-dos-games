#!/usr/bin/env python3
"""Upload seguro para o YouTube. Exige OAuth refresh token nos Secrets."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES=['https://www.googleapis.com/auth/youtube.upload','https://www.googleapis.com/auth/youtube.readonly']
RADAR_CHANNEL_ID='UCSZJZE-E10SVdx42wrDeWhw'
RADAR_CHANNEL_TITLE='Radar dos Games'


def service():
    required=['YT_CLIENT_ID','YT_CLIENT_SECRET','YT_REFRESH_TOKEN']
    missing=[x for x in required if not os.getenv(x)]
    if missing:
        raise RuntimeError('Secrets ausentes: '+', '.join(missing))
    c=Credentials(
        None,
        refresh_token=os.environ['YT_REFRESH_TOKEN'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.environ['YT_CLIENT_ID'],
        client_secret=os.environ['YT_CLIENT_SECRET'],
        scopes=SCOPES,
    )
    return build('youtube','v3',credentials=c)


def channel_identity(yt):
    r=yt.channels().list(part='id,snippet',mine=True).execute()
    items=r.get('items',[])
    if len(items) != 1:
        raise RuntimeError('Selecione exatamente um canal durante o consentimento OAuth.')
    item=items[0]
    return item['id'],item.get('snippet',{}).get('title','')


def assert_radar_channel(cid,title):
    if cid != RADAR_CHANNEL_ID or title.strip().casefold() != RADAR_CHANNEL_TITLE.casefold():
        raise RuntimeError(
            f'CANAL INCORRETO: autenticado={title} ({cid}); esperado={RADAR_CHANNEL_TITLE} ({RADAR_CHANNEL_ID}). Upload bloqueado.'
        )


def _scheduled_status(meta):
    privacy=meta.get('privacy','public')
    status={
        'privacyStatus':privacy,
        'selfDeclaredMadeForKids':False,
        'containsSyntheticMedia':bool(meta.get('containsSyntheticMedia',True)),
    }
    publish_at=(meta.get('publishAt') or '').strip()
    if publish_at:
        if privacy != 'private':
            raise RuntimeError('Agendamento nativo exige privacy=private.')
        parsed=datetime.fromisoformat(publish_at.replace('Z','+00:00'))
        if parsed.tzinfo is None:
            raise RuntimeError('publishAt precisa conter fuso horario/UTC.')
        if parsed.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise RuntimeError(f'publishAt precisa estar no futuro: {publish_at}')
        status['publishAt']=publish_at
    return status


def _is_master(path: str) -> bool:
    p = Path(path)
    return p.name.lower().startswith('master') and 'shorts' not in {x.lower() for x in p.parts}


def _prepare_master_thumbnail(video_path: str, meta: dict) -> Path | None:
    if not _is_master(video_path):
        return None
    thumb = Path(meta.get('thumbnail') or 'output/thumbnail.jpg')
    thumb.parent.mkdir(parents=True, exist_ok=True)

    # Quando uma capa foi aprovada editorialmente, preserva exatamente o arquivo
    # fornecido pelo workflow em vez de regenerá-lo no momento do upload.
    if meta.get('use_existing_thumbnail') is True:
        if not thumb.exists() or thumb.stat().st_size < 20_000:
            raise RuntimeError('QUALITY_BLOCK: capa aprovada indicada, mas arquivo está ausente ou inválido.')
        return thumb

    subprocess.run(
        [sys.executable, 'src/thumbnail.py', video_path, meta['title'], str(thumb)],
        check=True,
    )
    if not thumb.exists() or thumb.stat().st_size < 20_000:
        raise RuntimeError('QUALITY_BLOCK: thumbnail do Master ausente ou inválida.')
    return thumb


def _set_thumbnail(yt, video_id: str, thumbnail: Path | None):
    if thumbnail is None:
        return None
    response = yt.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(str(thumbnail), mimetype='image/jpeg', resumable=False),
    ).execute()
    return response


def upload(path,meta):
    yt=service()
    cid,title=channel_identity(yt)
    assert_radar_channel(cid,title)

    thumbnail = _prepare_master_thumbnail(path, meta)

    body={
        'snippet':{
            'title':meta['title'],
            'description':meta['description'],
            'tags':meta.get('tags',[]),
            'categoryId':'20',
        },
        'status':_scheduled_status(meta),
    }
    req=yt.videos().insert(
        part='snippet,status',
        body=body,
        media_body=MediaFileUpload(path,chunksize=8*1024*1024,resumable=True),
    )
    resp=None
    consecutive_errors=0
    while resp is None:
        try:
            _,resp=req.next_chunk()
            consecutive_errors=0
        except (TimeoutError, OSError) as exc:
            consecutive_errors += 1
            if consecutive_errors > 5:
                raise
            wait=min(5 * (2 ** (consecutive_errors - 1)), 60)
            print(f'Upload temporariamente interrompido ({type(exc).__name__}); retomando em {wait}s...', file=sys.stderr)
            time.sleep(wait)

    thumb_resp = _set_thumbnail(yt, resp['id'], thumbnail)
    if thumbnail is not None:
        resp['_radarThumbnail'] = {
            'path': str(thumbnail),
            'applied': bool(thumb_resp),
            'preservedApprovedCover': bool(meta.get('use_existing_thumbnail')),
        }
    print(json.dumps(resp))


if __name__=='__main__':
    upload(sys.argv[1],json.load(open(sys.argv[2],encoding='utf-8')))
