"""Blocking regression tests for the Radar editorial anti-repetition policy."""
import tempfile
import unittest
from pathlib import Path

from src.repetition_policy import (
    MAX_STATIC_BEAT_SECONDS, StaticTracker, asset_identity, match_score,
    qa_report, replace_short_repeats, subject_ok, validate_master, validate_short,
)


class RepetitionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=Path(self.tmp.name)
        self.pic=root/"reward.jpg"
        self.same=root/"duplicate-reward.jpg"
        self.pic.write_bytes(b"same reward art")
        self.same.write_bytes(b"same reward art")
        self.reward={"index":5,"path":str(self.pic),"type":"image","approved":True,
                     "role":"official_subject_reference_10",
                     "source_label":"Reward Pass cosmetics outfits",
                     "url":"https://official.example/RewardPass_Outfits.jpg"}
        self.duplicate={**self.reward,"index":6,"path":str(self.same)}
        self.video={"index":9,"path":str(root/"gameplay.mp4"),"type":"video",
                    "role":"official_steam_gameplay","approved":True,
                    "url":"https://steam.example/clip.mp4"}
        self.assets={5:self.reward,6:self.duplicate,9:self.video}
    def tearDown(self):
        self.tmp.cleanup()

    def beat(self,idx,secs=3.0,text="O Reward Pass oferece recompensas"):
        return {"media_index":idx,"duration":secs,"text":text}

    def test_picture_repeated_fifty_times_is_blocked(self):
        scenes=[{"beats":[self.beat(5)]*50}]
        with self.assertRaisesRegex(RuntimeError,"QUALITY_BLOCK"):
            validate_master(scenes,self.assets)

    def test_exact_duplicate_file_is_same_asset(self):
        self.assertEqual(asset_identity(self.reward),asset_identity(self.duplicate))
        scenes=[{"beats":[self.beat(5)]},{"beats":[self.beat(9)]},
                {"beats":[self.beat(9)]},{"beats":[self.beat(6)]}]
        with self.assertRaisesRegex(RuntimeError,"QUALITY_BLOCK"):
            validate_master(scenes,self.assets)

    def test_static_cooldown_and_duration(self):
        tracker=StaticTracker()
        self.assertTrue(tracker.can_use(self.reward,"Reward Pass",1,0,3))
        tracker.record(self.reward,1,0,3)
        self.assertFalse(tracker.can_use(self.reward,"Reward Pass",2,10,3))
        self.assertFalse(tracker.can_use(self.reward,"Reward Pass",4,30,3))
        self.assertFalse(tracker.can_use(self.reward,"Reward Pass",5,55,4))

    def test_unrelated_picture_cannot_fill_other_topic(self):
        self.assertFalse(subject_ok("O novo mapa Pendola Pass é coberto de neve",self.reward))
        self.assertFalse(subject_ok("A Frigate surge nos céus",self.reward))
        self.assertTrue(subject_ok("As recompensas do Reward Pass incluem cosméticos",self.reward))
        with self.assertRaisesRegex(RuntimeError,"QUALITY_BLOCK"):
            validate_master([{"beats":[self.beat(5,3,"O Bully ataca")]}],self.assets)

    def test_short_static_once_and_max_3_5_seconds(self):
        validate_short([self.beat(5)],self.assets)
        with self.assertRaisesRegex(RuntimeError,"QUALITY_BLOCK"):
            validate_short([self.beat(5),self.beat(5)],self.assets)
        with self.assertRaisesRegex(RuntimeError,"QUALITY_BLOCK"):
            validate_short([self.beat(5,3.6)],self.assets)

    def test_short_rebuild_swaps_duplicate_still_for_source_video(self):
        scene={"media_first_assets":[5,9],
               "visual_windows":{"9":[{"start":12,"end":20}]},
               "beats":[self.beat(5,2.7),self.beat(5,2.8)]}
        rebuilt=replace_short_repeats(scene,self.assets)
        self.assertEqual([b["media_index"] for b in rebuilt],[5,9])
        self.assertEqual(rebuilt[1]["source_window"]["start"],12)
        self.assertEqual([b["media_index"] for b in scene["beats"]],[5,5])

    def test_qa_uses_actual_short_source_beats(self):
        scenes=[{"beats":[self.beat(5)]}]
        clips={"assets":list(self.assets.values())}
        report=qa_report(scenes,clips,shorts=[{"media_beats":[self.beat(5)]}])
        self.assertEqual(report["status"],"APPROVED")
        with self.assertRaisesRegex(RuntimeError,"QUALITY_BLOCK"):
            qa_report(scenes,clips,shorts=[{"media_beats":[self.beat(5),self.beat(5)]}])


if __name__=="__main__":
    unittest.main()
