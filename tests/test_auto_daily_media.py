import unittest

from src.auto_daily import canonical_media, media_mix


class AutoDailyMediaTests(unittest.TestCase):
    def test_watch_and_embed_of_same_youtube_video_count_once(self):
        media = canonical_media([
            ("video", "https://www.youtube.com/watch?v=pry9pkfKUJk"),
            ("video", "https://www.youtube.com/embed/pry9pkfKUJk?feature=oembed"),
            ("image", "https://example.test/grounded.jpg"),
        ])
        self.assertEqual(media_mix(media)["videos"], 1)
        self.assertEqual(sum(1 for kind, _ in media if kind == "video"), 1)

    def test_distinct_youtube_ids_remain_distinct_sources(self):
        media = canonical_media([
            ("video", "https://www.youtube.com/watch?v=pry9pkfKUJk"),
            ("video", "https://www.youtube.com/watch?v=anotherVideo123"),
        ])
        self.assertEqual(media_mix(media)["videos"], 2)


if __name__ == "__main__":
    unittest.main()
