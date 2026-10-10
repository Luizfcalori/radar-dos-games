#!/usr/bin/env python3
"""One-off Crazy Taxi media-first alignment. Never change daily production code.

Preserve Brazil-map trailer for Brazil scenes and multiplayer trailer for its
own dedicated scene. Other shots can be used only after their dedicated part.
Anti-duplication and audio/visual quality gates remain enabled.
"""
import json
from pathlib import Path

out=Path("output")
planpath=out/"auto-media-plan.json"
plan=json.loads(planpath.read_text(encoding="utf-8"))
clips=json.loads((out/"clips.json").read_text(encoding="utf-8"))
assets={int(a["index"]):a for a in clips.get("assets",[]) if a.get("approved") and a.get("type")=="video"}
scenes=plan["scenes"]
assert len(scenes)>=10

def media_for_video(video_id):
    return [idx for idx,a in assets.items() if video_id in str(a.get("url") or "")]

def update_scene(scene_idx,keep,brazil_frame_windows=None):
    scene=scenes[scene_idx]
    windows=scene.get("visual_windows") or {}
    remaining={}
    for key,wins in windows.items():
        i=int(key)
        if i not in keep or not wins:
            continue
        if brazil_frame_windows is not None and i in brazil:
            # No new or repeated footage: assign entire, visually inspected
            # 7.2-second windows to exactly one Brazil-specific scene.
            wins=[w for w in wins if any(abs(float(w["start"])-t)<0.18
                        for t in brazil_frame_windows)]
        if wins:
            remaining[str(i)]=wins
    if not remaining:
        raise RuntimeError(f"QUALITY_BLOCK scene {scene_idx+1}: no remaining matching verified video window")
    vids=set(map(int,remaining))
    imgs=[i for i in scene.get("media_first_assets") or [] if int(i) not in assets and int(i) in clips_indexes]
    scene["media_first_assets"]=sorted(vids)+imgs
    scene["media_indices"]=scene["media_first_assets"]
    scene["allowed_roles"]=list(dict.fromkeys((all_assets[i].get("role") or "") for i in scene["media_first_assets"]))
    scene["allowed_role_prefixes"]=[]
    scene["visual_windows"]=remaining

all_assets={int(a["index"]):a for a in clips.get("assets",[]) if a.get("approved")}
clips_indexes=set(all_assets)

# Main Brazil trailer from SEGA; Portuguese edition can provide additional
# independent Brazil-specific clips without passing unrelated maps as Brazil.
brazil=set(media_for_video("DeSxlArFZcl"))
brazil_aux=set(media_for_video("DeR77bLFCnT"))
brazil_all=brazil|brazil_aux
# Official multiplayer gameplay versions (GameSpot and The Game Awards).
multi=set(media_for_video("DcecHgCkZa0"))|set(media_for_video("Dcei4hNuXN6"))
if not brazil or not multi:
    raise RuntimeError("QUALITY_BLOCK: required verified Brazil and multiplayer trailers missing")

# Prevent global source exhaustion: intro/setup must NOT consume Brazil footage.
for idx in (0,):
    eligible=set(int(x) for x in scenes[idx].get("visual_windows",{}))
    update_scene(idx,eligible-brazil_all-multi)

# Dedicated scenes 2, 3, 4 each show Brazil-specific official material.
# Brazil promo was manually reviewed window by window. The final 52.7s
# yellow "coming 2027" title card is excluded (not gameplay).
# Scene 2: country announcement and urban panorama (0.2, 15.2).
# Scene 3: storefront streets, food montage and taxi driving (7.7,37.7,45.2).
# Scene 4: waterfront scenery and actual beach images (22.7,30.2).
brazil_allocations={
    1:[0.2,15.2],
    2:[7.7,37.7,45.2],
    3:[22.7,30.2],
}
for idx,starts in brazil_allocations.items():
    update_scene(idx,brazil_all,brazil_frame_windows=starts)
    scenes[idx]["semantic_subject"]="Official Brazil map trailer | SEGA BGS 2026"

# Reserve Brazil only for the three map paragraphs, and reserve official
# multiplayer video for its own narration. Extended official game demos
# cover the general campaign and drive sections without replaying Brazil.
for idx in list(range(4,8))+list(range(9,len(scenes))):
    eligible=set(int(x) for x in scenes[idx].get("visual_windows",{}))
    keep=eligible-brazil_all-multi
    update_scene(idx,keep)

# Scene 9 focuses only on actual multiplayer footage.
update_scene(8,multi)
scenes[8]["semantic_subject"]="Official Crazy Taxi multiplayer trailer | SEGA 2026"

# Scene 10 onward can use any visually matching leftover footage. Do not loop.

# Early quality gate: estimated narration duration requires enough unique footage.
inventory=json.loads((out/"visual-inventory.json").read_text(encoding="utf-8"))
duration_by_asset={}
for a in inventory.get("assets",[]):
    if a.get("type")!="video" or a.get("duplicate_of"):continue
    if int(a.get("index") or 0) not in assets:continue
    duration_by_asset[int(a["index"])]=sum(max(0,float(w["end"])-float(w["start"])) for w in a.get("usable_windows",[]))
usable=sum(duration_by_asset.values())
script=(out/"auto-script-outline.txt").read_text(encoding="utf-8")
words=len(script.split())
needed=words/2.55
print(json.dumps({"available_unique_video_seconds":round(usable,1),
                  "narration_seconds_estimate":round(needed,1),
                  "source_usable_seconds_by_asset":{str(k):round(v,1) for k,v in duration_by_asset.items()},
                  "brazil_indices":sorted(brazil_all),"multiplayer_indices":sorted(multi)},
                 ensure_ascii=False),flush=True)
if usable<needed*0.985:
    raise RuntimeError(
      f"QUALITY_BLOCK: only {usable:.1f}s of distinct official footage for about "
      f"{needed:.1f}s narration; add real trailers or trim script rather than repeat video"
    )

planpath.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("CRAZY_TAXI_ALIGNED — Brazil/multiplayer protected and unique duration checked",flush=True)
