import tempfile
import unittest
from pathlib import Path

from src.media import sha256_file


class MediaDeduplicationTests(unittest.TestCase):
    def test_identical_video_bytes_have_same_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.mp4"
            second = Path(tmp) / "second.mp4"
            first.write_bytes(b"video bytes" * 1000)
            second.write_bytes(b"video bytes" * 1000)
            self.assertEqual(sha256_file(first), sha256_file(second))

    def test_different_video_bytes_have_different_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.mp4"
            second = Path(tmp) / "second.mp4"
            first.write_bytes(b"video A")
            second.write_bytes(b"video B")
            self.assertNotEqual(sha256_file(first), sha256_file(second))

    def test_hashing_works_with_small_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "video.mp4"
            path.write_bytes(b"0123456789" * 100)
            self.assertEqual(sha256_file(path, chunk_size=7), sha256_file(path, chunk_size=1024))


if __name__ == "__main__":
    unittest.main()
