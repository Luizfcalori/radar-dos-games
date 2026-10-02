#!/usr/bin/env python3
"""Upload seguro para o YouTube. Exige OAuth refresh token nos Secrets."""
import json, os, sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES=['https://www.googleapis.com/auth/youtube.upload','https://www.googleapis.com/auth/youtube.readonly']

def service():
    required=['YT_CLIENT_ID','YT_CLIENT_SECRET','YT_REFRESH_TOKEN']
    missing=[x for x in required if not os.getenv(x)]
    if missing: raise RuntimeError('Secrets ausentes: '+', '.join(missing))
    c=Credentials(None,refresh_token=os.environ['YT_REFRESH_TOKEN'],token_uri='https://oauth2.googleapis.com/token',client_id=os.environ['YT_CLIENT_ID'],client_secret=os.environ['YT_CLIENT_SECRET'],scopes=SCOPES)
    return build('youtube','v3',credentials=c)

def channel_id(yt):
    r=yt.channels().list(part='id,snippet',mine=True).execute()
    if not r.get('items'): raise RuntimeError('Nenhum canal autenticado')
    return r['items'][0]['id'],r['items'][0]['snippet']['title']

def upload(path,meta):
    yt=service(); cid,title=channel_id(yt)
    expected=os.getenv('YT_CHANNEL_ID')
    if not expected or cid != expected: raise RuntimeError(f'CANAL INCORRETO: autenticado={title} ({cid}), esperado={expected}')
    body={'snippet':{'title':meta['title'],'description':meta['description'],'tags':meta.get('tags',[]),'categoryId':'20'},'status':{'privacyStatus':meta.get('privacy','public'),'selfDeclaredMadeForKids':False,'containsSyntheticMedia':bool(meta.get('containsSyntheticMedia',True))}}
    req=yt.videos().insert(part='snippet,status',body=body,media_body=MediaFileUpload(path,chunksize=-1,resumable=True))
    resp=None
    while resp is None: _,resp=req.next_chunk()
    print(json.dumps(resp))

if __name__=='__main__': upload(sys.argv[1],json.load(open(sys.argv[2],encoding='utf-8')))
