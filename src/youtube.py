#!/usr/bin/env python3
"""Upload seguro para o YouTube. Exige OAuth refresh token nos Secrets."""
import json, os, sys
from datetime import datetime, timezone
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


def upload(path,meta):
    yt=service()
    cid,title=channel_identity(yt)
    assert_radar_channel(cid,title)
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
        media_body=MediaFileUpload(path,chunksize=-1,resumable=True),
    )
    resp=None
    while resp is None:
        _,resp=req.next_chunk()
    print(json.dumps(resp))


if __name__=='__main__':
    upload(sys.argv[1],json.load(open(sys.argv[2],encoding='utf-8')))
