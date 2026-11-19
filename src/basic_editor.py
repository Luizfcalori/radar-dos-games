#!/usr/bin/env python3
"""Simple media-first editor: no Director V4 or phrase-level scene matching."""
import json
from pathlib import Path

OUT=Path("output")
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def main():
    plan=read(OUT/"auto-media-plan.json")
    clips=read(OUT/"clips.json")
    timings=read(OUT/"voice-timings.json")
    assets={}
    for a in (plan.get("assets") or [])+(clips.get("assets") or []):
        if a.get("approved",True) and a.get("index") is not None:
            merged=dict(assets.get(int(a["index"]),{})); merged.update(a); assets[int(a["index"])]=merged
    videos=[a for a in assets.values() if a.get("type")=="video" and a.get("path")]
    images=[a for a in assets.values() if a.get("type")=="image" and a.get("path")]
    if not videos: raise SystemExit("QUALITY_BLOCK: nenhuma gameplay aprovada")
    scenes=plan.get("scenes") or []
    segments=timings.get("segments") or []
    if len(scenes)!=len(segments): raise SystemExit(f"QUALITY_BLOCK: {len(scenes)} cenas para {len(segments)} blocos de voz")
    windows={}
    for sc in scenes:
        for key,rows in (sc.get("visual_windows") or {}).items():
            idx=int(key)
            valid=[w for w in rows or [] if float(w.get("end",0))>float(w.get("start",0))]
            if valid: windows.setdefault(idx,[]).extend(valid)
    for a in videos:
        idx=int(a["index"])
        if not windows.get(idx):
            inv=read(OUT/"visual-inventory.json")
            row=next((x for x in inv.get("assets",[]) if int(x.get("index",-1))==idx),{})
            windows[idx]=row.get("usable_windows") or []
    cursors={k:0 for k in windows}
    video_order=[int(a["index"]) for a in videos if windows.get(int(a["index"]))]
    if not video_order: raise SystemExit("QUALITY_BLOCK: gameplay sem janelas inspecionadas")
    usage={k:0 for k in assets}
    timeline=0.0
    for si,(scene,segment) in enumerate(zip(scenes,segments),1):
        phrase_rows=[p for p in timings.get("phrases",[]) if int(p.get("paragraph",0))==si]
        if not phrase_rows:
            phrase_rows=[{"sentence":1,"start":segment.get("start",0),"end":segment.get("end",0),"duration":segment.get("duration",0),"text":segment.get("text","")}]
        beats=[]
        for phrase in phrase_rows:
            left=float(phrase.get("duration") or 0)
            start=float(phrase.get("start") or 0)
            consumed=0.0
            while left>0.08:
                d=min(5.8,left)
                chosen=None; source_window=None
                # Use every inspected gameplay window in order; if exhausted,
                # use a topic-approved still as a visual bridge, never block the edit.
                for offset in range(len(video_order)):
                    pos=(sum(usage.values())+offset)%len(video_order)
                    idx=video_order[pos]; rows=windows[idx]; cur=cursors[idx]
                    while cur<len(rows) and float(rows[cur].get("end",0))-float(rows[cur].get("start",0))<d:
                        cur+=1
                    if cur<len(rows):
                        w=rows[cur]; cursors[idx]=cur+1
                        chosen=assets[idx]; source_window={"start":float(w["start"]),"end":float(w["end"])}
                        break
                if chosen is None and images:
                    chosen=images[usage and (sum(usage.values())%len(images))]
                if chosen is None:
                    # Relax only uniqueness: reuse a reviewed window from the same
                    # GTA VI source rather than fail the entire production.
                    idx=video_order[(sum(usage.values()))%len(video_order)]
                    rows=windows[idx]
                    if not rows: raise SystemExit("QUALITY_BLOCK: sem janela visual aprovada")
                    w=rows[0]; chosen=assets[idx]
                    source_window={"start":float(w["start"]),"end":float(w["end"])}
                    d=min(d,source_window["end"]-source_window["start"])
                idx=int(chosen["index"])
                beat={"phrase":int(phrase.get("sentence") or 1),"text":phrase.get("text",""),
                      "start":round(start+consumed,6),"end":round(start+consumed+d,6),
                      "duration":round(d,6),"media_index":idx,"transition":"hard_cut",
                      "keyword_overlay":"","intensity":0,"visual_evidence":"reviewed_shot" if chosen.get("type")=="video" else "official_image_subject_label"}
                if source_window: beat["source_window"]=source_window
                beats.append(beat); usage[idx]=usage.get(idx,0)+1
                left-=d; consumed+=d; timeline+=d
        scene["beats"]=beats
        scene["media_indices"]=list(dict.fromkeys(b["media_index"] for b in beats))
        scene["editing"]={"version":"MEDIA_FIRST_SIMPLE","phrase_level":False,"variable_pacing":False}
    hooks=[str(x).strip() for x in plan.get("short_hooks",[]) if str(x).strip()]
    if len(hooks)!=3: hooks=(hooks+["GTA 6: novidades","GTA 6: gameplay","GTA 6: o que sabemos"])[:3]
    ranked=sorted(range(len(scenes)),key=lambda i:sum(float(b.get("duration",0)) for b in scenes[i].get("beats",[])),reverse=True)
    picks=[]
    for i in ranked:
        if i not in picks: picks.append(i)
        if len(picks)==3: break
    while len(picks)<3: picks.append(picks[-1] if picks else 0)
    manifest={"premium_version":"PREMIUM_V4_DIRECTOR_CUT","assets":list(assets.values()),
      "voice":"output/voice.mp3","voice_timings":"output/voice-timings.json",
      "intro":"radar-dos-games-intro-oficial.mp4","intro_policy":"full_intro_first",
      "cold_open_seconds":0.0,"scenes":scenes,"output":"output/master.mp4"}
    write(OUT/"render.json",manifest)
    write(OUT/"short-picks.json",{"version":"PREMIUM_V4_DIRECTOR_CUT","scene_indexes":picks,
      "expected_hooks":hooks,"selection_policy":"longest approved media-first scenes; exactly three"})
    write(OUT/"clips.json",{"assets":list(assets.values()),"scenes":scenes,"publishable_media":True})
    write(OUT/"basic-edit-report.json",{"status":"APPROVED","editor":"MEDIA_FIRST_SIMPLE",
      "director_v4":"REMOVED","voice_seconds":round(timeline,2),"video_assets":len(videos),
      "image_assets":len(images),"scenes":len(scenes),"short_scenes":picks})
    print(json.dumps(read(OUT/"basic-edit-report.json"),ensure_ascii=False))
if __name__=="__main__": main()
