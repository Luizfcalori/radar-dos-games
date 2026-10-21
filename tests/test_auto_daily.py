import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.auto_daily import classify_topic, make_script, validate_script_context
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
                "A montagem final deve evitar repetir cenas para preencher tempo. "
                "O vídeo final precisa usar cenas diferentes para preencher o tempo.",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "narração contém linguagem meta/privada"):
                narration_qa(str(path))

    def test_narration_qa_blocks_repeated_long_headline(self):
        repeated = (
            "The Saros Zenith update out today brings more ways to play for newcomers and veterans alike"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "script.txt"
            path.write_text(
                repeated + ". A novidade chega hoje.\n\n"
                + repeated + ". O anúncio traz opções novas.\n\n"
                + repeated + ". A atualização já está disponível.",
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


class EditorialTopicGateTests(unittest.TestCase):
    def test_accepts_specific_game_news(self):
        verdict = classify_topic(
            "Warhammer Survivors launches November 10, new characters revealed",
            "Official trailer reveals two new characters and launch date."
        )
        self.assertTrue(verdict["allowed"])
        self.assertEqual(verdict["category"], "jogo-ou-noticia-de-jogo")

    def test_accepts_concrete_console_update(self):
        verdict = classify_topic(
            "Xbox update adds new accessibility features",
            "The system update adds new accessibility features and fixes."
        )
        self.assertTrue(verdict["allowed"])
        self.assertEqual(verdict["category"], "atualizacao-plataforma")

    def test_rejects_unrelated_rewards_topic(self):
        verdict = classify_topic(
            "Microsoft Rewards: points and offers this week",
            "A roundup of points and offers."
        )
        self.assertFalse(verdict["allowed"])

    def test_rejects_generic_showcase_recap_without_specific_game(self):
        verdict = classify_topic(
            "ID Xbox / IGN Showcase recap all new",
            "A general roundup of announcements without a specific game."
        )
        self.assertFalse(verdict["allowed"])

    def test_script_gate_blocks_topic_without_context(self):
        candidate = {"title": "Microsoft Rewards: points and offers this week", "summary": "A roundup of points."}
        with self.assertRaisesRegex(RuntimeError, "EDITORIAL_TOPIC_BLOCK"):
            validate_script_context(candidate, "Parágrafo um.\n\nParágrafo dois.\n\nParágrafo três.\n\nParágrafo quatro.")


    def test_script_gate_blocks_repeated_paragraphs(self):
        candidate = {
            "title": "Warhammer Survivors launches November 10, new characters revealed",
            "summary": "Official trailer reveals new characters and launch date."
        }
        repeated = "Warhammer Survivors lança em novembro e apresenta novos personagens."
        script = "\n\n".join([repeated, repeated, repeated, repeated])
        with self.assertRaisesRegex(RuntimeError, "EDITORIAL_REPETITION_BLOCK"):
            validate_script_context(candidate, script)


if __name__ == "__main__":
    unittest.main()
