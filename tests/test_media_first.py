import hashlib
import tempfile
import unittest
from pathlib import Path
from src.media_first import compile_storyboard, relevance
from src.director_v4 import eligible

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
        plan,script,report=compile_storyboard(self.plan,self.clips,{},self.outline)
        self.assertEqual(report["policy"],"MEDIA_FIRST_V1")
        self.assertEqual(len(report["scenes"]),3)
        self.assertEqual(plan["media_first_policy"],"MEDIA_FIRST_V1")
        self.assertEqual(report["script_sha256"],hashlib.sha256(script.encode()).hexdigest())
        for s in plan["scenes"]:
            self.assertEqual(s["media_first_assets"],[7,13])
            self.assertEqual(len(s["allowed_roles"]),2)
    def test_final_script_digest_is_byte_stable(self):
        plan,script,report=compile_storyboard(self.plan,self.clips,{},self.outline)
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
            compile_storyboard(self.plan,self.clips,{},self.outline)
    def test_different_role_cannot_be_silently_substituted(self):
        with self.assertRaises(RuntimeError):
            eligible({"title":"Cena","allowed_roles":["not_in_downloads"],"media_first_assets":[7]},{7:self.assets[0]})
    def test_url_hints_not_automated_visual_truth(self):
        self.assertGreater(relevance("O ambiente é Vegas",self.assets[1],"Battlefield 6"),0)
        self.assertEqual(relevance("armas e monstros",self.assets[0],"Battlefield 6"),0)
if __name__=="__main__":
    unittest.main()
