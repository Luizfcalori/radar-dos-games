"""Regression tests for the user-approved full-frame GTA6 Shorts layout."""
import json
import shutil
import subprocess
import tempfile
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

    @patch.object(shorts_v4, "probe_duration", return_value=0.5)
    @patch.object(shorts_v4, "accent_from_asset", return_value="0xE06080")
    @patch.object(shorts_v4, "sh")
    def test_all_beats_have_identical_classic_frame(self, run, accent, duration):
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

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe")
        and Path(shorts_v4.FONT).exists() and Path(shorts_v4.FONT_REG).exists(),
        "FFmpeg and DejaVu fonts required",
    )
    def test_synthetic_video_renders_with_approved_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "sample.mp4"
            dest = Path(folder) / "short.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                "-i", "testsrc2=size=640x360:rate=30", "-t", "1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source)
            ], check=True)
            shorts_v4.render_vertical_piece(
                {"type": "video", "path": str(source)}, 0.4, dest, 1,
                headline="GTA 6 NA RETA FINAL",
                source_window={"start":0.0,"end":0.4},
            )
            info = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(dest)
            ], text=True))
            video = next(stream for stream in info["streams"] if stream["codec_type"]=="video")
            self.assertEqual((video["width"],video["height"]), (1080,1920))
            self.assertGreater(dest.stat().st_size, 1000)

if __name__ == "__main__":
    unittest.main()
