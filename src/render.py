#!/usr/bin/env python3
"""Renderizador editorial Radar dos Games: intro real + cenas semânticas + cards contextuais."""
import json
import subprocess
import sys
from pathlib import Path

FPS = 30
W = 1920
H = 1080
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


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
            result[pos] = {"index": pos, "path": item, "type": "image" if Path(item).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} else "video"}
        else:
            result[int(item.get("index", pos))] = item
    return result


def render_piece(asset, duration: float, dest: Path, card=None, piece_no=0):
    path = Path(asset["path"])
    typ = asset.get("type", "image")
    if not path.exists():
        raise RuntimeError(f"Asset ausente: {path}")

    # Movimento discreto e contínuo para imagens oficiais; vídeos são tratados como mídia em movimento.
    if typ == "image" or path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        zoom_step = "0.00042" if piece_no % 2 else "0.00034"
        base = (
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},"
            f"zoompan=z='min(zoom+{zoom_step},1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},"
            "format=yuv420p"
        )
        input_args = ["-loop", "1", "-i", str(path)]
    else:
        base = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p"
        input_args = ["-stream_loop", "-1", "-i", str(path)]

    vf = base
    # Marca discreta: nunca compete com o jogo.
    vf += (
        f",drawtext=fontfile='{FONT}':text='RADAR DOS GAMES':"
        "x=w-tw-42:y=30:fontsize=24:fontcolor=white@0.72:borderw=1:bordercolor=black@0.55:expansion=none"
    )

    if card:
        show_end = max(1.5, min(6.8, duration - 0.35))
        title = esc(card.get("title", ""))
        subtitle = esc(card.get("subtitle", ""))
        enable = f"between(t,0.65,{show_end:.3f})"
        vf += f",drawbox=x=66:y=h-226:w=1160:h=132:color=black@0.68:t=fill:enable='{enable}'"
        vf += f",drawbox=x=66:y=h-226:w=9:h=132:color=0x00F5B8@0.95:t=fill:enable='{enable}'"
        vf += (
            f",drawtext=fontfile='{FONT}':text='{title}':x=104:y=h-207:fontsize=40:"
            f"fontcolor=white:borderw=1:bordercolor=black@0.7:expansion=none:enable='{enable}'"
        )
        if subtitle:
            vf += (
                f",drawtext=fontfile='{FONT}':text='{subtitle}':x=104:y=h-151:fontsize=25:"
                f"fontcolor=0x63EFFF:borderw=1:bordercolor=black@0.7:expansion=none:enable='{enable}'"
            )

    sh(
        [
            "ffmpeg", "-y", "-v", "error", *input_args, "-t", f"{duration:.3f}", "-vf", vf,
            "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", str(dest),
        ]
    )


def normalize_intro(src: Path, dest: Path):
    sh(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(src),
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1,format=yuv420p",
            "-af", "aresample=48000,pan=stereo|c0=c0|c1=c0",
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
        indices = [int(x) for x in scene.get("media_indices", [])]
        if not indices:
            raise RuntimeError(f"Cena {scene_no} sem mídia contextual")
        missing = [x for x in indices if x not in assets]
        if missing:
            raise RuntimeError(f"Cena {scene_no} aponta para assets ausentes: {missing}")

        per_piece = duration / len(indices)
        scene_piece_paths = []
        for j, idx in enumerate(indices):
            piece_duration = duration - per_piece * j if j == len(indices) - 1 else per_piece
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
                "voice_duration": round(duration, 3),
                "media_indices": indices,
                "title": scene.get("title"),
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
            "-map", "0:v:0", "-map", "1:a:0", "-shortest", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "192k", "-ar", "48000", "-ac", "2", str(body),
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
        "intro_source": str(intro),
        "intro_audio_preserved": True,
        "voice": timings.get("voice"),
        "semantic_timing_source": timings.get("source"),
        "scenes": qa_scenes,
        "probe": json.loads(probe),
        "legacy_ace_input": False,
    }
    Path("output/qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"master": str(out), "scenes": len(qa_scenes), "intro": str(intro)}, ensure_ascii=False))


if __name__ == "__main__":
    render(sys.argv[1])
