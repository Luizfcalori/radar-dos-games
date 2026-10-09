#!/usr/bin/env python3
"""Offline, CPU-only zero-shot scene suggestions from representative source frames.

All frames were decoded in visual_inspector.py first. This second pass runs a
free open-weights CLIP model on clean-window keyframes. Suggestions are NOT
proof of game-specific enemy/weapon identities: official stills/labels remain
the source for exact names. No remote inference API or paid credits.
"""
import json
import re
import subprocess
import unicodedata
from pathlib import Path

OUT = Path("output")
MODEL = "openai/clip-vit-base-patch32"
# Broad visible categories only. CLIP cannot reliably identify game-specific bosses.
CATEGORIES = {
    "snow": "a snowy mountain landscape in a realistic video game",
    "robot": "giant mechanical enemy robots fighting in a science fiction game",
    "combat": "third person shooter video game combat with gunfire",
    "airship": "a large science fiction flying ship above a landscape",
    "settlement": "abandoned buildings, a town, or a village in a video game",
    "weapons": "close up of a rifle or a revolver weapon in a video game",
    "equipment": "a grappling hook or other climbing equipment in a video game",
    "interface": "video game inventory menu, upgrade skill tree or rewards interface",
    "title_card": "a promotional title card with large text and a logo",
}
SCENE_WORDS = {
    "snow": ("neve", "congelad", "frio", "montanha", "pendola", "freeze", "geleira"),
    "robot": ("robo", "maquina", "arc", "bully", "skulker", "hydra", "emperor", "inimig"),
    "combat": ("combate", "luta", "ataque", "confront", "tiro", "batalha"),
    "airship": ("frigate", "nave", "aerea", "ceu"),
    "settlement": ("vila", "cidade", "praca", "outpost", "observatorio", "predio"),
    "weapons": ("arma", "revolver", "fuzil", "bantam", "stiletto", "arsenal"),
    "equipment": ("gancho", "grappling", "corda", "tether", "granada"),
    "interface": ("habilidade", "inventario", "recompens", "skill", "passe", "pass"),
}


def ascii_text(value):
    value = unicodedata.normalize("NFKD", str(value or "").lower())
    return "".join(c for c in value if not unicodedata.combining(c))


def scene_categories(text):
    s=ascii_text(text)
    return [cat for cat, words in SCENE_WORDS.items() if any(word in s for word in words)]


def usable_for_scene(windows, expected):
    """Fail closed for subject-specific scenes; reject title cards as gameplay."""
    if not expected:
        return [w for w in windows if "title_card" not in w.get("semantic_categories", [])]
    return [w for w in windows if
            any(c in w.get("semantic_categories", []) for c in expected)
            and "title_card" not in w.get("semantic_categories", [])]


def extract_keyframe(path, time):
    from PIL import Image
    cmd=["ffmpeg","-hide_banner","-v","error","-nostdin","-ss",f"{time:.3f}",
         "-i",str(path),"-vf","scale=224:224:force_original_aspect_ratio=decrease,"
         "pad=224:224:(ow-iw)/2:(oh-ih)/2","-frames:v","1","-f","image2pipe",
         "-vcodec","mjpeg","-"]
    raw=subprocess.check_output(cmd, timeout=45)
    from io import BytesIO
    with Image.open(BytesIO(raw)) as img:
        return img.convert("RGB").copy()


def classify(inventory, clips, plan):
    import torch
    from transformers import CLIPModel, CLIPProcessor

    model=CLIPModel.from_pretrained(MODEL)
    processor=CLIPProcessor.from_pretrained(MODEL)
    model.eval().to("cpu")
    torch.set_num_threads(2)
    prompts=list(CATEGORIES.values())
    with torch.inference_mode():
        text_in=processor(text=prompts,padding=True,return_tensors="pt")
        texts=model.get_text_features(**text_in)
        texts=texts/texts.norm(dim=-1,keepdim=True)
    paths={int(a["index"]):a["path"] for a in clips.get("assets",[]) if a.get("approved")}
    rows=[]
    images=[];keys=[]
    for row in inventory.get("assets",[]):
        if row.get("type")!="video" or row.get("duplicate_of"):
            continue
        for i,window in enumerate(row.get("usable_windows",[])):
            middle=(float(window["start"])+float(window["end"]))/2
            try:
                images.append(extract_keyframe(paths[int(row["index"])],middle))
                keys.append((int(row["index"]),i))
            except (OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as exc:
                raise RuntimeError(f"QUALITY_BLOCK: sem keyframe da janela {row['index']}:{i}: {exc}") from exc
    if not images:
        raise RuntimeError("QUALITY_BLOCK: zero quadros visualmente analisáveis pela IA")
    predictions={}
    with torch.inference_mode():
        for offset in range(0,len(images),8):
            batch=images[offset:offset+8]
            inputs=processor(images=batch,return_tensors="pt")
            features=model.get_image_features(**inputs)
            features=features/features.norm(dim=-1,keepdim=True)
            sims=(features@texts.T).tolist()
            for key,values in zip(keys[offset:offset+8],sims):
                ranked=sorted(zip(CATEGORIES.keys(),values),key=lambda x:x[1],reverse=True)
                # Conservative tags: broad scene type, not named robot/weapon ID.
                top=ranked[0][1]
                cats=[name for name,value in ranked[:2] if value>=0.22 and top-value<=0.035]
                if not cats and top>=0.22:
                    cats=[ranked[0][0]]
                predictions[key]={"semantic_categories":cats,
                                  "vision_confidence":round(top,4),
                                  "top_categories":[{"category":k,"similarity":round(v,4)} for k,v in ranked[:3]]}
    for row in inventory.get("assets",[]):
        for i,window in enumerate(row.get("usable_windows",[])):
            window.update(predictions.get((int(row["index"]),i),{
                "semantic_categories":[],"vision_confidence":0.0}))
    report=[]
    for n,scene in enumerate(plan.get("scenes",[]),1):
        expected=scene_categories(" ".join((str(scene.get("title") or ""),
                    str(scene.get("subtitle") or ""))))
        report.append({"scene":n,"title":scene.get("title"),
                      "expected_broad_categories":expected,
                      "note":"CLIP labels are visual suggestions, not verified game-specific identities"})
    return {"status":"ANALYZED","policy":"CPU_CLIP_BROAD_CATEGORY_SUGGESTIONS_V1",
            "model":MODEL,"sampled_keyframes":len(images),"scenes":report}


def main():
    inventory_path=OUT/"visual-inventory.json"
    inventory=json.loads(inventory_path.read_text(encoding="utf-8"))
    clips=json.loads((OUT/"clips.json").read_text(encoding="utf-8"))
    plan=json.loads((OUT/"auto-media-plan.json").read_text(encoding="utf-8"))
    report=classify(inventory,clips,plan)
    inventory["semantic_model_policy"]=report["policy"]
    inventory_path.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"vision-semantic-report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"ANALYZED","sampled_keyframes":report["sampled_keyframes"],
                      "model":MODEL,"policy":report["policy"]}))


if __name__=="__main__":
    main()
