import unittest

from social_bot.bot import Interaction, decide


class SocialBotDecisionTests(unittest.TestCase):
    def make(self, text, **kwargs):
        return Interaction(
            platform="youtube",
            interaction_id=kwargs.pop("interaction_id", "c1"),
            parent_id="c1",
            author="viewer",
            text=text,
            **kwargs,
        )

    def test_praise_can_auto_reply(self):
        d = decide(self.make("Vídeo top demais!"))
        self.assertEqual(d["action"], "reply")
        self.assertEqual(d["category"], "praise")
        self.assertTrue(d["reply"])

    def test_question_requires_approval(self):
        d = decide(self.make("Quando esse jogo lança?"))
        self.assertEqual(d["action"], "approval")
        self.assertEqual(d["category"], "question")

    def test_spam_is_ignored(self):
        d = decide(self.make("me segue https://example.com"))
        self.assertEqual(d["action"], "ignore")
        self.assertEqual(d["category"], "spam")

    def test_own_comment_is_ignored(self):
        d = decide(self.make("boa", is_own=True))
        self.assertEqual(d["action"], "ignore")

    def test_already_replied_is_ignored(self):
        d = decide(self.make("show", already_replied=True))
        self.assertEqual(d["action"], "ignore")

    def test_emoji_reaction_can_auto_reply(self):
        d = decide(self.make("🔥🔥🔥"))
        self.assertEqual(d["action"], "reply")
        self.assertEqual(d["category"], "hype")

    def test_ambiguous_goes_to_approval(self):
        d = decide(self.make("GTA 6"))
        self.assertEqual(d["action"], "approval")


if __name__ == "__main__":
    unittest.main()
