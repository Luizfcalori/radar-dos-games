#!/usr/bin/env python3
"""Executa o rebuild ZERO usando vídeos oficiais incorporados no Xbox Wire.

Os IDs são os embeds das próprias páginas oficiais do Xbox Wire sobre E-Day.
Não existe fallback para outro jogo, outro canal ou mídia genérica.
"""
import rebuild_zero_gears as base

OFFICIAL_XBOX_VIDEOS = {
    "cmawSe1PkPg": {
        "role": "official_multiplayer_reveal_deep_dive",
        "evidence": "Embed oficial da página Xbox Wire 'Gears of War: E-Day - Get an In-Depth Look at Multiplayer with New Trailer and Deep Dive'",
    },
    "m8kSqrvBKoE": {
        "role": "official_gameplay_reveal_deep_dive",
        "evidence": "Embed oficial da página Xbox Wire 'Gears of War: E-Day Gameplay Reveal Deep Dive | Official Xbox Podcast'",
    },
}

base.MEDIA[0].update({
    "url": "https://www.youtube.com/watch?v=cmawSe1PkPg",
    **OFFICIAL_XBOX_VIDEOS["cmawSe1PkPg"],
})
base.MEDIA[1].update({
    "url": "https://www.youtube.com/watch?v=m8kSqrvBKoE",
    **OFFICIAL_XBOX_VIDEOS["m8kSqrvBKoE"],
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
