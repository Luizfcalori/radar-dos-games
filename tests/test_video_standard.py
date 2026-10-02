import importlib.util
from pathlib import Path


def load_render_module():
    path = Path(__file__).resolve().parents[1] / "src" / "render.py"
    spec = importlib.util.spec_from_file_location("radar_render", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_approved_card_geometry():
    r = load_render_module()
    assert (r.CARD_X, r.CARD_Y, r.CARD_W, r.CARD_H) == (62, 850, 1240, 138)
    assert (r.TITLE_X, r.TITLE_Y) == (102, 869)
    assert (r.SUBTITLE_X, r.SUBTITLE_Y) == (102, 927)
    assert r.CARD_ACCENT_W == 10


def test_approved_card_timing_and_colors():
    r = load_render_module()
    assert r.CARD_IN == 0.45
    assert r.CARD_MAX_SECONDS == 5.8
    assert r.CARD_BG == "black@0.68"
    assert r.CARD_ACCENT == "0x00DCC8@0.96"
    assert r.SUBTITLE_COLOR == "0x7FE8FF"


def test_four_cut_scene_cadence():
    r = load_render_module()
    assert r.scene_sequence([1, 2], 4) == [1, 2, 1, 2]
    assert r.scene_sequence([1, 2, 3], 4) == [1, 2, 3, 1]


def test_gameplay_has_priority_when_available():
    r = load_render_module()
    assets = {
        1: {"path": "image.jpg", "type": "image"},
        2: {"path": "gameplay.mp4", "type": "video"},
        3: {"path": "image2.png", "type": "image"},
    }
    assert r.ordered_scene_indices([1, 2, 3], assets) == [2, 1, 3]
