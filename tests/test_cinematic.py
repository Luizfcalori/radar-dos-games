import json
import shutil
import subprocess
from pathlib import Path

import pytest
from src import cinematic


def test_credits_only_for_finished_cinematic_assets(tmp_path):
    video=tmp_path/'master.mp4'
    meta=tmp_path/'master-youtube.json'
    meta.write_text(json.dumps({'description':'Descrição original'}))
    assert cinematic.credited_description(video,'Antigo')=='Antigo'
    cinematic.write_credit(video)
    description=json.loads(meta.read_text())['description']
    assert cinematic.MUSIC_CREDIT in description
    assert cinematic.credited_description(video,description)==description


@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg required')
def test_real_mix_keeps_voice_duration_and_produces_audio(tmp_path):
    def ff(*args):subprocess.run(['ffmpeg','-v','error','-y',*map(str,args)],check=True)
    visual=tmp_path/'visual.mp4';voice=tmp_path/'voice.wav';out=tmp_path/'short.mp4'
    ff('-f','lavfi','-i','color=c=gray:s=320x180:r=30:d=4','-an','-c:v','libx264',visual)
    ff('-f','lavfi','-i','sine=frequency=330:duration=3','-af',"volume=enable='between(t,1,2)':volume=0",voice)
    assert cinematic.mix(visual,voice,None,out)=='approved_bed_with_voice_ducking'
    assert abs(cinematic.duration(out)-3)<0.1
    raw=subprocess.check_output(['ffmpeg','-v','error','-ss','1.3','-i',str(out),'-t','0.3','-f','s16le','-ar','48000','-ac','1','-'])
    import array
    pcm=array.array('h',raw)
    assert sum(x*x for x in pcm)/len(pcm)>25  # Music remains audible during the silent voice interval.
    assert Path(str(out)+'.music.json').exists()
