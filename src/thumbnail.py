#!/usr/bin/env python3
"""Thumbnail 1280x720 padronizada do Radar dos Games.

Padrão editorial fixo:
- imagem oficial aprovada como fundo quando disponível;
- título principal grande no centro, branco + verde Radar;
- subtítulo dentro de barra metálica escura;
- assinatura RADAR DOS GAMES centralizada na base;
- alto contraste, sombra forte e leitura no celular;
- o upload preserva a capa pronta, nunca regenera uma capa diferente depois.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

W, H = 1280, 720
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
WHITE = (246, 247, 249)
RADAR_GREEN = (57, 255, 20)
RADAR_GREEN_DARK = (19, 118, 22)
GOLD = (255, 194, 35)
BLACK = (5, 7, 11)


def font(size: int):
    return ImageFont.truetype(FONT_BOLD, size)


def duration(video: str) -> float:
    try:
        return float(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", video
        ], text=True).strip())
    except Exception:
        return 0.0


def clean_title(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    value = re.sub(r"(?i)\s*#shorts?\b", "", value).strip()
    return value[:90].rstrip(" -:|") or "RADAR DOS GAMES"


def split_title(value: str):
    """Separa headline curta + subtítulo para manter sempre o mesmo layout."""
    title = clean_title(value).upper()
    if ":" in title:
        head, sub = [x.strip() for x in title.split(":", 1)]
        if head and sub:
            return head[:28], sub[:52]

    words = title.split()
    if len(words) <= 2:
        return title, "NOVIDADE NO RADAR DOS GAMES"

    # Nomes com duas palavras fortes, como STAR WARS / ACE COMBAT.
    if len(words[0]) <= 12 and len(words[1]) <= 12:
        head = " ".join(words[:2])
        sub = " ".join(words[2:])
    else:
        head = words[0]
        sub = " ".join(words[1:])
    return head[:28], sub[:52] or "NOVIDADE NO RADAR DOS GAMES"


def approved_image_from_manifest(out: Path):
    manifest = out.parent / "clips.json"
    if not manifest.exists():
        return None, None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return None, None

    candidates = []
    for asset in data.get("assets", []):
        if not asset.get("approved") or asset.get("type") != "image":
            continue
        p = Path(str(asset.get("path") or ""))
        if not p.exists() or p.stat().st_size < 20_000:
            continue
        try:
            with Image.open(p) as im:
                iw, ih = im.size
            if iw < 640 or ih < 360:
                continue
            ratio_penalty = abs((iw / max(ih, 1)) - (16 / 9)) * 350_000
            score = iw * ih - ratio_penalty
            evidence = str(asset.get("relevance_evidence", ""))
            if evidence.startswith("steam_exact_app") or "official" in evidence.lower():
                score += 2_000_000
            candidates.append((score, p, asset))
        except Exception:
            continue
    if not candidates:
        return None, None
    _, p, asset = max(candidates, key=lambda row: row[0])
    return p, asset


def extract_fallback_frame(video: str, out: Path) -> Path:
    total = duration(video)
    seek = 8.0 if total <= 0 else min(max(total * 0.30, 8.0), max(1.0, total - 1.0))
    tmp = out.with_name(out.stem + ".frame-fallback.jpg")
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-ss", f"{seek:.3f}", "-i", video,
        "-frames:v", "1", "-q:v", "2", str(tmp)
    ], check=True)
    return tmp


def cover_image(path: Path) -> Image.Image:
    with Image.open(path) as src:
        src = src.convert("RGB")
        base = ImageOps.fit(src, (W, H), method=Image.Resampling.LANCZOS, centering=(0.5, 0.48))
    base = ImageEnhance.Contrast(base).enhance(1.20)
    base = ImageEnhance.Color(base).enhance(1.16)
    base = ImageEnhance.Sharpness(base).enhance(1.08)
    return base


def fit_text(draw, text, max_width, start=104, end=48):
    for size in range(start, end - 1, -2):
        f = font(size)
        b = draw.textbbox((0, 0), text, font=f, stroke_width=5)
        if b[2] - b[0] <= max_width:
            return f
    return font(end)


def draw_text_shadow(draw, xy, text, f, fill, stroke=5):
    x, y = xy
    # sombra curta e presa ao texto: nunca flutuando no topo.
    draw.text((x + 7, y + 9), text, font=f, fill=(0, 0, 0, 220), stroke_width=stroke + 4, stroke_fill=(0, 0, 0, 220))
    draw.text((x, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=(4, 5, 8, 255))


def compose(base: Image.Image, title: str) -> Image.Image:
    headline, subtitle = split_title(title)
    canvas = base.convert("RGBA")

    # Vinheta cinematográfica + escurecimento inferior para leitura no celular.
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette, "RGBA")
    for i in range(18):
        pad = i * 18
        alpha = int(9 + i * 4.2)
        vd.rectangle((pad, pad, W - pad, H - pad), outline=(0, 0, 0, alpha), width=24)
    vd.rectangle((0, 365, W, H), fill=(0, 0, 0, 78))
    canvas = Image.alpha_composite(canvas, vignette)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")

    # Headline central. Última palavra em verde Radar — identidade oficial aprovada.
    words = headline.split()
    left = " ".join(words[:-1]) if len(words) > 1 else words[0]
    right = words[-1] if len(words) > 1 else ""
    full_for_fit = headline
    hf = fit_text(d, full_for_fit, 1120, start=112, end=58)
    gap = 24 if right else 0
    lb = d.textbbox((0, 0), left, font=hf, stroke_width=5)
    rb = d.textbbox((0, 0), right, font=hf, stroke_width=5) if right else (0, 0, 0, 0)
    total_w = (lb[2] - lb[0]) + gap + (rb[2] - rb[0])
    x = (W - total_w) // 2
    y = 390
    draw_text_shadow(d, (x, y), left, hf, WHITE)
    if right:
        draw_text_shadow(d, (x + (lb[2]-lb[0]) + gap, y), right, hf, RADAR_GREEN)

    # Barra metálica fixa do padrão Radar.
    panel = (90, 515, 1190, 630)
    d.rounded_rectangle(panel, radius=14, fill=(11, 14, 20, 238), outline=(156, 161, 171, 210), width=4)
    d.rounded_rectangle((100, 525, 1180, 620), radius=10, outline=(RADAR_GREEN[0], RADAR_GREEN[1], RADAR_GREEN[2], 235), width=4)
    d.rectangle((90, 551, 1190, 558), fill=(RADAR_GREEN[0], RADAR_GREEN[1], RADAR_GREEN[2], 150))
    for x0 in range(112, 1180, 44):
        d.line((x0, 526, x0 + 18, 526), fill=(95, 101, 112, 160), width=2)
        d.line((x0, 619, x0 + 18, 619), fill=(95, 101, 112, 160), width=2)

    sf = fit_text(d, subtitle, 990, start=54, end=30)
    sb = d.textbbox((0, 0), subtitle, font=sf, stroke_width=3)
    sx = (W - (sb[2] - sb[0])) // 2
    sy = 545
    # Última parte recebe ouro quando houver separador, mantendo o efeito da capa escolhida.
    draw_text_shadow(d, (sx, sy), subtitle, sf, WHITE, stroke=3)

    # Assinatura fixa na base.
    badge = (392, 646, 888, 704)
    d.rounded_rectangle(badge, radius=8, fill=(7, 9, 13, 245), outline=(RADAR_GREEN[0], RADAR_GREEN[1], RADAR_GREEN[2], 245), width=4)
    bf = font(28)
    a, b = "RADAR DOS ", "GAMES"
    aw = d.textbbox((0, 0), a, font=bf)[2]
    bw = d.textbbox((0, 0), b, font=bf)[2]
    bx = (W - aw - bw) // 2
    d.text((bx, 658), a, font=bf, fill=WHITE + (255,), stroke_width=2, stroke_fill=BLACK + (255,))
    d.text((bx + aw, 658), b, font=bf, fill=RADAR_GREEN + (255,), stroke_width=2, stroke_fill=BLACK + (255,))

    # Moldura inferior verde/metalizada consistente.
    d.line((0, 714, W, 714), fill=RADAR_GREEN + (255,), width=6)
    return Image.alpha_composite(canvas, overlay).convert("RGB")


def main():
    if len(sys.argv) not in (4, 5):
        raise SystemExit("uso: thumbnail.py VIDEO TITULO SAIDA.jpg [IMAGEM_OFICIAL]")

    video, title, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    explicit_image = Path(sys.argv[4]) if len(sys.argv) == 5 else None
    out.parent.mkdir(parents=True, exist_ok=True)

    asset = None
    source_kind = "approved_official_image"
    if explicit_image and explicit_image.exists():
        source_image = explicit_image
    else:
        source_image, asset = approved_image_from_manifest(out)

    fallback_tmp = None
    if source_image is None:
        fallback_tmp = extract_fallback_frame(video, out)
        source_image = fallback_tmp
        source_kind = "video_frame_fallback"

    result = compose(cover_image(source_image), title)
    result.save(out, format="JPEG", quality=95, subsampling=0, optimize=True)

    if fallback_tmp:
        fallback_tmp.unlink(missing_ok=True)

    if not out.exists() or out.stat().st_size < 30_000:
        raise RuntimeError("QUALITY_BLOCK: thumbnail não foi gerada corretamente")
    with Image.open(out) as check:
        if check.size != (W, H):
            raise RuntimeError(f"QUALITY_BLOCK: thumbnail em resolução incorreta: {check.size}")

    headline, subtitle = split_title(title)
    policy = {
        "status": "APPROVED",
        "policy": "radar_standard_v3_green; official_image_first; centered_white_green_headline; metallic_subtitle_bar; branded_footer; neon_green_brand_accents; mobile_legible; 16:9",
        "template_version": "radar-thumbnail-v3-green-2026-10-06",
        "source_kind": source_kind,
        "source_path": str(source_image),
        "source_url": (asset or {}).get("url"),
        "source": (asset or {}).get("source"),
        "relevance_evidence": (asset or {}).get("relevance_evidence"),
        "headline": headline,
        "subtitle": subtitle,
        "output": str(out),
        "size": [W, H],
    }
    (out.parent / "thumbnail-policy.json").write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(policy, ensure_ascii=False))
    print(str(out))


if __name__ == "__main__":
    main()
