#!/usr/bin/env python3
"""Narração PT-BR gratuita via edge-tts, com timings reais por parágrafo.

Além de sintetizar a voz, este módulo faz uma última revisão editorial automática:
- mantém exatamente a mesma quantidade de blocos/cenas;
- amplia cada bloco para um Master mais completo;
- remove linguagem interna de produção do texto narrado;
- encerra sempre com CTA natural de inscrição, like e sino.
"""
import argparse
import asyncio
import json
import re
import subprocess
from pathlib import Path

import edge_tts

VOICE = "pt-BR-AntonioNeural"


EXPANSIONS = [
    (
        "O ponto mais importante é separar novidade concreta de expectativa. Quando uma informação aparece em canal oficial, ela ganha peso, mas ainda vale observar exatamente o que foi confirmado, o que ficou para depois e o que não foi detalhado. "
        "É essa diferença que evita transformar uma boa notícia em promessa que o próprio estúdio nunca fez."
    ),
    (
        "Na prática, vale olhar para esses elementos pensando no jogador: o que muda no conteúdo, na forma de jogar e no motivo para acompanhar esse lançamento ou atualização. "
        "Mesmo quando o anúncio parece simples, detalhes de mecânica, campanha, progressão, combate ou estrutura podem mudar bastante a experiência final e merecem atenção."
    ),
    (
        "Outro cuidado é não preencher lacunas com rumor. Se a publicação não explica um ponto, o mais correto é tratar aquilo como informação ainda aberta. "
        "Isso também ajuda a acompanhar futuras atualizações com clareza, porque fica fácil perceber o que realmente mudou entre o anúncio de hoje e as próximas comunicações oficiais."
    ),
    (
        "Para quem acompanha o jogo em diferentes plataformas, esse detalhe faz diferença. Versão, disponibilidade, recursos específicos e possíveis diferenças entre edições podem alterar a decisão de compra ou de retorno ao game. "
        "Por isso, o cenário fica mais claro quando plataforma e conteúdo confirmado são analisados juntos, sem assumir suporte que ainda não foi anunciado."
    ),
    (
        "Também é importante ler qualquer data como o estado atual do planejamento. Desenvolvimento de jogos pode sofrer ajustes, então uma janela anunciada serve como referência até que a própria empresa publique algo diferente. "
        "Se houver mudança, atraso, antecipação ou nova edição, o que vale passa a ser a atualização oficial mais recente."
    ),
    (
        "Para quem já joga ou está pensando em entrar agora, a pergunta principal é simples: essa novidade muda alguma coisa relevante na experiência? "
        "Pode ser um novo conteúdo, uma melhoria, uma expansão da história, um recurso extra ou apenas mais contexto sobre o projeto. O valor da notícia está justamente em entender esse impacto sem exagerar o anúncio."
    ),
    (
        "O material oficial divulgado junto com a notícia ajuda a colocar tudo em contexto visual. Gameplay, trailer e imagens permitem conferir direção de arte, cenários, personagens e situações mostradas pela própria empresa. "
        "Ainda assim, o que aparece na tela deve ser lido junto com o texto oficial, porque uma imagem isolada nem sempre explica como aquele elemento funciona no jogo completo."
    ),
]


CTA = (
    "E esse foi o Radar dos Games de hoje. Se você curte notícias de games sem enrolação, com fonte oficial e contexto, se inscreva no canal, deixe o like neste vídeo e ative o sininho para não perder os próximos lançamentos e novidades. "
    "E comenta aqui embaixo o que você achou desta notícia e qual jogo você quer ver no próximo Radar. A gente se encontra no próximo vídeo."
)


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


def prepare_narration(text: str) -> str:
    """Mantém o número de parágrafos, amplia o conteúdo e força um CTA final."""
    paragraphs = [_clean_internal_language(p.strip()) for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        raise RuntimeError("Nenhum bloco de narração encontrado")

    polished = []
    for i, paragraph in enumerate(paragraphs):
        if i == len(paragraphs) - 1:
            # O último bloco nunca fala de processo interno: fecha para o público.
            game_match = re.search(r"(?i)radar dos games sobre\s+(.+?)(?:\.|$)", paragraph)
            prefix = ""
            if game_match:
                game = game_match.group(1).strip(" .")
                prefix = f"Para fechar, o principal sobre {game} é ficar com o que já foi confirmado oficialmente e acompanhar as próximas atualizações da empresa. "
            polished.append(prefix + CTA)
            continue

        extra = EXPANSIONS[i % len(EXPANSIONS)]
        polished.append(f"{paragraph} {extra}")

    return "\n\n".join(polished)


async def synthesize_one(text: str, output: Path, voice: str):
    output.parent.mkdir(parents=True, exist_ok=True)
    # Ritmo natural e ligeiramente mais calmo que os testes iniciais.
    communicate = edge_tts.Communicate(text, voice, rate="+0%", pitch="+0Hz")
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
        "duration": round(duration(out), 3),
        "source": "paragraph_boundaries",
        "editorial_revision": "expanded_master+no_internal_script+subscriber_cta",
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
    text_path = Path(a.text_file)
    text = prepare_narration(text_path.read_text(encoding="utf-8"))
    # O artefato de roteiro passa a refletir exatamente o que foi narrado.
    text_path.write_text(text + "\n", encoding="utf-8")
    asyncio.run(synthesize(text, a.output, a.voice, a.segments_json))
