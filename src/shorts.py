#!/usr/bin/env python3
"""Gera exatamente 3 Shorts 9:16 a partir do master, sem esticar a imagem."""
import subprocess, sys
from pathlib import Path

def duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',path],text=True))

def make(src,out,start,length=45):
    # Fundo preenchido/desfocado + vídeo 16:9 inteiro centralizado: preserva HUD/personagens melhor que crop central cego.
    fc=("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg];"
        "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
    subprocess.run(['ffmpeg','-y','-ss',str(start),'-i',src,'-t',str(length),'-filter_complex',fc,'-map','[v]','-map','0:a?','-c:v','libx264','-preset','medium','-crf','20','-c:a','aac','-b:a','160k',out],check=True)

def main(src):
    d=duration(src); out=Path('output/shorts'); out.mkdir(parents=True,exist_ok=True)
    starts=[max(0,d*.12),max(0,d*.42),max(0,d*.72)]
    for i,s in enumerate(starts,1): make(src,str(out/f'short_{i}.mp4'),s,min(45,max(20,d-s)))

if __name__=='__main__': main(sys.argv[1])
