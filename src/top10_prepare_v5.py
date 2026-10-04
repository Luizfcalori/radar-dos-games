#!/usr/bin/env python3
import json
from pathlib import Path

p=Path('output/auto-media-plan.json')
plan=json.loads(p.read_text(encoding='utf-8'))

# Mantém o primeiro Top 10 robusto com imagens oficiais por pauta.
plan['media']=[m for m in plan['media'] if m.get('type')=='image']

# FFmpeg drawtext: evita apóstrofo cru no card sem alterar a narração.
for scene in plan.get('scenes',[]):
    if scene.get('role')=='dragons_dogma_dark_arisen':
        scene['title']=scene.get('title','').replace("DRAGON'S DOGMA","DRAGONS DOGMA")

# Fontes diretas já validadas nas páginas oficiais / projeto aprovado anterior.
direct_roles={
    'kingdom_hearts_switch2': [
        'https://imguscdn.gamespress.com/cdn/files/Square-Enix/2026/06/090453-397a8af7/KHC_keyart_16x9_no_logo.png?w=600&mode=max&otf=y&quality=90&format=png&bgcolor=transparent&sky=571da1df12e6ae8ce287499185ca1c6f1f32c893ee985a7bef62dcdd965f1825'
    ],
    'ace_combat_8': [
        'https://us-east-1-bandai.graphassets.com/AXzioIclSWilEjFtsMJPwz/cmrwlrzb96u3u06lqcvr1hpxg',
        'https://us-east-1-bandai.graphassets.com/AXzioIclSWilEjFtsMJPwz/cmtqest6c15pf08lmvw006lre'
    ],
    'qssr_ps5': [
        'https://blog.playstation.com/tachyon/2026/10/5f2b04388e41b48507f4c8d57ce8f53bd059f03a.jpg'
    ],
    'gears_eday': [
        'https://xboxwire.thesourcemediaassets.com/sites/2/2026/10/GoW_EDAY_Adagio_4K_Final_09-0f31e58cf65dec22523a.jpg'
    ]
}
source_proof={
    'kingdom_hearts_switch2':'https://press.na.square-enix.com/SQUARE-ENIX-UNVEILS-NEW-KINGDOM-HEARTS-ANNOUNCEMENTS-DURING-NINTENDO-D',
    'ace_combat_8':'https://www.bandainamcoent.com/news/ace-combat-8-wings-of-theve-takes-flight-today',
    'qssr_ps5':'https://blog.playstation.com/2026/10/01/ai-upscaling-is-coming-to-ps5/',
    'gears_eday':'https://news.xbox.com/en-us/2026/10/01/gears-of-war-e-day-early-access-launch-trailer-xbox/'
}
blocked=['avatar','author','profile','headshot','newsletter','podcast','logo','icon','header','footer']
plan['media']=[m for m in plan['media'] if m.get('role') not in direct_roles]
for role,urls in direct_roles.items():
    for u in urls:
        plan['media'].append({
            'type':'image','url':u,'role':role,'max_assets':1,
            'source_proof':source_proof[role],
            'relevance_evidence':'direct_official_asset_validated',
            'blocked_tokens':blocked
        })
plan['minimum_assets']=10
plan['minimum_video_assets']=0
plan['minimum_unique_video_seconds']=0
plan['minimum_image_assets']=10
p.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')

# Robustez do coletor: ignora pseudo-URLs inválidas, aceita "no_logo" como key art
# e reconhece a CDN GraphAssets da Bandai mesmo sem extensão no URL.
mp=Path('src/media.py')
text=mp.read_text(encoding='utf-8')
old="""    for raw in raws:\n        u=urllib.parse.urljoin(page,raw.strip());low=u.lower();clean=low.split('?')[0]\n        is_video=clean.endswith(VIDEO_EXTS+STREAM_EXTS) or 'drive.google.com/file/d/' in low or 'youtube.com/watch' in low or 'youtu.be/' in low\n"""
new="""    for raw in raws:\n        try:\n            u=urllib.parse.urljoin(page,raw.strip())\n        except (ValueError, UnicodeError) as e:\n            print('invalid discovered url skipped', page, repr(raw[:160]), e)\n            continue\n        low=u.lower();clean=low.split('?')[0]\n        is_video=clean.endswith(VIDEO_EXTS+STREAM_EXTS) or 'drive.google.com/file/d/' in low or 'youtube.com/watch' in low or 'youtu.be/' in low\n"""
if old in text:
    text=text.replace(old,new,1)
old2="""def blocked_candidate(url,item):\n    low=url.lower();blocked=list(LOW_VALUE_TOKENS)+[str(x).lower() for x in item.get('blocked_tokens',[])]\n"""
new2="""def blocked_candidate(url,item):\n    low=url.lower().replace('no_logo','keyart')\n    blocked=list(LOW_VALUE_TOKENS)+[str(x).lower() for x in item.get('blocked_tokens',[])]\n"""
if old2 in text:
    text=text.replace(old2,new2,1)
old3="""            if low.endswith(VIDEO_EXTS+STREAM_EXTS+IMAGE_EXTS) or 'drive.google.com/file/d/' in url.lower() or 'youtube.com' in url or 'youtu.be' in url:\n"""
new3="""            if low.endswith(VIDEO_EXTS+STREAM_EXTS+IMAGE_EXTS) or ('bandai.graphassets.com' in low and wanted=='image') or 'drive.google.com/file/d/' in url.lower() or 'youtube.com' in url or 'youtu.be' in url:\n"""
if old3 in text:
    text=text.replace(old3,new3,1)
old4="""            low=u.lower();clean=low.split('?')[0];isimg=clean.endswith(IMAGE_EXTS);isstream=clean.endswith(STREAM_EXTS);isdrive='drive.google.com/file/d/' in low\n"""
new4="""            low=u.lower();clean=low.split('?')[0];isimg=clean.endswith(IMAGE_EXTS) or ('bandai.graphassets.com' in low and wanted=='image');isstream=clean.endswith(STREAM_EXTS);isdrive='drive.google.com/file/d/' in low\n"""
if old4 in text:
    text=text.replace(old4,new4,1)
mp.write_text(text,encoding='utf-8')
print(json.dumps({'prepared':True,'scenes':len(plan.get('scenes',[])),'media_specs':len(plan.get('media',[]))}))
