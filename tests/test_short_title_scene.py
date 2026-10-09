"""Regression: hooks must fit screen and narrate the promised scene."""
import unittest

from src.director_v4 import pick_shorts_for_hooks, hook_scene_score


def scene(title, narration):
    return {"title": title, "subtitle": "ARC RAIDERS • RADAR DOS GAMES",
            "beats": [{"phrase": 1,"text":narration,"duration": 29.0,
                       "media_index":1}]}


class ShortTitleAndSceneTests(unittest.TestCase):
    def test_short_hooks_match_actual_scene_not_game_name(self):
        scenes = [
            scene("EDIÇÕES E BÔNUS", "ARC Raiders chegou em oito de outubro e traz nova atualização."),
            scene("OUTROS DETALHES", "ARC Raiders tem muitas mudanças."),
            scene("PENDOLA PASS", "O mapa Pendola Pass é uma região italiana coberta de neve. "
                  "Explore a vila e o observatório no cenário congelado."),
            scene("COMBATE", "ARC Raiders tem novos riscos em combate."),
            scene("FRIGATE", "A Frigate desafia Raiders nos céus."),
            scene("NOVOS INIMIGOS", "O Bully avança, o Skulker ataca e a Hydra "
                  "protege áreas estratégicas."),
            scene("ARMAS", "A nova Stiletto e a Bantam são armas inéditas."),
            scene("ITENS", "O Grappling Hook amplia a mobilidade."),
            scene("OUTPOST", "O Outpost tem novos módulos."),
            scene("HABILIDADES", "A árvore de habilidades muda."),
            scene("RECOMPENSAS", "O Reward Pass apresenta novas recompensas."),
            scene("PATCH", "Frozen Trail inclui várias correções."),
            scene("PLATAFORMAS", "ARC Raiders pode ser experimentado gratuitamente "
                  "entre oito e doze de outubro. A oferta é um teste grátis de 8 a 12."),
            scene("FINAL", "A próxima experiência planejada chega em outubro."),
        ]
        hooks=["ARC RAIDERS GRÁTIS ATÉ 12 DE OUTUBRO!",
               "PENDOLA PASS: O NOVO MAPA CONGELADO DE ARC RAIDERS",
               "BULLY, SKULKER E HYDRA: TRÊS NOVOS INIMIGOS"]
        picks, _=pick_shorts_for_hooks(scenes,hooks)
        self.assertEqual(picks,[12,2,5])
        self.assertGreater(hook_scene_score(hooks[0],scenes[12])[0],
                           hook_scene_score(hooks[0],scenes[0])[0])

    def test_title_layout_contains_all_words_inside_safe_width(self):
        from PIL import ImageFont
        from src.shorts_v4 import FONT, title_layout, classic_short_filter
        hooks=["ARC RAIDERS GRÁTIS ATÉ 12 DE OUTUBRO!",
               "PENDOLA PASS: O NOVO MAPA CONGELADO DE ARC RAIDERS",
               "BULLY, SKULKER E HYDRA: TRÊS NOVOS INIMIGOS"]
        for hook in hooks:
            with self.subTest(hook=hook):
                layout=title_layout(hook)
                self.assertEqual(" ".join(layout["lines"]),hook.upper())
                self.assertLessEqual(len(layout["lines"]),3)
                font=ImageFont.truetype(FONT,layout["fontsize"])
                self.assertTrue(all(font.getlength(line)<=940 for line in layout["lines"]))
                filtergraph=classic_short_filter(hook,"0xFFFFFF")
                self.assertEqual(filtergraph.count("fontfile='"+FONT+"':text='"),2+len(layout["lines"]))

if __name__ == "__main__":
    unittest.main()
