"""Regression: broad semantic categories must not be inferred from substrings
inside unrelated proper names or ordinary words.
"""
import unittest
from src.vision_semantics import scene_categories


class SceneCategoriesTest(unittest.TestCase):
    def test_bonaventura_is_not_an_airship(self):
        text = (
            "A Paramount prepara um filme de Cyberpunk 2077. "
            "Lorenzo di Bonaventura está envolvido na produção."
        )
        self.assertNotIn("airship", scene_categories(text))

    def test_a_real_spaceship_keeps_its_category(self):
        self.assertIn("airship", scene_categories("Uma nave sobrevoa a cidade."))
        self.assertIn("airship", scene_categories("Uma nave espacial cruza o céu."))

    def test_non_descriptive_words_are_not_subject_identifiers(self):
        self.assertNotIn("settlement", scene_categories("A velocidade melhora no jogo."))
        self.assertNotIn("interface", scene_categories("O tempo passado no jogo."))

    def test_real_subject_categories_still_match(self):
        self.assertIn("settlement", scene_categories("A cidade de Night City."))
        self.assertIn("combat", scene_categories("O combate e os inimigos."))
        self.assertIn("interface", scene_categories("Árvore de habilidades e inventário."))


if __name__ == "__main__":
    unittest.main()
