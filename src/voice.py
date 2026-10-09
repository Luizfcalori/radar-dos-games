#!/usr/bin/env python3
"""Narração PT-BR gratuita via edge-tts, com timings reais por parágrafo.

Padrão editorial do Radar dos Games:
- a voz NÃO acrescenta parágrafos genéricos para aumentar duração;
- preserva o texto editorial específico de cada jogo;
- remove repetições acidentais entre cenas;
- limpa linguagem interna de produção;
- varia o CTA de forma determinística entre vídeos;
- mantém a quantidade de blocos/cenas do roteiro original.
"""
import argparse
import asyncio
import hashlib
import json
import re
import subprocess
from difflib import SequenceMatcher
from pathlib import Path

import edge_tts

VOICE = "pt-BR-ThalitaMultilingualNeural"


CTA_OPTIONS = [
    (
        "Se esse tipo de conteúdo te ajuda a acompanhar os lançamentos sem perder o que realmente importa, "
        "se inscreva no Radar dos Games e ative o sininho. E conta nos comentários o que mais chamou sua atenção neste anúncio."
    ),
    (
        "Quer continuar acompanhando novidades de games com contexto e fonte confiável? "
        "Deixe o like, se inscreva no Radar dos Games e diga nos comentários qual detalhe deste jogo você quer ver mais de perto."
    ),
    (
        "O Radar dos Games continua de olho nas próximas informações oficiais. "
        "Se curtiu o vídeo, se inscreva no canal, deixe o like e comenta qual lançamento você quer ver por aqui na sequência."
    ),
    (
        "Se você gosta de acompanhar cada novidade sem rumor tratado como fato, já sabe: "
        "se inscreva no Radar dos Games, ative as notificações e compartilhe nos comentários sua expectativa para este jogo."
    ),
    (
        "A cobertura continua assim que surgirem novas informações confirmadas. "
        "Se inscreva no Radar dos Games, deixe o like e participa nos comentários com a sua leitura desse anúncio."
    ),
]


def _clean_internal_language(text: str) -> str:
    """Evita que termos de bastidor virem fala da apresentadora."""
    replacements = [
        (r"(?i)al[eé]m do an[uú]ncio, o radar prioriza.*?(?=\.|$)", "O material oficial divulgado ajuda a entender melhor o anúncio"),
        (r"(?i)assim, o v[ií]deo tenta mostrar.*?(?=\.|$)", "Assim, fica mais fácil visualizar o que foi apresentado pela empresa"),
        (r"(?i)sem depender s[oó] de cards ou textos na tela", "com contexto visual e informação confirmada"),
        (r"(?i)\broteiro\b", "resumo"),
        (r"(?i)\bpipeline\b", "processo"),
        (r"(?i)\bcards?\b", "destaques"),
    ]
    value = text
    for pattern, repl in replacements:
        value = re.sub(pattern, repl, value)
    return re.sub(r"\s+", " ", value).strip()


def _sentence_key(sentence: str) -> str:
    value = sentence.lower()
    value = re.sub(r"[^a-z0-9áàâãéêíóôõúüç ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _is_near_duplicate(key: str, previous: list[str]) -> bool:
    """Bloqueia frases longas essencialmente iguais sem punir nomes repetidos do jogo."""
    if len(key) < 45:
        return key in previous
    for old in previous:
        if key == old:
            return True
        if len(old) >= 45 and SequenceMatcher(None, key, old).ratio() >= 0.91:
            return True
    return False


def _dedupe_paragraphs(paragraphs: list[str]) -> list[str]:
    seen: list[str] = []
    cleaned: list[str] = []

    for paragraph in paragraphs:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]
        kept: list[str] = []
        for sentence in sentences:
            key = _sentence_key(sentence)
            if not key or _is_near_duplicate(key, seen):
                continue
            kept.append(sentence)
            seen.append(key)

        # Preserva a estrutura por cenas. Em caso extremo, mantém o bloco original
        # em vez de reduzir a quantidade de cenas do render.
        cleaned.append(" ".join(kept).strip() or paragraph)

    return cleaned


def _choose_cta(seed_text: str) -> str:
    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()
    return CTA_OPTIONS[digest[0] % len(CTA_OPTIONS)]


def _already_has_cta(text: str) -> bool:
    low = text.lower()
    signals = ("se inscre", "inscreva", "deixe o like", "ativa o sininho", "ative o sininho")
    return any(signal in low for signal in signals)


def prepare_narration(text: str) -> str:
    """Limpa e desduplica o roteiro sem inserir texto genérico de preenchimento."""
    paragraphs = [_clean_internal_language(p.strip()) for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        raise RuntimeError("Nenhum bloco de narração encontrado")

    paragraphs = _dedupe_paragraphs(paragraphs)

    # O encerramento mantém o texto específico do jogo. Só adiciona um CTA curto
    # e variável quando o próprio roteiro ainda não trouxe chamada ao público.
    if not _already_has_cta(paragraphs[-1]):
        paragraphs[-1] = f"{paragraphs[-1]} {_choose_cta(text)}".strip()

    return "\n\n".join(paragraphs)


async def synthesize_one(text: str, output: Path, voice: str):
    output.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice, rate="+0%", pitch="+0Hz")
    await communicate.save(str(output))


def duration(path: Path) -> float:
    return float(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            text=True,
        ).strip()
    )


def _sentence_timings(text: str, start: float, duration_seconds: float, paragraph_index: int):
    """Estima limites de frase sem re-sintetizar a voz.

    A duração real do parágrafo continua vindo do MP3 da Thalita. As sentenças
    recebem fatias proporcionais ao conteúdo + pausa de pontuação, suficientes
    para dirigir cortes visuais sem degradar a prosódia.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        sentences = [text.strip()]
    weights = []
    for s in sentences:
        words = max(1, len(re.findall(r"\w+", s, re.UNICODE)))
        pause = 2.2 if s.endswith(("!", "?")) else 1.5
        weights.append(words + pause)
    total = sum(weights) or 1.0
    cursor = float(start)
    result = []
    for i, (s, w) in enumerate(zip(sentences, weights), 1):
        share = duration_seconds * (w / total)
        end = start + duration_seconds if i == len(sentences) else cursor + share
        result.append({
            "paragraph": paragraph_index,
            "sentence": i,
            "start": round(cursor, 3),
            "end": round(end, 3),
            "duration": round(end - cursor, 3),
            "text": s,
        })
        cursor = end
    return result


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
    phrases = []
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
        phrases.extend(_sentence_timings(paragraph, cursor, d, i))
        cursor += d

    concat_file = seg_dir / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{Path(s['file']).resolve()}'\n" for s in segments),
        encoding="utf-8",
    )
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(out)],
        check=True,
    )

    payload = {
        "voice": voice,
        "segments": segments,
        "phrases": phrases,
        "duration": round(duration(out), 3),
        "source": "paragraph_boundaries+sentence_estimates",
        "editorial_revision": "natural_script+cross_scene_dedupe+varied_cta+no_canned_expansion",
    }
    Path(segments_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"voice": voice, "segments": len(segments), "duration": payload["duration"]}, ensure_ascii=False))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("text_file")
    p.add_argument("output")
    p.add_argument("--voice", default=VOICE)
    p.add_argument("--segments-json")
    p.add_argument("--prepared", action="store_true", help="Narrar o roteiro já revisado e decupado sem o reescrever")
    a = p.parse_args()
    text_path = Path(a.text_file)
    original = text_path.read_text(encoding="utf-8")
    if a.prepared:
        if not original.strip() or not original.endswith("\n"):
            raise RuntimeError("QUALITY_BLOCK: roteiro media-first final ausente ou sem quebra de linha")
        text = original.rstrip("\n")
    else:
        text = prepare_narration(original)
        text_path.write_text(text + "\n", encoding="utf-8")
    asyncio.run(synthesize(text, a.output, a.voice, a.segments_json))
