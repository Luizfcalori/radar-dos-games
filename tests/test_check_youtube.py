import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import io
from contextlib import redirect_stdout

spec = importlib.util.spec_from_file_location("check_youtube", Path(__file__).resolve().parents[1] / "src/check_youtube.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class OAuthCheckTests(unittest.TestCase):
    def yt(self, items):
        client = Mock()
        client.channels.return_value.list.return_value.execute.return_value = {"items": items}
        return client

    def test_expected_channel(self):
        client = self.yt([{"id": "UC_EXPECTED", "snippet": {"title": "Radar dos Games"}}])
        self.assertEqual(check.verify_channel(client, "UC_EXPECTED"), ("UC_EXPECTED", "Radar dos Games"))
        client.channels.return_value.list.assert_called_once_with(part="id,snippet", mine=True)
        client.videos.assert_not_called()

    def test_wrong_title(self):
        with self.assertRaisesRegex(RuntimeError, "diferente"):
            check.verify_channel(
                self.yt([{"id": "UC_EXPECTED", "snippet": {"title": "Luiz Fernando Calori"}}]),
                "UC_EXPECTED",
            )

    def test_wrong_id(self):
        with self.assertRaisesRegex(RuntimeError, "ID"):
            check.verify_channel(
                self.yt([{"id": "UC_OTHER", "snippet": {"title": "Radar dos Games"}}]),
                "UC_EXPECTED",
            )

    def test_no_channel(self):
        with self.assertRaises(RuntimeError):
            check.verify_channel(self.yt([]), "UC_EXPECTED")

    def test_multiple_channels(self):
        with self.assertRaises(RuntimeError):
            check.verify_channel(
                self.yt([
                    {"id": "UC_EXPECTED", "snippet": {"title": "Radar dos Games"}},
                    {"id": "UC_OTHER", "snippet": {"title": "Outro"}},
                ]),
                "UC_EXPECTED",
            )

    def test_missing_secrets_fail_without_exposing_values(self):
        output = io.StringIO()
        with patch.dict(check.os.environ, {"YT_CLIENT_SECRET": "private-value"}, clear=True), redirect_stdout(output):
            self.assertEqual(check.main(), 1)
        self.assertIn("YT_REFRESH_TOKEN", output.getvalue())
        self.assertNotIn("private-value", output.getvalue())


if __name__ == "__main__":
    unittest.main()
