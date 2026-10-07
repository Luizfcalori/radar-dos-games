#!/usr/bin/env python3
"""QA bloqueante das quatro capas do Radar dos Games."""
import json
from pathlib import Path
from PIL import Image, ImageStat

OUT=Path("output")
FILES=[
    ("master",OUT/"thumbnail.jpg",(1280,720)),
    ("short_1",OUT/"shorts/short_1_cover.jpg",(1080,1920)),
    ("short_2",OUT/"shorts/short_2_cover.jpg",(1080,1920)),
    ("short_3",OUT/"shorts/short_3_cover.jpg",(1080,1920)),
]

def entropy_like(im):
    small=im.convert("L").resize((64,64))
    stat=ImageStat.Stat(small)
    return float(stat.var[0])

def main():
    policy_path=OUT/"cover-suite-policy.json"
    if not policy_path.exists():
        raise RuntimeError("QUALITY_BLOCK: cover-suite-policy.json ausente")
    policy=json.loads(policy_path.read_text(encoding="utf-8"))
    rows=[]
    for name,path,size in FILES:
        if not path.exists() or path.stat().st_size<30_000:
            raise RuntimeError(f"QUALITY_BLOCK: capa ausente ou pequena: {path}")
        with Image.open(path) as im:
            im.load()
            if im.size!=size:
                raise RuntimeError(f"QUALITY_BLOCK: resolução incorreta em {path}: {im.size}")
            var=entropy_like(im)
            if var<120:
                raise RuntimeError(f"QUALITY_BLOCK: capa visualmente pobre/chapada: {path} variance={var:.1f}")
        rows.append({"name":name,"path":str(path),"size":list(size),"bytes":path.stat().st_size,"visual_variance":round(var,1)})

    fallback=bool(policy.get("fallback_used"))
    status="APPROVED_WITH_FALLBACK" if fallback else "APPROVED_PREMIUM"
    report={
        "status":status,
        "premium_required":True,
        "premium_cover_generation":"FALLBACK" if fallback else "APPROVED",
        "premium_cover_qa":"APPROVED",
        "fallback_used":fallback,
        "template_version":policy.get("template_version"),
        "covers":rows
    }
    (OUT/"cover-qa.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
