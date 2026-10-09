"""Regression tests for the user-approved full-frame GTA6 Shorts layout."""
import unittest
from pathlib import Path
from unittest.mock import patch
from src import shorts_v4

class ClassicShortLayoutTests(unittest.TestCase):
    def test_approved_template_is_persistent_and_contains_all_sections(self):
        f = shorts_v4.classic_short_filter("GTA 6 NA RETA FINAL", "0xE06080")
        for fragment in (
            "RADAR DOS GAMES", "GTA 6 NA RETA FINAL",
            "CONFIRA O CONTEÚDO COMPLETO", "VÍDEO COMPLETO NO CANAL",
            "drawbox=x=0:y=112:w=1080:h=285",
            "drawbox=x=25:y=470:w=1030:h=535",
            "drawbox=x=96:y=525:w=888:h=430",
            "drawbox=x=250:y=1505:w=580:h=58",
            "drawbox=x=245:y=1569:w=590:h=64",
            "force_original_aspect_ratio=decrease",
            shorts_v4.COLOR_FILTER,
            "format=yuv420p[v]",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, f)
        self.assertNotIn("enable='between", f)
        self.assertNotIn("enable='gte", f)
        self.assertNotIn("force_original_aspect_ratio=increase[fg]", f)
        self.assertEqual(shorts_v4.SHORTS_LAYOUT_ID, "RADAR_SHORTS_CLASSIC_V1")

    @patch.object(shorts_v4, "accent_from_asset", return_value="0xE06080")
    @patch.object(shorts_v4, "sh")
    def test_all_beats_have_identical_classic_frame(self, run, accent):
        asset = {"type":"image", "path":"placeholder.png"}
        for idx in (1,2,3):
            shorts_v4.render_vertical_piece(asset, 0.5, Path("ignored.mp4"), idx,
                                            headline="GTA 6 NA RETA FINAL",
                                            keyword="MISSÕES",first=idx==1,last=idx==3)
        filters = []
        for c in run.call_args_list:
            cmd=c.args[0]
            filters.append(cmd[cmd.index("-filter_complex")+1])
        self.assertEqual(len(filters),3)
        self.assertEqual(filters[0],filters[1])
        self.assertEqual(filters[1],filters[2])
        self.assertIn("CONFIRA O CONTEÚDO COMPLETO",filters[2])
        self.assertIn("VÍDEO COMPLETO NO CANAL",filters[1])

if __name__ == "__main__":
    unittest.main()
