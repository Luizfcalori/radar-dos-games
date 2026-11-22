"""Regression tests: phrase-to-gameplay mismatch must stop production."""
import json
import tempfile
import unittest
from pathlib import Path

from src.semantic_gate import main


class FlexibleSemanticGateTests(unittest.TestCase):
    def make_files(self, root, category, phrase="Demônios avançam na arena."):
        assets={"assets":[{"index":1,"type":"video","duration":30,"approved":True,
                           "role":"official_gameplay","url":"https://official.test/gameplay.mp4"}]}
        plan={"scenes":[{"paragraph":1,"title":"Arena infernal","semantic_subject":"Arena infernal",
                         "vision_categories":["demon","arena"],"media_indices":[1],
                         "visual_windows":{"1":[{"start":0,"end":5,"reviewed":True,
                                                  "evidence":"frame-scan:1",
                                                  "semantic_categories":category,
                                                  "subjects":[]} ]},
                         "beats":[{"phrase":1,"text":phrase,"media_index":1,"duration":5,
                                   "source_window":{"start":0,"end":5}}]}]}
        clips_path=root/"clips.json";plan_path=root/"plan.json";out_path=root/"semantic.json"
        clips_path.write_text(json.dumps(assets),encoding="utf-8")
        plan_path.write_text(json.dumps(plan),encoding="utf-8")
        return plan_path,clips_path,out_path

    def test_matching_visual_category_is_approved(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.make_files(Path(folder),["demon","arena"])
            main(*(str(x) for x in paths))
            report=json.loads(paths[2].read_text(encoding="utf-8"))
            self.assertEqual(report["status"],"APPROVED")
            self.assertEqual(report["error_count"],0)

    def test_different_reviewed_gameplay_is_accepted_as_soft_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.make_files(Path(folder),["driving"])
            main(*(str(x) for x in paths))
            report=json.loads(paths[2].read_text(encoding="utf-8"))
            self.assertEqual(report["status"],"APPROVED")
            self.assertEqual(report["error_count"],0)
            self.assertEqual(report["warning_count"],1)
            self.assertEqual(report["warnings"][0]["type"],"flexible_same_game_fallback")

    def test_contextual_phrase_is_allowed_with_scene_context(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.make_files(Path(folder),["demon","arena"],phrase="A novidade muda tudo.")
            main(*(str(x) for x in paths))
            report=json.loads(paths[2].read_text(encoding="utf-8"))
            self.assertEqual(report["status"],"APPROVED")
            self.assertEqual(report["error_count"],0)
            self.assertEqual(report["warning_count"],1)

if __name__=="__main__":
    unittest.main()
