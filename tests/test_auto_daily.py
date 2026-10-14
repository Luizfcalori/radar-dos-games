import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.auto_daily import make_script
from src.narration_qa import main as narration_qa


class SourceGroundedNarrationTests(unittest.TestCase):
    def test_announcement_script_uses_facts_not_keyword_fragments(self):
        candidate = {
            "title": "Warhammer Survivors launches November 10, new characters revealed",
            "summary": "Today, we're excited to announce that Warhammer Survivors launches on PS5 November 10. To mark the occasion we're also revealing two characters in our latest trailer. Fans may have noticed Morvenn Vahl in the game's key art.",
            "url": "https://blog.playstation.com/2026/10/06/example/",
        }
        parser = SimpleNamespace(paragraphs=[], media=[("video", "https://example.com/trailer.mp4")])
        script = make_script(candidate, parser)
        self.assertIn("10 de novembro", script)
        self.assertIn("novos personagens", script)
        self.assertIn("Warhammer Survivors", script)
        self.assertNotIn("Warhammer, Vahl, Survivors", script)
        self.assertNotIn("we're", script.lower())
        self.assertNotIn("eagle-eyed fans", script.lower())

    def test_narration_qa_blocks_meta_production_sermon(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "script.txt"
            path.write_text(
                "É preciso usar o tempo necessário para não repetir as mesmas imagens. "
                "A montagem final deve evitar repetir cenas para preencher tempo.",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "narração contém linguagem meta/privada"):
                narration_qa(str(path))

    def test_narration_qa_blocks_english_leakage_and_keyword_salad(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "script.txt"
            path.write_text(
                "Entre os principais destaques estão Warhammer, Vahl, Survivors, we're.\n"
                "Today, we're excited to announce the update.",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "narração contém linguagem meta/privada"):
                narration_qa(str(path))


if __name__ == "__main__":
    unittest.main()
