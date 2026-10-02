#!/usr/bin/env python3
"""Renderizador editorial Radar dos Games no padrão visual aprovado."""
import json
import subprocess
import sys
from pathlib import Path

FPS = 30
W = 1920
H = 1080
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Padrão oficial aprovado no Master Ace Combat 8 (02/10/2026).
WATERMARK_X = "w-tw-44"
WATERMARK_Y = 30
WATERMARK_SIZE = 24

CARD_X = 62
CARD_Y = 850
CARD_W = 1240
CARD_H = 138
CARD_ACCENT_W = 10
CARD_BG = "black@0.68"
CARD_ACCENT = "0x00DCC8@0.96"
CARD_IN = 0.45
CARD_MAX_SECONDS = 5.8
CARD_END_MARGIN = 0.15

TITLE_X = 102
TITLE_Y = 869
TITLE_SIZE = 40
SUBTITLE_X = 102
SUBTITLE_Y = 927
SUBTITLE_SIZE = 25
SUBTITLE_COLOR = "0x7FE8FF"

AUDIO_NORMALIZE = "loudnorm=I=-16:LRA=7:TP=-1.5"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def sh(cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True)


def esc(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def asset_map(items):
    result = {}
    for pos, item in enumerate(items, 1):
        if isinstance(item, str):
            path = Path(item)
            result[pos] = {
                "index": pos,
                "path": item,
                "type": "image" if path.suffix.lower() in IMAGE_EXTENSIONS else "video",
            }
        else:
            result[int(item.get("index", pos))] = item
    return result


def is_video(asset) -> bool:
    path = Path(asset["path"])
    return asset.get("type", "image") != "image" and path.suffix.lower() not in IMAGE_EXTENSIONS


def ordered_scene_indices(indices, assets):
    """Gameplay/vídeo contextual vem antes da imagem, preservando ordem dentro de cada grupo."""
    return sorted(indices, key=lambda idx: 0 if is_video(assets[idx]) else 1)


def scene_sequence(indices, cuts=4):
    """Cadência padrão: quatro cortes por bloco, ciclando a mídia disponível."""
    return [indices[i % len(indices)] for i in range(cuts)]


def render_piece(asset, duration: float, dest: Path, card=None, piece_no=0):
    path = Path(asset["path"])
    typ = asset.get("type", "image")
    if not path.exists():
        raise RuntimeError(f"Asset ausente: {path}")

    # Regra permanente de enquadramento: a mídia principal fica SEMPRE 100% visível.
    # O espaço excedente é preenchido com a própria mídia ampliada/desfocada ao fundo,
    # evitando crop destrutivo em personagem, HUD, texto ou logo.
    if typ == "image" or path.suffix.lower() in IMAGE_EXTENSIONS:
        input_args = ["-loop", "1", "-i", str(path)]
    else:
        input_args = ["-stream_loop", "-1", "-i", str(path)]

    base = (
        f"[0:v]fps={FPS},split=2[bg0][fg0];"
        f"[bg0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        "boxblur=28:14,eq=brightness=-0.18:saturation=0.88[bg];"
        f"[fg0]scale={W}:{H}:force_original_aspect_ratio=decrease,setsar=1[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
    )

    filters = [
        (
            f"drawtext=fontfile='{FONT}':text='RADAR DOS GAMES':"
            f"x={WATERMARK_X}:y={WATERMARK_Y}:fontsize={WATERMARK_SIZE}:"
            "fontcolor=white@0.72:borderw=1:bordercolor=black@0.55:expansion=none"
        )
    ]

    if card:
        show_end = max(1.2, min(duration - CARD_END_MARGIN, CARD_MAX_SECONDS))
        title = esc(card.get("title", ""))
        subtitle = esc(card.get("subtitle", ""))
        enable = f"between(t,{CARD_IN:.2f},{show_end:.3f})"

        # A sombra/faixa pertence ao mesmo bloco do texto. Não mover separadamente.
        filters.extend(
            [
                f"drawbox=x={CARD_X}:y={CARD_Y}:w={CARD_W}:h={CARD_H}:color={CARD_BG}:t=fill:enable='{enable}'",
                f"drawbox=x={CARD_X}:y={CARD_Y}:w={CARD_ACCENT_W}:h={CARD_H}:color={CARD_ACCENT}:t=fill:enable='{enable}'",
                (
                    f"drawtext=fontfile='{FONT}':text='{title}':x={TITLE_X}:y={TITLE_Y}:fontsize={TITLE_SIZE}:"
                    f"fontcolor=white:borderw=2:bordercolor=black@0.65:expansion=none:enable='{enable}'"
                ),
            ]
        )
        if subtitle:
            filters.append(
                f"drawtext=fontfile='{FONT}':text='{subtitle}':x={SUBTITLE_X}:y={SUBTITLE_Y}:fontsize={SUBTITLE_SIZE}:"
                f"fontcolor={SUBTITLE_COLOR}:borderw=1:bordercolor=black@0.7:expansion=none:enable='{enable}'"
            )

    fc = base + ",".join(filters) + ",format=yuv420p[v]"

    sh(
        [
            "ffmpeg", "-y", "-v", "error", *input_args, "-t", f"{duration:.3f}",
            "-filter_complex", fc, "-map", "[v]",
            "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", str(dest),
        ]
    )


def normalize_intro(src: Path, dest: Path):
    # A intro oficial também é preservada integralmente; sem cortar bordas.
    sh(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(src),
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,fps={FPS},setsar=1,format=yuv420p",
            "-af", "aresample=48000",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(dest),
        ]
    )


def render(manifest_path):
    m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    out = Path(m.get("output", "output/master.mp4"))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / "editorial"
    tmp.mkdir(exist_ok=True)

    intro = Path(m["intro"])
    if not intro.exists():
        raise RuntimeError("QUALITY_BLOCK: intro oficial real ausente")

    timings = json.loads(Path(m["voice_timings"]).read_text(encoding="utf-8"))
    voice_segments = timings.get("segments", [])
    scenes = m.get("scenes", [])
    if len(voice_segments) != len(scenes):
        raise RuntimeError(f"QUALITY_BLOCK: {len(voice_segments)} blocos de voz para {len(scenes)} cenas")

    assets = asset_map(m.get("assets") or m.get("clips") or [])
    pieces = []
    qa_scenes = []

    for scene_no, (timing, scene) in enumerate(zip(voice_segments, scenes), 1):
        duration = float(timing["duration"])
        raw_indices = [int(x) for x in scene.get("media_indices", [])]
        if not raw_indices:
            raise RuntimeError(f"Cena {scene_no} sem mídia contextual")
        missing = [x for x in raw_indices if x not in assets]
        if missing:
            raise RuntimeError(f"Cena {scene_no} aponta para assets ausentes: {missing}")

        indices = ordered_scene_indices(raw_indices, assets)
        sequence = scene_sequence(indices, cuts=4)
        per_piece = duration / len(sequence)
        scene_piece_paths = []

        for j, idx in enumerate(sequence):
            piece_duration = duration - per_piece * j if j == len(sequence) - 1 else per_piece
            p = tmp / f"scene_{scene_no:02d}_{j+1:02d}.mp4"
            render_piece(
                assets[idx],
                piece_duration,
                p,
                card={"title": scene.get("title", ""), "subtitle": scene.get("subtitle", "")} if j == 0 else None,
                piece_no=scene_no + j,
            )
            pieces.append(p)
            scene_piece_paths.append(str(p))

        qa_scenes.append(
            {
                "scene": scene_no,
                "paragraph": scene.get("paragraph"),
                "voice_start": timing.get("start"),
                "voice_end": timing.get("end"),
                "voice_duration": round(duration, 3),
                "media_indices_original": raw_indices,
                "media_indices_priority": indices,
                "sequence": sequence,
                "gameplay_first": any(is_video(assets[idx]) for idx in indices),
                "title": scene.get("title"),
                "subtitle": scene.get("subtitle"),
                "pieces": scene_piece_paths,
            }
        )

    concat_visuals = tmp / "visuals.txt"
    concat_visuals.write_text("".join(f"file '{p.resolve()}'\n" for p in pieces), encoding="utf-8")
    visuals = tmp / "body_visuals.mp4"
    sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_visuals), "-c", "copy", str(visuals)])

    body = tmp / "body_av.mp4"
    sh(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(visuals), "-i", m["voice"],
            "-map", "0:v:0", "-map", "1:a:0", "-shortest", "-c:v", "copy", "-af", AUDIO_NORMALIZE,
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(body),
        ]
    )

    intro_norm = tmp / "intro.mp4"
    normalize_intro(intro, intro_norm)

    final_list = tmp / "final.txt"
    final_list.write_text(f"file '{intro_norm.resolve()}'\nfile '{body.resolve()}'\n", encoding="utf-8")
    sh(
        [
            "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(final_list),
            "-c", "copy", "-movflags", "+faststart", str(out),
        ]
    )

    probe = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-show_entries", "stream=codec_type,width,height,r_frame_rate", "-of", "json", str(out)],
        text=True,
    )
    qa = {
        "master": str(out),
        "standard": "radar-dos-games-ace-combat-8-approved-v2-full-frame",
        "intro_source": str(intro),
        "intro_audio_preserved": True,
        "voice": timings.get("voice"),
        "semantic_timing_source": timings.get("source"),
        "framing_policy": "full_source_visible; blurred_background_fill; no_destructive_crop",
        "scenes": qa_scenes,
        "card_style": {
            "x": CARD_X, "y": CARD_Y, "w": CARD_W, "h": CARD_H,
            "title_x": TITLE_X, "title_y": TITLE_Y,
            "subtitle_x": SUBTITLE_X, "subtitle_y": SUBTITLE_Y,
            "shadow_attached_to_text": True,
        },
        "probe": json.loads(probe),
    }
    Path("output/qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"master": str(out), "scenes": len(qa_scenes), "intro": str(intro)}, ensure_ascii=False))


if __name__ == "__main__":
    render(sys.argv[1])
