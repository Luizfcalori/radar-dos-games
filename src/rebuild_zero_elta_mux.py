#!/usr/bin/env python3
"""Rebuild ZERO de Elta usando os MP4s incorporados na matéria oficial do PlayStation Blog.

Os dois vídeos são extraídos em tempo real somente da matéria oficial de Elta. O script
não aceita vídeo de página relacionada, outro jogo, YouTube genérico ou fallback externo.
"""
import html
import re

import requests

import rebuild_zero_elta as base

PLAYSTATION_ARTICLE = "https://blog.playstation.com/2026/10/01/martial-arts-meet-fluid-platforming-in-elta-defy-all-gods-with-a-free-ps5-demo-out-today/"


def exact_article_videos():
    r = requests.get(PLAYSTATION_ARTICLE, headers={"User-Agent": "Mozilla/5.0 RadarDosGames/1.0"}, timeout=30)
    r.raise_for_status()
    raw = html.unescape(r.text).replace("\\/", "/")
    if "Elta: Defy All Gods" not in raw or "Afterburner Studios" not in raw:
        raise RuntimeError("QUALITY_BLOCK: a página oficial do PlayStation não confirmou Elta")

    # Somente <figure class="wp-block-video"> do corpo editorial da matéria.
    figures = re.findall(r'<figure class="wp-block-video[^>]*>.*?</figure>', raw, flags=re.I | re.S)
    urls = []
    for figure in figures:
        match = re.search(r'data-src="(https://stream\.mux\.com/[^\"]+?capped-1080p\.mp4\?[^\"]+)"', figure, flags=re.I)
        if match:
            url = html.unescape(match.group(1))
            if url not in urls:
                urls.append(url)

    if len(urls) != 2:
        raise RuntimeError(f"QUALITY_BLOCK: esperados 2 vídeos editoriais de Elta no PlayStation Blog; encontrados {len(urls)}")

    return [
        {
            "type": "video",
            "url": urls[0],
            "role": "official_playstation_elta_gameplay_01",
            "evidence": "MP4 embedded inside the official PlayStation Blog Elta article, immediately after the action-platformer gameplay section",
            "topic": base.TOPIC,
            "verified_same_game": True,
        },
        {
            "type": "video",
            "url": urls[1],
            "role": "official_playstation_elta_gameplay_02",
            "evidence": "MP4 embedded inside the official PlayStation Blog Elta article, inside the development/game-feel section",
            "topic": base.TOPIC,
            "verified_same_game": True,
        },
    ]


videos = exact_article_videos()
base.MEDIA[0] = videos[0]
base.MEDIA[1] = videos[1]


def verify_media_strict():
    for idx, item in enumerate(base.MEDIA):
        url = item["url"]
        if idx < 2:
            if not url.startswith("https://stream.mux.com/") or "capped-1080p.mp4" not in url:
                raise RuntimeError(f"QUALITY_BLOCK: vídeo não veio do player oficial de Elta: {url}")
            if not item["role"].startswith("official_playstation_elta_"):
                raise RuntimeError("QUALITY_BLOCK: papel do vídeo não corresponde à pauta")
        else:
            host = url.split("/", 3)[2].lower()
            if host != "cdn.focus-home.com" or "/games/elta-defy-all-gods/" not in url.lower():
                raise RuntimeError(f"QUALITY_BLOCK: imagem fora da galeria oficial de Elta: {url}")
        if item.get("topic") != base.TOPIC or item.get("verified_same_game") is not True:
            raise RuntimeError(f"QUALITY_BLOCK: mídia sem validação do mesmo jogo: {url}")
    return base.MEDIA


base.verify_media = verify_media_strict
base.main()
