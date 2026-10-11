"""Approved cinematic finish shared by Master and independent Shorts."""
import json
import subprocess
from pathlib import Path

COLOR_FILTER = 'eq=contrast=1.025:saturation=0.94:brightness=0.008'
VOICE_CHAIN = 'highpass=f=75,acompressor=threshold=-20dB:ratio=2.4:attack=12:release=140,loudnorm=I=-16:LRA=7:TP=-1.5'
MUSIC_CREDIT = ('Trilha: Five Armies — Kevin MacLeod (incompetech.com).\n'
                'Licença: Creative Commons Attribution 4.0 — https://creativecommons.org/licenses/by/4.0/\n'
                'Fonte: https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1100875\n'
                'Música editada e mixada para este vídeo.')

def approved_music_bed():
    path = Path(__file__).resolve().parents[1] / 'assets/audio/radar-bed.mp3'
    if not path.is_file() or path.stat().st_size < 20000:
        raise RuntimeError('QUALITY_BLOCK: trilha cinematográfica aprovada ausente')
    return path

def duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(path)],text=True))

def write_credit(path):
    Path(str(path)+'.music.json').write_text(json.dumps({'profile':'RADAR_CINEMATIC_V1','color_filter':COLOR_FILTER,'credit':MUSIC_CREDIT},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    path=Path(path)
    meta_path=None
    if path.name=='master.mp4':
        meta_path=path.parent/'master-youtube.json'
    elif path.stem.startswith('short_') and path.stem[6:].isdigit():
        meta_path=path.parent.parent/f'short-{int(path.stem[6:])}-youtube.json'
    if meta_path and meta_path.exists():
        meta=json.loads(meta_path.read_text(encoding='utf-8'))
        meta['description']=credited_description(path,meta.get('description',''))
        meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def credited_description(path, description):
    sidecar=Path(str(path)+'.music.json')
    if not sidecar.exists():
        return description
    credit=json.loads(sidecar.read_text(encoding='utf-8'))['credit']
    return description if credit in description else description.rstrip()+'\n\n'+credit

def mix(visuals, voice, sfx, dest):
    bed=approved_music_bed()
    seconds=duration(voice)
    fade=max(0,seconds-1.2)
    cmd=['ffmpeg','-y','-v','error','-i',str(visuals),'-i',str(voice)]
    cmd += ['-i',str(sfx)] if sfx else ['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
    cmd += ['-stream_loop','-1','-ss','38','-i',str(bed)]
    graph=(f'[1:a]{VOICE_CHAIN},aresample=48000,asetpts=PTS-STARTPTS,asplit=2[v][sc];[2:a]aresample=48000,asetpts=PTS-STARTPTS,volume=0.5[s];'
           f'[3:a]loudnorm=I=-24:LRA=9:TP=-3,aresample=48000,asetpts=PTS-STARTPTS,volume=0.6,afade=t=in:d=0.8,afade=t=out:st={fade:.3f}:d=1.2[b];'
           '[b][sc]sidechaincompress=threshold=0.025:ratio=6:attack=18:release=300[d];'
           '[v][d][s]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.84:level=false[a]')
    subprocess.run(cmd+['-filter_complex',graph,'-map','0:v:0','-map','[a]','-t',str(seconds),'-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',str(dest)],check=True)
    write_credit(dest)
    return 'approved_bed_with_voice_ducking'
