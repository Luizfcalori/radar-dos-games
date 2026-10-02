#!/usr/bin/env python3
"""Monta automaticamente a pauta diária do Radar dos Games a partir da pesquisa RSS.

Não usa API paga nem LLM externo. A narração é uma síntese editorial própria
baseada em metadados e sinais objetivos da publicação oficial selecionada.
"""
import html
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

OUT = Path("output")
DATA = Path("data")
OUT.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/129 Safari/537.36"
STOP = {"para","com","uma","como","que","por","dos","das","de","do","da","em","no","na","nos","nas","e","o","a","os","as","um","uns","umas","se","ao","aos","à","às","mais","novo","nova","novos","novas","game","games","jogo","jogos","the","and","for","with","from","this","that","your","you","are","was","will","has","have","into","its","our","out","new","official","today","news","update","release","available","now","get","all","can","on","in","of","to"}
PLATFORM_PATTERNS = [(r"\bPlayStation\s*5\b|\bPS5\b","PlayStation 5"),(r"\bPlayStation\s*4\b|\bPS4\b","PlayStation 4"),(r"\bXbox Series X\|S\b|\bXbox Series\b","Xbox Series X|S"),(r"\bXbox One\b","Xbox One"),(r"\bNintendo Switch 2\b","Nintendo Switch 2"),(r"\bNintendo Switch\b","Nintendo Switch"),(r"\bSteam\b","Steam"),(r"\bPC\b","PC")]


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


class PageParser(HTMLParser):
    def __init__(self, base):
        super().__init__(); self.base=base; self.meta={}; self.media=[]; self.paragraphs=[]; self._in_p=False; self._p=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if tag=="meta":
            key=(d.get("property") or d.get("name") or "").lower(); val=d.get("content")
            if key and val:
                self.meta[key]=val
                if key in ("og:image","twitter:image"): self.media.append(("image",urljoin(self.base,val)))
        elif tag in ("img","source"):
            for key in ("src","data-src","data-original","srcset"):
                val=d.get(key)
                if val:
                    for part in val.split(","):
                        u=part.strip().split(" ")[0]
                        if u: self.media.append(("image",urljoin(self.base,u)))
        elif tag in ("iframe","embed","video"):
            for key in ("src","data-src"):
                val=d.get(key)
                if val:
                    u=urljoin(self.base,val); typ="video" if ("youtube.com" in u or "youtu.be" in u or re.search(r"\.(mp4|webm|mov)(\?|$)",u,re.I)) else "image"
                    self.media.append((typ,u))
        elif tag=="p": self._in_p=True; self._p=[]
    def handle_data(self,data):
        if self._in_p: self._p.append(data)
    def handle_endtag(self,tag):
        if tag=="p" and self._in_p:
            txt=clean(" ".join(self._p))
            if len(txt)>=45: self.paragraphs.append(txt)
            self._in_p=False; self._p=[]


def fetch_page(url):
    r=requests.get(url,headers={"User-Agent":UA,"Accept-Language":"pt-BR,pt;q=0.9,en;q=0.8"},timeout=25); r.raise_for_status()
    p=PageParser(url); p.feed(r.text); return p


def media_quality(kind,url):
    u=url.lower()
    if not url.startswith("http") or any(x in u for x in ("logo","icon","avatar","sprite","favicon","badge","tracking","pixel")): return False
    if kind=="video": return True
    return any(x in u for x in (".jpg",".jpeg",".png",".webp","image","media","cdn","assets","akamai","cloudfront"))


def canonical_media(items):
    seen=set(); out=[]
    for kind,url in items:
        url=url.replace("&amp;","&"); key=re.sub(r"[?#].*$","",url)
        if key in seen or not media_quality(kind,url): continue
        seen.add(key); out.append((kind,url))
    videos=[x for x in out if x[0]=="video"]; images=[x for x in out if x[0]=="image"]
    return (videos[:2]+images[:14])[:16]


def load_history():
    p=DATA/"published.json"
    try: return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"videos":[]}
    except Exception: return {"videos":[]}


def source_name(url):
    h=urlparse(url).netloc.lower()
    if "xbox" in h or "microsoft" in h: return "Xbox"
    if "playstation" in h or "sony" in h: return "PlayStation"
    if "nintendo" in h: return "Nintendo"
    if "steam" in h or "valve" in h: return "Steam"
    return h.replace("www.","").split(".")[0].title() or "fonte oficial"


def keywords(text,limit=7):
    words=re.findall(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9'’\-]{2,}",clean(text)); c=Counter(); original={}
    for w in words:
        k=w.lower()
        if k in STOP or k.isdigit() or len(k)<4: continue
        c[k]+=1; original.setdefault(k,w)
    return [original[k] for k,_ in c.most_common(limit)]


def platforms(text):
    found=[]
    for pat,name in PLATFORM_PATTERNS:
        if re.search(pat,text,re.I) and name not in found: found.append(name)
    return found


def dates_and_numbers(text):
    pats=[r"\b\d{1,2}\s+de\s+[A-Za-zÀ-ÿ]+\s+de\s+\d{4}\b",r"\b[A-Z][a-z]+\s+\d{1,2},\s+\d{4}\b",r"\b\d{1,2}/\d{1,2}/\d{4}\b",r"\b20\d{2}\b"]
    found=[]
    for pat in pats:
        for x in re.findall(pat,text):
            if x not in found: found.append(x)
    return found[:5]


def sentence(text): return re.sub(r"\s+"," ",text).strip(" .")


def make_script(candidate,parser):
    title=sentence(candidate["title"]); src=source_name(candidate["url"]); corpus=" ".join([candidate.get("summary","")]+parser.paragraphs[:20])
    kws=keywords(title+" "+corpus,8); plats=platforms(corpus+" "+title); dates=dates_and_numbers(corpus+" "+title)
    focus=", ".join(kws[:4]) if kws else "o anúncio e suas principais novidades"; extra=", ".join(kws[4:7]) if len(kws)>4 else "os detalhes apresentados pela fonte oficial"
    plat_txt=", ".join(plats) if plats else "as plataformas citadas pela publicação oficial"; date_txt=", ".join(dates[:3]) if dates else "as datas destacadas no anúncio"
    blocks=[
        f"{title}. Essa é a pauta que entrou no topo do radar agora. O material vem de uma fonte oficial da {src}, e a ideia aqui é separar o que foi realmente apresentado do barulho em volta da notícia, sem transformar expectativa em confirmação.",
        f"O anúncio gira principalmente em torno de {focus}. Esses são os sinais mais fortes do texto oficial e ajudam a entender por que a pauta ganhou prioridade na nossa varredura. Quando uma atualização concentra tantos elementos do mesmo assunto, normalmente vale acompanhar de perto o impacto para quem já joga e para quem estava esperando uma novidade.",
        f"Nas informações publicadas, também aparecem referências a {extra}. Isso não significa que todo detalhe imaginado pela comunidade esteja confirmado. O Radar dos Games usa justamente essa diferença como filtro: primeiro o que está documentado na fonte, depois a leitura do que pode mudar na experiência de jogo.",
        f"Sobre disponibilidade, o material menciona {plat_txt}. Esse ponto é importante porque versão, plataforma e janela de lançamento podem mudar completamente a relevância de uma notícia. Se houver atualização posterior da própria empresa, ela deve valer mais do que qualquer especulação anterior.",
        f"Outro dado que merece atenção é a janela temporal: {date_txt}. Em notícias de games, datas e períodos são o primeiro ponto que costuma receber ajustes, então o melhor é tratar essas referências como o estado atual do anúncio e conferir novamente quando a publicação oficial for atualizada.",
        f"Para o jogador, a leitura mais útil é simples: observar como {focus} se conecta ao jogo real, ao conteúdo disponível e às próximas etapas anunciadas. O que importa não é só o tamanho do anúncio, mas se ele traz mudança concreta, conteúdo jogável, melhoria de experiência ou uma nova razão para voltar ao título.",
        f"Também vale acompanhar os próximos materiais oficiais, principalmente trailer, gameplay, notas de atualização e páginas de produto. São essas fontes que normalmente resolvem as dúvidas que ficam abertas no primeiro anúncio. Se aparecer informação nova, o Radar atualiza a pauta em vez de reaproveitar uma versão antiga como se ainda fosse novidade.",
        f"Esse foi o resumo automático do Radar dos Games sobre {title}. A fonte selecionada nesta edição está vinculada na descrição para conferência. Se você curte receber as principais notícias de games com contexto e sem enrolação, acompanhe o canal porque o radar continua ligado.",
    ]
    return "\n\n".join(blocks)


def make_scenes(candidate,media_count,script):
    paras=[x.strip() for x in script.split("\n\n") if x.strip()]
    titles=["NO TOPO DO RADAR","O QUE FOI CONFIRMADO","POR QUE ESSA PAUTA IMPORTA","PLATAFORMAS E DISPONIBILIDADE","DATAS E JANELAS","IMPACTO PARA QUEM JOGA","O QUE OBSERVAR AGORA","RESUMO DO RADAR"]
    subs=[candidate["title"][:70],"FATOS DA FONTE OFICIAL","CONTEXTO SEM ESPECULAÇÃO","ONDE A NOTÍCIA SE APLICA","O ESTADO ATUAL DO ANÚNCIO","O QUE PODE MUDAR NA EXPERIÊNCIA","TRAILER, GAMEPLAY E ATUALIZAÇÕES","RADAR DOS GAMES"]
    scenes=[]
    for i,_ in enumerate(paras):
        a=(i%media_count)+1; b=((i+1)%media_count)+1
        scenes.append({"paragraph":i+1,"title":titles[i] if i<len(titles) else f"DESTAQUE {i+1}","subtitle":subs[i] if i<len(subs) else "RADAR DOS GAMES","media_indices":[a] if a==b else [a,b]})
    return scenes


def build_metadata(candidate,privacy):
    title=sentence(candidate["title"]); base=f"{title} | Radar dos Games"; base=base if len(base)<=98 else base[:95].rstrip()+"..."
    desc=f"Radar dos Games: resumo e contexto da pauta selecionada automaticamente nas fontes oficiais de games.\n\nFonte oficial consultada: {candidate['url']}\n\n#RadarDosGames #Games #Gaming #NoticiasDeGames"
    master={"title":base,"description":desc,"tags":["Radar dos Games","games","gaming","notícias de games"],"privacy":privacy,"containsSyntheticMedia":False}
    hooks=["O QUE FOI CONFIRMADO","POR QUE ISSO IMPORTA","O QUE VEM AGORA"]; shorts=[]
    for i in range(3):
        st=f"{hooks[i]}: {title}"; st=st if len(st)<=90 else st[:87].rstrip()+"..."
        shorts.append({"title":st+" #Shorts","description":desc+"\n#Shorts","tags":master["tags"]+["Shorts"],"privacy":privacy,"containsSyntheticMedia":False})
    return master,shorts


def main():
    research_path=OUT/"research.json"
    if not research_path.exists(): raise RuntimeError("output/research.json ausente")
    candidates=json.loads(research_path.read_text(encoding="utf-8")).get("candidates",[])
    if not candidates: raise RuntimeError("Nenhuma pauta recente encontrada nas fontes oficiais")
    used={x.get("content_id") for x in load_history().get("videos",[]) if isinstance(x,dict)}; forced=os.getenv("RADAR_TOPIC","AUTO").strip(); selected=selected_parser=selected_media=None; errors=[]
    for c in candidates:
        if c.get("content_id") in used: continue
        if forced.upper()!="AUTO" and forced.lower() not in c.get("title","").lower(): continue
        try:
            p=fetch_page(c["url"]); media=canonical_media(p.media)
            if len(media)<2: errors.append({"title":c.get("title"),"error":f"somente {len(media)} mídias descobertas"}); continue
            selected,selected_parser,selected_media=c,p,media; break
        except Exception as exc: errors.append({"title":c.get("title"),"error":str(exc)[:200]})
    if not selected: raise RuntimeError("Nenhuma pauta com mídia oficial suficiente. "+json.dumps(errors[:5],ensure_ascii=False))
    script=make_script(selected,selected_parser); (OUT/"auto-script.txt").write_text(script+"\n",encoding="utf-8")
    media_items=[{"type":typ,"url":url,"role":f"official_context_{i:02d}"} for i,(typ,url) in enumerate(selected_media,1)]
    plan={"topic":selected["title"],"source":selected["url"],"minimum_assets":2,"media":media_items,"scenes":make_scenes(selected,len(media_items),script)}
    (OUT/"auto-media-plan.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf-8")
    privacy=os.getenv("PUBLISH_PRIVACY","unlisted").strip() or "unlisted"; master_meta,shorts_meta=build_metadata(selected,privacy)
    (OUT/"master-youtube.json").write_text(json.dumps(master_meta,ensure_ascii=False,indent=2),encoding="utf-8")
    for i,meta in enumerate(shorts_meta,1): (OUT/f"short-{i}-youtube.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    payload={"selected_at":datetime.now(timezone.utc).isoformat(),**selected,"discovered_media":len(selected_media),"script_paragraphs":len([x for x in script.split("\n\n") if x.strip()]),"privacy":privacy,"selection_errors":errors}
    (OUT/"selected.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(payload,ensure_ascii=False))

if __name__=="__main__": main()
