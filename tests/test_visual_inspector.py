"""Regression tests for genuinely decoded-frame technical QA and storyboard bindings."""
import unittest
from src.visual_inspector import choose_windows, deduplicate, sample_metrics, perceptual_hash


class VisualInspectorTests(unittest.TestCase):
    def test_each_frame_metrics_detect_darkness_and_motion(self):
        black = bytes([0] * (64 * 36))
        bright = bytes(([40, 80, 160, 220] * (64 * 36 // 4)))
        m = sample_metrics(black, bright)
        self.assertLess(m[0], 14)
        self.assertGreater(m[1], .90)
        self.assertGreater(m[3], 1)
        self.assertEqual(len(perceptual_hash(bright)), 64)

    def test_usable_timecodes_exclude_dark_ranges(self):
        seconds = {i: {"frames": 30, "good": 30} for i in range(20)}
        for i in range(6, 11):
            seconds[i] = {"frames": 30, "good": 0}
        windows = choose_windows(seconds, 20)
        self.assertTrue(windows)
        self.assertTrue(all(not (w["start"] < 11 and w["end"] > 6) for w in windows))
        self.assertTrue(all(w["end"] - w["start"] >= 2.6 for w in windows))

    def test_duplicate_encodes_share_same_footage(self):
        rows = [
            {"index": 1, "type": "video", "duration": 150,
             "perceptual_signatures": ["0"*64, "1"*64, "01"*32],
             "usable_windows": [{"start": 4, "end": 9}]},
            {"index": 2, "type": "video", "duration": 150.2,
             "perceptual_signatures": ["0"*64, "1"*64, "01"*32],
             "usable_windows": [{"start": 4, "end": 9}]},
        ]
        deduplicate(rows)
        self.assertEqual(rows[1]["duplicate_of"], 1)
        self.assertEqual(rows[1]["usable_windows"], [])

    def test_visual_inventory_limits_candidate_clips(self):
        from src.media_first import compile_storyboard
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p/"video_a.mp4").write_bytes(b"v")
            (p/"video_b.mp4").write_bytes(b"v")
            (p/"image.jpg").write_bytes(b"img")
            assets = [
                {"index": 1, "path": str(p/"video_a.mp4"), "type": "video",
                 "role": "official_gameplay_01", "source": "steam", "approved": True,
                 "duration": 70, "url": "https://steam.example/video"},
                {"index": 2, "path": str(p/"video_b.mp4"), "type": "video",
                 "role": "official_gameplay_01", "source": "steam", "approved": True,
                 "duration": 70, "url": "https://steam.example/video2"},
                {"index": 3, "path": str(p/"image.jpg"), "type": "image",
                 "role": "official_context_03", "source": "official", "approved": True,
                 "url": "https://example.com/image_Bully.jpg"},
            ]
            plan = {"topic": "ARC Raiders", "scenes": [
                {"title": "MÁQUINAS"}, {"title": "BULLY"}, {"title": "ATUALIZAÇÃO"}]}
            inventory = {"status": "ANALYZED", "assets": [
                {"index": 1, "type": "video", "usable_windows": [{"start": 5, "end": 12}]},
                {"index": 2, "type": "video", "duplicate_of": 1, "usable_windows": []},
            ]}
            outline = "As máquinas avançam.\n\nO Bully ataca rapidamente.\n\nNova atualização chegou."
            built, text, report = compile_storyboard(plan,
                {"assets": assets, "publishable_media": True}, {}, outline, inventory)
            self.assertTrue(text)
            for scene in built["scenes"]:
                self.assertEqual(scene["media_indices"][0], 1)
                self.assertNotIn(2, scene["media_first_assets"])
                self.assertEqual(scene["visual_windows"]["1"][0]["start"], 5)
            self.assertIn(3, built["scenes"][1]["preferred_media_indices"])
            self.assertEqual(report["source_frames_analyzed"], 0)


if __name__ == "__main__":
    unittest.main()
