# Castlevania retry: use the explicit production trigger so the manual brief is honored.
# QSSR PS5 brief is explicitly mapped above and uses approved official gameplay URLs.
# [run-production] TOPIC=Deadlock — validate embedded video extraction in the locked-topic pipeline.
#!/usr/bin/env python3
"""Monta automaticamente a pauta diária do Radar dos Games a partir da pesquisa RSS.

Regras editoriais principais:
- evitar repetição da mesma franquia/tema em sequência;
- exigir gameplay/vídeo oficial em movimento como parte obrigatória do Master;
- imagens oficiais podem complementar, mas nunca substituir totalmente o gameplay/vídeo;
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

try:
    from media import steam_candidates, discover_social_posts, social_profile_url, social_post_url, youtube_video_id
except ImportError:
    from src.media import steam_candidates, discover_social_posts, social_profile_url, social_post_url, youtube_video_id

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
                    image_url = urljoin(self.base, val)
                    self.media.append(("image", image_url))
                    # Publisher metadata often points at the official trailer's
                    # YouTube thumbnail even when no iframe is present in HTML.
                    thumb = re.search(
                        r"(?:i\.|img\.)?ytimg\.com/vi/([A-Za-z0-9_-]{6,})/",
                        image_url, re.I
                    )
                    if thumb:
                        self.media.append(("video", "https://www.youtube.com/watch?v=" + thumb.group(1)))
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
                            resolved = urljoin(self.base, u)
                            self.media.append((typ, resolved))
                            # Some official publisher articles expose the trailer only
                            # through its YouTube thumbnail (i.ytimg.com/vi/<id>/...),
                            # not an iframe. Register the matching full video as well;
                            # media.py will download it through the existing fallback.
                            thumb = re.search(
                                r"(?:i\.|img\.)?ytimg\.com/vi/([A-Za-z0-9_-]{6,})/",
                                resolved, re.I
                            )
                            if thumb:
                                self.media.append(("video", "https://www.youtube.com/watch?v=" + thumb.group(1)))
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

    # Muitos portais montam players dentro de JSON/script e não em tags iframe.
    # O HTMLParser ignora esse conteúdo; extrair referências de vídeo do HTML bruto
    # evita que uma página com gameplay real seja classificada como "só imagens".
    raw = (r.text or "").replace("\\\\/", "/").replace("\\/", "/").replace("&amp;", "&")
    embedded = []
    video_patterns = (
        r"https?://(?:www\.)?youtube\.com/(?:watch\?[^\s\"'<>]*?v=|embed/|shorts/)([A-Za-z0-9_-]{11})",
        r"https?://(?:www\.)?youtube-nocookie\.com/embed/([A-Za-z0-9_-]{11})",
        r"https?://youtu\.be/([A-Za-z0-9_-]{11})",
    )
    for pattern in video_patterns:
        for match in re.finditer(pattern, raw, re.I):
            video_id = match.group(1)
            embedded.append(("video", "https://www.youtube.com/watch?v=" + video_id))
    for match in re.finditer(r"https?:[^\s\"'<>\\]+?\.(?:mp4|webm|mov)(?:\?[^\s\"'<>\\]*)?", raw, re.I):
        media_url = match.group(0).rstrip("),;]")
        embedded.append(("video", media_url))
    known = {u for _, u in p.media}
    for item in embedded:
        if item[1] not in known:
            p.media.append(item)
            known.add(item[1])
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
        # Identidade canônica cobre watch, embed, youtu.be, shorts e live.
        # Sem isso, um trailer encontrado em formatos diferentes parece ser
        # duas fontes e infla artificialmente a variedade disponível.
        video_id = youtube_video_id(url) if kind == "video" else ""
        if video_id:
            key = "youtube:" + video_id
        else:
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



def classify_topic(title, summary=""):
    """Allow game-specific news and meaningful platform updates; reject unrelated/general filler."""
    text = clean(f"{title} {summary}").casefold()
    slug = ascii_slug(text)
    platform_terms = (
        "xbox", "playstation", "ps5", "ps4", "nintendo switch", "steam deck",
        "firmware", "console update", "system update", "atualizacao do sistema",
        "atualizacao do xbox", "atualizacao do ps5", "atualizacao do ps4",
        "game pass", "ps plus", "playstation plus", "backward compatibility",
        "retrocompatibilidade", "compatibilidade"
    )
    platform_update_terms = (
        "update", "updated", "updating", "firmware", "patch", "atualizacao",
        "atualiza", "novidade", "recurso", "feature", "support", "suporte",
        "compatibilidade", "correcao", "correcoes", "desempenho", "performance",
        "game pass", "ps plus", "playstation plus", "catalog", "catalogo"
    )
    if any(term in slug for term in ("microsoft rewards", "id xbox", "ign showcase recap", "top news roundup", "gaming news roundup")):
        # Generic brand/service headlines are only eligible when they explicitly describe a
        # concrete gaming-platform change, not a broad recap or rewards/promotional topic.
        if not (any(p in slug for p in ("xbox", "playstation", "ps5", "ps4")) and
                any(t in slug for t in ("atualizacao", "update", "firmware", "recurso", "compatibilidade"))):
            return {"allowed": False, "category": "assunto-geral", "reason": "pauta genérica/serviço sem mudança gamer concreta"}

    has_platform = any(term in slug for term in platform_terms)
    has_platform_change = any(term in slug for term in platform_update_terms)
    if has_platform and has_platform_change:
        return {"allowed": True, "category": "atualizacao-plataforma", "reason": "mudança concreta em plataforma/serviço gamer"}

    game_signals = (
        "gameplay", "trailer", "dlc", "expansion", "patch", "update", "launch",
        "launches", "release date", "early access", "demo", "beta", "new characters",
        "characters revealed", "gameplay reveal", "announced", "announces", "reveals",
        "revealed", "new map", "season", "quest", "boss", "campaign", "jogo",
        "jogavel", "lancamento", "personagens", "mapa", "expansao", "atualizacao"
    )
    has_game_signal = any(term in slug for term in game_signals)
    blocked_broad = any(term in slug for term in (
        "showcase recap", "all new", "industry roundup", "gaming roundup",
        "microsoft rewards", "rewards points", "weekly gaming news", "gaming industry"
    ))
    if has_game_signal and not blocked_broad:
        return {"allowed": True, "category": "jogo-ou-noticia-de-jogo", "reason": "pauta com sinal concreto de jogo"}
    # A named game can appear without obvious keywords, but AUTO must not guess from a
    # generic headline. Require an explicit game/topic signal or a platform change.
    return {"allowed": False, "category": "sem-contexto", "reason": "não foi possível confirmar jogo específico ou mudança concreta de plataforma"}


def validate_script_context(candidate, script):
    """Block scripts that mislabel the topic or pad narration by repeating generic claims."""
    verdict = classify_topic(candidate.get("title", ""), candidate.get("summary", ""))
    if not verdict["allowed"]:
        raise RuntimeError(
            f"EDITORIAL_TOPIC_BLOCK: pauta rejeitada ({verdict['category']}): "
            f"{candidate.get('title', '')!r}; {verdict['reason']}"
        )
    paragraphs = [sentence(p) for p in re.split(r"\n\s*\n", script or "") if sentence(p)]
    if len(paragraphs) < 4:
        raise RuntimeError("EDITORIAL_SCRIPT_BLOCK: roteiro sem desenvolvimento suficiente")
    normalized = [ascii_slug(p) for p in paragraphs]
    for i, left in enumerate(normalized):
        for j in range(i + 1, len(normalized)):
            right = normalized[j]
            if not left or not right:
                continue
            a, b = set(left.split()), set(right.split())
            overlap = jaccard(a, b)
            if overlap >= 0.72:
                raise RuntimeError(
                    f"EDITORIAL_REPETITION_BLOCK: parágrafos {i+1} e {j+1} repetem a mesma ideia (similaridade {overlap:.2f})"
                )
    return verdict

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
    """Build a source-grounded PT-BR outline; never turn extracted keywords into prose."""
    title = pt_headline(candidate, parser)
    src = source_name(candidate["url"])
    game = game_name(candidate.get("title", "")) or "o jogo"
    raw_title = sentence(candidate.get("title", ""))
    corpus = clean(" ".join([candidate.get("summary", "")] + parser.paragraphs[:20]))
    full = raw_title + " " + corpus
    plats = platforms(full)
    month_names = {
        "january":"janeiro", "february":"fevereiro", "march":"março",
        "april":"abril", "may":"maio", "june":"junho", "july":"julho",
        "august":"agosto", "september":"setembro", "october":"outubro",
        "november":"novembro", "december":"dezembro",
    }
    launch_date = None
    date_match = re.search(
        r"\b(?:launches|launching|launch(?:e)? on|release(?:s)? on)\s+"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2})(?:,\s*(20\d{2}))?\b",
        full, re.I
    )
    if date_match:
        launch_date = f"{int(date_match.group(2))} de {month_names[date_match.group(1).lower()]}"
        if date_match.group(3):
            launch_date += f" de {date_match.group(3)}"
    lower = full.casefold()
    has_characters = any(x in lower for x in ("new characters", "characters revealed", "personagens novos", "novos personagens"))
    has_update = any(x in lower for x in ("update", "patch", "atualização", "atualizacao"))
    has_trailer = any(x in lower for x in ("trailer", "gameplay", "latest trailer"))
    platform_text = ", ".join(plats) if plats else ""
    blocks = [
        f"{title}. A {src} publicou a informação em sua fonte oficial, e o assunto é {game}.",
        (f"O material informa que o lançamento de {game} está previsto para {launch_date}. Essa é a data indicada na publicação consultada, e não uma estimativa acrescentada pelo Radar."
         if launch_date else
         f"O ponto de partida é o anúncio publicado sobre {game}. Para entender a novidade, vale separar o que a fonte apresenta como informação concreta das perguntas que ainda dependem de novos comunicados."),
        (f"O anúncio também revela novos personagens para {game}. Esse é um dos pontos destacados pela própria publicação."
         if has_characters else
         (f"A notícia trata de uma atualização de {game}, conforme o material oficial. O foco editorial é explicar o que a atualização pretende acrescentar, sem transformar objetivos anunciados em recursos que não foram confirmados."
          if has_update else
          f"A publicação acrescenta contexto sobre {game}. O texto disponível é a base para esta análise; por isso, qualquer detalhe que não esteja descrito ali permanece fora das afirmações do Radar.")),
        (f"Sobre plataformas de {game}, o material cita {platform_text}. A confirmação deve ficar restrita às plataformas mencionadas oficialmente."
         if platform_text else
         f"A disponibilidade por plataforma é uma informação importante para quem acompanha {game}, mas só deve ser afirmada quando estiver explícita no anúncio oficial. Não vamos presumir versões, datas ou serviços que a fonte não confirme."),
        (f"O artigo também apresenta material visual associado à notícia sobre {game}{', incluindo trailer ou gameplay' if has_trailer else ''}. Essas imagens ajudam a contextualizar o anúncio, mas não comprovam detalhes que o texto não confirma."
         if parser.media else
         f"A publicação consultada é a referência principal para conferir os detalhes anunciados sobre {game}. O material visual, quando disponível, deve servir para contextualizar a notícia, e não para inventar funções ou acontecimentos que não estejam demonstrados."),
        f"Para avaliar o alcance desta novidade em {game}, a pergunta central é o que muda de forma concreta para quem joga. A resposta precisa vir dos recursos, modos, condições ou objetivos descritos pela fonte, sem transformar possibilidades em promessas.",
        f"Também é importante observar o contexto do anúncio de {game}. Uma atualização pode ter objetivos diferentes de uma expansão ou de um lançamento completo; o Radar deve manter essa distinção e usar a nomenclatura adotada no comunicado oficial.",
        f"Se a publicação descreve objetivos para a atualização de {game}, esses objetivos devem ser apresentados como intenção declarada pelos responsáveis. Isso é diferente de garantir um resultado para todos os jogadores, algo que só pode ser avaliado com informações e experiência concretas.",
        f"Outro cuidado é não confundir material promocional com uma lista completa de mudanças. Os vídeos e imagens associados a {game} ajudam a visualizar a novidade, mas os detalhes não mostrados continuam dependendo do texto oficial ou de futuras informações dos desenvolvedores.",
        f"Para quem acompanha {game}, vale conferir os próximos comunicados e observar se surgem notas detalhadas, demonstrações adicionais ou esclarecimentos sobre disponibilidade. Esses pontos só devem entrar numa atualização do Radar quando houver uma fonte identificável que os sustente.",
        f"Em resumo, a notícia sobre {game} deve ser entendida pelo que foi efetivamente publicado: o anúncio, os objetivos declarados e os detalhes confirmados. Essa separação evita misturar informação, expectativa da comunidade e especulação como se fossem a mesma coisa.",
        f"Até que a fonte oficial divulgue outros dados sobre {game}, recursos, modos ou datas não mencionados aqui devem continuar tratados como não confirmados.",
        f"E agora queremos saber: qual parte deste anúncio sobre {game} mais chamou sua atenção? Comente, acompanhe o Radar dos Games e inscreva-se para receber as próximas notícias."
    ]
    return "\n\n".join(blocks)

def scene_headline(paragraph, candidate, index):
    """Cria headline curta e semântica para a barra; nunca usa 'DESTAQUE X'."""
    raw = sentence(paragraph)
    low = ascii_slug(raw)
    rules = [
        (("data" in low and ("lancamento" in low or "estreia" in low)) or "19 de novembro" in low, "DATA DE LANÇAMENTO"),
        (("playstation" in low and "xbox" in low) and ("plataforma" in low or "pc" in low), "PLATAFORMAS CONFIRMADAS"),
        ("jason" in low and "lucia" in low and ("historia" in low or "campanha" in low), "JASON E LUCIA"),
        ("jason" in low and "lucia" not in low, "QUEM É JASON"),
        ("lucia" in low and "jason" not in low, "QUEM É LUCIA"),
        (("mapa" in low or "vice city" in low) and "leonida" in low, "LEONIDA ALÉM DE VICE CITY"),
        (("imagens de jogo" in low or "gameplay" in low or "capturado inteiramente" in low), "GAMEPLAY E IMAGENS DE JOGO"),
        ("pre carga" in low or "pre-carga" in low, "PRÉ-CARGA E LANÇAMENTO"),
        (("standard" in low and "ultimate" in low) or "edicao" in low, "EDIÇÕES E BÔNUS"),
        (("musica" in low or "faixas" in low or "trilha" in low), "TRILHA SONORA"),
        (("xbox cloud" in low or "cloud gaming" in low) and ("reportagem" in low or "confusao" in low or "exclusividade" in low), "XBOX CLOUD: FATO OU RUMOR"),
        ("streaming" in low and "pc" in low, "STREAMING NÃO É VERSÃO DE PC"),
        (("novos materiais oficiais" in low or "merecem atencao" in low), "O QUE AINDA PODE MUDAR"),
        (("comenta" in low or "queremos saber" in low or "pergunta" in low), "SUA VEZ NO RADAR"),
    ]
    for ok, title in rules:
        if ok:
            return title

    kws = keywords(raw, 6)
    if kws:
        title = " ".join(kws[:5]).upper()
        if title and not re.fullmatch(r"DESTAQUE\s*\d*", title, re.I):
            return title[:48].rstrip(" -:|")

    first = re.split(r"[.!?]", raw, maxsplit=1)[0]
    first = re.sub(r"^(agora|também|por isso|na prática|outro detalhe|entre os principais)\s+", "", first, flags=re.I)
    words = first.split()
    title = " ".join(words[:7]).upper()[:48].rstrip(" -:|")
    return title or f"{game_name(candidate.get('title','')).upper()[:42]} EM FOCO"


def scene_subtitle(paragraph, candidate):
    game = (game_name(candidate.get("title", "")) or "RADAR DOS GAMES").upper()
    low = ascii_slug(paragraph)
    if "rockstar" in low:
        return "INFORMAÇÃO OFICIAL DA ROCKSTAR"
    if "rumor" in low or "reportagem" in low:
        return "FATO, CONTEXTO E RUMOR SEPARADOS"
    return f"{game[:48]} • RADAR DOS GAMES"


def make_scenes(candidate, media, script):
    paras = [x.strip() for x in script.split("\n\n") if x.strip()]
    n = max(1, len(media))
    scenes = []
    for i, paragraph in enumerate(paras):
        a = (i % n) + 1
        b = ((i + 1) % n) + 1
        title = scene_headline(paragraph, candidate, i + 1)
        if re.fullmatch(r"DESTAQUE\s*\d*", title, re.I):
            raise RuntimeError(f"QUALITY_BLOCK: headline genérica proibida na cena {i+1}: {title}")
        scenes.append({
            "paragraph": i + 1,
            "title": title,
            "subtitle": scene_subtitle(paragraph, candidate),
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

    # Hashtags do Master: até 15 termos relevantes, específicos e deduplicados.
    # Keep these values scoped to build_metadata; manual descriptions build their own tags.
    # Shorts continuam com um conjunto mais curto e contextualizado.
    def tag_key(value):
        return unicodedata.normalize("NFKD", value.lstrip("#")).encode("ascii", "ignore").decode().lower()

    topic_tags = []
    for item in [game] + kws[:10] + plats[:5]:
        h = hashtag(item)
        if not h or len(h) < 4:
            continue
        if tag_key(h) in {tag_key(x) for x in topic_tags}:
            continue
        if tag_key(h) in {"game", "games", "gaming", "video", "news", "official"}:
            continue
        topic_tags.append(h)
    master_hashtags = topic_tags[:15]
    hashtags = topic_tags[:5]

    desc = (
        f"🎮 {headline}.\n\n"
        f"Neste vídeo, reunimos o que foi confirmado pela {src}, com foco em {focus} e em como a novidade se aplica a {plat_txt}. "
        "A ideia é mostrar o contexto sem transformar rumor em fato e, sempre que possível, combinar gameplay/trailer com imagens oficiais.\n\n"
        f"🔎 Fonte oficial: {candidate['url']}\n\n"
        "📡 Acompanhe o Radar dos Games para notícias, lançamentos, gameplays e atualizações sem repetição de pauta.\n\n"
        + " ".join(master_hashtags)
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
            + " ".join(hashtags)
        )
        shorts.append({
            "title": st,
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



def load_manual_brief(path=None):
    p = Path(path) if path else Path("production/manual-brief.json")
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    valid_until = parse_dt(data.get("valid_until"))
    if valid_until and datetime.now(timezone.utc) > valid_until:
        return None
    blocks = [sentence(x) for x in data.get("script_blocks", []) if sentence(x)]
    sources = [x for x in data.get("media_source_urls", []) if isinstance(x, str) and x.startswith("http")]
    if not blocks or not sources:
        return None
    data["script_blocks"] = blocks
    data["media_source_urls"] = sources
    return data


def fetch_manual_media(brief):
    """Use only the approved trailer and official posts that match the topic.

    Do not crawl news-page HTML for media: pages can embed unrelated ads/videos.
    """
    primary = brief.get("primary_source") or brief["media_source_urls"][0]
    combined = PageParser(primary)
    combined.media = []
    combined.paragraphs = []
    errors = []
    curated = []

    # Explicit video URLs are trusted only as the supplied trailer, direct media,
    # or topic-matched posts discovered on official profiles.
    # A pauta manual pode trazer uma lista principal e uma lista de reserva.
    # Inclua todas as URLs aprovadas, sem depender de uma por posição nem perder
    # trailers oficiais extras quando o primeiro host bloqueia downloads.
    approved_video_urls=[]
    for raw in list(brief.get("video_urls", []) or []) + list(brief.get("video_fallback_urls", []) or []):
        if isinstance(raw,str) and raw.startswith("https://") and raw not in approved_video_urls:
            approved_video_urls.append(raw)
    for raw in approved_video_urls:
        if not isinstance(raw, str) or not raw.startswith("https://"):
            continue
        url = raw.strip()
        if social_profile_url(url):
            try:
                for post_url, evidence, title in discover_social_posts(url):
                    curated.append(("video", post_url))
                    print("manual brief accepted topic-matched official post", evidence, title[:120], flush=True)
            except Exception as exc:
                errors.append({"url": url, "error": str(exc)[:180]})
            continue
        low = url.lower().split("?")[0]
        if (
            "youtube.com/watch" in low
            or "youtu.be/" in low
            or social_post_url(url)
            or low.endswith((".mp4", ".mov", ".webm", ".m4v", ".m3u8", ".mpd"))
        ):
            curated.append(("video", url))

    # Recover direct media from the exact official source pages named in the brief.
    # YouTube embeds are not treated as downloadable media here: GitHub runners can
    # be rate-limited by YouTube, so prefer direct PlayStation-hosted video assets.
    # Official publisher domains are allowed for this exact game brief; never crawl generic news/ad pages.
    trusted_hosts = (".playstation.com", ".playstation.net", ".sony.com", ".sony.net", ".ea.com", ".eaassets-a.akamaihd.net")
    for source_url in list(brief.get("media_source_urls", []) or []):
        if not isinstance(source_url, str) or not source_url.startswith("https://"):
            continue
        host = urlparse(source_url).netloc.lower()
        if not any(host == suffix.lstrip(".") or host.endswith(suffix) for suffix in trusted_hosts):
            continue
        try:
            page = fetch_page(source_url)
            for kind, asset_url in page.media:
                asset_host = urlparse(asset_url).netloc.lower()
                if kind == "video":
                    direct_video = bool(re.search(r"\\.(?:mp4|webm|mov|m4v|m3u8|mpd)(?:$|\\?)", asset_url, re.I))
                    trusted_video_host = any(
                        asset_host == suffix.lstrip(".") or asset_host.endswith(suffix)
                        for suffix in trusted_hosts
                    )
                    if direct_video and trusted_video_host:
                        curated.append(("video", asset_url))
                elif kind == "image":
                    curated.append(("image", asset_url))
        except Exception as exc:
            errors.append({"url": source_url, "error": str(exc)[:180]})
    media = canonical_media(curated)
    # A single explicitly approved trailer is valid source footage. Topic-specific
    # stills are added later as separate media items; never pad with page ads.
    if not media or not any(kind == "video" for kind, _ in media):
        raise RuntimeError(
            "QUALITY_BLOCK: trailer oficial explicitamente aprovado indisponível; "
            "não será usada mídia genérica nem publicidade de páginas."
            + json.dumps(errors, ensure_ascii=False)
        )
    return combined, media, errors

def main():
    research_path = OUT / "research.json"
    if not research_path.exists():
        raise RuntimeError("output/research.json ausente")
    candidates = json.loads(research_path.read_text(encoding="utf-8")).get("candidates", [])
    forced_topic_slug = ascii_slug(os.getenv("RADAR_TOPIC", "AUTO").strip())
    manual = load_manual_brief()
    # Pautas especiais independentes mantêm briefs próprios para não sobrescrever
    # o brief genérico nem herdar o tema de uma produção anterior.
    if forced_topic_slug == ascii_slug("Saros Zenith"):
        manual = load_manual_brief("production/manual-brief-saros-zenith-2026-10-21.json")
    elif forced_topic_slug == ascii_slug("Free Fire"):
        manual = load_manual_brief("production/manual-brief-free-fire-2026-10-13.json")
    elif forced_topic_slug == ascii_slug("Microsoft Rewards"):
        manual = load_manual_brief("production/manual-brief-microsoft-rewards-2026-10-19.json")
    elif forced_topic_slug == ascii_slug("The Witcher 3: Wild Hunt"):
        manual = load_manual_brief("production/manual-brief-witcher-3-remastered-2026-10-19.json")
    elif forced_topic_slug == ascii_slug("QSSR PS5"):
        manual = load_manual_brief("production/manual-brief-qssr-ps5-2026-10-19.json")
    elif forced_topic_slug == ascii_slug("Fight Night"):
        manual = load_manual_brief("production/manual-brief-fight-night-return-2026-10-21.json")
    elif forced_topic_slug == ascii_slug("The Blood of Dawnwalker"):
        manual = load_manual_brief("production/manual-brief-the-blood-of-dawnwalker-2026-10-23.json")
    elif forced_topic_slug == ascii_slug("The Wolf Among Us Remastered"):
        manual = load_manual_brief("production/manual-brief-the-wolf-among-us-remastered-2026-10-24.json")
    elif forced_topic_slug == ascii_slug("Zenless Zone Zero"):
        manual = load_manual_brief("production/manual-brief-zenless-zone-zero-2026-10-25.json")
    # Execuções explícitas run-only/run-private podem ignorar o brief genérico
    # vigente de outro jogo e carregar somente o brief correspondente ao tema.
    if os.getenv("RADAR_IGNORE_MANUAL_BRIEF", "").strip().lower() in {"1", "true", "yes"}:
        if forced_topic_slug == ascii_slug("Saros Zenith"):
            manual = load_manual_brief("production/manual-brief-saros-zenith-2026-10-21.json")
        elif forced_topic_slug == ascii_slug("League of Legends"):
            manual = load_manual_brief("production/manual-brief-league-of-legends-2026-10-14.json")
        elif forced_topic_slug == ascii_slug("Phantom Blade Zero"):
            manual = load_manual_brief("production/manual-brief-phantom-blade-zero.json")
        elif forced_topic_slug == ascii_slug("Roblox"):
            manual = load_manual_brief("production/manual-brief-roblox-2026-10-13.json")
        elif forced_topic_slug == ascii_slug("Free Fire"):
            manual = load_manual_brief("production/manual-brief-free-fire-2026-10-13.json")
        elif forced_topic_slug == ascii_slug("Fortnite"):
            manual = load_manual_brief("production/manual-brief-fortnite-yeat-2026-10-14.json")
        elif forced_topic_slug == ascii_slug("ARC Raiders"):
            manual = load_manual_brief("production/manual-brief-arc-raiders-pve-toggle-2026-10-15.json")
        elif forced_topic_slug == ascii_slug("Castlevania"):
            manual = load_manual_brief("production/manual-brief-castlevania-2026-10-15.json")
        elif forced_topic_slug == ascii_slug("Call of Duty: Modern Warfare 4"):
            manual = load_manual_brief("production/manual-brief-call-of-duty-modern-warfare-4-2026-10-16.json")
        elif forced_topic_slug == ascii_slug("Enshrouded"):
            manual = load_manual_brief("production/manual-brief-enshrouded-2026-10-17.json")
        elif forced_topic_slug == ascii_slug("The Witcher 3: Wild Hunt"):
            manual = load_manual_brief("production/manual-brief-witcher-3-remastered-2026-10-19.json")
        elif forced_topic_slug == ascii_slug("QSSR PS5"):
            manual = load_manual_brief("production/manual-brief-qssr-ps5-2026-10-19.json")
        elif forced_topic_slug == ascii_slug("Mycopunk"):
            # Prefer accessible official trailers; age-gated URLs must not be the only source.
            manual = load_manual_brief("production/manual-brief-mycopunk-1-0-2026-10-20.json")
        elif forced_topic_slug == ascii_slug("Once Human — Isles of Abyss"):
            # Use the refreshed brief with two distinct, publisher-approved Isles of Abyss trailers.
            manual = load_manual_brief("production/manual-brief-once-human-isles-of-abyss-2026-10-20.json")
        elif forced_topic_slug == ascii_slug("Fight Night"):
            manual = load_manual_brief("production/manual-brief-fight-night-return-2026-10-21.json")
        elif forced_topic_slug == ascii_slug("Final Fantasy Resonance"):
            # Keep the requested game pinned for private, manually triggered productions.
            manual = load_manual_brief("production/manual-brief-final-fantasy-resonance-2026-10-22.json")
        elif forced_topic_slug == ascii_slug("Mega Man: Dual Override"):
            # Lock this explicit production to the official Capcom/Nintendo brief.
            manual = load_manual_brief("production/manual-brief-mega-man-dual-override-2026-10-22.json")
        elif forced_topic_slug == ascii_slug("The Blood of Dawnwalker"):
            # Lock this production to the latest official Update 1.1 brief and curated game-specific footage.
            manual = load_manual_brief("production/manual-brief-the-blood-of-dawnwalker-2026-10-23.json")
        elif forced_topic_slug == ascii_slug("The Wolf Among Us Remastered"):
            manual = load_manual_brief("production/manual-brief-the-wolf-among-us-remastered-2026-10-24.json")
        elif forced_topic_slug == ascii_slug("Zenless Zone Zero"):
            manual = load_manual_brief("production/manual-brief-zenless-zone-zero-2026-10-25.json")
        else:
            manual = None
    if not candidates and not manual:
        raise RuntimeError("Nenhuma pauta recente encontrada nas fontes oficiais")

    history = load_history()
    used = {x.get("content_id") for x in history.get("videos", []) if isinstance(x, dict)}
    forced = os.getenv("RADAR_TOPIC", "AUTO").strip()
    now = datetime.now(timezone.utc)
    evaluated = []
    errors = []

    if manual:
        if forced.upper() != "AUTO":
            requested = ascii_slug(forced)
            manual_identity = ascii_slug(" ".join([str(manual.get("title", "")), str(manual.get("headline", ""))]))
            if requested not in manual_identity:
                brief_title = manual.get("title") or "sem título"
                raise RuntimeError(
                    f"TOPIC_LOCK_BLOCK: pauta manual incompatível com o tema solicitado; "
                    f"solicitado={forced!r}, brief={brief_title!r}. "
                    "A produção foi interrompida para impedir a troca de jogo."
                )
        parser, selected_media, manual_errors = fetch_manual_media(manual)
        errors.extend(manual_errors)
        # Explicitly skip publisher trailer IDs previously confirmed age-gated;
        # the same brief supplies verified stills plus two working video routes.
        blocked_video_urls = set(manual.get("blocked_video_urls") or [])
        if blocked_video_urls:
            selected_media = [
                (kind, url) for kind, url in selected_media
                if not (kind == "video" and url in blocked_video_urls)
            ]
        selected = {
            "content_id": manual.get("content_id") or ("manual-" + ascii_slug(manual.get("title", "pauta"))[:48]),
            "title": manual.get("title") or "Pauta especial",
            "summary": " ".join(manual["script_blocks"][:3]),
            "url": manual.get("primary_source") or manual["media_source_urls"][0],
            "source": "manual_brief",
            "published_at": now.isoformat(),
            "score": 999,
            "manual_brief_path": {
                "manual-the-wolf-among-us-remastered-launch-2026-10-24": "production/manual-brief-the-wolf-among-us-remastered-2026-10-24.json",
                "manual-zenless-zone-zero-version-3-3-journey-to-the-sky-2026-10-25": "production/manual-brief-zenless-zone-zero-2026-10-25.json",
                "manual-the-blood-of-dawnwalker-update-1-1-2026-10-23": "production/manual-brief-the-blood-of-dawnwalker-2026-10-23.json",
                "manual-fight-night-return-announcement-2026-10-21": "production/manual-brief-fight-night-return-2026-10-21.json",
                "manual-once-human-isles-of-abyss-launch-2026-10-20": "production/manual-brief-once-human-isles-of-abyss-2026-10-20.json",
                "manual-arc-raiders-pve-toggle-oct-2026": "production/manual-brief-arc-raiders-pve-toggle-2026-10-15.json",
                "manual-castlevania-belmonts-curse-2026-10-15": "production/manual-brief-castlevania-2026-10-15.json",
                "manual-call-of-duty-modern-warfare-4-campaign-early-access-2026-10-16": "production/manual-brief-call-of-duty-modern-warfare-4-2026-10-16.json",
                "manual-enshrouded-1-0-launch-2026-10-17": "production/manual-brief-enshrouded-2026-10-17.json",
                "microsoft-rewards-brasil-2026-10-19": "production/manual-brief-microsoft-rewards-2026-10-19.json",
                "manual-witcher-3-remastered-patch-501-switch2-2026-10-19": "production/manual-brief-witcher-3-remastered-2026-10-19.json",
                "qssr-ps5-2026-10-19": "production/manual-brief-qssr-ps5-2026-10-19.json",
            }.get(manual.get("content_id"), "production/manual-brief.json"),
        }
        mix = media_mix(selected_media)
        winner = {
            "candidate": selected,
            "parser": parser,
            "media": selected_media,
            "selection_score": 999.0,
            "mix": mix,
            "repeat": {
                "blocked": False,
                "penalty": 0,
                "reasons": [],
                "topic_key": topic_key(selected["title"]),
            },
            "media_sources": {url: url for _, url in selected_media},
        }
        script = "\n\n".join(manual["script_blocks"])
    else:
        for index, c in enumerate(candidates):
            if c.get("content_id") in used:
                errors.append({"title": c.get("title"), "error": "content_id já publicado"})
                continue
            if forced.upper() != "AUTO" and forced.lower() not in c.get("title", "").lower():
                continue

            topic_verdict = classify_topic(c.get("title", ""), c.get("summary", ""))
            if not topic_verdict["allowed"]:
                errors.append({"title": c.get("title"), "error": f"EDITORIAL_TOPIC_BLOCK: {topic_verdict['reason']}"})
                continue

            repeat = repetition_check(c, history, now)
            if repeat["blocked"] and forced.upper() == "AUTO":
                errors.append({"title": c.get("title"), "error": "; ".join(repeat["reasons"])})
                continue

            try:
                p = fetch_page(c["url"])
                media_sources = {asset_url: c["url"] for _, asset_url in p.media}
                # The official Deadlock news feed contains patch notes and character
                # posts without embedded video. Supplement only this explicit topic
                # with the game's official Steam store media, preserving provenance.
                if forced.casefold() == "deadlock":
                    # Preserve the selected news item; discover direct trailer streams
                    # from Steam's app API/CDN instead of relying on HTML embeds.
                    game_page_url = "https://store.steampowered.com/app/1422450/Deadlock/"
                    game_page = fetch_page(game_page_url)
                    p.media.extend(game_page.media)
                    for _, asset_url in game_page.media:
                        media_sources.setdefault(asset_url, game_page_url)
                    steam_assets = steam_candidates(1422450, "video")
                    for asset_url, asset_source, asset_label in steam_assets:
                        p.media.append(("video", asset_url))
                        media_sources.setdefault(asset_url, game_page_url)
                    print(f"Deadlock official Steam direct streams discovered: {len(steam_assets)}", flush=True)
                    # Fallback editorial específico de Deadlock: página recente de gameplay
                    # do herói Solomon. A pauta continua bloqueada em Deadlock; não se troca
                    # por outro jogo quando a loja oficial não oferece um stream direto.
                    if not any(kind == "video" for kind, _ in p.media):
                        gameplay_page_url = "https://thegamehaus.com/deadlock/deadlock-solomon-abilities-breakdown-first-look/2026/10/09/"
                        try:
                            gameplay_page = fetch_page(gameplay_page_url)
                            for kind, asset_url in gameplay_page.media:
                                p.media.append((kind, asset_url))
                                media_sources.setdefault(asset_url, gameplay_page_url)
                            print(
                                "Deadlock Solomon gameplay-page fallback discovered:",
                                len(gameplay_page.media), flush=True
                            )
                        except Exception as exc:
                            print("Deadlock Solomon gameplay-page fallback failed:", str(exc)[:180], flush=True)
                media = canonical_media(p.media)
                if len(media) < 2:
                    errors.append({"title": c.get("title"), "error": f"somente {len(media)} mídias descobertas"})
                    continue
                score, mix = candidate_score(c, index, media, repeat)
                # O plano de produção exige duas fontes de vídeo distintas.
                # Uma URL duplicada do mesmo trailer não deve ganhar a pauta
                # nem empurrar a falha de diversidade para o diretor no fim.
                if mix["videos"] < 2:
                    errors.append({"title": c.get("title"), "error": f"somente {mix['videos']} vídeo(s) único(s); mínimo exigido: 2"})
                    continue
                evaluated.append({
                    "candidate": c,
                    "parser": p,
                    "media": media,
                    "selection_score": round(score, 2),
                    "mix": mix,
                    "repeat": repeat,
                    "media_sources": media_sources,
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
    validate_script_context(selected, script)
    media_sources = winner.get("media_sources") or {asset_url: selected["url"] for _, asset_url in selected_media}
    # Apenas o esboço; a narração final só existe após a decupagem da mídia.
    (OUT / "auto-script-outline.txt").write_text(script + "\n", encoding="utf-8")

    planned_scenes = make_scenes(selected, selected_media, script)
    if manual:
        short_hooks = [sentence(x) for x in (manual.get("short_hooks") or []) if sentence(x)]
        if len(short_hooks) != 3:
            raise RuntimeError(
                f"QUALITY_BLOCK: brief manual precisa definir exatamente 3 short_hooks aprovados; recebeu {len(short_hooks)}"
            )
    else:
        short_hooks = []
        seen_hooks = set()
        for scene in planned_scenes:
            hook = sentence(scene.get("title") or "")
            key = hook.casefold()
            if not hook or key in seen_hooks:
                continue
            if re.fullmatch(r"(DESTAQUE|CENA|BLOCO|T[ÓO]PICO)\\s*\\d*.*", hook, re.I) or hook.casefold()=="contexto oficial":
                continue
            seen_hooks.add(key)
            short_hooks.append(hook[:88])
            if len(short_hooks) == 3:
                break
        if len(short_hooks) != 3:
            raise RuntimeError("QUALITY_BLOCK: não foi possível definir 3 hooks editoriais reais para os Shorts")

    short_hooks = [h[:88].rstrip(" -:|") for h in short_hooks]

    media_items = []
    planned_video_urls = set()
    # Download the fast, publisher-hosted stills before slow/blocked video fallbacks.
    # The media gate still requires the configured number of unique moving-video seconds.
    # Optional exact-subject stills curated from the game's official notes.
    # This is a generic schema; no hardcoded game, no inference from unrelated media.
    if manual:
        for i, visual in enumerate(manual.get("visual_reference_images") or [], 1):
            if not isinstance(visual, dict) or not str(visual.get("url","")).startswith("https://"):
                continue
            media_items.append({
                "type": "image",
                "url": visual["url"],
                "role": f"official_subject_reference_{i:02d}",
                "source_label": str(visual.get("label") or "").strip()[:90],
                "max_assets": 1,
                "source_proof": visual.get("source_proof") or selected["url"],
                "relevance_evidence": "publisher_curated_subject_specific_still",
            })

    for i, (typ, url) in enumerate(selected_media, 1):
        role = f"official_gameplay_or_trailer_{i:02d}" if typ == "video" else f"official_context_{i:02d}"
        item = {
            "type": typ,
            "url": url,
            "role": ((manual.get("video_roles") or {}).get(url, role) if manual and typ == "video" else role),
            "source_label": ((manual.get("video_labels") or {}).get(url, "") if manual else ""),
            "max_assets": 1,
            "source_proof": media_sources.get(url, selected["url"]),
            "relevance_evidence": "official_source_page_discovered_asset",
        }
        if typ == "video":
            # Nunca limitar o fallback ao índice da cena: todos os trailers oficiais
            # aprovados ficam disponíveis quando a primeira URL falha/bloqueia.
            item["min_duration"] = 5
            planned_video_urls.add(url)
        media_items.append(item)

    # Automatic productions also inspect the original publisher page for extra official video embeds.
    # This is a fallback pool, not a replacement for relevance/visual QA.
    if not manual:
        source_page = str(selected.get("url") or "")
        if source_page.startswith("https://"):
            media_items.append({
                "type": "video",
                "url": source_page,
                "role": "official_topic_page_video_fallback",
                "source_label": "Official publisher topic page",
                "max_assets": 8,
                "min_duration": 5,
                "source_proof": source_page,
                "relevance_evidence": "official_topic_page_video_fallback",
            })
        # Grounded 2's official game and Xbox product pages expose additional
        # publisher-controlled trailers when the news article only exposes one clip.
        if "grounded 2" in str(selected.get("title") or "").casefold():
            for official_page in (
                "https://grounded2.obsidian.net/",
                "https://www.xbox.com/en-US/games/grounded-2",
            ):
                media_items.append({
                    "type": "video",
                    "url": official_page,
                    "role": "official_grounded2_video_fallback",
                    "source_label": "Official Grounded 2 publisher/platform page",
                    "max_assets": 8,
                    "min_duration": 5,
                    "source_proof": official_page,
                    "relevance_evidence": "official_game_page_video_fallback",
                })

    # Manual briefs can carry a curated pool of official videos that is larger
    # than the article parser's discovered media. Enqueue every unique candidate
    # explicitly, in order, so a failed first URL cannot hide the remaining pool.
    if manual:
        curated_video_urls = []
        for key in ("video_urls", "video_fallback_urls"):
            for candidate_url in manual.get(key) or []:
                if (isinstance(candidate_url, str) and candidate_url.startswith("https://")
                        and candidate_url not in planned_video_urls
                        and candidate_url not in curated_video_urls):
                    curated_video_urls.append(candidate_url)
        labels = manual.get("video_labels") or {}
        roles = manual.get("video_roles") or {}
        for j, candidate_url in enumerate(curated_video_urls, 1):
            media_items.append({
                "type": "video",
                "url": candidate_url,
                "role": roles.get(candidate_url, f"official_curated_fallback_{j:02d}"),
                "source_label": labels.get(candidate_url, "Publisher-curated official video"),
                "max_assets": 1,
                "min_duration": 5,
                "source_proof": candidate_url,
                "relevance_evidence": "manual_brief_curated_official_video_fallback",
            })
            planned_video_urls.add(candidate_url)

    # For an explicitly curated manual brief, prefer original game media on
    # Steam's own CDN when its exact app ID is supplied. This does not alter
    # automatic editorial discovery or other productions.
    if manual and str(manual.get("steam_app_id") or "").isdigit():
        steam_id = int(manual["steam_app_id"])
        steam_source = f"https://store.steampowered.com/app/{steam_id}/"
        # Independent route 1: exact-app official Steam CDN videos, before YouTube.
        media_items.append({
            "type": "video",
            "steam_app_id": steam_id,
            "role": "official_steam_gameplay",
            "max_assets": 8,
            "min_duration": 5,
            "source_proof": steam_source,
            "relevance_evidence": "steam_exact_app_direct_stream",
        })
        # Independent route 2: curated screenshots from the same official game's
        # Steam record. These supplement footage if only one moving source survives;
        # they never replace the minimum-video and unique-motion quality gates.
        media_items.append({
            "type": "image",
            "steam_app_id": steam_id,
            "role": "official_steam_game_screenshot",
            "max_assets": 4,
            "source_proof": steam_source,
            "relevance_evidence": "steam_exact_app_screenshot",
        })

    minimum_assets = int(manual.get("minimum_assets", 3 if (
        str(manual.get("title","")).casefold() == "arc raiders"
        or str(manual.get("content_id","")).startswith("manual-castlevania-")
    ) else 2)) if manual else 2
    minimum_video_assets = int(manual.get("minimum_video_assets", 4 if
        str(manual.get("content_id","")).startswith("manual-castlevania-")
        else (3 if str(manual.get("title","")).casefold() == "arc raiders" else 1)
    )) if manual else 2
    minimum_unique_video_seconds = float(manual.get("minimum_unique_video_seconds", 180 if
        str(manual.get("content_id","")).startswith("manual-castlevania-")
        else (90 if str(manual.get("title","")).casefold() == "arc raiders" else 15)
    )) if manual else 75
    minimum_image_assets = int(manual.get("minimum_image_assets", 0)) if manual else 0

    plan = {
        "topic": (manual.get("headline") if manual else pt_headline(selected, parser)),
        "source": selected["url"],
        "minimum_assets": minimum_assets,
        "minimum_video_assets": minimum_video_assets,
        "minimum_unique_video_seconds": minimum_unique_video_seconds,
        "minimum_image_assets": minimum_image_assets,
        "media_policy": "gameplay_or_official_moving_footage_required; minimum_15s_unique_video; images_are_complement_only; no_image_only_master; premium_v4_motion_for_images",
        "short_hooks": short_hooks,
        "short_hook_policy": "exact_approved_hook; semantic_scene_match; qa_block_on_mismatch",
        "allow_official_subject_fallback": bool(manual and str(manual.get("content_id","")).startswith("manual-castlevania-")),
        "media": media_items,
        "scenes": planned_scenes,
    }
    (OUT / "auto-media-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    privacy = os.getenv("PUBLISH_PRIVACY", "unlisted").strip() or "unlisted"
    master_meta, shorts_meta = build_metadata(selected, parser, privacy)
    for i, meta in enumerate(shorts_meta):
        meta["title"] = short_hooks[i]
    if manual:
        headline = sentence(manual.get("headline") or master_meta["title"])[:100]
        master_meta["title"] = headline
        all_sources = manual.get("source_urls") or [selected["url"]]
        source_lines = "\n".join(f"- {u}" for u in all_sources[:8])
        # Build topic-specific hashtags locally: build_metadata keeps these lists
        # internal, so do not reference its local variables from main().
        manual_game = game_name(manual.get("title") or headline)
        manual_slug = ascii_slug(" ".join([manual_game, headline]))
        if "blood of dawnwalker" in manual_slug or "dawnwalker" in manual_slug:
            # Tags editoriais específicas para The Blood of Dawnwalker.
            # Master YouTube usa conjunto ampliado; TikTok Helper aplica sua própria regra de 5.
            tag_candidates = [
                "The Blood of Dawnwalker", "Dawnwalker", "Rebel Wolves",
                "Vampire RPG", "Dark Fantasy", "Action RPG", "RPG Games",
                "Open World RPG", "Fantasy Games", "Gaming News",
                "Upcoming Games", "PC Gaming", "PlayStation 5",
                "Xbox Series X", "Radar dos Games",
            ]
        elif "mega man" in manual_slug:
            tag_candidates = [
                "Mega Man Dual Override", "Mega Man", "Proto Man", "Capcom",
                "Twinkle Girl", "Astro Man", "Action Platformer", "Platform Games",
                "Nintendo", "PC Gaming", "PlayStation 5", "Xbox Series X",
                "Gaming News", "Upcoming Games", "Radar dos Games",
            ]
        else:
            # Não preencher com hashtags genéricas fixas: derivar termos do jogo/pauta.
            tag_candidates = [manual_game]
            tag_candidates.extend(keywords(headline, limit=12))
            tag_candidates.extend(["Gaming News", "Upcoming Games", "Gameplay", "Radar dos Games"])
        topic_tags = []
        seen_tag_keys = set()
        for item in tag_candidates:
            tag = hashtag(item)
            key = unicodedata.normalize("NFKD", tag.lstrip("#")).encode("ascii", "ignore").decode().lower() if tag else ""
            if tag and len(tag) >= 4 and key not in seen_tag_keys:
                topic_tags.append(tag)
                seen_tag_keys.add(key)
        topic_hashtags = " ".join(topic_tags[:15])
        short_topic_hashtags = " ".join(topic_tags[:8])
        master_meta["description"] = (
            f"🎮 {headline}\n\n"
            "Especial aprofundado com informações das fontes oficiais consultadas, "
            "contexto do anúncio e separação clara entre fatos confirmados e interpretações.\n\n"
            f"🔎 Fontes consultadas:\n{source_lines}\n\n"
            f"{topic_hashtags}"
        )
        for i, meta in enumerate(shorts_meta):
            meta["description"] = (
                f"{headline}. Recorte {i+1}/3 do especial.\n\n"
                f"Fonte principal: {selected['url']}\n\n"
                f"{short_topic_hashtags}"
            )
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
        "manual_brief": bool(manual),
        "short_hooks": short_hooks,
        "short_hook_policy": "exact_approved_hook; semantic_scene_match; qa_block_on_mismatch",
        "source_urls": (manual.get("source_urls") if manual else [selected["url"]]),
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

# [run-production] TOPIC=Deadlock — retry with explicit topic lock and Solomon gameplay-page media fallback.

# Media fallback fix 2026-10-16: enqueue every unique publisher-curated video URL before media QA.

# Controlled rerun after Master render timeout increased to 60 minutes.
