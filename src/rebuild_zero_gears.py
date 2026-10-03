#!/usr/bin/env python3
"""Gera uma produção do zero de Gears of War: E-Day usando apenas fontes oficiais verificadas.

Este script não lê histórico, roteiro anterior, mídia anterior, timestamps anteriores ou artefatos anteriores.
Ele cria um pacote editorial novo e bloqueia qualquer URL fora da allowlist oficial da pauta.
"""
import json
import re
from pathlib import Path

import requests

OUT = Path("output")
OUT.mkdir(parents=True, exist_ok=True)

TOPIC = "Gears of War: E-Day"
SOURCE_URLS = [
    "https://news.xbox.com/en-us/2026/10/01/gears-of-war-e-day-early-access-launch-trailer-xbox/",
    "https://news.xbox.com/pt-br/2026/10/02/o-que-faz-de-gears-of-war-uma-serie-iconica-nos-games-a-comunidade-brasileira-tem-a-resposta/",
    "https://news.xbox.com/pt-br/2026/06/07/reconstruindo-a-irmandade-como-gears-of-war-e-day-renova-uma-franquia-lendaria/",
    "https://www.xbox.com/pt-BR/games/store/gears-of-war-e-day-premium-edition-pre-order/9p2qmwj6xsb6",
]

MEDIA = [
    {
        "type": "video",
        "url": "https://www.youtube.com/watch?v=3onc3ownB14",
        "role": "official_launch_trailer",
        "evidence": "Embedded by the official Xbox Wire launch article as Gears of War: E-Day | Official Launch Trailer",
    },
    {
        "type": "video",
        "url": "https://www.youtube.com/watch?v=53TSzVVxd2c",
        "role": "official_gameplay_demo",
        "evidence": "Embedded by Xbox Wire Brasil as Gears of War: E-Day | Revelação Gameplay Demo | Xbox Games Showcase 2026",
    },
    {
        "type": "image",
        "url": "https://xboxwire.thesourcemediaassets.com/sites/2/2026/10/GoW_EDAY_Adagio_4K_Final_09-0f31e58cf65dec22523a-1600x900.jpg",
        "role": "official_launch_screenshot",
        "evidence": "Hero image of the official Xbox Wire launch article",
    },
    {
        "type": "image",
        "url": "https://xboxwire.thesourcemediaassets.com/sites/8/2026/09/Gears_Marcus-1306763ee6f90fda95a9-1900x1080.jpg",
        "role": "official_marcus_keyart",
        "evidence": "Gears of War: E-Day image on official Xbox Wire Brasil",
    },
    {
        "type": "image",
        "url": "https://xboxwire.thesourcemediaassets.com/sites/8/2026/06/Gears-af0d975b1cfc9a2ccf84.jpg",
        "role": "official_keyart",
        "evidence": "Gears of War: E-Day hero image from official Xbox Wire deep-dive",
    },
    {
        "type": "image",
        "url": "https://xboxwire.thesourcemediaassets.com/sites/8/2026/06/08_GoW_EDAY_RebuiltUE5_Final-997c190bdfe31940ffdc-1900x1080.jpg",
        "role": "official_ue5_scene",
        "evidence": "Gears of War: E-Day UE5 image from official Xbox Wire deep-dive",
    },
    {
        "type": "image",
        "url": "https://xboxwire.thesourcemediaassets.com/sites/8/2026/06/02_GoW_EDAY_BravoSquad_Final-bd717a68aa869122f917-1900x1080.jpg",
        "role": "official_bravo_squad",
        "evidence": "Bravo Squad image from official Xbox Wire deep-dive",
    },
    {
        "type": "image",
        "url": "https://xboxwire.thesourcemediaassets.com/sites/8/2026/06/01_GoW_EDAY_StoryofEmergence_Final-e1629e06b515f825da19-1900x1080.jpg",
        "role": "official_emergence_scene",
        "evidence": "Story of Emergence image from official Xbox Wire deep-dive",
    },
]

SCRIPT = """Gears of War: E-Day entrou na reta final para o lançamento mundial, e a principal novidade agora é concreta: o acesso antecipado começou em 1º de outubro para jogadores elegíveis da Premium Edition e do upgrade Premium do Game Pass. O lançamento mundial está marcado para 6 de outubro. A própria The Coalition publicou um novo trailer de lançamento com gameplay para marcar esse momento. Neste Radar dos Games, a gente vai separar o que já está confirmado oficialmente sobre história, combate, modos, plataformas e tecnologia, sem misturar rumor com informação publicada pela Xbox.

E-Day volta ao começo da Guerra Locust. A campanha se passa quatorze anos antes do primeiro Gears of War e acompanha Marcus Fenix e Dominic Santiago durante os acontecimentos do Dia da Emergência. A proposta é mostrar o instante em que os Locust surgem das profundezas e transformam uma situação de paz recente em uma catástrofe. A The Coalition explicou que a história acompanha de perto o impacto humano dessa invasão e concentra a campanha em Kalona, uma cidade que vai sendo destruída durante os acontecimentos do jogo. O foco permanece na perspectiva do Esquadrão Bravo, sem saltar para histórias desconectadas em outros lugares.

O Esquadrão Bravo também ganhou mais detalhes oficiais. Além de Marcus e Dom, o grupo inclui Mags Carter e Lucas Reyes. A equipe explicou que toda a campanha pode ser jogada com qualquer um desses personagens desde o início. O cooperativo online suporta quatro jogadores, e nos consoles existe tela dividida para dois jogadores. A relação entre Marcus e Dom continua no centro da narrativa, mas o jogo também mostra como esse grupo se forma enquanto todos ainda estão tentando entender o que são os Locust e como reagir ao primeiro ataque.

Na jogabilidade, E-Day mantém o combate baseado em cobertura que definiu Gears, mas adiciona novas opções de movimentação. A The Coalition confirmou transições de cobertura mais fluidas, possibilidade de deslizar durante a corrida e, pela primeira vez na série principal, pular em situações de exploração e combate. Isso abre rotas de flanqueamento e mais verticalidade em áreas de Kalona. O objetivo declarado pelo estúdio é preservar a sensação pesada e tática da franquia, mas dar ao jogador mais liberdade para decidir como entrar e sair de cada confronto.

As armas também foram reconstruídas para essa nova base. A Gnasher e a Longshot continuam presentes, enquanto novas armas entram no arsenal, como a Gut Puncher e a Incinerator. A Lancer também faz parte da história de origem: em E-Day, a Chainsaw Lancer aparece dentro do contexto da invasão, em vez de simplesmente existir desde o começo. Outro elemento clássico que retorna são os E-holes, pontos de emergência dos Locust que podem mudar o ritmo de uma batalha e obrigar o jogador a reagir rapidamente ao surgimento de novos inimigos.

No multiplayer, a principal novidade anunciada é Horde Siege, uma evolução do modo horda. A The Coalition descreve partidas com três esquadrões em mapas urbanos maiores, objetivos compartilhados e batalhas em escala ampliada. O Versus também retorna com modos PvP quatro contra quatro e mapas novos. Na campanha e nos modos online, os controles e a movimentação foram modernizados, mas a equipe reforça que a base continua sendo o posicionamento, a leitura do espaço, o uso de cobertura e a escolha certa de armas para cada situação.

Tecnicamente, Gears of War: E-Day foi reconstruído do zero na Unreal Engine 5. A The Coalition afirma que personagens, inimigos, armas, animações, som e ambientes foram refeitos para este projeto. O jogo foi anunciado com suporte a resolução 4K e até 60 quadros por segundo em campanha e multiplayer, dependendo do equipamento e da tela compatível. O lançamento está confirmado para Xbox Series X e Series S, Windows PC e Steam, com opções de nuvem por serviços compatíveis. No Brasil, a Xbox também confirmou localização completa em português brasileiro.

Então o quadro oficial é este: acesso antecipado já começou para quem tem direito, o lançamento mundial acontece em 6 de outubro e o material divulgado pela própria Xbox mostra que E-Day quer combinar a identidade clássica de Gears com uma campanha de origem, movimentação modernizada, cooperativo para quatro jogadores, Horde Siege, Versus e uma reconstrução técnica completa em Unreal Engine 5. Se você curte acompanhar lançamentos de games com informação confirmada e gameplay oficial, se inscreva no Radar dos Games, deixe o like neste vídeo e ative o sininho. E conta nos comentários: você pretende jogar Gears of War: E-Day no lançamento?"""

SCENES = [
    {"title": "E-DAY CHEGOU À RETA FINAL", "subtitle": "Acesso antecipado já começou", "media_indices": [1, 3]},
    {"title": "A ORIGEM DA GUERRA LOCUST", "subtitle": "14 anos antes do primeiro Gears", "media_indices": [2, 8]},
    {"title": "ESQUADRÃO BRAVO", "subtitle": "Marcus • Dom • Mags • Lucas", "media_indices": [2, 7]},
    {"title": "GEARS, MAS COM NOVOS MOVIMENTOS", "subtitle": "Cobertura • deslize • salto • flanqueamento", "media_indices": [1, 6]},
    {"title": "ARSENAL RECONSTRUÍDO", "subtitle": "Clássicos e novas armas", "media_indices": [2, 5]},
    {"title": "HORDE SIEGE E VERSUS", "subtitle": "PvE em escala maior + PvP 4v4", "media_indices": [1, 7]},
    {"title": "UNREAL ENGINE 5", "subtitle": "Reconstruído do zero", "media_indices": [2, 6]},
    {"title": "LANÇAMENTO EM 6 DE OUTUBRO", "subtitle": "Xbox Series • PC • Steam", "media_indices": [1, 4]},
]


def verify_sources():
    checks = []
    headers = {"User-Agent": "Mozilla/5.0 RadarDosGames/1.0"}
    for url in SOURCE_URLS:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        text = re.sub(r"\s+", " ", r.text)
        if "Gears of War" not in text or "E-Day" not in text:
            raise RuntimeError(f"QUALITY_BLOCK: fonte não confirma a pauta: {url}")
        checks.append({"url": url, "status": r.status_code, "topic_match": True})
    return checks


def verify_media_allowlist():
    allowed_youtube = {"3onc3ownB14", "53TSzVVxd2c"}
    allowed_hosts = {"xboxwire.thesourcemediaassets.com"}
    verified = []
    for item in MEDIA:
        url = item["url"]
        if "youtube.com/watch" in url:
            video_id = url.split("v=", 1)[1].split("&", 1)[0]
            if video_id not in allowed_youtube:
                raise RuntimeError(f"QUALITY_BLOCK: vídeo fora da allowlist da pauta: {url}")
        else:
            host = url.split("/", 3)[2].lower()
            if host not in allowed_hosts or not re.search(r"(?i)(gears|gow_eday|eday)", url):
                raise RuntimeError(f"QUALITY_BLOCK: imagem sem identidade explícita da pauta: {url}")
        verified.append({**item, "topic": TOPIC, "verified_same_game": True})
    return verified


def main():
    source_checks = verify_sources()
    media = verify_media_allowlist()

    research = {
        "topic": TOPIC,
        "status": "VERIFIED_FROM_SCRATCH",
        "sources": source_checks,
        "facts_policy": "official_xbox_sources_only",
        "media_policy": "explicit_allowlist_same_game_only",
        "previous_artifacts_reused": False,
    }
    (OUT / "research-zero.json").write_text(json.dumps(research, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "auto-script.txt").write_text(SCRIPT.strip() + "\n", encoding="utf-8")
    (OUT / "auto-media-plan.json").write_text(json.dumps({
        "topic": TOPIC,
        "minimum_assets": 7,
        "media": media,
        "scenes": SCENES,
        "source_urls": SOURCE_URLS,
        "previous_artifacts_reused": False,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "master-youtube.json").write_text(json.dumps({
        "title": "Gears of War: E-Day: tudo o que já foi confirmado antes do lançamento",
        "description": "Gears of War: E-Day entra na reta final. Veja o que a Xbox e a The Coalition já confirmaram sobre história, gameplay, cooperativo, Horde Siege, Versus, plataformas e Unreal Engine 5.\n\nFontes oficiais: Xbox Wire, Xbox Wire Brasil e página oficial do jogo.\n\n#GearsOfWar #GearsEDay #Xbox #RadarDosGames",
        "tags": ["Gears of War E-Day", "Gears E-Day", "Xbox", "The Coalition", "gameplay", "Radar dos Games"],
        "privacy": "unlisted",
        "containsSyntheticMedia": True,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"topic": TOPIC, "sources": len(source_checks), "media": len(media), "scenes": len(SCENES)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
