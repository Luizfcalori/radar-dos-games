import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src import voice as voice_module


class VoiceRetryTests(unittest.TestCase):
    def test_synthesize_one_retries_transient_429_and_keeps_requested_voice(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "segment.mp3"
                calls = {"count": 0}

                class FakeCommunicate:
                    def __init__(self, text, voice, **kwargs):
                        self.voice = voice

                    async def save(self, audio_path, metadata_path):
                        calls["count"] += 1
                        if calls["count"] < 3:
                            raise RuntimeError("429 Too Many Requests")
                        Path(audio_path).write_bytes(b"fake-audio")
                        Path(metadata_path).write_text(
                            json.dumps({"type": "WordBoundary", "text": {"text": "Olá"}}) + "\\n",
                            encoding="utf-8",
                        )

                with patch.object(voice_module.edge_tts, "Communicate", FakeCommunicate), \\
                     patch.object(voice_module.asyncio, "sleep", new=AsyncMock()) as sleep:
                    events = await voice_module.synthesize_one(
                        "Olá, mundo.", output, "pt-BR-ThalitaMultilingualNeural"
                    )
                self.assertEqual(calls["count"], 3)
                self.assertEqual(len(events), 1)
                self.assertEqual(sleep.await_count, 2)
                self.assertTrue(output.exists())

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
