import unittest

from src.continuity import VideoTimeline


class FreshGameplayFallbackTests(unittest.TestCase):
    def test_short_unused_reviewed_fragment_is_used_before_replay(self):
        asset = {
            "index": 1,
            "type": "video",
            "duration": 5.0,
            "url": "https://example.test/gameplay.mp4",
            "approved": True,
        }
        window = {
            "start": 0.0,
            "end": 5.0,
            "reviewed": True,
            "evidence": "frame-scan:1",
            "semantic_categories": ["gameplay"],
            "subjects": [],
        }
        scene = {"visual_windows": {"1": [window]}}
        timeline = VideoTimeline({1: asset})

        first, first_start, first_length, _ = timeline.choose(
            scene, "gameplay", 4.2, [asset]
        )
        self.assertEqual(first["index"], 1)
        self.assertEqual(first_start, 0.0)
        self.assertAlmostEqual(first_length, 4.2)

        second, second_start, second_length, proof = timeline.choose(
            scene, "gameplay", 1.2, [asset]
        )
        self.assertEqual(second["index"], 1)
        self.assertGreater(second_start, 4.0)
        self.assertGreater(second_length, 0.25)
        self.assertFalse(proof["reused_source"])


if __name__ == "__main__":
    unittest.main()
