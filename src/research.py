#!/usr/bin/env python3
"""Coleta notícias via RSS/feeds públicos e ranqueia pautas. Tema pode repetir; vídeo não."""
import feedparser, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
FEEDS=[
 'https://news.xbox.com/en-us/feed/',
 'https://blog.playstation.com/feed/',
 'https://www.nintendo.com/us/whatsnew/rss/',
 'https://store.steampowered.com/feeds/news.xml'
]
KEYS=('release','launch','trailer','gameplay','update','dlc','beta','demo','announc','lançamento','trailer')
def clean(s): return re.sub(r'<[^>]+>',' ',s or '').strip()
def main():
 items=[]
 for url in FEEDS:
  try:
   f=feedparser.parse(url)
   for e in f.entries[:20]:
    title=clean(e.get('title','')); summary=clean(e.get('summary','')); link=e.get('link','')
    score=sum(3 for k in KEYS if k in (title+' '+summary).lower())
    if score:
     cid=hashlib.sha256((title+'|'+link).encode()).hexdigest()[:16]
     items.append({'content_id':cid,'title':title,'summary':summary[:700],'url':link,'source':url,'score':score})
  except Exception as ex: print('feed warning',url,ex,file=sys.stderr)
 items=sorted(items,key=lambda x:x['score'],reverse=True)[:15]
 out={'generated_at':datetime.now(timezone.utc).isoformat(),'candidates':items}
 Path('output').mkdir(exist_ok=True); Path('output/research.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__': main()
