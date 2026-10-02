#!/usr/bin/env python3
"""Upload seguro para o YouTube. Exige OAuth refresh token nos Secrets."""
import json, os, sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES=['https://www.googleapis.com/auth/youtube.upload','https://www.googleapis.com/auth/youtube.readonly']
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


def expected_channel_id():
    # O ID correto deve ser gravado somente depois de confirmar o canal real.
    # Enquanto isso, o nome exato do canal funciona como trava adicional.
    return os.getenv('YT_CHANNEL_ID','').strip()


def channel_identity(yt):
    r=yt.channels().list(part='id,snippet',mine=True).execute()
    if not r.get('items'):
        raise RuntimeError('Nenhum canal autenticado')
    item=r['items'][0]
    return item['id'],item['snippet']['title']


def assert_radar_channel(cid,title):
    if title.strip().casefold() != RADAR_CHANNEL_TITLE.casefold():
        raise RuntimeError(
            f'CANAL INCORRETO: autenticado={title} ({cid}); esperado={RADAR_CHANNEL_TITLE}. Upload bloqueado.'
        )
    expected=expected_channel_id()
    if expected and cid != expected:
        raise RuntimeError(
            f'CANAL INCORRETO: autenticado={title} ({cid}), esperado ID={expected}. Upload bloqueado.'
        )


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
        'status':{
            'privacyStatus':meta.get('privacy','public'),
            'selfDeclaredMadeForKids':False,
            'containsSyntheticMedia':bool(meta.get('containsSyntheticMedia',True)),
        },
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
