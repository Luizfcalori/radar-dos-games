#!/usr/bin/env python3
import argparse, hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
DATA = ROOT / "data"
OUT.mkdir(exist_ok=True); DATA.mkdir(exist_ok=True)


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def run(cmd):
    print('+', ' '.join(map(str,cmd)), flush=True)
    subprocess.run(cmd, check=True)


def load_history():
    p=DATA/'published.json'
    return json.loads(p.read_text()) if p.exists() else {"videos":[]}


def save_history(x): (DATA/'published.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')


def quality_gate(video):
    if not video.exists() or video.stat().st_size < 1_000_000: raise RuntimeError('Vídeo final ausente/pequeno demais')
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(video)],text=True).strip()
    duration=float(probe)
    if duration < 180: raise RuntimeError(f'Duração inesperadamente curta: {duration:.1f}s')
    return duration


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--topic',default=os.getenv('RADAR_TOPIC','AUTO')); args=ap.parse_args()
    # O workflow começa conservador: não publica até que os módulos de mídia/voz e OAuth estejam configurados.
    manifest={"created_at":datetime.now(timezone.utc).isoformat(),"topic":args.topic,"status":"pipeline_bootstrapped","publish_enabled":False}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False))

if __name__=='__main__': main()
