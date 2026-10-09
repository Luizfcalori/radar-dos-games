"""Reserve unique source intervals and match footage to individual phrases."""
import math
from collections import defaultdict

try:
    from repetition_policy import asset_identity
    from vision_semantics import scene_categories
except ModuleNotFoundError:
    from src.repetition_policy import asset_identity
    from src.vision_semantics import scene_categories

POLICY='PHRASE_VISUAL_CONTINUITY_V1'
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

    def reserve(self, idx, start, duration):
        end=start+duration
        if not all(math.isfinite(v) for v in (start,duration,end)) or start<0 or duration<=0:
            raise RuntimeError('QUALITY_BLOCK: intervalo de vídeo inválido')
        a=self.assets[int(idx)]
        if a.get('duration') and end>float(a['duration'])+EPS:
            raise RuntimeError('QUALITY_BLOCK: vídeo acabaria antes da fala')
        key=self.identity(idx)
        if any(min(end,b)-max(start,a)>EPS for a,b in self.used[key]):
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
                if required_subjects and (not reviewed or not set(required_subjects)<=set(w.get('subjects',[]))):
                    continue
                if expected and not (expected & cats): continue
                for lo,hi in self.free(idx,w['start'],w['end']):
                    room=hi-lo
                    if room<min(1.0,remaining)-EPS: continue
                    length=min(math.floor((room+1e-8)*30)/30,remaining,10.0)
                    if length<=0: continue
                    # Prefer continuing the same shot, then coverage, then length.
                    continuous=self.last is not None and self.last[0]==self.identity(idx) and abs(self.last[1]-lo)<.06
                    rank=(bool(reviewed),continuous,len(cats & expected),length,-idx,-lo)
                    candidates.append((rank,asset,lo,length,w))
        if not candidates:
            raise RuntimeError(f'QUALITY_BLOCK: faltam cenas inéditas correspondentes à fala: {text}; ampliar fontes ou revisar roteiro')
        _,asset,lo,length,w=max(candidates,key=lambda x:x[0])
        reserved=math.ceil((length-1e-8)*30)/30
        self.reserve(asset['index'],lo,reserved)
        return asset,lo,length,{**w,'reserved_end':lo+reserved}

def validate_video_beats(beats, assets, require_windows=True):
    timeline=VideoTimeline(assets);count=0
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
        timeline.reserve(idx,start,duration);count+=1
    return {'policy':POLICY,'video_beats':count,'repeated_intervals':0}
