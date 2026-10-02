#!/usr/bin/env python3
"""Coleta pautas recentes em fontes oficiais e ranqueia por frescor + relevância."""
import calendar
import feedparser
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

FEEDS = [
    "https://news.xbox.com/en-us/feed/",
    "https://blog.playstation.com/feed/",
    "https://www.nintendo.com/us/whatsnew/rss/",
    "https://store.steampowered.com/feeds/news.xml",
]
KEYS = (
    "release", "launch", "trailer", "gameplay", "update", "dlc", "beta", "demo",
    "announc", "showcase", "patch", "season", "lançamento", "trailer", "atualização",
)
MAX_AGE_DAYS = 7


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def entry_ts(e):
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        t = e.get(key)
        if t:
            try:
                return float(calendar.timegm(t))
            except Exception:
                pass
    return None


def main():
    now = time.time()
    items = []
    for url in FEEDS:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:30]:
                title = clean(e.get("title", ""))
                summary = clean(e.get("summary", "") or e.get("description", ""))
                link = e.get("link", "")
                if not title or not link:
                    continue
                text = (title + " " + summary).lower()
                keyword_hits = sum(1 for k in KEYS if k in text)
                if not keyword_hits:
                    continue
                ts = entry_ts(e)
                age_hours = None if ts is None else max(0.0, (now - ts) / 3600.0)
                if age_hours is not None and age_hours > MAX_AGE_DAYS * 24:
                    continue
                recency = 0
                if age_hours is not None:
                    if age_hours <= 12: recency = 18
                    elif age_hours <= 24: recency = 14
                    elif age_hours <= 48: recency = 10
                    elif age_hours <= 72: recency = 7
                    else: recency = 3
                title_hits = sum(1 for k in KEYS if k in title.lower())
                score = keyword_hits * 4 + title_hits * 3 + recency
                cid = hashlib.sha256((title + "|" + link).encode()).hexdigest()[:16]
                items.append({
                    "content_id": cid,
                    "title": title,
                    "summary": summary[:900],
                    "url": link,
                    "source": url,
                    "published_at": datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else None,
                    "age_hours": round(age_hours, 1) if age_hours is not None else None,
                    "score": score,
                })
        except Exception as ex:
            print("feed warning", url, ex, file=sys.stderr)

    dedup = {}
    for item in items:
        key = (item["url"].split("#")[0], item["title"].lower())
        old = dedup.get(key)
        if old is None or item["score"] > old["score"]:
            dedup[key] = item
    items = sorted(
        dedup.values(),
        key=lambda x: (x["score"], -(x["age_hours"] if x["age_hours"] is not None else 9999)),
        reverse=True,
    )[:20]
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": {"max_age_days": MAX_AGE_DAYS, "ranking": "recency+official_feed_relevance"},
        "candidates": items,
    }
    Path("output").mkdir(exist_ok=True)
    Path("output/research.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
