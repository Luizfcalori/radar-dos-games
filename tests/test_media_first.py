import hashlib
import tempfile
import unittest
from pathlib import Path
from src.media_first import compile_storyboard, relevance
from src.director_v4 import eligible, phrase_asset_match, pick_shorts_for_hooks

class MediaFirstTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        p=Path(self.tmp.name)
        (p/"soldados.mp4").write_bytes(b"video")
        (p/"vegas.png").write_bytes(b"image")
        self.assets=[
            dict(index=7,path=str(p/"soldados.mp4"),type="video",duration=35,
                 role="official_gameplay_01",source="https://news.example/test",
                 url="https://news.example/soldados.mp4",approved=True),
            dict(index=13,path=str(p/"vegas.png"),type="image",duration=0,
                 role="official_context_02",source="https://news.example/test",
                 url="https://news.example/vegas.png",approved=True)]
        self.plan={"topic":"Battlefield 6","scenes":[
            {"paragraph":i,"title":title} for i,title in enumerate(
                ("SOLDADOS","VEGAS","NOVIDADES"),1)]}
        self.outline="Combates de soldados.\n\nLas Vegas em destaque.\n\nNovas informações."
        self.clips={"assets":self.assets,"publishable_media":True}
    def tearDown(self):self.tmp.cleanup()
    def test_inventory_before_voice_and_three_scene_binding(self):
        plan,script,report=compile_storyboard(self.plan,self.clips,{"url":"https://news.example/test","title":"Battlefield 6"},self.outline)
        self.assertEqual(report["policy"],"MEDIA_FIRST_V1")
        self.assertEqual(len(report["scenes"]),3)
        self.assertEqual(plan["media_first_policy"],"MEDIA_FIRST_V1")
        self.assertEqual(report["script_sha256"],hashlib.sha256(script.encode()).hexdigest())
        for s in plan["scenes"]:
            self.assertEqual(s["media_first_assets"],[7,13])
            self.assertEqual(len(s["allowed_roles"]),2)
        # Hashed filenames still receive a topic label only because the image
        # is served from the exact official article URL.
        self.assertEqual(self.assets[1]["source_label"],"Battlefield 6")
    def test_official_image_with_opaque_cdn_name_uses_verified_source_host(self):
        # Fight Night lesson: an official EA CDN filename may be opaque, and
        # the source page can differ from the selected landing page on the same host.
        self.assets[1].update({
            "url":"https://cdn.news.example/assets/9f8e7d6c5b4a.png",
            "source":"https://news.example/official-game-page",
            "role":"official_subject_reference_01",
            "source_label":"",
        })
        plan,script,report=compile_storyboard(
            self.plan,self.clips,
            {"url":"https://news.example/test","title":"Battlefield 6"},
            self.outline
        )
        self.assertIn(13, plan["scenes"][0]["media_first_assets"])
        self.assertEqual(self.assets[1]["source_label"],"Battlefield 6")

    def test_unrelated_host_official_role_is_not_admitted_as_contextual_fallback(self):
        self.assets[1].update({
            "url":"https://cdn.unrelated.example/assets/9f8e7d6c5b4a.png",
            "source":"https://unrelated.example/official-game-page",
            "role":"official_subject_reference_01",
            "source_label":"",
        })
        # The ordinary image can still be chosen by explicit relevance; it must
        # not gain the privileged contextual-image fallback solely from its role.
        plan,script,report=compile_storyboard(
            self.plan,self.clips,
            {"url":"https://news.example/test","title":"Battlefield 6"},
            self.outline
        )
        self.assertNotIn(13, plan["scenes"][2]["media_first_assets"])

    def test_final_script_digest_is_byte_stable(self):
        plan,script,report=compile_storyboard(self.plan,self.clips,{"url":"https://news.example/test","title":"Battlefield 6"},self.outline)
        data=script.encode("utf-8")
        self.assertEqual(report["script_sha256"],hashlib.sha256(data).hexdigest())
        self.assertTrue(script.endswith("\n"))
    def test_metadata_hashtag_does_not_change_approved_hook(self):
        from src.premium_v4_qa import norm_short_title
        self.assertEqual(norm_short_title("BATTLEFIELD 6 CHEGA AO GAME PASS! #Shorts"),
                         norm_short_title("BATTLEFIELD 6 CHEGA AO GAME PASS!"))
    def test_missing_media_blocks(self):
        self.assets[0]["path"]="/nonexistent/radar-test-asset.mp4"
        with self.assertRaises(RuntimeError):
            compile_storyboard(self.plan,self.clips,{"url":"https://news.example/test","title":"Battlefield 6"},self.outline)
    def test_different_role_cannot_be_silently_substituted(self):
        with self.assertRaises(RuntimeError):
            eligible({"title":"Cena","allowed_roles":["not_in_downloads"],"media_first_assets":[7]},{7:self.assets[0]})
    def test_same_role_clips_are_not_interchangeable(self):
        # Two clips from the Steam CDN can have one role but different IDs.
        # A scene bound to clip 7 must never silently receive clip 19.
        alternate=dict(self.assets[0],index=19,source_label="second trailer")
        scene={"title":"Cena congelada","allowed_roles":["official_gameplay_01"],
               "media_first_assets":[7]}
        results=eligible(scene,{7:self.assets[0],19:alternate})
        self.assertEqual([int(a["index"]) for a in results],[7])
        with self.assertRaises(RuntimeError):
            eligible({**scene,"media_first_assets":[123]},
                     {7:self.assets[0],19:alternate})

    def test_curated_same_game_fallback_is_available_but_not_implicit(self):
        alternate=dict(self.assets[0],index=19,source_label="official airboat clip")
        scene={"title":"Barco","allowed_roles":["official_gameplay_01"],
               "media_first_assets":[7],"fallback_media_indices":[19],
               "allow_same_source_role_fallback":True}
        results=eligible(scene,{7:self.assets[0],19:alternate})
        self.assertEqual([int(a["index"]) for a in results],[7,19])
        strict={**scene,"allow_same_source_role_fallback":False}
        self.assertEqual([int(a["index"]) for a in eligible(strict,{7:self.assets[0],19:alternate})],[7])

    def test_boat_phrase_matches_official_airboat_clip_label(self):
        boat=dict(self.assets[0],source_label="Rockstar Games official Instagram — GTA VI airboat gameplay clip")
        trailer=dict(self.assets[0],index=19,source_label="Rockstar Games official GTA VI Launch Trailer")
        self.assertGreater(phrase_asset_match("Um barco atravessando canais e áreas alagadas",boat),
                           phrase_asset_match("Um barco atravessando canais e áreas alagadas",trailer))

    def test_three_short_hooks_map_to_three_distinct_narration_scenes(self):
        scenes = [
            {"title":"ABERTURA","subtitle":"GRAND THEFT AUTO VI","beats":[
                {"text":"Faltam apenas três dias para a chegada de Grand Theft Auto VI. A Rockstar abre as portas de Vice City e Leonida.", "duration":20}
            ]},
            {"title":"PRÉ-CARREGAMENTO DIGITAL","subtitle":"INFORMAÇÃO OFICIAL DA ROCKSTAR","beats":[
                {"text":"A Rockstar confirmou que o pré-carregamento digital de GTA 6 já está disponível para quem reservou o jogo.", "duration":20}
            ]},
            {"title":"JASON E LUCIA","subtitle":"GRAND THEFT AUTO VI","beats":[
                {"text":"Jason e Lucia estão prestes a entrar em ação em uma sequência de perseguições e encontros.", "duration":20}
            ]},
            {"title":"DATA DE LANÇAMENTO","subtitle":"INFORMAÇÃO OFICIAL DA ROCKSTAR","beats":[
                {"text":"A data está confirmada: GTA 6 chega em 19 de novembro de 2026.", "duration":20}
            ]},
        ]
        hooks = [
            "PRÉ-CARREGAMENTO DIGITAL DE GTA 6 JÁ ESTÁ DISPONÍVEL!",
            "JASON E LUCIA ESTÃO PRESTES A ENTRAR EM AÇÃO!",
            "DATA CONFIRMADA: GTA 6 CHEGA EM 19 DE NOVEMBRO!",
        ]
        picks, matches = pick_shorts_for_hooks(scenes, hooks)
        self.assertEqual(picks, [1, 2, 3])
        self.assertTrue(all(m["semantic_score"] > 0 for m in matches))

    def test_url_hints_not_automated_visual_truth(self):
        self.assertGreater(relevance("O ambiente é Vegas",self.assets[1],"Battlefield 6"),0)
        self.assertEqual(relevance("armas e monstros",self.assets[0],"Battlefield 6"),0)
if __name__=="__main__":
    unittest.main()
