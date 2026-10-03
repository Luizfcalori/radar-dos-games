#!/usr/bin/env python3
"""Narra exatamente o roteiro fornecido, sem reescrever, expandir ou inserir texto interno."""
import argparse
import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts

VOICE = "pt-BR-ThalitaNeural"


def duration(path: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path)
    ], text=True).strip())


async def synthesize_one(text: str, output: Path, voice: str):
    output.parent.mkdir(parents=True, exist_ok=True)
    await edge_tts.Communicate(text, voice, rate="+0%", pitch="+0Hz").save(str(output))


async def main_async(text_file: Path, output: Path, voice: str, segments_json: Path):
    text = text_file.read_text(encoding="utf-8").strip()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        raise RuntimeError("Nenhum bloco de narração encontrado")

    seg_dir = output.parent / "voice_segments_exact"
    seg_dir.mkdir(parents=True, exist_ok=True)
    segments = []
    cursor = 0.0

    for i, paragraph in enumerate(paragraphs, 1):
        seg = seg_dir / f"segment_{i:02d}.mp3"
        await synthesize_one(paragraph, seg, voice)
        d = duration(seg)
        segments.append({
            "index": i,
            "start": round(cursor, 3),
            "end": round(cursor + d, 3),
            "duration": round(d, 3),
            "text": paragraph,
            "file": str(seg),
        })
        cursor += d

    concat_file = seg_dir / "concat.txt"
    concat_file.write_text("".join(
        f"file '{Path(s['file']).resolve()}'\n" for s in segments
    ), encoding="utf-8")
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), "-c", "copy", str(output)
    ], check=True)

    payload = {
        "voice": voice,
        "segments": segments,
        "duration": round(duration(output), 3),
        "source": "verbatim_script",
        "editorial_revision": "NONE_VERBATIM_ONLY",
    }
    segments_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"voice": voice, "segments": len(segments), "duration": payload["duration"]}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("text_file")
    p.add_argument("output")
    p.add_argument("--voice", default=VOICE)
    p.add_argument("--segments-json", required=True)
    a = p.parse_args()
    asyncio.run(main_async(Path(a.text_file), Path(a.output), a.voice, Path(a.segments_json)))


if __name__ == "__main__":
    main()
