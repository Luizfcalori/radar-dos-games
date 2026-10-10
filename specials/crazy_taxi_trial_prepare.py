#!/usr/bin/env python3
"""Local, one-off scene prompts for Crazy Taxi: World Tour.

Patches only the temporary GitHub Actions checkout, never committed production
vision_semantics.py. Actual shots remain inspected, timed and uniqueness-checked.
"""
from pathlib import Path

MODULE = Path("src/vision_semantics.py")
src = MODULE.read_text(encoding="utf-8")
i = src.index("CATEGORIES = {")
j = src.index("\n\ndef ascii_text", i)
replace = '''CATEGORIES = {
    "driving": "video game footage of a taxi or car driving fast on roads, arcade car racing",
    "settlement": "a vibrant city with streets storefronts buildings traffic and roads in a driving video game",
    "coast": "a colorful coastal city with beaches seaside streets and vehicles in a video game",
    "multiplayer": "multiple vehicles competing against each other in a racing driving video game",
    "interface": "video game menu and map navigation interface",
    "title_card": "a promotional game title card with large text and a logo",
    "arcade": "a colorful arcade racing game with a taxi swerving through busy city traffic",
}
SCENE_WORDS = {
    "driving": ("dirig", "direcao", "corr", "veloc", "conduc", "volante", "veiculo", "carro", "taxi", "cidade", "rua", "mapa", "destino", "campanha", "lanc", "jogador", "mundo", "brasil"),
    "settlement": ("cidade", "loja", "fachada", "bairro", "mapa", "brasil", "litoral", "paisagem", "costa", "rua", "avenida", "edificio", "urbana", "destino"),
    "coast": ("praia", "praias", "litoral", "mar", "costa"),
    "multiplayer": ("multijogador", "multiplayer", "online", "compet", "equipe", "ranquead", "batalha", "policia"),
    "arcade": ("arcade", "classico", "cronometro", "pontos", "passageiro", "taxi"),
    "interface": ("menu", "interface", "personaliza", "veiculos", "mapa"),
}
'''
MODULE.write_text(src[:i]+replace+src[j:],encoding="utf-8")
assert "crazy" in MODULE.read_text(encoding="utf-8").lower()
print("CRAZY_TAXI_LOCAL_VISUAL_PROMPTS_READY — repository production module unchanged")
