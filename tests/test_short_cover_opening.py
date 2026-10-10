"""Regression tests for cover-first opening in every premium Short."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from src.premium_covers import apply_cover_opening, ffprobe_duration


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class CoverFirstOpeningTests(unittest.TestCase):
    def test_cover_is_first_frame_and_audio_duration_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            video = root / "short.mp4"
            cover = root / "short_cover.jpg"
            Image.new("RGB", (1080, 1920), (30, 240, 80)).save(cover, quality=100)
            subprocess.run([
                "ffmpeg", "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30:d=2",
                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest", str(video)
            ], check=True)
            original_duration = ffprobe_duration(video)
            result = apply_cover_opening(video, cover, duration=1.4)
            self.assertEqual(result["status"], "APPROVED")
            self.assertLessEqual(abs(ffprobe_duration(video) - original_duration), 0.12)

            frame = root / "first.jpg"
            subprocess.run([
                "ffmpeg", "-y", "-v", "error", "-i", str(video),
                "-frames:v", "1", "-q:v", "2", str(frame)
            ], check=True)
            with Image.open(cover) as expected, Image.open(frame) as actual:
                diff = ImageStat.Stat(ImageChops.difference(
                    expected.convert("RGB"), actual.convert("RGB")
                )).mean
            self.assertLess(sum(diff) / 3, 22.0)

            streams = __import__("json").loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(video)
            ], text=True))["streams"]
            self.assertTrue(any(s["codec_type"] == "audio" for s in streams))


if __name__ == "__main__":
    unittest.main()
