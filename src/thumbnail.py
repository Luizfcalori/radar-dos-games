#!/usr/bin/env python3
"""Gera thumbnail profissional 1280x720 a partir do próprio Master."""
import re
import subprocess
import sys
from pathlib import Path

W, H = 1280, 720
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


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
    # Thumbnail precisa ser curta: remove caudas genéricas quando possível.
    title = re.sub(r"(?i):\s*(lançamento ganha novos detalhes|veja o que foi confirmado oficialmente)$", "", title)
    return title[:58].rstrip(" -:|")


def wrap_title(title: str, max_chars: int = 22, max_lines: int = 3) -> str:
    words = clean_title(title).upper().split()
    lines, current = [], []
    for word in words:
        trial = " ".join(current + [word])
        if current and len(trial) > max_chars:
            lines.append(" ".join(current))
            current = [word]
            if len(lines) >= max_lines - 1:
                break
        else:
            current.append(word)
    remaining_start = sum(len(x.split()) for x in lines)
    remaining = words[remaining_start:]
    if len(lines) < max_lines and remaining:
        last = " ".join(remaining)
        if len(last) > max_chars + 6:
            last = last[: max_chars + 3].rstrip() + "…"
        lines.append(last)
    return "\n".join(lines[:max_lines]) or "RADAR DOS GAMES"


def main():
    if len(sys.argv) != 4:
        raise SystemExit("uso: thumbnail.py VIDEO TITULO SAIDA.jpg")

    video, title, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.parent.mkdir(parents=True, exist_ok=True)
    title_file = out.with_suffix(".title.txt")
    title_file.write_text(wrap_title(title), encoding="utf-8")

    total = duration(video)
    seek = 8.0 if total <= 0 else min(max(total * 0.30, 8.0), max(1.0, total - 1.0))

    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        "eq=brightness=-0.08:saturation=1.12,"
        "drawbox=x=0:y=0:w=1280:h=720:color=black@0.10:t=fill,"
        "drawbox=x=0:y=0:w=1280:h=74:color=0x020A23@0.96:t=fill,"
        "drawbox=x=0:y=365:w=1280:h=355:color=black@0.66:t=fill,"
        "drawbox=x=48:y=410:w=12:h=220:color=0x00DCC8@0.98:t=fill,"
        f"drawtext=fontfile='{FONT_BOLD}':text='RADAR DOS GAMES':x=48:y=22:fontsize=32:fontcolor=white:borderw=2:bordercolor=black@0.65,"
        f"drawtext=fontfile='{FONT_BOLD}':textfile='{title_file.as_posix()}':x=82:y=405:fontsize=66:line_spacing=10:fontcolor=white:borderw=3:bordercolor=black@0.82,"
        f"drawtext=fontfile='{FONT}':text='NOTÍCIA • GAMEPLAY • CONTEXTO':x=84:y=646:fontsize=25:fontcolor=0xF4FF00:borderw=1:bordercolor=black@0.8"
    )

    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{seek:.3f}", "-i", video,
            "-frames:v", "1", "-vf", vf, "-q:v", "2", str(out),
        ],
        check=True,
    )

    if not out.exists() or out.stat().st_size < 20_000:
        raise RuntimeError("QUALITY_BLOCK: thumbnail não foi gerada corretamente")

    probe = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(out)],
        text=True,
    ).strip()
    if probe != "1280x720":
        raise RuntimeError(f"QUALITY_BLOCK: thumbnail em resolução incorreta: {probe}")
    print(str(out))


if __name__ == "__main__":
    main()
