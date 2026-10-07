#!/usr/bin/env python3
"""Radar Social Bot v1: comentários seguros em YouTube, Instagram e Facebook."""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

RADAR_CHANNEL_ID = "UCSZJZE-E10SVdx42wrDeWhw"
RADAR_CHANNEL_TITLE = "Radar dos Games"


@dataclass
class Interaction:
    platform: str
    interaction_id: str
    parent_id: str
    author: str
    text: str
    source_id: str = ""
    already_replied: bool = False
    is_own: bool = False


def _fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    return "".join(c for c in value if not unicodedata.combining(c)).casefold().strip()


REPLIES = {
    "praise": [
        "Valeu demais! 🎮🔥 Tamo junto no Radar dos Games!",
        "Boa! 🔥 Obrigado por fortalecer o Radar dos Games! 🎮",
        "Aí sim! 👊🎮 Valeu por acompanhar!",
    ],
    "thanks": ["Tamo junto! 👊🎮", "Nós que agradecemos! 🔥🎮", "Valeu demais! 🚀"],
    "greeting": ["Salve! 🎮🔥 Tamo junto!", "Opa! 👊 Bom ter você por aqui!", "Fala, gamer! 🎮🚀"],
    "hype": ["🔥🎮 Esse hype tá forte!", "Aí sim! 👀🔥", "Bora! 🎮🚀"],
}
PRAISE = {"bom","boa","top","massa","show","incrivel","perfeito","excelente","brabo","legal","curti","amei","insano","maneiro","daora"}
THANKS = {"obrigado","obrigada","valeu","vlw","agradeco"}
GREET = {"oi","ola","opa","salve","fala","eae","eai","bom dia","boa tarde","boa noite"}
QUESTION = {"qual","quais","quando","onde","como","porque","por que","quem","quanto","vale","vai","tem","sera","pode","consegue"}
SENSITIVE = {"ruim","horrivel","lixo","mentira","fake","errado","pessimo","decepcionante","odio"}
SPAM = [r"https?://", r"www\.", r"bit\.ly", r"t\.me/", r"me segue", r"segue de volta", r"follow me", r"sub4sub"]


def choose(key: str, category: str) -> str:
    bank = REPLIES[category]
    n = int.from_bytes(hashlib.sha256((key + category).encode()).digest()[:2], "big")
    return bank[n % len(bank)]


def decide(i: Interaction) -> dict:
    text = (i.text or "").strip()
    folded = _fold(text)

    if i.is_own:
        return {"action":"ignore","category":"own","reason":"Comentário do próprio perfil.","reply":""}
    if i.already_replied:
        return {"action":"ignore","category":"already_replied","reason":"Já respondido.","reply":""}
    if not text:
        return {"action":"ignore","category":"empty","reason":"Sem texto.","reply":""}
    if any(re.search(p, folded, re.I) for p in SPAM):
        return {"action":"ignore","category":"spam","reason":"Possível spam/link.","reply":""}
    if "?" in text or any(folded == _fold(q) or folded.startswith(_fold(q) + " ") for q in QUESTION):
        return {"action":"approval","category":"question","reason":"Pergunta exige contexto para não inventar informação.","reply":""}
    if any(_fold(w) in folded for w in SENSITIVE):
        return {"action":"approval","category":"sensitive","reason":"Crítica/tema sensível exige revisão.","reply":""}
    if any(_fold(w) in folded for w in THANKS):
        return {"action":"reply","category":"thanks","reason":"Agradecimento simples.","reply":choose(i.interaction_id,"thanks")}
    if any(_fold(w) in folded for w in GREET):
        return {"action":"reply","category":"greeting","reason":"Saudação simples.","reply":choose(i.interaction_id,"greeting")}
    if any(_fold(w) in folded for w in PRAISE):
        return {"action":"reply","category":"praise","reason":"Engajamento positivo.","reply":choose(i.interaction_id,"praise")}
    if len(text) <= 12 and re.fullmatch(r"[\W_]+", text, re.UNICODE):
        return {"action":"reply","category":"hype","reason":"Reação curta/emoji.","reply":choose(i.interaction_id,"hype")}
    return {"action":"approval","category":"ambiguous","reason":"Intenção ambígua.","reply":""}


def required(*names: str) -> dict:
    missing = [n for n in names if not os.getenv(n, "").strip()]
    if missing:
        raise RuntimeError("Configuração ausente: " + ", ".join(missing))
    return {n: os.environ[n].strip() for n in names}


class YouTube:
    name = "youtube"
    def __init__(self, write: bool):
        self.write = write
        self.yt = None

    def service(self):
        if self.yt:
            return self.yt
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        env = required("YT_CLIENT_ID","YT_CLIENT_SECRET","YT_REFRESH_TOKEN")
        token = os.getenv("YT_SOCIAL_REFRESH_TOKEN", "").strip() or env["YT_REFRESH_TOKEN"]
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        if self.write:
            scopes.append("https://www.googleapis.com/auth/youtube.force-ssl")
        cred = Credentials(None, refresh_token=token, token_uri="https://oauth2.googleapis.com/token",
                           client_id=env["YT_CLIENT_ID"], client_secret=env["YT_CLIENT_SECRET"], scopes=scopes)
        self.yt = build("youtube","v3",credentials=cred,cache_discovery=False)
        return self.yt

    def check_channel(self, yt):
        items = yt.channels().list(part="id,snippet", mine=True).execute().get("items",[])
        if len(items) != 1:
            raise RuntimeError("OAuth precisa apontar para exatamente um canal.")
        cid = items[0].get("id","")
        title = items[0].get("snippet",{}).get("title","")
        if cid != RADAR_CHANNEL_ID or title.strip().casefold() != RADAR_CHANNEL_TITLE.casefold():
            raise RuntimeError(f"CANAL INCORRETO: {title} ({cid}).")

    def has_reply(self, yt, parent_id, count):
        if not count:
            return False
        page = None
        while True:
            r = yt.comments().list(part="snippet",parentId=parent_id,maxResults=100,pageToken=page,textFormat="plainText").execute()
            for item in r.get("items",[]):
                if item.get("snippet",{}).get("authorChannelId",{}).get("value","") == RADAR_CHANNEL_ID:
                    return True
            page = r.get("nextPageToken")
            if not page:
                return False

    def fetch(self, limit=30):
        yt = self.service()
        self.check_channel(yt)
        r = yt.commentThreads().list(part="snippet",allThreadsRelatedToChannelId=RADAR_CHANNEL_ID,
                                     maxResults=min(limit,100),order="time",textFormat="plainText").execute()
        out = []
        for thread in r.get("items",[]):
            ts = thread.get("snippet",{})
            top = ts.get("topLevelComment",{})
            sn = top.get("snippet",{})
            cid = top.get("id","")
            out.append(Interaction(
                "youtube", cid, cid, sn.get("authorDisplayName",""),
                sn.get("textDisplay","") or sn.get("textOriginal",""),
                ts.get("videoId",""),
                self.has_reply(yt,cid,int(ts.get("totalReplyCount",0) or 0)),
                sn.get("authorChannelId",{}).get("value","") == RADAR_CHANNEL_ID
            ))
        return out

    def reply(self, i, message):
        if not self.write:
            raise RuntimeError("Escrita no YouTube desativada.")
        r = self.service().comments().insert(
            part="snippet",
            body={"snippet":{"parentId":i.parent_id,"textOriginal":message}}
        ).execute()
        return r.get("id","")


class Meta:
    def __init__(self, platform: str, write: bool):
        self.name = platform
        self.write = write
        env = required("META_ACCESS_TOKEN","META_GRAPH_VERSION")
        self.token = env["META_ACCESS_TOKEN"]
        self.base = "https://graph.facebook.com/" + env["META_GRAPH_VERSION"]
        if platform == "instagram":
            e = required("INSTAGRAM_USER_ID","INSTAGRAM_USERNAME")
            self.account = e["INSTAGRAM_USER_ID"]
            self.username = e["INSTAGRAM_USERNAME"].casefold()
        else:
            self.account = required("FACEBOOK_PAGE_ID")["FACEBOOK_PAGE_ID"]
            self.username = ""

    def get(self, path, **params):
        params["access_token"] = self.token
        r = requests.get(self.base + "/" + path, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def post(self, path, **data):
        data["access_token"] = self.token
        r = requests.post(self.base + "/" + path, data=data, timeout=30)
        r.raise_for_status()
        return r.json()

    def fetch(self, limit=30):
        return self.fetch_instagram(limit) if self.name == "instagram" else self.fetch_facebook(limit)

    def fetch_instagram(self, limit):
        media = self.get(self.account + "/media", fields="id,caption,timestamp", limit=min(limit,25)).get("data",[])
        out = []
        for m in media:
            comments = self.get(m["id"] + "/comments",
                fields="id,text,username,timestamp,replies.limit(50){id,text,username}",limit=50).get("data",[])
            for c in comments:
                replies = c.get("replies",{}).get("data",[])
                user = c.get("username","")
                out.append(Interaction("instagram",c.get("id",""),c.get("id",""),user,c.get("text",""),m.get("id",""),
                    any((x.get("username","") or "").casefold()==self.username for x in replies),
                    user.casefold()==self.username))
        return out[:limit]

    def fetch_facebook(self, limit):
        posts = self.get(self.account + "/feed", fields="id,message,created_time", limit=min(limit,25)).get("data",[])
        out = []
        for p in posts:
            comments = self.get(p["id"] + "/comments",
                fields="id,message,from,created_time,comments.limit(50){id,message,from}",limit=50).get("data",[])
            for c in comments:
                replies = c.get("comments",{}).get("data",[])
                author = c.get("from") or {}
                out.append(Interaction("facebook",c.get("id",""),c.get("id",""),author.get("name",""),c.get("message",""),p.get("id",""),
                    any(str((x.get("from") or {}).get("id",""))==self.account for x in replies),
                    str(author.get("id",""))==self.account))
        return out[:limit]

    def reply(self, i, message):
        if not self.write:
            raise RuntimeError("Escrita Meta desativada.")
        path = i.parent_id + ("/replies" if self.name == "instagram" else "/comments")
        return str(self.post(path,message=message).get("id",""))


def env_bool(name, default=False):
    value = os.getenv(name)
    return default if value is None else value.casefold().strip() in {"1","true","yes","sim","on"}


def main():
    auto = env_bool("SOCIAL_BOT_AUTO_REPLY", False)
    max_replies = max(0,int(os.getenv("SOCIAL_BOT_MAX_REPLIES","5")))
    limit = max(1,int(os.getenv("SOCIAL_BOT_FETCH_LIMIT","30")))
    networks = [x.strip().casefold() for x in os.getenv("SOCIAL_BOT_NETWORKS","youtube").split(",") if x.strip()]

    report = {"generated_at":datetime.now(timezone.utc).isoformat(),"auto_reply":auto,
              "networks":{},"replied":[],"pending":[],"ignored":[],
              "notes":["Curtidas não disparam DM automática.","TikTok e Kwai aguardam endpoint oficial compatível."]}
    sent = 0

    for network in networks:
        if network in {"tiktok","kwai"}:
            report["networks"][network]={"status":"unsupported_write"}
            continue
        try:
            adapter = YouTube(auto) if network=="youtube" else Meta(network,auto)
            interactions = adapter.fetch(limit)
            report["networks"][network]={"status":"ok","fetched":len(interactions)}
            for i in interactions:
                d = decide(i)
                item = {"interaction":asdict(i),"decision":d}
                if d["action"]=="ignore":
                    report["ignored"].append(item)
                elif d["action"]=="approval" or not auto or sent>=max_replies:
                    item["status"]="proposed_only" if d["action"]=="reply" and not auto else "pending"
                    report["pending"].append(item)
                else:
                    item["response_id"]=adapter.reply(i,d["reply"])
                    item["status"]="sent"
                    report["replied"].append(item)
                    sent += 1
        except Exception as exc:
            report["networks"][network]={"status":"error","error":type(exc).__name__ + ": " + str(exc)}

    out = Path("social_bot/out")
    out.mkdir(parents=True,exist_ok=True)
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"pending.json").write_text(json.dumps(report["pending"],ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"networks":report["networks"],"replied":len(report["replied"]),"pending":len(report["pending"])},ensure_ascii=False,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
