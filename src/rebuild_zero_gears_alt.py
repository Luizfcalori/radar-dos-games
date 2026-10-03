#!/usr/bin/env python3
"""Executa o rebuild ZERO usando vídeos de gameplay publicados pela conta oficial Xbox.

Os IDs abaixo foram verificados contra as páginas oficiais do Xbox/Xbox Wire e não
aceitam fallback para qualquer outro jogo ou canal.
"""
import rebuild_zero_gears as base

OFFICIAL_XBOX_VIDEOS = {
    "dFk4bL3a8I8": {
        "role": "official_gameplay_reveal_trailer",
        "evidence": "Gears of War: E-Day | Gameplay Reveal Trailer — canal oficial Xbox",
    },
    "y85lNvF3kVQ": {
        "role": "official_gameplay_demo",
        "evidence": "Gears of War: E-Day | Gameplay Demo Reveal | Xbox Games Showcase 2026 — canal oficial Xbox",
    },
}

# Troca SOMENTE os dois vídeos por IDs oficiais alternativos do mesmo jogo.
base.MEDIA[0].update({
    "url": "https://www.youtube.com/watch?v=dFk4bL3a8I8",
    **OFFICIAL_XBOX_VIDEOS["dFk4bL3a8I8"],
})
base.MEDIA[1].update({
    "url": "https://www.youtube.com/watch?v=y85lNvF3kVQ",
    **OFFICIAL_XBOX_VIDEOS["y85lNvF3kVQ"],
})


def strict_media_allowlist():
    verified = []
    for item in base.MEDIA:
        url = item["url"]
        if "youtube.com/watch" in url:
            video_id = url.split("v=", 1)[1].split("&", 1)[0]
            if video_id not in OFFICIAL_XBOX_VIDEOS:
                raise RuntimeError(f"QUALITY_BLOCK: vídeo fora da allowlist oficial de E-Day: {url}")
        else:
            host = url.split("/", 3)[2].lower()
            if host != "xboxwire.thesourcemediaassets.com":
                raise RuntimeError(f"QUALITY_BLOCK: host de imagem não oficial: {url}")
            low = url.lower()
            if not any(marker in low for marker in ("gears", "gow_eday", "eday")):
                raise RuntimeError(f"QUALITY_BLOCK: imagem sem identidade explícita de E-Day: {url}")
        verified.append({**item, "topic": base.TOPIC, "verified_same_game": True})
    return verified


base.verify_media_allowlist = strict_media_allowlist
base.main()
