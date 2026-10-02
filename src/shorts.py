#!/usr/bin/env python3
"""Gera exatamente 3 Shorts 9:16 no padrão oficial Radar dos Games.

Referência aprovada em 02/10/2026:
- 1080x1920, 30 fps
- branding RADAR DOS GAMES no topo
- headline grande em bloco preto
- mídia contextual central preservada, sem crop destrutivo
- moldura/acento com cor contextual extraída do próprio trecho
- faixa contextual com a mesma cor de destaque
- CTA inferior: VÍDEO COMPLETO NO CANAL / RADAR DOS GAMES
- fundo derivado da própria mídia, desfocado
- áudio original do trecho normalizado

Importante: a cor ciano da referência original pertencia àquele vídeo/corte e NÃO
faz parte da identidade fixa. A composição é fixa; a cor de destaque é adaptativa.

Mantém compatibilidade com: python src/shorts.py <master.mp4>
Se output/qa.json existir, usa títulos/subtítulos das cenas do Master.
"""

import colorsys
import json
import subprocess
import sys
import textwrap
from pathlib import Path

W = 1080
H = 1920
FPS = 30
DEFAULT_LENGTH = 22
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
AUDIO_NORMALIZE = "loudnorm=I=-16:LRA=7:TP=-1.5"
NAVY = "0x020A23"
BLACK = "black"
YELLOW = "0xF4FF00"
NEUTRAL_ACCENT = "0xFFFFFF"


def sh(cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True)


def duration(path):
    return float(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            text=True,
        ).strip()
    )


def esc(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace("\n", "\\n")
    )


def wrapped(text: str, width: int, max_lines: int = 2) -> str:
    clean = " ".join((text or "").strip().split())
    if not clean:
        return ""
    lines = textwrap.wrap(clean.upper(), width=width, break_long_words=False, break_on_hyphens=False)
    if len(lines) > max_lines:
        kept = lines[:max_lines]
        kept[-1] = textwrap.shorten(" ".join(lines[max_lines - 1 :]), width=width, placeholder="…")
        lines = kept
    return "\n".join(lines)


def accent_from_source(src: Path, sample_time: float) -> str:
    """Extrai uma cor viva do próprio trecho, sem depender de libs/serviços pagos.

    Faz amostragem 64x64 com FFmpeg, agrupa pixels saturados por faixa de matiz e
    escolhe a família cromática mais representativa. Em material sem cor forte,
    usa branco neutro para não inventar uma identidade cromática.
    """
    try:
        raw = subprocess.check_output(
            [
                "ffmpeg", "-v", "error", "-ss", f"{max(0.0, sample_time):.3f}",
                "-i", str(src), "-frames:v", "1", "-vf",
                "scale=64:64:force_original_aspect_ratio=decrease,pad=64:64:(ow-iw)/2:(oh-ih)/2",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
            ]
        )
        if len(raw) < 3:
            return NEUTRAL_ACCENT

        buckets = {}
        for i in range(0, len(raw) - 2, 3):
            r, g, b = raw[i], raw[i + 1], raw[i + 2]
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if s < 0.34 or v < 0.28 or v > 0.99:
                continue
            hue_bin = int(h * 12) % 12
            weight = (s ** 1.35) * (0.55 + v)
            rec = buckets.setdefault(hue_bin, [0.0, 0.0, 0.0, 0.0])
            rec[0] += r * weight
            rec[1] += g * weight
            rec[2] += b * weight
            rec[3] += weight

        if not buckets:
            return NEUTRAL_ACCENT

        _, best = max(buckets.items(), key=lambda item: item[1][3])
        weight = best[3]
        r = max(0, min(255, round(best[0] / weight)))
        g = max(0, min(255, round(best[1] / weight)))
        b = max(0, min(255, round(best[2] / weight)))

        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        s = max(0.55, min(0.88, s))
        v = max(0.78, min(0.96, v))
        rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
        return f"0x{round(rr * 255):02X}{round(gg * 255):02X}{round(bb * 255):02X}"
    except Exception as exc:
        print(f"Aviso: cor contextual indisponível ({exc}); usando branco neutro.", file=sys.stderr)
        return NEUTRAL_ACCENT


def load_cards():
    qa = Path("output/qa.json")
    if not qa.exists():
        return []
    try:
        data = json.loads(qa.read_text(encoding="utf-8"))
        scenes = data.get("scenes", [])
        cards = []
        for scene in scenes:
            title = scene.get("title") or "DESTAQUE DO VÍDEO"
            subtitle = scene.get("subtitle") or "CONFIRA O CONTEÚDO COMPLETO"
            cards.append({"title": title, "subtitle": subtitle})
        return cards
    except Exception as exc:
        print(f"Aviso: não foi possível ler output/qa.json: {exc}", file=sys.stderr)
        return []


def pick_cards(cards):
    if not cards:
        return [
            {"title": "DESTAQUE DO VÍDEO", "subtitle": "CONFIRA O CONTEÚDO COMPLETO"},
            {"title": "VOCÊ PRECISA VER ISSO", "subtitle": "DESTAQUE DO RADAR DOS GAMES"},
            {"title": "MAIS UM DESTAQUE", "subtitle": "VÍDEO COMPLETO NO CANAL"},
        ]
    if len(cards) >= 3:
        picks = [0, len(cards) // 2, len(cards) - 1]
        return [cards[i] for i in picks]
    return [cards[i % len(cards)] for i in range(3)]


def make(src, out, start, length, card):
    headline = esc(wrapped(card.get("title", ""), 24, 2))
    subtitle = esc(wrapped(card.get("subtitle", ""), 34, 1))
    accent = accent_from_source(Path(src), start + min(length * 0.5, 8.0))

    # O layout é o padrão fixo. A cor de moldura/faixa é contextual ao trecho.
    fc = (
        f"[0:v]fps={FPS},split=2[base][fg0];"
        f"[base]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        "boxblur=28:14,eq=brightness=-0.18:saturation=0.85[bg];"
        "[fg0]scale=900:600:force_original_aspect_ratio=decrease[fg];"
        "[bg]drawbox=x=0:y=0:w=1080:h=112:color=0x020A23@0.98:t=fill,"
        "drawbox=x=0:y=112:w=1080:h=285:color=black@0.96:t=fill,"
        "drawbox=x=25:y=470:w=1030:h=535:color=0x020A23@0.94:t=fill,"
        f"drawbox=x=96:y=525:w=888:h=430:color={accent}@0.96:t=8,"
        f"drawbox=x=110:y=539:w=860:h=402:color={accent}@0.42:t=3[canvas];"
        "[canvas][fg]overlay=(W-w)/2:575+(430-h)/2[tmp];"
        f"[tmp]drawtext=fontfile='{FONT}':text='RADAR DOS GAMES':x=48:y=55:fontsize=32:"
        "fontcolor=white:borderw=2:bordercolor=black@0.7:expansion=none,"
        f"drawtext=fontfile='{FONT}':text='{headline}':x=(w-text_w)/2:y=155:fontsize=52:"
        "fontcolor=white:borderw=2:bordercolor=black@0.7:line_spacing=12:expansion=none,"
        "drawbox=x=170:y=1040:w=740:h=64:color=black@0.86:t=fill,"
        f"drawtext=fontfile='{FONT}':text='{subtitle}':x=(w-text_w)/2:y=1053:fontsize=30:"
        f"fontcolor={accent}:borderw=1:bordercolor=black@0.8:expansion=none,"
        "drawbox=x=250:y=1505:w=580:h=58:color=black@0.86:t=fill,"
        f"drawtext=fontfile='{FONT_REGULAR}':text='VÍDEO COMPLETO NO CANAL':x=(w-text_w)/2:y=1517:fontsize=29:"
        "fontcolor=white:borderw=1:bordercolor=black@0.8:expansion=none,"
        "drawbox=x=245:y=1569:w=590:h=64:color=black@0.9:t=fill,"
        f"drawtext=fontfile='{FONT}':text='RADAR DOS GAMES':x=(w-text_w)/2:y=1580:fontsize=36:"
        f"fontcolor={YELLOW}:borderw=1:bordercolor=black@0.9:expansion=none,format=yuv420p[v]"
    )

    sh(
        [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}", "-i", str(src),
            "-t", f"{length:.3f}", "-filter_complex", fc,
            "-map", "[v]", "-map", "0:a?",
            "-af", AUDIO_NORMALIZE,
            "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(out),
        ]
    )
    return accent


def main(src):
    src = Path(src)
    if not src.exists():
        raise SystemExit(f"Arquivo não encontrado: {src}")

    d = duration(src)
    out = Path("output/shorts")
    out.mkdir(parents=True, exist_ok=True)

    cards = pick_cards(load_cards())
    starts = [max(0, d * 0.12), max(0, d * 0.42), max(0, d * 0.72)]

    manifest = {
        "standard": "radar-dos-games-short-reference-2026-10-02-v2-adaptive-accent",
        "source": str(src),
        "resolution": [W, H],
        "fps": FPS,
        "accent_policy": "contextual_from_each_clip; neutral_white_fallback; never_fixed_cyan",
        "shorts": [],
    }

    for i, (start, card) in enumerate(zip(starts, cards), 1):
        remaining = max(1.0, d - start)
        length = min(DEFAULT_LENGTH, remaining)
        dest = out / f"short_{i}.mp4"
        accent = make(src, dest, start, length, card)
        manifest["shorts"].append(
            {
                "index": i,
                "path": str(dest),
                "start": round(start, 3),
                "duration": round(length, 3),
                "title": card.get("title"),
                "subtitle": card.get("subtitle"),
                "accent": accent,
            }
        )

    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python src/shorts.py <master.mp4>")
    main(sys.argv[1])
