import unittest
from src.continuity import VideoTimeline, validate_video_beats
from src.pronunciation import spoken_text, measured_phrases

class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.assets={1:{'index':1,'type':'video','duration':60,'url':'https://official/one.mp4'},
                     2:{'index':2,'type':'video','duration':60,'url':'https://official/two.mp4'}}
        self.scene={'visual_windows':{'1':[{'start':0,'end':20,'semantic_categories':['combat']}],
                                      '2':[{'start':0,'end':20,'semantic_categories':['hacking']}]}}

    def test_follows_same_gameplay_without_restarting(self):
        t=VideoTimeline(self.assets)
        first=t.choose(self.scene,'Combate',5,list(self.assets.values()))
        second=t.choose(self.scene,'Combate',5,list(self.assets.values()))
        self.assertEqual((first[0]['index'],first[1],second[1]),(1,0,5))

    def test_hacking_is_not_generic_combat(self):
        result=VideoTimeline(self.assets).choose(self.scene,'Invasão digital de um netrunner',5,list(self.assets.values()))
        self.assertEqual(result[0]['index'],2)

    def test_exhaustion_never_wraps_or_uses_wrong_subject(self):
        t=VideoTimeline(self.assets)
        t.choose(self.scene,'Combate',10,list(self.assets.values()))
        t.choose(self.scene,'Combate',10,list(self.assets.values()))
        with self.assertRaisesRegex(RuntimeError,'faltam cenas inéditas'):
            t.choose(self.scene,'Combate',5,list(self.assets.values()))

    def test_overlap_across_scenes_and_aliases_blocked(self):
        self.assets[2]['duplicate_of']=1
        beats=[{'media_index':1,'duration':5,'source_window':{'start':0,'end':5}},
               {'media_index':2,'duration':5,'source_window':{'start':3,'end':8}}]
        with self.assertRaisesRegex(RuntimeError,'repetido'):validate_video_beats(beats,self.assets)

    def test_exact_subject_needs_reviewed_evidence(self):
        t=VideoTimeline(self.assets)
        with self.assertRaises(RuntimeError):
            t.choose(self.scene,'A arma Teste',2,list(self.assets.values()),['Teste'])
        w=self.scene['visual_windows']['1'][0]
        w.update(reviewed=True,evidence='review/frame-12.jpg',subjects=['Teste'],semantic_categories=['weapons'])
        self.assertEqual(t.choose(self.scene,'A arma Teste',2,list(self.assets.values()),['Teste'])[0]['index'],1)

    def test_missing_and_out_of_bounds_intervals_blocked(self):
        for b in [{'media_index':1,'duration':2},
                  {'media_index':1,'duration':3,'source_window':{'start':59,'end':62}}]:
            with self.assertRaises(RuntimeError):validate_video_beats([b],self.assets)

    def test_reserves_frame_rounding_without_overlap(self):
        t=VideoTimeline(self.assets)
        a=t.choose(self.scene,'Combate',1.011,list(self.assets.values()))
        b=t.choose(self.scene,'Combate',1.011,list(self.assets.values()))
        self.assertAlmostEqual(b[1],a[3]['reserved_end'])

class PronunciationTests(unittest.TestCase):
    def test_alias_only_changes_complete_names_in_speech(self):
        original='Cyberpunk 2077 e Cyberpunkers. CYBERPUNK!'
        self.assertEqual(spoken_text(original),'Sáiber pânk 2077 e Cyberpunkers. Sáiber pânk!')
        self.assertIn('Cyberpunk 2077',original)

    def test_longest_alias_wins_and_does_not_recurse(self):
        self.assertEqual(spoken_text('Night City',{'Night':'Náit','Night City':'Night cíti'}),'Night cíti')

    def test_word_events_preserve_editorial_text_and_real_pauses(self):
        original='Cyberpunk chega. Invasão digital.'
        events=[{'type':'WordBoundary','text':w,'offset':int(t*1e7)}
                for w,t in [('Sáiber',0.1),('pânk',0.4),('chega',0.8),('Invasão',2.1),('digital',2.5)]]
        phrases=measured_phrases(original,events,10,3,1)
        self.assertEqual(phrases[0]['text'],'Cyberpunk chega.')
        self.assertEqual(phrases[0]['end'],12.1)
        self.assertEqual(phrases[1]['start'],12.1)
        self.assertEqual(phrases[-1]['end'],13)

    def test_unmatched_events_never_claim_measured_timing(self):
        with self.assertRaisesRegex(RuntimeError,'QUALITY_BLOCK'):
            measured_phrases('Cyberpunk chega.',[],0,3,1)

if __name__=='__main__':unittest.main()

class DirectorIntegrationTests(unittest.TestCase):
    def test_three_scenes_keep_unique_intervals_and_pass_semantic_gate(self):
        import contextlib
        import io
        import json
        import os
        import tempfile
        from pathlib import Path
        from src import director_v4, semantic_gate
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'output').mkdir()
            scenes=[];segments=[];phrases=[]
            titles=['Combate intenso','Invasão digital','Cidade futurista']
            cats=['combat','hacking','settlement']
            assets=[]
            for i,(title,cat) in enumerate(zip(titles,cats),1):
                assets.append({'index':i,'type':'video','duration':30,'approved':True,
                               'url':f'https://official/{i}.mp4','role':f'official_context_{i}'})
                scenes.append({'title':title,'paragraph':i,'media_indices':[i],
                               'visual_windows':{str(i):[{'start':0,'end':30,'semantic_categories':[cat]}]}})
                segments.append({'text':title,'start':(i-1)*12,'end':i*12,'duration':12})
                for j in range(2):
                    phrases.append({'paragraph':i,'sentence':j+1,'text':title,
                                    'start':(i-1)*12+j*6,'end':(i-1)*12+(j+1)*6,'duration':6})
            for name,data in [('auto-media-plan.json',{'scenes':scenes,'short_hooks':titles}),
                              ('clips.json',{'assets':assets}),
                              ('voice-timings.json',{'segments':segments,'phrases':phrases})]:
                (root/'output'/name).write_text(json.dumps(data))
            previous=os.getcwd()
            try:
                os.chdir(root)
                with contextlib.redirect_stdout(io.StringIO()):
                    director_v4.main()
                    semantic_gate.main('output/auto-media-plan.json','output/clips.json')
                result=json.loads(Path('output/render.json').read_text())
                for scene in result['scenes']:
                    self.assertEqual([b['source_window']['start'] for b in scene['beats']],[0,6])
                self.assertEqual(json.loads(Path('output/short-picks.json').read_text())['scene_indexes'],[0,1,2])
            finally:
                os.chdir(previous)
