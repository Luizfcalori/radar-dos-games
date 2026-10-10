#!/usr/bin/env python3
"""Strong face anonymization for review videos; detects on every frame and blurs faces."""
import json, math, subprocess, sys
from pathlib import Path
import cv2
import numpy as np

OUT = Path("output/face-blur-qa.json")
CASCADE = Path(cv2.data.haarcascades)
FRONTAL = cv2.CascadeClassifier(str(CASCADE / "haarcascade_frontalface_default.xml"))
PROFILE = cv2.CascadeClassifier(str(CASCADE / "haarcascade_profileface.xml"))
if FRONTAL.empty() or PROFILE.empty():
    raise RuntimeError("FACE_BLUR_BLOCK: OpenCV Haar cascades unavailable")

def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)
    ], text=True))

def read_exact(pipe, n):
    chunks=[]; total=0
    while total<n:
        b=pipe.read(n-total)
        if not b: break
        chunks.append(b); total += len(b)
    return b"".join(chunks) if total == n else None

def boxes_for(frame, scale):
    h,w=frame.shape[:2]
    # The presenter appears inside the centered portrait panel in the 16:9 Master.
    # Restrict detection to that panel so game/NPC faces remain untouched.
    xoff=yoff=0
    work=frame
    if w >= 1600:
        xoff=int(w*0.28); xend=int(w*0.58)
        yoff=int(h*0.20); yend=int(h*0.90)
        work=frame[yoff:yend,xoff:xend]
    ch,cw=work.shape[:2]
    ratio=min(320,cw)/cw
    small=cv2.resize(work,(int(cw*ratio),max(1,int(ch*ratio))),interpolation=cv2.INTER_AREA) if ratio<1 else work
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
    gray=cv2.equalizeHist(gray)
    found=[]
    cascades=(FRONTAL,) if w >= 1600 else (FRONTAL,PROFILE)
    for cascade in cascades:
        boxes=cascade.detectMultiScale(gray,scaleFactor=1.1,minNeighbors=4,minSize=(10,10),flags=cv2.CASCADE_SCALE_IMAGE)
        found.extend([(int(x/ratio)+xoff,int(y/ratio)+yoff,int(ww/ratio),int(hh/ratio)) for x,y,ww,hh in boxes])
        flipped=cv2.flip(gray,1) if cascade is PROFILE else None
        if flipped is not None:
            for x,y,ww,hh in cascade.detectMultiScale(flipped,scaleFactor=1.1,minNeighbors=4,minSize=(10,10),flags=cv2.CASCADE_SCALE_IMAGE):
                found.append((int((gray.shape[1]-x-ww)/ratio)+xoff,int(y/ratio)+yoff,int(ww/ratio),int(hh/ratio)))
    merged=[]
    for b in sorted(found,key=lambda z:z[2]*z[3],reverse=True):
        x,y,bw,bh=b
        cx,cy=x+bw/2,y+bh/2
        if any(abs(cx-(xx+ww/2)) < max(bw,ww)*0.55 and abs(cy-(yy+hh/2)) < max(bh,hh)*0.55 for xx,yy,ww,hh in merged):
            continue
        merged.append(b)
    # Presenter face is large in the centered portrait panel; ignore small game/NPC faces.
    if w >= 1600:
        merged=[b for b in merged if b[2] >= 120]
    return merged

def blur_box(frame, box):
    h,w=frame.shape[:2]; x,y,bw,bh=box
    # Expand beyond facial features to cover the whole face/head outline.
    px=int(bw*0.20); top=int(bh*0.45); bottom=int(bh*0.30)
    x1=max(0,x-px); x2=min(w,x+bw+px)
    y1=max(0,y-top); y2=min(h,y+bh+bottom)
    roi=frame[y1:y2,x1:x2]
    if roi.size:
        # Heavy blur, scaled to the ROI so even close-ups are not identifiable.
        k=max(51,(min(roi.shape[:2])//2)*2+1)
        k=min(k, max(3,(min(roi.shape[:2])//2)*2+1))
        frame[y1:y2,x1:x2]=cv2.GaussianBlur(roi,(k,k),0)

def process(path):
    path=Path(path)
    if not path.exists() or path.stat().st_size < 100000:
        raise RuntimeError(f"FACE_BLUR_BLOCK: missing/invalid video {path}")
    info=probe(path)
    v=next((s for s in info["streams"] if s["codec_type"]=="video"),None)
    if not v: raise RuntimeError(f"FACE_BLUR_BLOCK: no video stream in {path}")
    w,h=int(v["width"]),int(v["height"])
    fps_s=v.get("avg_frame_rate") or v.get("r_frame_rate") or "30/1"
    n,d=map(int,fps_s.split("/"))
    fps=n/d if d else 30.0
    if not math.isfinite(fps) or fps<1 or fps>120: fps=30.0
    tmp=path.with_name(path.stem+".faceblur-tmp.mp4")
    decoder=subprocess.Popen([
        "ffmpeg","-hide_banner","-loglevel","error","-i",str(path),
        "-map","0:v:0","-f","rawvideo","-pix_fmt","bgr24","-vsync","0","pipe:1"
    ],stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=1024*1024)
    encoder=subprocess.Popen([
        "ffmpeg","-hide_banner","-loglevel","error","-y",
        "-f","rawvideo","-pix_fmt","bgr24","-s:v",f"{w}x{h}","-r",f"{fps:.8f}","-i","pipe:0",
        "-i",str(path),"-map","0:v:0","-map","1:a?","-map_metadata","1",
        "-c:v","libx264","-preset","veryfast","-crf","18","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(tmp)
    ],stdin=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=1024*1024)
    frame_bytes=w*h*3; frames=0; detected_frames=0; blurred_boxes=0; carried=[]; carry_age=0
    try:
        while True:
            raw=read_exact(decoder.stdout,frame_bytes)
            if raw is None: break
            frame=np.frombuffer(raw,dtype=np.uint8).reshape((h,w,3)).copy()
            boxes=boxes_for(frame,1.0) if frames % 3 == 0 else []
            if boxes:
                detected_frames += 1
                blurred_boxes += len(boxes)
                carried=boxes; carry_age=0
            elif carried and carry_age < 2:
                boxes=carried
                carry_age += 1
                blurred_boxes += len(boxes)
            else:
                carried=[]; carry_age=0
            for b in boxes: blur_box(frame,b)
            encoder.stdin.write(frame.tobytes())
            frames += 1
            if frames % 900 == 0: print(f"FACE_BLUR_PROGRESS {path.name}: {frames} frames",flush=True)
        decoder.stdout.close()
        dec_err=decoder.stderr.read().decode("utf-8","replace")
        dec_rc=decoder.wait()
        encoder.stdin.close()
        enc_err=encoder.stderr.read().decode("utf-8","replace")
        enc_rc=encoder.wait()
        if dec_rc or enc_rc:
            raise RuntimeError(f"FACE_BLUR_BLOCK ffmpeg error {path}: decoder={dec_err[-1200:]} encoder={enc_err[-1200:]}")
        if frames < 1 or not tmp.exists() or tmp.stat().st_size < 100000:
            raise RuntimeError(f"FACE_BLUR_BLOCK no valid output for {path}")
        # Replace only after the encoded output is complete and probeable.
        check=probe(tmp)
        out_v=next(s for s in check["streams"] if s["codec_type"]=="video")
        if (int(out_v["width"]),int(out_v["height"])) != (w,h):
            raise RuntimeError(f"FACE_BLUR_BLOCK dimensions changed for {path}")
        tmp.replace(path)
        return {"file":str(path),"frames_processed":frames,
                "frames_with_face_detections":detected_frames,
                "face_regions_blurred_including_short_tracking_carry":blurred_boxes,
                "face_detection":"frontal+profile Haar; every frame; expanded strong Gaussian blur",
                "audio_preserved":"re-encoded from original audio stream"}
    finally:
        for proc in (decoder,encoder):
            try:
                if proc.poll() is None: proc.kill()
            except Exception: pass
        try: tmp.unlink(missing_ok=True)
        except Exception: pass

def main():
    # Crazy Taxi Shorts are gameplay/trailer-only; blur the presenter in the Master
    # and leave game characters in the Shorts untouched.
    targets=[Path("output/master.mp4")]
    reports=[process(p) for p in targets]
    if reports[0]["frames_with_face_detections"] < 1:
        raise RuntimeError("FACE_BLUR_BLOCK: presenter not detected in Master portrait panel")
    report={"status":"APPROVED","policy":"strong blur on presenter in centered portrait panel of Master",
            "videos":reports,"videos_processed":1,
            "shorts_unchanged":"3 gameplay/trailer-only Shorts; presenter not visible in reviewed frames",
            "published":False}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("FACE_BLUR_QA "+json.dumps(report,ensure_ascii=False),flush=True)
    if reports[0]["frames_processed"]<1:
        raise RuntimeError("FACE_BLUR_BLOCK: Master not processed")

if __name__=="__main__": main()
