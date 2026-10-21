#!/usr/bin/env python3
"""Rebuild Saros audio and Shorts from the already-rendered private artifact."""
import json
import math
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("output")
SHORTS = OUT / "shorts"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MUSIC = Path("assets/audio/radar-bed.mp3")
MASTER_TITLES = [
    "ZENITH - NOVAS FORMAS DE JOGAR",
    "MAIS TEMPO PARA REAGIR",
    "AUTO-FIRE E MIRA POR MOVIMENTO",
    "10 NOVOS MODIFICADORES DE PROTECAO",
    "NEW GAME+ - ECLIPSE LAYERS",
    "25 TRIALS PARA COMBINAR",
    "COROA DOURADA E 12 VISIONS",
    "OVERLORD RUSH - DESAFIO DE CHEFES",
    "TRES MODOS DE CHEFES",
    "OITO CHEFES EM SEQUENCIA",
    "PLACAR GLOBAL POR ARMA",
    "ATUALIZACAO GRATUITA",
    "QUAL NOVIDADE VOCE VAI TESTAR?",
]
SHORT_CONFIG = [
    {
        "start": 51.2, "duration": 18.6,
        "voice": SHORTS / "short_1_voice.mp3",
        "title": "MODIFICADORES DE PROTECAO",
        "cta": "VOCE TESTARIA ESSE MODIFICADOR?",
        "filename": SHORTS / "short_1.mp4",
    },
    {
        "start": 130.5, "duration": 17.5,
        "voice": SHORTS / "short_2_voice.mp3",
        "title": "NEW GAME+ EM CAMADAS",
        "cta": "VOCE ENCARARIA ESSE DESAFIO?",
        "filename": SHORTS / "short_2.mp4",
    },
    {
        "start": 154.3, "duration": 20.3,
        "voice": SHORTS / "short_3_voice.mp3",
        "title": "OITO CHEFES EM SEQUENCIA",
        "cta": "QUAL MODO VOCE ESCOLHERIA?",
        "filename": SHORTS / "short_3.mp4",
    },
]
SHORT_TITLES = [
    "Saros: modificadores de proteção explicados #Shorts",
    "Saros: New Game+ com Eclipse Layers #Shorts",
    "Saros: Overlord Rush reúne oito chefes #Shorts",
]
SHORT_DESCRIPTIONS = [
    "A Zenith adiciona modificadores de proteção e novas formas de lidar com a corrupção. Fonte oficial: https://blog.playstation.com/2026/10/19/the-saros-zenith-update-out-today-brings-more-ways-to-play-for-newcomers-and-veterans-alike/",
    "Os Eclipse Layers ampliam o New Game Plus com combinações de Trials. Fonte oficial: https://blog.playstation.com/2026/10/19/the-saros-zenith-update-out-today-brings-more-ways-to-play-for-newcomers-and-veterans-alike/",
    "Overlord Rush inclui Incursion, Ascension e Totality, com oito chefes na sequência final. Fonte oficial: https://blog.playstation.com/2026/10/19/the-saros-zenith-update-out-today-brings-more-ways-to-play-for-newcomers-and-veterans-alike/",
]

def run(args):
    subprocess.run([str(x) for x in args], check=True)

def probe_duration(path):
    value = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(value)

def esc_text(value):
    return (value.replace("\\", "\\\\").replace(":", "\\:")
            .replace("'", "\\'").replace("%", "\\%").replace(",", "\\,"))

def font(size):
    return ImageFont.truetype(FONT, size)

def fit_audio_segment(source, target_duration, destination):
    source_duration = probe_duration(source)
    tempo = source_duration / target_duration
    if not 0.76 <= tempo <= 1.26:
        raise RuntimeError(
            f"VOICE_TIMING_BLOCK: {Path(source).name} precisa de atempo={tempo:.3f}; "
            "ajuste o tamanho do parágrafo para preservar a voz natural."
        )
    af = f"atempo={tempo:.6f},apad=pad_dur=0.25,atrim=duration={target_duration:.6f},asetpts=N/SR/TB"
    run(["ffmpeg", "-y", "-i", source, "-vn", "-af", af, "-ar", "48000",
         "-ac", "2", "-c:a", "pcm_s16le", destination])
    return target_duration

def concat_wavs(paths, destination, list_path):
    with open(list_path, "w", encoding="utf-8") as fp:
        for path in paths:
            fp.write("file '" + str(Path(path).resolve()).replace("'", "'\\''") + "'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
         "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", destination])

def mix_voice_music(voice_wav, duration, destination):
    music_fade_start = max(0.0, duration - 2.0)
    graph = (
        f"[0:a]volume=1.0[voice];"
        f"[1:a]atrim=duration={duration:.6f},volume=0.15,"
        f"afade=t=in:st=0:d=0.7,afade=t=out:st={music_fade_start:.6f}:d=2.0[music];"
        "[voice][music]amix=inputs=2:duration=first:dropout_transition=0,"
        "alimiter=limit=0.96[out]"
    )
    run(["ffmpeg", "-y", "-i", voice_wav, "-stream_loop", "-1", "-i", MUSIC,
         "-filter_complex", graph, "-map", "[out]", "-t", f"{duration:.6f}",
         "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", destination])

def make_master(source, legacy_timings_path, new_timings_path, master_voice):
    legacy = json.loads(Path(legacy_timings_path).read_text(encoding="utf-8"))
    new = json.loads(Path(new_timings_path).read_text(encoding="utf-8"))
    old_segments = legacy.get("segments", [])
    new_segments = new.get("segments", [])
    if len(old_segments) != 13 or len(new_segments) != 13:
        raise RuntimeError(f"VOICE_SEGMENT_BLOCK: esperado 13 segmentos; antigo={len(old_segments)}, novo={len(new_segments)}")
    targets = [float(s.get("duration") or (s["end"] - s["start"])) for s in old_segments]
    target_voice_duration = sum(targets)
    video_duration = probe_duration(source)
    intro_duration = video_duration - target_voice_duration
    if not 0 <= intro_duration <= 8:
        raise RuntimeError(f"INTRO_DURATION_BLOCK: duração inesperada de intro {intro_duration:.3f}s")

    stretched = []
    for i, (new_segment, target) in enumerate(zip(new_segments, targets), 1):
        source_segment = Path(new_segment["file"])
        if not source_segment.exists():
            raise RuntimeError(f"VOICE_SEGMENT_BLOCK: arquivo ausente {source_segment}")
        destination = OUT / "matched_voice_segments" / f"segment_{i:02d}.wav"
        destination.parent.mkdir(parents=True, exist_ok=True)
        fit_audio_segment(source_segment, target, destination)
        stretched.append(destination)

    voice_matched = OUT / "voice-matched.wav"
    concat_wavs(stretched, voice_matched, OUT / "voice-concat.txt")
    intro_audio = OUT / "intro-audio.wav"
    run(["ffmpeg", "-y", "-i", source, "-t", f"{intro_duration:.6f}", "-vn",
         "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", intro_audio])
    main_mix = OUT / "master-main-mix.wav"
    mix_voice_music(voice_matched, target_voice_duration, main_mix)
    final_audio = OUT / "master-final-audio.wav"
    concat_wavs([intro_audio, main_mix], final_audio, OUT / "master-audio-concat.txt")

    filters = []
    title_offset = 2.0
    title_duration = 4.5
    for segment, title in zip(old_segments, MASTER_TITLES):
        start = intro_duration + float(segment["start"]) + title_offset
        end = min(start + title_duration, video_duration)
        enable = f"between(t,{start:.3f},{end:.3f})"
        filters.append(f"drawbox=x=50:y=730:w=1320:h=120:color=black@0.90:t=fill:enable='{enable}'")
        filters.append(f"drawbox=x=50:y=730:w=8:h=120:color=0x39FF63:t=fill:enable='{enable}'")
        filters.append(
            f"drawtext=fontfile={FONT}:text='{esc_text(title)}':"
            f"x=86:y=765:fontsize=36:fontcolor=white:borderw=1:bordercolor=black@0.4:"
            f"enable='{enable}'"
        )
    filter_chain = ",".join(filters)
    master_out = OUT / "master.mp4"
    run(["ffmpeg", "-y", "-i", source, "-i", final_audio,
         "-vf", filter_chain, "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
         "-t", f"{video_duration:.3f}", master_out])
    return master_out, video_duration

def make_short(master, config, index):
    duration = float(config["duration"])
    voice = config["voice"]
    voice_wav = OUT / "shorts" / f"short_{index}_voice_fit.wav"
    fit_audio_segment(voice, duration, voice_wav)
    audio_mix = OUT / "shorts" / f"short_{index}_audio.wav"
    mix_voice_music(voice_wav, duration, audio_mix)

    title = esc_text(config["title"])
    cta = esc_text(config["cta"])
    start = float(config["start"])
    filter_chain = (
        "crop=608:1080:656:0,scale=1080:1920:flags=lanczos,setsar=1,"
        "drawbox=x=0:y=0:w=1080:h=132:color=black@0.70:t=fill,"
        "drawbox=x=0:y=126:w=1080:h=7:color=0x39FF63:t=fill,"
        f"drawtext=fontfile={FONT}:text='RADAR DOS GAMES':x=54:y=40:fontsize=42:fontcolor=white:borderw=1:bordercolor=black,"
        f"drawbox=x=35:y=1270:w=1010:h=190:color=black@0.84:t=fill:enable='between(t,0,3.2)',"
        f"drawtext=fontfile={FONT}:text='{title}':x=65:y=1325:fontsize=42:fontcolor=white:borderw=1:bordercolor=black:enable='between(t,0,3.2)',"
        f"drawbox=x=35:y=1260:w=1010:h=260:color=black@0.90:t=fill:enable='between(t,{max(0,duration-2.8):.3f},{duration:.3f})',"
        f"drawtext=fontfile={FONT}:text='{cta}':x=65:y=1310:fontsize=36:fontcolor=white:borderw=1:bordercolor=black:enable='between(t,{max(0,duration-2.8):.3f},{duration:.3f})',"
        f"drawtext=fontfile={FONT}:text='COMENTE AQUI - RADAR DOS GAMES':x=65:y=1380:fontsize=27:fontcolor=0x39FF63:borderw=1:bordercolor=black:enable='between(t,{max(0,duration-2.8):.3f},{duration:.3f})'"
    )
    output = config["filename"]
    run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", master,
         "-i", audio_mix, "-t", f"{duration:.3f}", "-vf", filter_chain,
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "fast",
         "-crf", "19", "-r", "30", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", output])
    return output

def make_master_thumbnail(legacy_thumb, destination):
    image = Image.open(legacy_thumb).convert("RGBA").resize((1280, 720))
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle((85, 500, 1195, 635), radius=12, fill=(3, 10, 20, 238),
                           outline=(57, 255, 99, 255), width=5)
    image = Image.alpha_composite(image, layer)
    draw = ImageDraw.Draw(image)
    line1 = "ATUALIZACAO ZENITH"
    line2 = "ACESSIBILIDADE  •  NEW GAME+  •  OVERLORD RUSH"
    f1, f2 = font(43), font(25)
    box1 = draw.textbbox((0, 0), line1, font=f1, stroke_width=1)
    box2 = draw.textbbox((0, 0), line2, font=f2, stroke_width=1)
    draw.text(((1280 - (box1[2] - box1[0])) / 2, 514), line1, font=f1,
              fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0, 255))
    draw.text(((1280 - (box2[2] - box2[0])) / 2, 574), line2, font=f2,
              fill=(75, 245, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0, 255))
    image.convert("RGB").save(destination, quality=95)

def make_short_cover(video, title, destination):
    frame = OUT / "shorts" / (Path(destination).stem + "_frame.jpg")
    run(["ffmpeg", "-y", "-ss", "5", "-i", video, "-frames:v", "1", "-q:v", "2", frame])
    image = Image.open(frame).convert("RGB").resize((1080, 1920))
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, 1080, 150), fill=(0, 0, 0, 180))
    draw.rectangle((0, 142, 1080, 153), fill=(57, 255, 99, 255))
    draw.rectangle((0, 1370, 1080, 1920), fill=(2, 7, 15, 220))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)
    draw.text((55, 48), "RADAR DOS GAMES", font=font(43), fill="white",
              stroke_width=2, stroke_fill="black")
    wrapped = title.replace(" - ", "\n")
    draw.multiline_text((55, 1450), wrapped, font=font(52), fill="white",
                        spacing=14, stroke_width=2, stroke_fill="black")
    image.convert("RGB").save(destination, quality=94)

def write_metadata():
    source_url = "https://blog.playstation.com/2026/10/19/the-saros-zenith-update-out-today-brings-more-ways-to-play-for-newcomers-and-veterans-alike/"
    tags = ["Saros", "Saros Zenith", "PlayStation 5", "Housemarque", "jogos", "Radar dos Games"]
    master_meta = {
        "title": "Saros: atualização Zenith traz acessibilidade, New Game+ e Overlord Rush",
        "description": "A atualização Zenith amplia as opções de acessibilidade, adiciona modificadores, Eclipse Layers e o desafio Overlord Rush. Fonte oficial: " + source_url,
        "tags": tags, "privacy": "private", "containsSyntheticMedia": True,
        "thumbnail": "output/thumbnail.jpg", "use_existing_thumbnail": True,
    }
    (OUT / "master-youtube.json").write_text(json.dumps(master_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for i, title in enumerate(SHORT_TITLES, 1):
        meta = {
            "title": title, "description": SHORT_DESCRIPTIONS[i-1] + "\n\n#Shorts #Saros #PlayStation5",
            "tags": tags + ["Shorts", "gaming"], "privacy": "private", "containsSyntheticMedia": True,
        }
        (OUT / f"short-{i}-youtube.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main():
    OUT.mkdir(exist_ok=True)
    SHORTS.mkdir(parents=True, exist_ok=True)
    source = OUT / "master-source.mp4"
    legacy_timings = OUT / "legacy-voice-timings.json"
    new_timings = OUT / "new-voice-timings.json"
    legacy_thumb = OUT / "legacy-thumbnail.jpg"
    for path in (source, legacy_timings, new_timings, legacy_thumb, MUSIC):
        if not path.exists():
            raise FileNotFoundError(f"Required rebuild input missing: {path}")

    master, master_duration = make_master(source, legacy_timings, new_timings, OUT / "new-voice.mp3")
    for i, config in enumerate(SHORT_CONFIG, 1):
        make_short(master, config, i)
        cover = SHORTS / f"short_{i}_cover.jpg"
        make_short_cover(SHORTS / f"short_{i}.mp4", config["title"], cover)
    make_master_thumbnail(legacy_thumb, OUT / "thumbnail.jpg")
    write_metadata()

    # Basic deliverable QA: one master, exactly three shorts, correct formats/durations.
    if probe_duration(master) < 240:
        raise RuntimeError("QUALITY_BLOCK: rebuilt Master is unexpectedly short.")
    for i in range(1, 4):
        p = SHORTS / f"short_{i}.mp4"
        d = probe_duration(p)
        if not 15 <= d <= 25:
            raise RuntimeError(f"QUALITY_BLOCK: Short {i} duration out of range: {d:.2f}s")
    print(json.dumps({
        "master": str(master), "master_duration": round(master_duration, 3),
        "shorts": [str(SHORTS / f"short_{i}.mp4") for i in range(1, 4)],
        "titles": [json.loads((OUT / "master-youtube.json").read_text())["title"]] + SHORT_TITLES,
        "privacy": "private",
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
