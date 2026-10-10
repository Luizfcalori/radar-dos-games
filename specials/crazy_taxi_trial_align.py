#!/usr/bin/env python3
"""Keep Brazil-map narration bound to the two verified Brazil trailers.

Only changes a generated test storyboard after downloading and inspecting real
footage. No fabricated scenes, no cloned video, no edits to daily code.
"""
import json
from pathlib import Path

out=Path("output")
planpath=out/"auto-media-plan.json"
plan=json.loads(planpath.read_text(encoding="utf-8"))
clips=json.loads((out/"clips.json").read_text(encoding="utf-8"))
assets=[a for a in clips.get("assets",[]) if a.get("approved") and a.get("type")=="video"]
urls={
 "brazil":("qdStLWu0RAs","ci_eiuGio0M"),
 "multiplayer":("a3mF9zwozJk",),
}
def matches(group):
    return [a for a in assets if any(k in str(a.get("url") or "") for k in urls[group])]
def restrict(scene_idx, matched, topic):
    scene=plan["scenes"][scene_idx]
    approved={int(a["index"]):a for a in matched}
    windows=scene.get("visual_windows") or {}
    usable={str(i):w for k,w in windows.items() if (i:=int(k)) in approved and w}
    if not usable:
        raise RuntimeError(f"QUALITY_BLOCK: no matching confirmed footage for {topic}, scene {scene_idx+1}")
    scene["media_first_assets"]=list(map(int,usable.keys()))
    scene["media_indices"]=list(map(int,usable.keys()))
    scene["allowed_roles"]=list(dict.fromkeys(approved[i]["role"] for i in scene["media_first_assets"]))
    scene["allowed_role_prefixes"]=[]
    scene["visual_windows"]=usable
    scene["semantic_subject"]=topic
    print(f"BOUND_SCENE {scene_idx+1} {topic} -> {scene['media_first_assets']}",flush=True)

brazil=matches("brazil")
if len(brazil)<2:
    raise RuntimeError("QUALITY_BLOCK: both verified official Brazil trailers not downloaded")
for index in (1,2,3):  # Scenes 2–4: announcement, Brazilian retailers and scenery.
    restrict(index,brazil,"Brazil map - official SEGA promotional footage")
multi=matches("multiplayer")
if multi:
    restrict(8,multi,"Crazy Taxi World Tour - official multiplayer footage")
planpath.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
