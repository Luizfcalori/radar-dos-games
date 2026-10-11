"""Reserve unique source intervals and match footage to individual phrases."""
import math
from collections import defaultdict

try:
    from repetition_policy import asset_identity
    from vision_semantics import scene_categories
except ModuleNotFoundError:
    from src.repetition_policy import asset_identity
    from src.vision_semantics import scene_categories

POLICY='PHRASE_VISUAL_CONTINUITY_V1'  # reviewed windows require traceable frame-scan evidence  # labels rank reviewed gameplay; unreviewed windows remain ineligible
EPS=0.002

class VideoTimeline:
    def __init__(self, assets):
        self.assets=assets
        self.identities={}
        self.used=defaultdict(list)
        self.last=None

    def identity(self, idx):
        idx=int(idx)
        if idx not in self.identities:
            a=self.assets[idx]
            alias=a.get('duplicate_of')
            self.identities[idx]=(self.identity(alias) if alias and int(alias)!=idx
                                  else a.get('content_identity') or asset_identity(a))
        return self.identities[idx]

    def free(self, idx, begin, end):
        ranges=[(float(begin),float(end))]
        for a,b in sorted(self.used[self.identity(idx)]):
            new=[]
            for lo,hi in ranges:
                if b<=lo or a>=hi: new.append((lo,hi))
                else:
                    if a>lo: new.append((lo,a))
                    if b<hi: new.append((b,hi))
            ranges=new
        return ranges

    def reserve(self, idx, start, duration, allow_reuse=False):
        end=start+duration
        if not all(math.isfinite(v) for v in (start,duration,end)) or start<0 or duration<=0:
            raise RuntimeError('QUALITY_BLOCK: intervalo de vídeo inválido')
        a=self.assets[int(idx)]
        if a.get('duration') and end>float(a['duration'])+EPS:
            raise RuntimeError('QUALITY_BLOCK: vídeo acabaria antes da fala')
        key=self.identity(idx)
        if not allow_reuse and any(min(end,b)-max(start,a)>EPS for a,b in self.used[key]):
            raise RuntimeError('QUALITY_BLOCK: intervalo de gameplay repetido')
        self.used[key].append((start,end));self.last=(key,end)

    def choose(self, scene, text, remaining, assets, required_subjects=()):
        expected=set(scene_categories(text))
        candidates=[]
        for asset in assets:
            idx=int(asset['index'])
            if asset.get('type')!='video': continue
            for w in (scene.get('visual_windows') or {}).get(str(idx),[]):
                cats=set(w.get('semantic_categories',[]))
                if 'title_card' in cats: continue
                reviewed=w.get('reviewed') is True and bool(w.get('evidence'))
                if not reviewed: continue
                subject_match=not required_subjects or set(required_subjects)<=set(w.get('subjects',[]))
                # Explicitly required named subjects remain a hard editorial constraint.
                # Only inferred subject/category labels are relaxed for fallback gameplay.
                if required_subjects and not subject_match: continue
                # Subject labels are a preference, not a hard stop when a phrase
                # has exhausted exact matches. Only use the broader fallback for
                # visually reviewed footage from the already-approved game source.
                # Subject labels rank candidates but do not block gameplay from approved assets.
                # One-off editorial source context can explicitly allow a
                # visible fallback category for footage limited to verified
                # topic-specific sources (e.g. driving in a multiplayer trailer).
                # Normal productions are unchanged when this field is absent.
                source_context=set(scene.get('verified_source_fallback_categories') or ())
                # Flexible fallback: when no unused shot matches the phrase's
                # exact visual category, allow another reviewed, topic-approved
                # gameplay window from the same approved source. Exact matches
                # still rank higher; title cards and required-subject constraints
                # remain hard blocks, as do reused intervals.
                category_match=bool(expected & cats)
                # Category labels rank candidates but do not block fallback gameplay from approved assets.
                # Technical inspection bins can end at ceil(duration), a fraction
                # beyond the actual last decodable frame. Never reserve beyond
                # the probed media duration; keep the strict QA guard enabled.
                source_end=float(asset.get('duration') or 0)
                window_end=float(w['end'])
                if source_end>0:
                    window_end=min(window_end,source_end-EPS)
                if window_end<=float(w['start'])+EPS: continue
                for lo,hi in self.free(idx,w['start'],window_end):
                    room=hi-lo
                    if room<min(1.0,remaining)-EPS: continue
                    length=min(math.floor((room+1e-8)*30)/30,remaining,10.0)
                    if length<=0: continue
                    # Prefer continuing the same shot, then coverage, then length.
                    continuous=self.last is not None and self.last[0]==self.identity(idx) and abs(self.last[1]-lo)<.06
                    rank=(bool(reviewed),subject_match,category_match or bool(source_context & cats),continuous,len(cats & expected),length,-idx,-lo)
                    candidates.append((rank,asset,lo,length,w))
        reused_source=False
        if not candidates:
            # Controlled fallback: reuse a reviewed gameplay window only after
            # all unused windows are exhausted. The director marks this explicitly.
            fallback=[]
            for asset in assets:
                idx=int(asset['index'])
                if asset.get('type')!='video': continue
                for w in (scene.get('visual_windows') or {}).get(str(idx),[]):
                    cats=set(w.get('semantic_categories',[]))
                    if 'title_card' in cats or w.get('reviewed') is not True or not w.get('evidence'): continue
                    if required_subjects and not set(required_subjects)<=set(w.get('subjects',[])): continue
                    lo=float(w['start'])
                    hi=min(float(w['end']),float(asset.get('duration') or w['end'])-EPS)
                    length=min(math.floor(max(0,hi-lo)*30)/30,remaining,10.0)
                    if length>=min(1.0,remaining)-EPS:
                        fallback.append((idx!=(self.last[0] if self.last else None),length,-idx,asset,lo,w))
            if not fallback:
                raise RuntimeError(f'QUALITY_BLOCK: sem gameplay aprovado suficiente para a fala: {text}')
            _,length,_,asset,lo,w=max(fallback,key=lambda x:x[:3])
            reused_source=True
        else:
            _,asset,lo,length,w=max(candidates,key=lambda x:x[0])
        reserved=math.ceil((length-1e-8)*30)/30
        self.reserve(asset['index'],lo,reserved,allow_reuse=reused_source)
        return asset,lo,length,{**w,'reserved_end':lo+reserved,'reused_source':reused_source}

def validate_video_beats(beats, assets, require_windows=True):
    timeline=VideoTimeline(assets);count=0;total_video=0.0;reused_seconds=0.0
    for beat in beats:
        idx=int(beat['media_index']);asset=assets[idx]
        if asset.get('type')!='video':continue
        w=beat.get('source_window')
        if not w:
            if require_windows: raise RuntimeError('QUALITY_BLOCK: gameplay sem intervalo de origem explícito')
            continue
        duration=float(beat['duration']);start=float(w['start'])
        if start+duration>float(w['end'])+EPS:
            raise RuntimeError('QUALITY_BLOCK: corte extrapola a janela aprovada')
        allow_reuse=beat.get('approved_reuse') is True
        timeline.reserve(idx,start,duration,allow_reuse=allow_reuse)
        total_video+=duration
        if allow_reuse: reused_seconds+=duration
        count+=1
    if total_video and reused_seconds/total_video>0.25+EPS:
        raise RuntimeError('QUALITY_BLOCK: fallback repetido excede 25% do gameplay')
    return {'policy':POLICY,'video_beats':count,'repeated_intervals':0,
            'approved_reuse_beats':sum(1 for b in beats if b.get('approved_reuse') is True),
            'approved_reuse_ratio':round(reused_seconds/total_video,4) if total_video else 0.0}
