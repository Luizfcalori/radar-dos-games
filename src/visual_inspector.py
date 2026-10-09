#!/usr/bin/env python3
"""Free CPU visual inventory: decode every original video frame before narration.

Technical vision (light/motion/freeze/cuts) is distinct from semantic recognition.
No filename or classifier guess is represented as verified gameplay content.
"""
import hashlib
import json
import math
import subprocess
from pathlib import Path

OUT = Path("output")
W, H = 64, 36
FRAME_BYTES = W * H


def probe(path):
    obj = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=avg_frame_rate,r_frame_rate",
        "-show_entries", "format=duration", "-of", "json", str(path)
    ], text=True))
    stream = (obj.get("streams") or [{}])[0]
    fraction = stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "30/1"
    try:
        a, b = [float(x) for x in fraction.split("/")]
        fps = a / b if b else 30.0
    except (TypeError, ValueError):
        fps = 30.0
    return max(1.0, min(120.0, fps)), float(obj.get("format", {}).get("duration") or 0)


def sample_metrics(frame, previous):
    # Spatial subsampling changes workload, never the number of frames examined.
    pixels = frame[::4]
    mean = sum(pixels) / max(1, len(pixels))
    dark = sum(v < 18 for v in pixels) / max(1, len(pixels))
    variance = sum((v - mean) ** 2 for v in pixels) / max(1, len(pixels))
    motion = (sum(abs(a - b) for a, b in zip(frame[::8], previous[::8]))
              / max(1, len(frame[::8]))) if previous is not None else 0.0
    return mean, dark, math.sqrt(variance), motion


def perceptual_hash(frame):
    # Eight by eight brightness grid, robust to video encoding differences.
    grid = [frame[(r * 4 + 2) * W + (c * 8 + 4)] for r in range(8) for c in range(8)]
    avg = sum(grid) / 64
    return "".join("1" if px >= avg else "0" for px in grid)


def choose_windows(seconds, duration):
    """Return source time ranges clear enough to edit; never use dark transitions."""
    spans = []
    start = None
    for sec, metrics in sorted(seconds.items()):
        usable = metrics["good"] >= max(1, metrics["frames"] * 0.68)
        if usable and start is None:
            start = sec
        if not usable and start is not None:
            if sec - start >= 3:
                spans.append((start, sec))
            start = None
    if start is not None:
        end = min(int(math.ceil(duration)), max(seconds) + 1)
        if end - start >= 3:
            spans.append((start, end))
    windows = []
    for a, b in spans:
        pos = float(a) + 0.2
        while pos + 2.6 <= b:
            end = min(float(b) - 0.2, pos + 7.2)
            if end - pos >= 2.6:
                windows.append({"start": round(pos, 3), "end": round(end, 3),
                                "duration": round(end - pos, 3)})
            pos = end + 0.3
    # Retain a spread of windows rather than just the opening of the trailer.
    if len(windows) > 24:
        windows = [windows[round(i * (len(windows) - 1) / 23)] for i in range(24)]
    return windows


def analyze_video(path, index):
    fps, duration = probe(path)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path),
           "-map", "0:v:0", "-an", "-sn", "-vf", f"scale={W}:{H}:flags=fast_bilinear,format=gray",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    previous = None
    n = 0
    dark_count = freeze_count = cuts = 0
    seconds = {}
    targets = [max(0, int(duration * fps * t)) for t in (0.15, 0.5, 0.85)]
    signatures = []
    try:
        while True:
            frame = proc.stdout.read(FRAME_BYTES)
            if len(frame) != FRAME_BYTES:
                break
            mean, dark, std, motion = sample_metrics(frame, previous)
            sec = int(n / fps)
            bucket = seconds.setdefault(sec, {"frames": 0, "good": 0})
            bucket["frames"] += 1
            bad = mean < 14 or dark > 0.90 or std < 7.5
            if not bad:
                bucket["good"] += 1
            else:
                dark_count += 1
            if previous is not None:
                if motion < 0.8:
                    freeze_count += 1
                if motion > 32.0:
                    cuts += 1
            if len(signatures) < len(targets) and n >= targets[len(signatures)]:
                signatures.append(perceptual_hash(frame))
            previous = frame
            n += 1
    finally:
        proc.stdout.close()
        code = proc.wait(timeout=30)
    if code or n == 0:
        raise RuntimeError(f"QUALITY_BLOCK: não foi possível inspecionar quadros do vídeo {index}")
    windows = choose_windows(seconds, min(duration, n / fps))
    return {"index": index, "type": "video", "status": "ANALYZED",
            "frames_analyzed": n, "fps": round(fps, 3), "duration": round(duration, 3),
            "dark_frame_ratio": round(dark_count / n, 4),
            "static_frame_ratio": round(freeze_count / n, 4),
            "potential_cuts": cuts, "perceptual_signatures": signatures,
            "usable_windows": windows,
            "semantic_status": "NOT_VERIFIED_BY_PIXEL_ANALYSIS"}


def hamming(a, b):
    return sum(x != y for x, y in zip(a, b))


def deduplicate(rows):
    videos = [r for r in rows if r["type"] == "video"]
    for i, row in enumerate(videos):
        for older in videos[:i]:
            if older.get("duplicate_of"):
                continue
            if abs(row["duration"] - older["duration"]) > 1.0:
                continue
            lhs, rhs = row["perceptual_signatures"], older["perceptual_signatures"]
            if len(lhs) == len(rhs) == 3 and max(hamming(a, b) for a, b in zip(lhs, rhs)) <= 12:
                row["duplicate_of"] = older["index"]
                row["usable_windows"] = []
                break


def inspect(clips):
    rows = []
    for asset in clips.get("assets", []):
        if not asset.get("approved"):
            continue
        idx = int(asset["index"])
        path = Path(asset["path"])
        if asset["type"] == "video":
            rows.append(analyze_video(path, idx))
        elif asset["type"] == "image":
            rows.append({"index": idx, "type": "image", "status": "SOURCE_IMAGE",
                         "semantic_status": "SOURCE_LABEL_ONLY"})
    deduplicate(rows)
    if not any(r.get("usable_windows") and not r.get("duplicate_of") for r in rows):
        raise RuntimeError("QUALITY_BLOCK: nenhum trecho de vídeo visualmente utilizável")
    return {"status": "ANALYZED", "policy": "FULL_FRAME_TECHNICAL_SCAN_V1",
            "note": "All decoded frames checked for darkness/motion; object identity is NOT inferred",
            "assets": rows}


def main():
    clips = json.loads((OUT / "clips.json").read_text(encoding="utf-8"))
    result = inspect(clips)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "visual-inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ANALYZED",
                      "videos": sum(x["type"] == "video" for x in result["assets"]),
                      "frames": sum(x.get("frames_analyzed", 0) for x in result["assets"]),
                      "duplicates": sum(bool(x.get("duplicate_of")) for x in result["assets"]),
                      "usable_windows": sum(len(x.get("usable_windows", [])) for x in result["assets"])}))


if __name__ == "__main__":
    main()
