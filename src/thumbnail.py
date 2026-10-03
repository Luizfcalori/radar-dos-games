#!/usr/bin/env python3
"""Gera thumbnail 1280x720 usando arte oficial aprovada do jogo + identidade Radar."""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

W, H = 1280, 720
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
RADAR = (0, 232, 196)
WHITE = (248, 250, 252)


def duration(video: str) -> float:
    try:
        return float(
            subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                text=True,
            ).strip()
        )
    except Exception:
        return 0.0


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(r"(?i):\s*(lançamento ganha novos detalhes|veja o que foi confirmado oficialmente)$", "", title)
    # Na capa, prioriza o nome do jogo e evita frases longas de roteiro.
    if " - " in title:
        head = title.split(" - ", 1)[0].strip()
        if len(head) >= 6:
            title = head
    return title[:52].rstrip(" -:|") or "RADAR DOS GAMES"


def fit_title_lines(draw: ImageDraw.ImageDraw, title: str, max_width: int, max_lines: int = 3):
    words = clean_title(title).upper().split()
    for size in range(82, 45, -2):
        font = ImageFont.truetype(FONT_BOLD, size)
        lines, current = [], []
        for word in words:
            trial = " ".join(current + [word])
            if current and draw.textbbox((0, 0), trial, font=font)[2] > max_width:
                lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            lines.append(" ".join(current))
        if len(lines) <= max_lines:
            return lines, font
    return [clean_title(title).upper()[:38]], ImageFont.truetype(FONT_BOLD, 46)


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
            ratio = iw / max(ih, 1)
            ratio_penalty = abs(ratio - (16 / 9)) * 350_000
            score = (iw * ih) - ratio_penalty
            # Steam screenshot do app exato é a fonte preferida.
            if str(asset.get("relevance_evidence", "")).startswith("steam_exact_app"):
                score += 2_000_000
            candidates.append((score, p, asset))
        except Exception:
            continue

    if not candidates:
        return None, None
    _, path, asset = max(candidates, key=lambda row: row[0])
    return path, asset


def extract_fallback_frame(video: str, out: Path) -> Path:
    total = duration(video)
    seek = 8.0 if total <= 0 else min(max(total * 0.30, 8.0), max(1.0, total - 1.0))
    tmp = out.with_name(out.stem + ".frame-fallback.jpg")
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{seek:.3f}", "-i", video,
            "-frames:v", "1", "-q:v", "2", str(tmp),
        ],
        check=True,
    )
    return tmp


def cover_image(path: Path) -> Image.Image:
    with Image.open(path) as src:
        src = src.convert("RGB")
        base = ImageOps.fit(src, (W, H), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    base = ImageEnhance.Contrast(base).enhance(1.12)
    base = ImageEnhance.Color(base).enhance(1.08)
    base = ImageEnhance.Sharpness(base).enhance(1.12)
    return base


def draw_brand_logo(layer: Image.Image):
    d = ImageDraw.Draw(layer, "RGBA")
    panel = (28, 24, 520, 142)
    d.rounded_rectangle(panel, radius=24, fill=(2, 8, 15, 205), outline=(0, 232, 196, 115), width=2)

    cx, cy, r = 82, 82, 44
    d.ellipse((cx-r, cy-r, cx+r, cy+r), outline=RADAR + (245,), width=5)
    d.ellipse((cx-29, cy-29, cx+29, cy+29), outline=RADAR + (155,), width=2)
    d.ellipse((cx-14, cy-14, cx+14, cy+14), outline=RADAR + (120,), width=2)
    # Sweep do radar.
    ang = math.radians(-38)
    x2, y2 = cx + int(r * math.cos(ang)), cy + int(r * math.sin(ang))
    d.line((cx, cy, x2, y2), fill=RADAR + (255,), width=5)
    d.ellipse((102, 54, 112, 64), fill=RADAR + (255,))

    # Mini gamepad integrado ao radar.
    d.rounded_rectangle((49, 77, 116, 111), radius=14, fill=(248, 250, 252, 245), outline=(10, 18, 28, 255), width=2)
    d.line((63, 87, 63, 101), fill=(9, 18, 30, 255), width=4)
    d.line((56, 94, 70, 94), fill=(9, 18, 30, 255), width=4)
    d.ellipse((95, 88, 102, 95), fill=(9, 18, 30, 255))
    d.ellipse((104, 97, 111, 104), fill=(9, 18, 30, 255))

    radar_font = ImageFont.truetype(FONT_BOLD, 39)
    sub_font = ImageFont.truetype(FONT_BOLD, 25)
    d.text((142, 44), "RADAR", font=radar_font, fill=WHITE + (255,), stroke_width=2, stroke_fill=(0, 0, 0, 180))
    d.text((143, 88), "DOS", font=sub_font, fill=WHITE + (255,))
    d.text((205, 88), "GAMES", font=sub_font, fill=RADAR + (255,))
    d.rounded_rectangle((142, 121, 317, 126), radius=2, fill=RADAR + (230,))


def compose(base: Image.Image, title: str) -> Image.Image:
    canvas = base.convert("RGBA")

    # Sombra/vignette para preservar imagem oficial e garantir legibilidade sem virar "print com tarja".
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = shade.load()
    for y in range(H):
        for x in range(W):
            edge = max(abs(x - W/2) / (W/2), abs(y - H/2) / (H/2))
            right = max(0.0, (x - W * 0.42) / (W * 0.58))
            bottom = max(0.0, (y - H * 0.46) / (H * 0.54))
            alpha = int(min(205, 30 + 75 * edge + 100 * right + 65 * bottom))
            px[x, y] = (0, 0, 0, alpha)
    canvas = Image.alpha_composite(canvas, shade)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_brand_logo(overlay)
    d = ImageDraw.Draw(overlay, "RGBA")

    lines, font = fit_title_lines(d, title, max_width=665, max_lines=3)
    spacing = 7
    line_boxes = [d.textbbox((0, 0), line, font=font, stroke_width=2) for line in lines]
    widths = [b[2] - b[0] for b in line_boxes]
    heights = [b[3] - b[1] for b in line_boxes]
    block_h = sum(heights) + spacing * max(0, len(lines) - 1)
    x_right = 1232
    y = 690 - block_h

    # Accent bar do padrão Radar.
    d.rounded_rectangle((548, y - 8, 560, 694), radius=5, fill=RADAR + (250,))
    for line, lw, lh in zip(lines, widths, heights):
        x = x_right - lw
        d.text(
            (x, y), line, font=font, fill=WHITE + (255,),
            stroke_width=4, stroke_fill=(0, 0, 0, 220)
        )
        y += lh + spacing

    # Assinatura discreta; o jogo continua protagonista.
    tag_font = ImageFont.truetype(FONT_BOLD, 20)
    tag = "RADAR DOS GAMES • CAPA OFICIAL"
    tw = d.textbbox((0, 0), tag, font=tag_font)[2]
    d.rounded_rectangle((1232 - tw - 28, 168, 1232, 204), radius=10, fill=(1, 8, 14, 160))
    d.text((1232 - tw - 14, 174), tag, font=tag_font, fill=RADAR + (255,))

    return Image.alpha_composite(canvas, overlay).convert("RGB")


def main():
    if len(sys.argv) not in (4, 5):
        raise SystemExit("uso: thumbnail.py VIDEO TITULO SAIDA.jpg [IMAGEM_OFICIAL] ")

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
        # Fallback técnico para workflows antigos sem imagens; novos fluxos STRICT devem fornecer screenshots oficiais.
        fallback_tmp = extract_fallback_frame(video, out)
        source_image = fallback_tmp
        source_kind = "video_frame_fallback"
        print("WARNING: thumbnail sem screenshot oficial aprovada; usando frame do Master como fallback técnico")

    result = compose(cover_image(source_image), title)
    result.save(out, format="JPEG", quality=95, subsampling=0, optimize=True)

    if fallback_tmp:
        fallback_tmp.unlink(missing_ok=True)

    if not out.exists() or out.stat().st_size < 30_000:
        raise RuntimeError("QUALITY_BLOCK: thumbnail não foi gerada corretamente")

    with Image.open(out) as check:
        if check.size != (W, H):
            raise RuntimeError(f"QUALITY_BLOCK: thumbnail em resolução incorreta: {check.size}")

    policy = {
        "status": "APPROVED" if source_kind == "approved_official_image" else "FALLBACK",
        "policy": "official_game_image_first; radar_brand_lockup; 16:9; never_prefer_video_frame",
        "source_kind": source_kind,
        "source_path": str(source_image),
        "source_url": (asset or {}).get("url"),
        "source": (asset or {}).get("source"),
        "relevance_evidence": (asset or {}).get("relevance_evidence"),
        "output": str(out),
        "size": [W, H],
        "title": clean_title(title),
    }
    (out.parent / "thumbnail-policy.json").write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(policy, ensure_ascii=False))
    print(str(out))


if __name__ == "__main__":
    main()
