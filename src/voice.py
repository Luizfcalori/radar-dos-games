#!/usr/bin/env python3
"""Narração PT-BR gratuita via edge-tts, com timings reais por parágrafo."""
import argparse
import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts

VOICE = "pt-BR-AntonioNeural"


async def synthesize_one(text: str, output: Path, voice: str):
    output.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice, rate="+2%", pitch="+0Hz")
    await communicate.save(str(output))


def duration(path: Path) -> float:
    return float(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            text=True,
        ).strip()
    )


async def synthesize(text: str, output: str, voice: str = VOICE, segments_json: str | None = None):
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not segments_json:
        await synthesize_one(text, out, voice)
        return

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        raise RuntimeError("Nenhum bloco de narração encontrado")

    seg_dir = out.parent / "voice_segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    segments = []
    cursor = 0.0

    for i, paragraph in enumerate(paragraphs, 1):
        seg = seg_dir / f"segment_{i:02d}.mp3"
        await synthesize_one(paragraph, seg, voice)
        d = duration(seg)
        segments.append(
            {
                "index": i,
                "start": round(cursor, 3),
                "end": round(cursor + d, 3),
                "duration": round(d, 3),
                "text": paragraph,
                "file": str(seg),
            }
        )
        cursor += d

    concat_file = seg_dir / "concat.txt"
    concat_file.write_text("".join(f"file '{s['file']}'\n" for s in segments), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(out)],
        check=True,
    )

    payload = {
        "voice": voice,
        "segments": segments,
        "duration": round(duration(out), 3),
        "source": "paragraph_boundaries",
    }
    Path(segments_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"voice": voice, "segments": len(segments), "duration": payload["duration"]}, ensure_ascii=False))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("text_file")
    p.add_argument("output")
    p.add_argument("--voice", default=VOICE)
    p.add_argument("--segments-json")
    a = p.parse_args()
    text = Path(a.text_file).read_text(encoding="utf-8")
    asyncio.run(synthesize(text, a.output, a.voice, a.segments_json))
