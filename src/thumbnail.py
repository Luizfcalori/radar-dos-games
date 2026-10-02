#!/usr/bin/env python3
"""Thumbnail 1280x720 gratuita usando frame do próprio vídeo + texto de impacto."""
import subprocess, sys
from pathlib import Path
video,title,out=sys.argv[1],sys.argv[2],Path(sys.argv[3]); out.parent.mkdir(parents=True,exist_ok=True)
safe=title.replace("'","\\'").replace(':','\\:')
vf=f"scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,drawbox=x=0:y=430:w=1280:h=290:color=black@0.58:t=fill,drawtext=text='{safe}':x=55:y=500:fontsize=58:fontcolor=white:borderw=3:bordercolor=black"
subprocess.run(['ffmpeg','-y','-ss','12','-i',video,'-frames:v','1','-vf',vf,str(out)],check=True)
