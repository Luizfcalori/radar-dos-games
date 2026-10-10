"""Optional free acquisition of public Instagram posts and reels.

Explicit, public URLs only. No login, private API, cookies or paid services.
Downloading public video does not establish permission to republish it.
"""
from pathlib import Path
from urllib.parse import urlparse
import subprocess

def is_instagram_video_url(url):
    try:
        parsed=urlparse(str(url))
        segments=parsed.path.strip("/").split("/")
        public_short=(len(segments)>=2 and segments[0] in ("reel","reels","p","tv"))
        account_short=(len(segments)>=3 and segments[1] in ("reel","reels","p","tv")
                       and bool(segments[0]) and not segments[0].startswith("."))
        return (parsed.scheme=="https"
                and (parsed.hostname or "").lower() in
                    ("instagram.com","www.instagram.com","m.instagram.com")
                and (public_short or account_short))
    except (TypeError,ValueError):
        return False

def download_public_instagram(url,dest,probe_info):
    """Use yt-dlp on public reel/post URL, inspect output; return None on failure."""
    if not is_instagram_video_url(url):
        return None
    dest=Path(dest)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.unlink(missing_ok=True)
    cmd=["yt-dlp","--ignore-config","--no-playlist","--no-progress",
         "--no-warnings","--retries","2","--fragment-retries","2",
         "--extractor-retries","2","--socket-timeout","20",
         "--max-filesize","180M","--merge-output-format","mp4",
         "-o",str(dest),url]
    try:
        result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              text=True,timeout=100,check=False)
        print("Instagram public download",result.returncode,result.stdout[-900:],flush=True)
        if result.returncode:
            return None
        info=probe_info(dest)
        if info and float(info.get("duration") or 0)>=5:
            print("Instagram verified",url,info,flush=True)
            return info
        return None
    except (OSError,subprocess.TimeoutExpired) as exc:
        print("Instagram unavailable",url,str(exc)[:180],flush=True)
        return None
    finally:
        if not probe_info(dest):
            dest.unlink(missing_ok=True)
