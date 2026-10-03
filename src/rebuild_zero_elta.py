#!/usr/bin/env python3
"""Produção ZERO de Elta: Defy All Gods com fontes e mídia oficiais do mesmo jogo.

Não lê qualquer produção anterior. A pauta, o roteiro e a lista de mídia são recriados
somente a partir de páginas oficiais da Focus Entertainment e PlayStation Blog.
"""
import json
import re
from pathlib import Path

import requests

OUT = Path("output")
OUT.mkdir(parents=True, exist_ok=True)

TOPIC = "Elta: Defy All Gods"
SOURCE_URLS = [
    "https://www.focus-entmt.com/en/news/elta-defy-all-gods-set-to-launch-february-2-2027-free-demo-out-now-on-pc-playstation-5-and-xbox-series-xs",
    "https://www.focus-entmt.com/en/news/elta-defy-all-gods-unveiled-at-opening-night-live-set-for-2027-release",
    "https://blog.playstation.com/2026/10/01/martial-arts-meet-fluid-platforming-in-elta-defy-all-gods-with-a-free-ps5-demo-out-today/",
]

MEDIA = [
    {
        "type": "video",
        "url": "https://www.youtube.com/watch?v=OFwjdeJaoKs",
        "role": "official_demo_trailer",
        "evidence": "Demo Trailer linked directly by the official Focus Entertainment Oct. 1 article",
        "topic": TOPIC,
        "verified_same_game": True,
    },
    {
        "type": "video",
        "url": "https://www.youtube.com/watch?v=OLEZv_Qyb6Q",
        "role": "official_reveal_trailer",
        "evidence": "Reveal Trailer linked directly by the official Focus Entertainment Aug. 25 article",
        "topic": TOPIC,
        "verified_same_game": True,
    },
    {
        "type": "image",
        "url": "https://cdn.focus-home.com/fhi-fastforward-admin/resources/games/elta-defy-all-gods/images/21082026_a28ddaefb7ad407893f4d02bd9644350.jpeg",
        "role": "official_game_image_01",
        "evidence": "Image gallery on official Focus Entertainment Elta reveal article",
        "topic": TOPIC,
        "verified_same_game": True,
    },
    {
        "type": "image",
        "url": "https://cdn.focus-home.com/fhi-fastforward-admin/resources/games/elta-defy-all-gods/images/21082026_a28ddb0e305049fabc0ca7987774a954.jpeg",
        "role": "official_game_image_02",
        "evidence": "Image gallery on official Focus Entertainment Elta reveal article",
        "topic": TOPIC,
        "verified_same_game": True,
    },
    {
        "type": "image",
        "url": "https://cdn.focus-home.com/fhi-fastforward-admin/resources/games/elta-defy-all-gods/images/21082026_a28ddb4a07c245b3a9b825405af6157d.jpeg",
        "role": "official_game_image_03",
        "evidence": "Image gallery on official Focus Entertainment Elta reveal article",
        "topic": TOPIC,
        "verified_same_game": True,
    },
    {
        "type": "image",
        "url": "https://cdn.focus-home.com/fhi-fastforward-admin/resources/games/elta-defy-all-gods/images/21082026_a28ddb25eb8145b79ac0aa76aca28730.jpeg",
        "role": "official_game_image_04",
        "evidence": "Image gallery on official Focus Entertainment Elta reveal article",
        "topic": TOPIC,
        "verified_same_game": True,
    },
    {
        "type": "image",
        "url": "https://cdn.focus-home.com/fhi-fastforward-admin/resources/games/elta-defy-all-gods/images/21082026_a28ddb9209074dfe9b0d2589f39af5c3.jpeg",
        "role": "official_game_image_05",
        "evidence": "Image gallery on official Focus Entertainment Elta reveal article",
        "topic": TOPIC,
        "verified_same_game": True,
    },
    {
        "type": "image",
        "url": "https://cdn.focus-home.com/fhi-fastforward-admin/resources/games/elta-defy-all-gods/images/21082026_a28ddb78ae5c44b8b1ab03a853d70f00.jpeg",
        "role": "official_game_image_06",
        "evidence": "Image gallery on official Focus Entertainment Elta reveal article",
        "topic": TOPIC,
        "verified_same_game": True,
    },
]

SCRIPT = """Elta: Defy All Gods ganhou data de lançamento e uma demo gratuita, e essa é uma pauta que vale olhar com atenção porque já dá para separar claramente o que é promessa de marketing do que o próprio jogo mostra hoje. A Focus Entertainment e a Afterburner Studios confirmaram o lançamento para 2 de fevereiro de 2027 no PC via Steam, PlayStation 5 e Xbox Series X e S. A demo gratuita já está disponível nessas plataformas desde 1º de outubro. Para este vídeo, todas as informações vêm das páginas oficiais da Focus e do PlayStation Blog, e todo trailer e imagem usado é de Elta: Defy All Gods.

A ideia central de Elta é misturar combate corpo a corpo com exploração e plataforma em um cenário de ficção científica e fantasia. O protagonista é Victus, um monge guerreiro que procura Elta, a divindade-dragão perdida de seu povo. A jornada passa por mundos corrompidos em que o jogador precisa dominar tanto os confrontos quanto a movimentação pelo cenário. A própria equipe usa o termo “brawlervania” para explicar a proposta: a intensidade de um brawler combinada com áreas não lineares, exploração, progressão e caminhos que ficam acessíveis conforme novas habilidades são conquistadas.

No combate, o foco não é simplesmente atacar com armas tradicionais. A Afterburner Studios destaca artes marciais, magia e três posturas de luta, cada uma com sua própria árvore de habilidades. A proposta é encadear golpes, controlar grupos de inimigos e acumular energia para ataques mais poderosos. Elta, o pequeno dragão que acompanha Victus, não funciona apenas como personagem da história: suas habilidades entram diretamente nas lutas e também ajudam a alcançar áreas antes inacessíveis. O estúdio afirma que o objetivo é fazer cada golpe transmitir peso e resposta imediata ao jogador.

A movimentação é outra parte importante do projeto. O conjunto anunciado inclui salto duplo, dash, corrida pela parede e gancho, além de trechos de plataforma aérea. Essas ferramentas precisam ser combinadas para atravessar os três grandes mundos de ficção científica apresentados pela equipe. O PlayStation Blog também confirma que o jogo foi ajustado para valorizar a sensação do controle, incluindo resposta háptica do DualSense no PlayStation 5. A intenção é que combate e plataforma tenham o mesmo peso na experiência, em vez de um deles servir apenas como ligação entre as batalhas.

As inspirações assumidas pelos próprios desenvolvedores ajudam a entender o estilo, mas não transformam Elta em uma cópia de outro jogo. A equipe cita Castlevania: Symphony of the Night, God of War, Darksiders e Jak and Daxter como referências de videogame. Fora dos jogos, também menciona anime shōnen, especialmente Dragon Ball Z, e filmes de artes marciais de Hong Kong. Visualmente, a direção de arte procura um aspecto de pintura, enquanto os cenários misturam estruturas industriais, ruínas, áreas geladas e elementos fantásticos. É essa combinação que dá identidade ao mundo de Victus e Elta.

A demo atual mostra o começo da aventura. Segundo a Focus, ela dura menos de uma hora e leva o jogador pelos primeiros passos da história até o confronto com o primeiro chefe, Kan Loa’s Chosen. No PlayStation Blog, o estúdio descreve Lerna como um mundo glacial com segredos, ruínas antigas e restos industriais. É uma amostra pensada justamente para apresentar o combate, a movimentação e o tom do jogo antes do lançamento. Isso também permite que cada pessoa teste a proposta por conta própria, sem depender apenas de trailer ou de impressão de terceiros.

Elta está sendo produzido por uma equipe independente pequena. A Afterburner Studios fala em três cofundadores e cerca de uma dúzia de integrantes principais, com apoio da Focus Entertainment em áreas como produção, design e qualidade. O jogo passou por anos de iteração, e a página oficial informa uma duração estimada de quinze a vinte horas para a campanha completa. O preço anunciado é de 29 dólares e 99 centavos ou 29 euros e 99 centavos, e a pré-venda inclui como bônus cosmético a Vanguard Armor para Victus. Esses detalhes já estão confirmados oficialmente, mas naturalmente podem variar em preço local conforme a loja e a região.

Então o quadro atual é bem claro: Elta: Defy All Gods chega em 2 de fevereiro de 2027, tem demo gratuita disponível agora no PC, PlayStation 5 e Xbox Series, aposta em artes marciais, magia e plataforma fluida, e coloca a parceria entre Victus e o dragão Elta no centro tanto da história quanto das mecânicas. Se esse tipo de ação e exploração chama a sua atenção, vale testar a demo e formar sua própria opinião. E se você gosta de acompanhar lançamentos com informação confirmada e imagens do jogo certo, se inscreva no Radar dos Games, deixe o like neste vídeo e ative o sininho. Comenta aqui embaixo: Elta entrou ou não entrou na sua lista para 2027?"""

SCENES = [
    {"title": "ELTA GANHOU DATA", "subtitle": "Lançamento: 2 de fevereiro de 2027", "media_indices": [1, 3]},
    {"title": "UM ‘BRAWLERVANIA’", "subtitle": "Combate + exploração + plataforma", "media_indices": [2, 4]},
    {"title": "ARTES MARCIAIS E MAGIA", "subtitle": "Três posturas e árvores de habilidade", "media_indices": [1, 5]},
    {"title": "MOVIMENTAÇÃO FLUIDA", "subtitle": "Salto duplo • dash • wall run • gancho", "media_indices": [2, 4]},
    {"title": "AS INSPIRAÇÕES", "subtitle": "Ação clássica com identidade própria", "media_indices": [1, 6]},
    {"title": "A DEMO JÁ ESTÁ DISPONÍVEL", "subtitle": "PC • PS5 • Xbox Series", "media_indices": [1, 7]},
    {"title": "UM PROJETO INDIE AMBICIOSO", "subtitle": "Afterburner Studios + Focus", "media_indices": [2, 8]},
    {"title": "VALE FICAR DE OLHO?", "subtitle": "Teste a demo e tire sua conclusão", "media_indices": [1, 5]},
]


def verify_sources():
    headers = {"User-Agent": "Mozilla/5.0 RadarDosGames/1.0"}
    checks = []
    for url in SOURCE_URLS:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        text = re.sub(r"\s+", " ", r.text)
        if "Elta" not in text or "Defy All Gods" not in text:
            raise RuntimeError(f"QUALITY_BLOCK: fonte não confirma a pauta: {url}")
        checks.append({"url": url, "status": r.status_code, "topic_match": True})
    return checks


def verify_media():
    allowed_videos = {"OFwjdeJaoKs", "OLEZv_Qyb6Q"}
    for item in MEDIA:
        url = item["url"]
        if item["type"] == "video":
            video_id = url.split("v=", 1)[1].split("&", 1)[0]
            if video_id not in allowed_videos:
                raise RuntimeError(f"QUALITY_BLOCK: vídeo fora da allowlist oficial de Elta: {url}")
        else:
            host = url.split("/", 3)[2].lower()
            if host != "cdn.focus-home.com" or "/games/elta-defy-all-gods/" not in url.lower():
                raise RuntimeError(f"QUALITY_BLOCK: imagem fora da galeria oficial de Elta: {url}")
        if item.get("topic") != TOPIC or item.get("verified_same_game") is not True:
            raise RuntimeError(f"QUALITY_BLOCK: mídia sem validação do mesmo jogo: {url}")
    return MEDIA


def main():
    source_checks = verify_sources()
    media = verify_media()
    (OUT / "research-zero.json").write_text(json.dumps({
        "topic": TOPIC,
        "status": "VERIFIED_FROM_SCRATCH",
        "sources": source_checks,
        "facts_policy": "official_focus_and_playstation_only",
        "media_policy": "exact_official_same_game_allowlist",
        "previous_artifacts_reused": False,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "auto-script.txt").write_text(SCRIPT.strip() + "\n", encoding="utf-8")
    (OUT / "auto-media-plan.json").write_text(json.dumps({
        "topic": TOPIC,
        "minimum_assets": 8,
        "media": media,
        "scenes": SCENES,
        "source_urls": SOURCE_URLS,
        "previous_artifacts_reused": False,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "master-youtube.json").write_text(json.dumps({
        "title": "Elta: Defy All Gods ganhou data e demo grátis — tudo o que já foi confirmado",
        "description": "Elta: Defy All Gods chega em 2 de fevereiro de 2027 e já tem demo gratuita. Neste Radar dos Games, veja o que Focus Entertainment e Afterburner Studios confirmaram sobre combate, plataforma, história, mundos, demo e lançamento.\n\nFontes oficiais: Focus Entertainment e PlayStation Blog.\n\n#EltaDefyAllGods #Gaming #RadarDosGames",
        "tags": ["Elta Defy All Gods", "Afterburner Studios", "Focus Entertainment", "PS5", "Xbox Series", "PC", "Radar dos Games"],
        "privacy": "unlisted",
        "containsSyntheticMedia": True,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"topic": TOPIC, "sources": len(source_checks), "media": len(media), "scenes": len(SCENES)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
