#!/usr/bin/env python3
"""Monta automaticamente a pauta diária do Radar dos Games a partir da pesquisa RSS.

Regras editoriais principais:
- evitar repetição da mesma franquia/tema em sequência;
- priorizar pautas com gameplay/vídeo oficial + imagens oficiais;
- usar somente vídeo ou somente imagens como fallback;
- gerar títulos, descrições e hashtags em português-BR e contextualizados.
"""
import html
import json
import os
import re
import unicodedata
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

STOP = {
    "para","com","uma","como","que","por","dos","das","de","do","da","em","no","na","nos","nas","e","o","a","os","as","um","uns","umas","se","ao","aos","à","às","mais","novo","nova","novos","novas",
    "game","games","jogo","jogos","the","and","for","with","from","this","that","your","you","are","was","will","has","have","into","its","our","out","new","official","today","news","update","release","available","now","get","all","can","on","in","of","to",
    "trailer","gameplay","launch","announced","announcement","watch","early","access","season","patch","demo","beta","dlc"
}

PLATFORM_PATTERNS = [
    (r"\bPlayStation\s*5\b|\bPS5\b", "PlayStation 5"),
    (r"\bPlayStation\s*4\b|\bPS4\b", "PlayStation 4"),
    (r"\bXbox Series X\|S\b|\bXbox Series\b", "Xbox Series X|S"),
    (r"\bXbox One\b", "Xbox One"),
    (r"\bNintendo Switch 2\b", "Nintendo Switch 2"),
    (r"\bNintendo Switch\b", "Nintendo Switch"),
    (r"\bSteam\b", "Steam"),
    (r"\bPC\b", "PC"),
]

GENERIC_TOPIC_WORDS = STOP | {
    "edition","details","revealed","reveals","coming","arrives","arriving","available","launches","launching",
    "first","look","latest","shows","showcases","introducing","returns","return","event","october","september"
}


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def sentence(text):
    return re.sub(r"\s+", " ", text or "").strip(" .")


def ascii_slug(text):
    norm = unicodedata.normalize("NFKD", text)
    norm = "".join(ch for ch in norm if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", norm.lower()).strip()


class PageParser(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.meta = {}
        self.media = []
        self.paragraphs = []
        self._in_p = False
        self._p = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "meta":
            key = (d.get("property") or d.get("name") or "").lower()
            val = d.get("content")
            if key and val:
                self.meta[key] = val
                if key in ("og:image", "twitter:image"):
                    self.media.append(("image", urljoin(self.base, val)))
                if key in ("og:video", "og:video:url", "twitter:player:stream"):
                    self.media.append(("video", urljoin(self.base, val)))
        elif tag in ("img", "source"):
            for key in ("src", "data-src", "data-original", "srcset"):
                val = d.get(key)
                if val:
                    for part in val.split(","):
                        u = part.strip().split(" ")[0]
                        if u:
                            typ = "video" if re.search(r"\.(mp4|webm|mov)(\?|$)", u, re.I) else "image"
                            self.media.append((typ, urljoin(self.base, u)))
        elif tag in ("iframe", "embed", "video"):
            for key in ("src", "data-src"):
                val = d.get(key)
                if val:
                    u = urljoin(self.base, val)
                    typ = "video" if ("youtube.com" in u or "youtu.be" in u or re.search(r"\.(mp4|webm|mov)(\?|$)", u, re.I)) else "image"
                    self.media.append((typ, u))
        elif tag == "p":
            self._in_p = True
            self._p = []

    def handle_data(self, data):
        if self._in_p:
            self._p.append(data)

    def handle_endtag(self, tag):
        if tag == "p" and self._in_p:
            txt = clean(" ".join(self._p))
            if len(txt) >= 45:
                self.paragraphs.append(txt)
            self._in_p = False
            self._p = []


def fetch_page(url):
    r = requests.get(
        url,
        headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"},
        timeout=25,
    )
    r.raise_for_status()
    p = PageParser(url)
    p.feed(r.text)
    return p


def media_quality(kind, url):
    u = url.lower()
    if not url.startswith("http") or any(x in u for x in ("logo", "icon", "avatar", "sprite", "favicon", "badge", "tracking", "pixel")):
        return False
    if kind == "video":
        return True
    return any(x in u for x in (".jpg", ".jpeg", ".png", ".webp", "image", "media", "cdn", "assets", "akamai", "cloudfront"))


def canonical_media(items):
    seen = set()
    videos = []
    images = []
    for kind, url in items:
        url = url.replace("&amp;", "&")
        key = re.sub(r"[?#].*$", "", url)
        if key in seen or not media_quality(kind, url):
            continue
        seen.add(key)
        (videos if kind == "video" else images).append((kind, url))

    # O plano já sai mesclado: gameplay/vídeo, foto, gameplay/vídeo, foto...
    mixed = []
    while videos or images:
        if videos:
            mixed.append(videos.pop(0))
        if images:
            mixed.append(images.pop(0))
        if len(mixed) >= 16:
            break
    return mixed[:16]


def media_mix(media):
    videos = sum(1 for kind, _ in media if kind == "video")
    images = sum(1 for kind, _ in media if kind == "image")
    if videos and images:
        quality = "video+images"
        bonus = 45
    elif videos:
        quality = "video-only"
        bonus = 25
    else:
        quality = "images-only"
        bonus = 10
    return {"videos": videos, "images": images, "quality": quality, "bonus": bonus}


def load_history():
    p = DATA / "published.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"videos": []}
    except Exception:
        return {"videos": []}


def source_name(url):
    h = urlparse(url).netloc.lower()
    if "xbox" in h or "microsoft" in h:
        return "Xbox"
    if "playstation" in h or "sony" in h:
        return "PlayStation"
    if "nintendo" in h:
        return "Nintendo"
    if "steam" in h or "valve" in h:
        return "Steam"
    return h.replace("www.", "").split(".")[0].title() or "fonte oficial"


def keywords(text, limit=7):
    words = re.findall(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9'’\-]{2,}", clean(text))
    c = Counter()
    original = {}
    for w in words:
        k = w.lower()
        if k in STOP or k.isdigit() or len(k) < 4:
            continue
        c[k] += 1
        original.setdefault(k, w)
    return [original[k] for k, _ in c.most_common(limit)]


def platforms(text):
    found = []
    for pat, name in PLATFORM_PATTERNS:
        if re.search(pat, text, re.I) and name not in found:
            found.append(name)
    return found


def dates_and_numbers(text):
    pats = [
        r"\b\d{1,2}\s+de\s+[A-Za-zÀ-ÿ]+\s+de\s+\d{4}\b",
        r"\b[A-Z][a-z]+\s+\d{1,2},\s+\d{4}\b",
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        r"\b20\d{2}\b",
    ]
    found = []
    for pat in pats:
        for x in re.findall(pat, text):
            if x not in found:
                found.append(x)
    return found[:5]


def game_name(title):
    title = sentence(title)
    # Mantém subtítulos como "Gears of War: E-Day" e corta a parte de notícia.
    cuts = [
        r"\s+is\s+available\b", r"\s+available\s+now\b", r"\s+launches\b", r"\s+launching\b",
        r"\s+gets\b", r"\s+receives\b", r"\s+reveals\b", r"\s+revealed\b", r"\s+announces\b",
        r"\s+watch\b", r"\s+shows\b", r"\s+showcases\b", r"\s+release\s+date\b",
    ]
    for pat in cuts:
        m = re.search(pat, title, re.I)
        if m and m.start() >= 3:
            return title[:m.start()].strip(" :-|")[:70]
    return re.split(r"\s+[|–—]\s+", title, maxsplit=1)[0][:70].strip()


def topic_tokens(title):
    name = game_name(title)
    toks = [x for x in ascii_slug(name).split() if len(x) >= 3 and x not in GENERIC_TOPIC_WORDS]
    return set(toks)


def topic_key(title):
    toks = list(topic_tokens(title))
    if not toks:
        return ascii_slug(game_name(title))[:60]
    # Ordem original para diagnóstico legível.
    ordered = [x for x in ascii_slug(game_name(title)).split() if x in set(toks)]
    return " ".join(ordered[:6])


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def repetition_check(candidate, history, now):
    c_title = candidate.get("title", "")
    c_key = topic_key(c_title)
    c_tokens = topic_tokens(c_title)
    penalty = 0
    reasons = []
    blocked = False

    for old in history.get("videos", []):
        if not isinstance(old, dict):
            continue
        old_title = old.get("title", "")
        old_key = old.get("topic_key") or topic_key(old_title)
        old_tokens = topic_tokens(old_title)
        dt = parse_dt(old.get("published_at"))
        if dt is None:
            continue
        age_h = max(0.0, (now - dt).total_seconds() / 3600.0)
        sim = jaccard(c_tokens, old_tokens)

        # Mesma franquia/jogo: 48h sem repetir. Isso evita "terceiro Gears no mesmo dia".
        if c_key and old_key and c_key == old_key and age_h <= 48:
            blocked = True
            reasons.append(f"mesmo tema em cooldown 48h: {old_key}")
            break

        # Mesmo dia + grande sobreposição temática: bloqueio duro.
        if age_h <= 24 and sim >= 0.50:
            blocked = True
            reasons.append(f"tema muito parecido nas ultimas 24h: similaridade={sim:.2f}")
            break

        # Na semana, assuntos parecidos continuam possíveis, mas perdem prioridade.
        if age_h <= 7 * 24 and sim >= 0.30:
            penalty += int(35 * sim)
            reasons.append(f"penalidade por repeticao semanal: similaridade={sim:.2f}")

    return {"blocked": blocked, "penalty": penalty, "reasons": reasons, "topic_key": c_key}


def pt_headline(candidate, parser):
    original = sentence(candidate.get("title", ""))
    game = game_name(original) or "Game em destaque"
    low = original.lower()
    corpus = " ".join([candidate.get("summary", "")] + parser.paragraphs[:8]).lower()

    if "early access" in low or "early access" in corpus:
        headline = f"{game}: acesso antecipado começou e novo gameplay foi divulgado"
    elif "release date" in low or "launch date" in low:
        headline = f"{game}: data de lançamento foi confirmada"
    elif "gameplay" in low and "trailer" in low:
        headline = f"{game}: novo trailer mostra gameplay e detalhes"
    elif "gameplay" in low:
        headline = f"{game}: novo gameplay revela mais detalhes"
    elif "trailer" in low:
        headline = f"{game}: novo trailer revela novidades"
    elif "update" in low or "patch" in low:
        headline = f"{game}: nova atualização traz mudanças importantes"
    elif "dlc" in low or "expansion" in low:
        headline = f"{game}: novo conteúdo foi anunciado"
    elif "beta" in low or "demo" in low:
        headline = f"{game}: teste jogável ganha novos detalhes"
    elif "launch" in low or "available" in low or "release" in low:
        headline = f"{game}: lançamento ganha novos detalhes"
    else:
        headline = f"{game}: veja o que foi confirmado oficialmente"
    return headline[:96].rstrip(" -:|")


def contextual_terms(candidate, parser):
    corpus = " ".join([candidate.get("title", ""), candidate.get("summary", "")] + parser.paragraphs[:16])
    kws = keywords(corpus, 10)
    plats = platforms(corpus)
    return kws, plats


def make_script(candidate, parser):
    title = pt_headline(candidate, parser)
    src = source_name(candidate["url"])
    game = game_name(candidate.get("title", "")) or "o jogo"
    corpus = " ".join([candidate.get("summary", "")] + parser.paragraphs[:20])
    kws = keywords(candidate.get("title", "") + " " + corpus, 8)
    plats = platforms(corpus + " " + candidate.get("title", ""))
    dates = dates_and_numbers(corpus + " " + candidate.get("title", ""))
    focus = ", ".join(kws[:4]) if kws else "as principais novidades anunciadas"
    extra = ", ".join(kws[4:7]) if len(kws) > 4 else "novos detalhes do projeto"
    plat_txt = ", ".join(plats) if plats else "as plataformas confirmadas pela empresa"
    date_txt = ", ".join(dates[:3]) if dates else "a janela divulgada pela empresa"

    blocks = [
        f"{title}. A {src} confirmou a novidade, e {game} ganhou novos detalhes que já chamam a atenção de quem acompanha o jogo.",
        f"Entre os principais destaques estão {focus}. O anúncio mexe diretamente com a experiência de {game} e ajuda a entender o que muda daqui para frente.",
        f"{extra} também aparecem entre as informações divulgadas. Juntos, esses detalhes deixam o anúncio mais completo e dão uma ideia melhor do que os jogadores podem esperar.",
        f"Em relação à disponibilidade, {game} aparece ligado a {plat_txt}. Esse ponto é importante porque versão, plataforma e lançamento podem mudar bastante a experiência de cada público.",
        f"A referência de lançamento ou atualização é {date_txt}. Até aqui, essa é a janela oficial divulgada para a novidade.",
        f"Na prática, o que mais chama atenção é como {focus} pode mudar a experiência de quem já joga ou de quem estava esperando um bom motivo para conhecer {game}.",
        f"O material oficial também traz elementos de gameplay, trailers ou imagens de {game}, reforçando os principais pontos anunciados e deixando mais claro o tamanho da novidade.",
        f"E agora fica a pergunta para vocês: qual parte dessa novidade de {game} mais chamou a atenção? Conta nos comentários e acompanhem o Radar dos Games para as próximas notícias.",
    ]
    return "\n\n".join(blocks)

def make_scenes(candidate, media, script):
    paras = [x.strip() for x in script.split("\n\n") if x.strip()]
    titles = [
        "NO TOPO DO RADAR", "O QUE FOI CONFIRMADO", "POR QUE ISSO IMPORTA", "PLATAFORMAS E DISPONIBILIDADE",
        "DATAS E JANELAS", "IMPACTO PARA QUEM JOGA", "GAMEPLAY + IMAGENS", "RESUMO DO RADAR"
    ]
    subs = [
        pt_headline(candidate, type("P", (), {"paragraphs": []})())[:70],
        "FATOS DA FONTE OFICIAL", "CONTEXTO SEM ESPECULAÇÃO", "ONDE A NOTÍCIA SE APLICA",
        "O ESTADO ATUAL DO ANÚNCIO", "O QUE PODE MUDAR NA EXPERIÊNCIA", "MÍDIA OFICIAL SEM REPETIÇÃO", "RADAR DOS GAMES"
    ]
    n = max(1, len(media))
    scenes = []
    for i, _ in enumerate(paras):
        a = (i % n) + 1
        b = ((i + 1) % n) + 1
        scenes.append({
            "paragraph": i + 1,
            "title": titles[i] if i < len(titles) else f"DESTAQUE {i+1}",
            "subtitle": subs[i] if i < len(subs) else "RADAR DOS GAMES",
            "media_indices": [a] if a == b else [a, b],
        })
    return scenes


def hashtag(text):
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", text or "")
    if not words:
        return None
    value = "".join(w[:1].upper() + w[1:] for w in words)
    value = re.sub(r"[^A-Za-z0-9À-ÿ]", "", value)
    return "#" + value[:32] if value else None


def build_metadata(candidate, parser, privacy):
    headline = pt_headline(candidate, parser)
    game = game_name(candidate.get("title", ""))
    src = source_name(candidate["url"])
    kws, plats = contextual_terms(candidate, parser)
    focus = ", ".join(kws[:3]) if kws else "as principais novidades confirmadas"
    plat_txt = ", ".join(plats[:3]) if plats else "as plataformas citadas oficialmente"

    hashtags = ["#RadarDosGames"]
    for item in [game] + plats[:2] + kws[:2]:
        h = hashtag(item)
        if h and h.lower() not in {x.lower() for x in hashtags}:
            hashtags.append(h)
    hashtags = hashtags[:6]

    desc = (
        f"🎮 {headline}.\n\n"
        f"Neste vídeo, reunimos o que foi confirmado pela {src}, com foco em {focus} e em como a novidade se aplica a {plat_txt}. "
        "A ideia é mostrar o contexto sem transformar rumor em fato e, sempre que possível, combinar gameplay/trailer com imagens oficiais.\n\n"
        f"🔎 Fonte oficial: {candidate['url']}\n\n"
        "📡 Acompanhe o Radar dos Games para notícias, lançamentos, gameplays e atualizações sem repetição de pauta.\n\n"
        + " ".join(hashtags)
    )

    tags = ["Radar dos Games", game, src] + plats + kws[:5]
    tags = [x for i, x in enumerate(tags) if x and x.casefold() not in {y.casefold() for y in tags[:i]}][:12]

    master = {
        "title": headline,
        "description": desc,
        "tags": tags,
        "privacy": privacy,
        "containsSyntheticMedia": False,
        "thumbnail": "output/thumbnail.jpg",
    }

    hooks = ["O QUE FOI CONFIRMADO", "POR QUE ISSO IMPORTA", "O QUE VEM AGORA"]
    shorts = []
    for i, hook in enumerate(hooks, 1):
        st = f"{game}: {hook.lower()}"
        if len(st) > 88:
            st = st[:88].rstrip(" -:|")
        short_desc = (
            f"{headline}. Recorte {i}/3 do Radar dos Games.\n\n"
            f"Fonte oficial: {candidate['url']}\n\n"
            + " ".join(hashtags + ["#Shorts"])
        )
        shorts.append({
            "title": st + " #Shorts",
            "description": short_desc,
            "tags": tags + ["Shorts"],
            "privacy": privacy,
            "containsSyntheticMedia": False,
            "thumbnail": f"output/shorts/short_{i}_cover.jpg",
        })
    return master, shorts


def candidate_score(candidate, index, media, repeat):
    # Ranking original ainda conta, mas qualidade visual e diversidade pesam mais.
    base = float(candidate.get("score") or 0)
    freshness_bonus = max(0, 20 - index)
    mix = media_mix(media)
    total = base + freshness_bonus + mix["bonus"] - repeat["penalty"]
    return total, mix


def main():
    research_path = OUT / "research.json"
    if not research_path.exists():
        raise RuntimeError("output/research.json ausente")
    candidates = json.loads(research_path.read_text(encoding="utf-8")).get("candidates", [])
    if not candidates:
        raise RuntimeError("Nenhuma pauta recente encontrada nas fontes oficiais")

    history = load_history()
    used = {x.get("content_id") for x in history.get("videos", []) if isinstance(x, dict)}
    forced = os.getenv("RADAR_TOPIC", "AUTO").strip()
    now = datetime.now(timezone.utc)
    evaluated = []
    errors = []

    for index, c in enumerate(candidates):
        if c.get("content_id") in used:
            errors.append({"title": c.get("title"), "error": "content_id já publicado"})
            continue
        if forced.upper() != "AUTO" and forced.lower() not in c.get("title", "").lower():
            continue

        repeat = repetition_check(c, history, now)
        if repeat["blocked"] and forced.upper() == "AUTO":
            errors.append({"title": c.get("title"), "error": "; ".join(repeat["reasons"])})
            continue

        try:
            p = fetch_page(c["url"])
            media = canonical_media(p.media)
            if len(media) < 2:
                errors.append({"title": c.get("title"), "error": f"somente {len(media)} mídias descobertas"})
                continue
            score, mix = candidate_score(c, index, media, repeat)
            evaluated.append({
                "candidate": c,
                "parser": p,
                "media": media,
                "selection_score": round(score, 2),
                "mix": mix,
                "repeat": repeat,
            })
        except Exception as exc:
            errors.append({"title": c.get("title"), "error": str(exc)[:200]})

    if not evaluated:
        raise RuntimeError("Nenhuma pauta nova com mídia oficial suficiente e diversidade aceitável. " + json.dumps(errors[:8], ensure_ascii=False))

    evaluated.sort(
        key=lambda x: (
            x["mix"]["quality"] == "video+images",
            x["mix"]["videos"] > 0,
            x["selection_score"],
        ),
        reverse=True,
    )
    winner = evaluated[0]
    selected = winner["candidate"]
    parser = winner["parser"]
    selected_media = winner["media"]

    script = make_script(selected, parser)
    (OUT / "auto-script.txt").write_text(script + "\n", encoding="utf-8")

    media_items = []
    for i, (typ, url) in enumerate(selected_media, 1):
        item = {
            "type": typ,
            "url": url,
            "role": f"official_context_{i:02d}",
            "max_assets": 1,
            "source_proof": selected["url"],
            "relevance_evidence": "official_source_page_discovered_asset",
        }
        if typ == "video":
            # Clipes oficiais curtos (5s+) ainda são úteis no V3: o render usa
            # cortes de 3-6s e nunca precisa esticar um único trecho como cena inteira.
            item["min_duration"] = 5
        media_items.append(item)

    plan = {
        "topic": pt_headline(selected, parser),
        "source": selected["url"],
        "minimum_assets": 2,
        "minimum_video_assets": 0,
        "minimum_unique_video_seconds": 0,
        "minimum_image_assets": 0,
        "media_policy": "prefer_video_plus_images; accept_official_video_5s_plus; graceful_single_type_fallback; premium_v3_motion_for_images",
        "media": media_items,
        "scenes": make_scenes(selected, selected_media, script),
    }
    (OUT / "auto-media-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    privacy = os.getenv("PUBLISH_PRIVACY", "unlisted").strip() or "unlisted"
    master_meta, shorts_meta = build_metadata(selected, parser, privacy)
    (OUT / "master-youtube.json").write_text(json.dumps(master_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    for i, meta in enumerate(shorts_meta, 1):
        (OUT / f"short-{i}-youtube.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    payload = {
        "selected_at": now.isoformat(),
        **selected,
        "editorial_title_ptbr": master_meta["title"],
        "topic_key": winner["repeat"]["topic_key"],
        "selection_score": winner["selection_score"],
        "media_mix": winner["mix"],
        "selection_policy": {
            "franchise_cooldown_hours": 48,
            "same_day_similarity_block": 0.50,
            "weekly_similarity_penalty_from": 0.30,
            "prefer_video_plus_images": True,
        },
        "discovered_media": len(selected_media),
        "script_paragraphs": len([x for x in script.split("\n\n") if x.strip()]),
        "alternatives_considered": [
            {
                "title": x["candidate"].get("title"),
                "score": x["selection_score"],
                "media_mix": x["mix"],
                "topic_key": x["repeat"]["topic_key"],
            }
            for x in evaluated[:5]
        ],
        "rejected": errors[:12],
    }
    (OUT / "selected.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
