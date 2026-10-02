#!/usr/bin/env python3
"""Narração PT-BR gratuita via edge-tts."""
import asyncio
from pathlib import Path
import edge_tts

VOICE = "pt-BR-AntonioNeural"

async def synthesize(text: str, output: str, voice: str = VOICE):
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice, rate="+2%", pitch="+0Hz")
    await communicate.save(output)

if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("text_file"); p.add_argument("output"); p.add_argument("--voice",default=VOICE)
    a=p.parse_args(); asyncio.run(synthesize(Path(a.text_file).read_text(encoding="utf-8"),a.output,a.voice))
