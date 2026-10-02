#!/usr/bin/env python3
"""Obtém assets oficiais/relevantes preservando imagens originais para a montagem editorial."""
import html
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def valid_visual(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 20_000:
        return False
    try:
        subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def request(url, data=None, referer=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/129 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    return urllib.request.Request(url, data=data, headers=headers)


def download(url: str, dest: Path, referer=None) -> bool:
    try:
        with urllib.request.urlopen(request(url, referer=referer), timeout=40) as r, open(dest, "wb") as f:
            while True:
                b = r.read(1024 * 1024)
                if not b:
                    break
                f.write(b)
        if valid_visual(dest):
            return True
        dest.unlink(missing_ok=True)
    except Exception as e:
        print("download failed:", e)
        dest.unlink(missing_ok=True)
    return False


def direct_video(url: str, dest: Path, referer=None) -> bool:
    tmp = dest.with_suffix(".download")
    if not download(url, tmp, referer):
        return False
    tmp.replace(dest)
    return valid_visual(dest)


def ytdlp(url: str, dest: Path) -> bool:
    try:
        subprocess.run(
            [
                "yt-dlp", "--no-playlist", "--retries", "1", "--fragment-retries", "1", "--socket-timeout", "15",
                "-f", "b[height<=1080]/best", "--merge-output-format", "mp4", "-o", str(dest), url,
            ],
            check=True,
        )
        return valid_visual(dest)
    except subprocess.CalledProcessError:
        dest.unlink(missing_ok=True)
        return False


def savefrom(url: str, dest: Path) -> bool:
    endpoints = ["https://pt1.savefrom.net/8bb/", "https://savefrom.net/1-youtube-video-downloader-4/"]
    for endpoint in endpoints:
        try:
            payload = urllib.parse.urlencode({"sf_url": url, "sf_submit": "", "new": "2", "lang": "pt"}).encode()
            with urllib.request.urlopen(request(endpoint, payload, endpoint), timeout=40) as r:
                text = r.read().decode("utf-8", "ignore")
            for raw in re.findall(r"https?:[^\"\'<>\\ ]+", text):
                media_url = html.unescape(raw).replace("\\/", "/")
                low = media_url.lower()
                if ("googlevideo.com" in low or ".mp4" in low or "videoplayback" in low) and "savefrom" not in low:
                    if direct_video(media_url, dest, endpoint):
                        return True
        except Exception as e:
            print("SaveFrom fallback failed:", e)
    return False


def main(spec_path: str):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    out = Path("output/media")
    out.mkdir(parents=True, exist_ok=True)

    assets = []
    errors = []
    for i, item in enumerate(spec.get("media", []), 1):
        url = item["url"]
        typ = item.get("type", "video")
        role = item.get("role", "")
        ok = False

        if typ == "image":
            dest = out / f"asset_{i:02d}.jpg"
            ok = download(url, dest)
        else:
            dest = out / f"asset_{i:02d}.mp4"
            if url.lower().split("?")[0].endswith((".mp4", ".mov", ".webm")):
                ok = direct_video(url, dest)
            if not ok:
                ok = ytdlp(url, dest)
            if not ok and ("youtube.com" in url or "youtu.be" in url):
                ok = savefrom(url, dest)

        if ok:
            assets.append({"index": i, "path": str(dest), "type": typ, "role": role, "url": url})
        else:
            errors.append({"index": i, "url": url, "error": "remote_media_unavailable_after_fallbacks"})

    minimum = int(spec.get("minimum_assets", 8))
    manifest = {
        "assets": assets,
        "clips": [a["path"] for a in assets],
        "errors": errors,
        "publishable_media": len(assets) >= minimum,
        "generic_fallback": False,
        "official_assets": True,
        "minimum_assets": minimum,
    }
    Path("output/clips.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if len(assets) < minimum:
        raise RuntimeError(f"QUALITY_BLOCK: somente {len(assets)} assets relevantes; minimo {minimum}")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
