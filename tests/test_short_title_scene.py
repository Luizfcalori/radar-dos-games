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

    def test_master_cut_pipeline_contract_is_explicit(self):
        from src import shorts_v4
        self.assertEqual(shorts_v4.SHORTS_LAYOUT_ID, "RADAR_PREMIUM_MASTER_CROP_V1")
        self.assertEqual(shorts_v4.SOURCE_POLICY, "master_timeline_crops_preserve_original_audio")
        self.assertIn("no_an", shorts_v4.AUDIO_POLICY)
        self.assertIn("no_silent_rebuild", shorts_v4.AUDIO_POLICY)

if __name__ == "__main__":
    unittest.main()
