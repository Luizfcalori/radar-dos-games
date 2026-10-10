#!/usr/bin/env python3
"""One-off Radar dos Games promotional Short; no changes to daily production pipeline."""
import asyncio, json, math, random, shutil, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path("promo-once"); ROOT.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30
VIDEO=ROOT/"Radar_dos_Games_Convite_Exclusivo_Multiplataforma_V3.mp4"
COVER=ROOT/"Radar_dos_Games_Convite_Capa_Multiplataforma_V3.jpg"
GREEN=(151,255,37); WHITE=(243,247,253)
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONTREG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SCRIPT=("Olá, pessoal! Vocês gostam de jogos? Então conheçam o Radar dos Games! "
"Aqui você acompanha lançamentos, notícias quentes, vídeos de gameplay e análises, em vídeos completos e shorts rápidos. "
"A nossa missão é transformar cada novidade em conteúdo que vale o seu tempo. "
"E o nosso sonho é crescer junto com vocês e construir uma comunidade gamer de verdade! "
"Se você curte esse universo, deixa o like e inscreva-se no canal. "
"Vem fazer parte do Radar dos Games. O seu radar no mundo dos jogos!")
# Speech-only pronunciation guidance: preserve exact original spelling in the script
# and subtitles, but pronounce English "gameplay" with a hard G: /geɪmpleɪ/.
SPEECH_SCRIPT = SCRIPT.replace("gameplay", "guêim plêi")

SOURCES=[
 ("CYBERPUNK 2077", "cyberpunk-2026-10-09-short-1.mp4"),
 ("ARC RAIDERS", "arc-raiders-gratis-ate-12-de-outubro-shorts-37913899117-short-1.mp4"),
 ("GTA VI", "gta6-leak-2026-10-08-short-2.mp4"),
 ("BATTLEFIELD 6","battlefield6-2026-10-07-short-1.mp4"),
 ("FORTNITE", "fortnitemares-2026-jwXtn0b0rYA.mp4"),
 ("GEARS OF WAR: E-DAY", "gears-eday-2026-10-06-short-1.mp4"),
]
SOURCE_BASE="https://github.com/Luizfcalori/radar-dos-games/releases/download/tiktok-approved-assets/"

# Carefully measured from full-frame thumbnails of the original approved Shorts:
# GTA footage fills roughly y=755..1295; Battlefield footage y=750..1160.
# The former y=525..1025 crop displayed only the upper black letterboxing
# and clipped the actual gameplay, especially from 00:12 to 00:22.
# x:y:w:h for each exceptional original 1080x1920 source.
SAFE_REFRAME={
    "gta6-leak-2026-10-08-short-2.mp4":(65,755,950,540),
    "battlefield6-2026-10-07-short-1.mp4":(65,720,950,540),
}
DEFAULT_CROP=(90,525,900,500)


def run(cmd):
 print("CMD", " ".join(map(str,cmd))[:310], flush=True)
 subprocess.run(list(map(str,cmd)),check=True)

def duration(f):
 return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(f)],text=True).strip())

def font(sz,bold=True):
 return ImageFont.truetype(FONT if bold else FONTREG,sz)

def textcenter(d,y,tx,sz,color=WHITE,bold=True):
 f=font(sz,bold); b=d.textbbox((0,0),tx,font=f)
 x=(W-(b[2]-b[0]))/2
 d.text((x,y),tx,font=f,fill=color,stroke_width=2 if sz>39 else 0,stroke_fill=(0,0,0))

def roundrect(d,xy,rad,fill,outline=None,width=1):
 d.rounded_rectangle(xy,radius=rad,fill=fill,outline=outline,width=width)

def frame_overlay(label,final=False):
 im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
 d.rectangle((0,0,W,124),fill=(4,12,31,253))
 d.line((0,124,W,124),fill=(*GREEN,190),width=4)
 d.rounded_rectangle((46,35,210,93),radius=12,fill=(*GREEN,255))
 d.text((72,45),"RDG",font=font(34),fill=(1,15,20))
 d.text((227,40),"RADAR",font=font(44),fill=WHITE)
 d.text((421,40),"DOS GAMES",font=font(44),fill=GREEN)
 d.rectangle((0,125,W,410),fill=(0,0,0,231))
 textcenter(d,158,"GAMES, NOTÍCIAS E",57)
 textcenter(d,241,"MUITO MAIS!",68,GREEN)
 textcenter(d,350,"O CANAL QUE CRESCE COM VOCÊ",28,(199,213,226),False)
 d.rounded_rectangle((69,587,1011,1141),radius=22,fill=None,outline=GREEN,width=7)
 roundrect(d,(118,1198,962,1272),17,(3,11,20,241),GREEN,3)
 textcenter(d,1217,label,32,GREEN)
 roundrect(d,(79,1445,1001,1560),28,GREEN)
 textcenter(d,1469,"INSCREVA-SE AGORA",52,(7,19,25))
 textcenter(d,1600,"DEIXE O LIKE",34,WHITE)
 d.rectangle((0,1743,W,1920),fill=(3,9,23,252))
 textcenter(d,1771,"RADAR DOS GAMES",44,GREEN)
 textcenter(d,1841,"GAMES  •  NOTÍCIAS  •  GAMEPLAY",25,(182,196,210),False)
 if final:
  d.rectangle((0,410,W,587),fill=(2,7,16,225))
  textcenter(d,469,"FAÇA PARTE DO NOSSO RADAR!",41,WHITE)
 return im

def background_image():
 random.seed(20261009)
 im=Image.new("RGB",(W,H)); p=im.load()
 for y in range(H):
  for x in range(W):
   glow=max(0,1-math.hypot(x-790,y-790)/1320)
   g=int(15+37*glow);b=int(26+37*glow)
   p[x,y]=(3,g,b)
 d=ImageDraw.Draw(im,"RGBA")
 for j in range(24):
  x=random.randrange(W);y=random.randrange(H)
  d.line((x,y,x+random.randrange(75,380),y-random.randrange(30,180)),fill=(98,255,40,28),width=2)
 for y in range(450,1450,95):
  d.line((0,y,W,y),fill=(40,156,114,15),width=1)
 return im

def download_sources():
 src=[]
 for label,name in SOURCES:
  p=ROOT/name
  if not p.exists():
   try:
    req=urllib.request.Request(SOURCE_BASE+name,headers={"User-Agent":"RadarDosGames-OneOff-Promo/1.0"})
    with urllib.request.urlopen(req,timeout=60) as fd,open(p,"wb") as out:
     shutil.copyfileobj(fd,out)
   except Exception as e:
    print("SOURCE_UNAVAILABLE",name,str(e)[:180],flush=True)
    p.unlink(missing_ok=True);continue
  try:
   if p.stat().st_size>150000 and duration(p)>8:src.append((label,p))
  except Exception as e:
   print("SOURCE_INVALID",name,str(e)[:100]);p.unlink(missing_ok=True)
 if len(src)<4:
  raise RuntimeError("Quality gate: fewer than 4 approved source clips")
 return src

def make_voice():
 p=ROOT/"voice.mp3"
 if not p.exists():
  import edge_tts
  async def go():
   await edge_tts.Communicate(SPEECH_SCRIPT,voice="pt-BR-ThalitaMultilingualNeural",rate="+0%",pitch="+0Hz").save(str(p))
  asyncio.run(go())
 if duration(p)<12:raise RuntimeError("Narração com duração inválida")
 return p

def make_clip(source,idx,length,label,n):
 overlay=ROOT/f"layout_{idx:02}.png"
 frame_overlay(label,final=idx==n-1).save(overlay)
 bg=ROOT/"background.png";out=ROOT/f"cut_{idx:02}.mp4"
 # Extract central gameplay from previous approved Radar Short:
 # avoids stacking the old title/CTA over the new promotional identity.
 crop=SAFE_REFRAME.get(Path(source).name,DEFAULT_CROP)
 x,y,w,h=crop
 if x<0 or y<0 or x+w>1080 or y+h>1920: raise RuntimeError(f"QUALITY_BLOCK invalid crop {source} {crop}")
 vf=(f"[0:v]fps=30,crop={w}:{h}:{x}:{y},scale=900:506:flags=lanczos,setsar=1,eq=contrast=1.025:saturation=0.94:brightness=0.008[fg];"
     "[1:v]format=rgba[base];[base][fg]overlay=x=90:y=612:shortest=1[composed];"
     "[2:v]format=rgba[brand];[composed][brand]overlay=0:0:shortest=1,format=yuv420p[out]")
 run(["ffmpeg","-y","-v","error","-ss",f"{1.2+idx*.63:.2f}","-i",source,
      "-loop","1","-i",bg,"-loop","1","-i",overlay,
      "-filter_complex",vf,"-map","[out]","-an","-t",f"{length:.3f}",
      "-r",FPS,"-c:v","libx264","-preset","veryfast","-crf","22",out])
 return out

def make_cover(clip):
 base=background_image().convert("RGB")
 shot=ROOT/"cover_frame.jpg"
 run(["ffmpeg","-y","-v","error","-ss","2","-i",clip,"-frames:v","1",shot])
 with Image.open(shot) as im:
  crop=im.crop((85,600,995,1145)).resize((920,550))
  base.paste(crop,(80,592))
 ov=frame_overlay("NOSSO CANAL • NOSSA MISSÃO",True)
 base=Image.alpha_composite(base.convert("RGBA"),ov).convert("RGB")
 base.save(COVER,quality=92)

def main():
 voice=make_voice();src=download_sources()
 total=duration(voice)+0.85
 background_image().save(ROOT/"background.png")
 labels=["LANÇAMENTOS E NOVIDADES","GAMEPLAY QUE IMPRESSIONA",
         "NOTÍCIAS DO MUNDO GAMER","ANÁLISES E CONTEÚDO COMPLETO",
         "UMA COMUNIDADE DE GAMERS","NOSSO PRÓXIMO CAPÍTULO É COM VOCÊ"]
 n=min(len(src),6);parts=[]
 for i,(_,s) in enumerate(src[:n]):
  t0=round(total*i/n*FPS)/FPS;t1=round(total*(i+1)/n*FPS)/FPS
  parts.append(make_clip(s,i,round(t1-t0,3),labels[i],n))
 listing=ROOT/"concat.txt"
 listing.write_text("".join(f"file '{p.resolve()}'\n" for p in parts),encoding="utf8")
 visuals=ROOT/"visuals.mp4"
 run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",listing,"-c","copy",visuals])
 music=Path("assets/audio/radar-bed.mp3")
 if not music.exists():
  raise RuntimeError("Trilha aprovada assets/audio/radar-bed.mp3 ausente")
 fc=("[1:a]highpass=f=75,acompressor=threshold=-20dB:ratio=2.4:attack=12:release=140[v];"
     "[2:a]volume=0.095,afade=t=in:st=0:d=0.4,afade=t=out:st="
     +f"{max(0,total-1.4):.2f}"+":d=1.3[m];"
     "[v][m]amix=inputs=2:duration=first:dropout_transition=1,loudnorm=I=-16:LRA=7:TP=-1.5[a]")
 run(["ffmpeg","-y","-v","error","-i",visuals,"-i",voice,"-stream_loop","-1","-i",music,
      "-filter_complex",fc,"-map","0:v","-map","[a]","-t",f"{total:.3f}",
      "-c:v","copy","-c:a","aac","-b:a","192k","-ac","2","-movflags","+faststart",VIDEO])
 make_cover(parts[0])
 actual=duration(VIDEO)
 if actual<20 or actual>65:raise RuntimeError(f"Invalid Short length: {actual}")
 report={"video":str(VIDEO),"cover":str(COVER),"duration_s":round(actual,2),
   "voice":"pt-BR-ThalitaMultilingualNeural",
   "video_sources":[x[0] for x in src[:n]],
   "music":"Five Armies - Kevin MacLeod (CC BY 4.0)",
   "upload_status":"NOT_UPLOADED_TO_YOUTUBE_OR_TIKTOK",
   "pipeline_changes":"NONE",
   "pronunciation":{"original_word":"gameplay","speech_only":"guêim plêi","english_phonemes":"/geɪmpleɪ/"},
   "opening_language":"pt-BR",
   "reframe_profile":"RADAR_PROMO_V2_ACTUAL_GAMEPLAY_CENTERED",
   "corrected_sources":{k:list(v) for k,v in SAFE_REFRAME.items()},
   "affected_seconds":[12,22],
   "promo_style":"RADAR_PREMIUM_CONVERSAO_V1",
   "cta_text":["INSCREVA-SE AGORA","DEIXE O LIKE","RADAR DOS GAMES"],
   "cross_platform_visual":True}
 (ROOT/"production-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
 (ROOT/"narration.txt").write_text(SCRIPT,encoding="utf8")
 print("PRODUCTION_DONE",json.dumps(report,ensure_ascii=False),flush=True)

if __name__=="__main__":main()
