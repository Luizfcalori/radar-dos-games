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
- duração variável: nunca encerrar no meio de uma fala

Importante: a cor ciano da referência original pertencia àquele vídeo/corte e NÃO
faz parte da identidade fixa. A composição é fixa; a cor de destaque é adaptativa.

Mantém compatibilidade com: python src/shorts.py <master.mp4>
Se output/qa.json e output/voice-timings.json existirem, usa títulos e limites
semânticos reais das cenas/falas do Master.
"""

import colorsys
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

W = 1080
H = 1920
FPS = 30
FALLBACK_MIN_LENGTH = 22.0
FALLBACK_MAX_LENGTH = 60.0
SPEECH_TAIL = 0.45
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
    """Extrai uma cor viva do próprio trecho, sem depender de libs/serviços pagos."""
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
        for idx, scene in enumerate(scenes):
            title = scene.get("title") or "DESTAQUE DO VÍDEO"
            subtitle = scene.get("subtitle") or "CONFIRA O CONTEÚDO COMPLETO"
            cards.append({"title": title, "subtitle": subtitle, "scene_index": idx})
        return cards
    except Exception as exc:
        print(f"Aviso: não foi possível ler output/qa.json: {exc}", file=sys.stderr)
        return []


def pick_cards(cards):
    if not cards:
        return [
            {"title": "DESTAQUE DO VÍDEO", "subtitle": "CONFIRA O CONTEÚDO COMPLETO", "scene_index": 0},
            {"title": "VOCÊ PRECISA VER ISSO", "subtitle": "DESTAQUE DO RADAR DOS GAMES", "scene_index": 1},
            {"title": "MAIS UM DESTAQUE", "subtitle": "VÍDEO COMPLETO NO CANAL", "scene_index": 2},
        ]
    picks_file = Path("output/short-picks.json")
    if picks_file.exists():
        try:
            data = json.loads(picks_file.read_text(encoding="utf-8"))
            picks = [int(x) for x in data.get("scene_indexes", [])]
            if len(picks) == 3 and all(0 <= i < len(cards) for i in picks):
                print("SHORT_SEMANTIC_PICKS", picks, flush=True)
                return [cards[i] for i in picks]
        except Exception as exc:
            print(f"Aviso: short-picks.json inválido ({exc}); usando seleção automática.", file=sys.stderr)
    if len(cards) >= 3:
        picks = [0, len(cards) // 2, len(cards) - 1]
        return [cards[i] for i in picks]
    return [cards[i % len(cards)] for i in range(3)]


def load_voice_segments():
    p = Path("output/voice-timings.json")
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("segments", [])
    except Exception as exc:
        print(f"Aviso: voice timings indisponíveis ({exc}).", file=sys.stderr)
        return []


def intro_offset_seconds():
    """Descobre a duração da intro para converter timings do corpo em timings do Master."""
    candidates = [
        Path("output/editorial/intro.mp4"),
        Path("output/intro-normalized.mp4"),
        Path("output/radar-intro-oficial.mp4"),
    ]
    qa = Path("output/qa.json")
    if qa.exists():
        try:
            intro_src = json.loads(qa.read_text(encoding="utf-8")).get("intro_source")
            if intro_src:
                candidates.append(Path(intro_src))
        except Exception:
            pass
    for p in candidates:
        try:
            if p.exists() and p.stat().st_size > 1000:
                return duration(p)
        except Exception:
            continue
    return 0.0


def fallback_natural_length(src: Path, start: float, total: float) -> float:
    """Sem timings estruturados, estende até a primeira pausa natural após o mínimo."""
    max_len = min(FALLBACK_MAX_LENGTH, max(1.0, total - start))
    if max_len <= FALLBACK_MIN_LENGTH:
        return max_len
    cmd = [
        "ffmpeg", "-v", "info", "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{max_len:.3f}",
        "-af", "silencedetect=noise=-38dB:d=0.32", "-f", "null", "-",
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False)
        pauses = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", proc.stderr or "")]
        for pause in pauses:
            if pause >= FALLBACK_MIN_LENGTH:
                return min(max_len, pause + SPEECH_TAIL)
    except Exception as exc:
        print(f"Aviso: detecção de pausa falhou ({exc}).", file=sys.stderr)
    return max_len


def resolve_window(src: Path, total: float, card: dict, fallback_start: float, segments: list, intro_offset: float):
    """Prefere o parágrafo inteiro: o Short termina somente após a fala selecionada acabar."""
    idx = int(card.get("scene_index", -1))
    if 0 <= idx < len(segments):
        seg = segments[idx]
        try:
            start = max(0.0, intro_offset + float(seg["start"]))
            speech_end = min(total, intro_offset + float(seg["end"]))
            end = min(total, speech_end + SPEECH_TAIL)
            if end > start + 1.0:
                return start, end - start, "voice_segment_complete"
        except Exception as exc:
            print(f"Aviso: timing semântico inválido para cena {idx + 1}: {exc}", file=sys.stderr)

    start = max(0.0, min(fallback_start, max(0.0, total - 1.0)))
    length = fallback_natural_length(src, start, total)
    return start, length, "silence_boundary_fallback"


def make(src, out, start, length, card):
    headline = esc(wrapped(card.get("title", ""), 24, 2))
    subtitle = esc(wrapped(card.get("subtitle", ""), 34, 1))
    accent = accent_from_source(Path(src), start + min(length * 0.5, 8.0))

    # O layout é o padrão fixo. A cor de moldura/faixa é contextual ao trecho.
    # A mídia central sempre usa contain/decrease: nada importante é cortado.
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
        "[canvas][fg]overlay=x='(W-w)/2+5*sin(t*0.70)':y='575+(430-h)/2+4*cos(t*0.55)'[tmp];"
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
    source_credit=Path(str(src)+'.music.json')
    if source_credit.exists():
        Path(str(out)+'.music.json').write_bytes(source_credit.read_bytes())
    return accent


def main(src):
    src = Path(src)
    if not src.exists():
        raise SystemExit(f"Arquivo não encontrado: {src}")

    d = duration(src)
    out = Path("output/shorts")
    out.mkdir(parents=True, exist_ok=True)

    cards = pick_cards(load_cards())
    fallback_starts = [max(0, d * 0.12), max(0, d * 0.42), max(0, d * 0.72)]
    segments = load_voice_segments()
    intro_offset = intro_offset_seconds()

    manifest = {
        "standard": "radar-dos-games-shorts-premium-v3",
        "premium_version": "PREMIUM_V3",
        "hook_policy": "headline_visible_from_first_frame; semantic_scene_pick; visual_motion_continuous",
        "source": str(src),
        "resolution": [W, H],
        "fps": FPS,
        "accent_policy": "contextual_from_each_clip; neutral_white_fallback; never_fixed_cyan",
        "speech_end_policy": "complete_voice_segment_when_available; otherwise_first_natural_silence; never_fixed_22s",
        "motion_policy": "subtle_non_destructive_vertical_reframe",
        "intro_offset_seconds": round(intro_offset, 3),
        "shorts": [],
    }

    for i, (fallback_start, card) in enumerate(zip(fallback_starts, cards), 1):
        start, length, boundary_policy = resolve_window(src, d, card, fallback_start, segments, intro_offset)
        dest = out / f"short_{i}.mp4"
        accent = make(src, dest, start, length, card)
        manifest["shorts"].append(
            {
                "index": i,
                "path": str(dest),
                "start": round(start, 3),
                "duration": round(length, 3),
                "boundary_policy": boundary_policy,
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
