"""Regression tests for the Premium V4 Master-derived Shorts pipeline."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from src import shorts_v4


class MasterCutShortTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
    def test_probe_requires_and_detects_original_audio_stream(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "master.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
                "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", str(source)
            ], check=True)
            info = shorts_v4.probe(source)
            self.assertTrue(info["video"])
            self.assertTrue(info["audio"])
            self.assertGreater(info["duration"], 1.9)

    def test_pipeline_contract_requires_master_crops_and_original_audio(self):
        self.assertEqual(shorts_v4.SHORTS_LAYOUT_ID, "RADAR_PREMIUM_MASTER_CROP_V1")
        self.assertEqual(shorts_v4.SOURCE_POLICY, "master_timeline_crops_preserve_original_audio")
        self.assertEqual(shorts_v4.RENDER_POLICY, "direct_master_timeline_crop_with_original_narration")
        self.assertIn("no_an", shorts_v4.AUDIO_POLICY)
        self.assertIn("no_silent_rebuild", shorts_v4.AUDIO_POLICY)

    def test_renderer_maps_master_audio_and_never_disables_audio(self):
        source = Path("src/shorts.py").read_text(encoding="utf-8")
        self.assertIn('"0:a?"', source)
        self.assertNotIn('"-an"', source)
        wrapper = Path("src/shorts_v4.py").read_text(encoding="utf-8")
        self.assertIn('Path("output/master.mp4")', wrapper)
        self.assertIn('len(shorts)!=3', wrapper)
        self.assertIn('not info["audio"]', wrapper)


if __name__ == "__main__":
    unittest.main()
