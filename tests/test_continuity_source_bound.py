"""Regression: source windows must not outlive the real video duration."""
from src.continuity import VideoTimeline


def test_clip_never_overruns_actual_duration():
    asset={
        "index":1, "path":"output/media/asset_01.mp4", "type":"video",
        "role":"test", "url":"https://example.com/video.mp4",
        "approved":True, "duration":10.05
    }
    scene={"visual_windows":{
        "1":[{"start":8.0,"end":11.0,"duration":3.0,
              "semantic_categories":[]}]
    }}
    timeline=VideoTimeline({1:asset})
    picked,start,length,window=timeline.choose(scene,"trecho visual",3.0,[asset])
    assert picked["index"]==1
    assert start+length<=asset["duration"]
    assert start+window["reserved_end"]-start<=asset["duration"]


def test_repeated_reserved_interval_is_still_blocked():
    asset={
        "index":1,"path":"output/media/asset_01.mp4","type":"video",
        "role":"test","url":"https://example.com/video.mp4",
        "approved":True,"duration":10.05
    }
    timeline=VideoTimeline({1:asset})
    timeline.reserve(1,1.0,2.0)
    try:
        timeline.reserve(1,2.0,2.0)
    except RuntimeError as error:
        assert "repetido" in str(error)
    else:
        raise AssertionError("Duplicate source interval must remain prohibited")
