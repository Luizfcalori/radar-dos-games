#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path

def probe(path):
    raw=subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],text=True)
    return json.loads(raw)

def check(path, short=False):
    p=Path(path)
    if not p.exists() or p.stat().st_size < 500_000: raise RuntimeError(f'Arquivo inválido: {p}')
    d=probe(p); dur=float(d['format']['duration']); streams=d['streams']
    v=next((x for x in streams if x['codec_type']=='video'),None); a=next((x for x in streams if x['codec_type']=='audio'),None)
    if not v or not a: raise RuntimeError('Vídeo precisa ter imagem e áudio')
    if short:
        if v['width'] >= v['height']: raise RuntimeError('Short não está vertical')
        if not 15 <= dur <= 60: raise RuntimeError(f'Duração de Short inválida: {dur:.1f}s')
    else:
        if v['width'] < v['height']: raise RuntimeError('Master não está horizontal')
        if not 180 <= dur <= 600: raise RuntimeError(f'Duração master fora da faixa segura: {dur:.1f}s')
    print(json.dumps({'file':str(p),'duration':dur,'width':v['width'],'height':v['height'],'audio':True,'ok':True}))

if __name__=='__main__': check(sys.argv[1], '--short' in sys.argv)
