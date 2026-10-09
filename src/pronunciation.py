"""Speech-only aliases. Never change titles, subtitles or the editorial script.

The free Edge backend does not support custom SSML/phonemes. Multilingual
Thalita handles unlisted words; a reviewed lexicon corrects known exceptions.
"""
import json
import re
from pathlib import Path

LEXICON = Path(__file__).resolve().parents[1] / 'production' / 'pronunciations.json'

def spoken_text(text, aliases=None):
    if aliases is None:
        aliases = json.loads(LEXICON.read_text(encoding='utf-8'))['aliases']
    if not aliases:
        return text
    if any(not k.strip() or not isinstance(v, str) or not v.strip()
           for k, v in aliases.items()):
        raise ValueError('Pronunciation aliases must be non-empty strings')
    mapping = {k.casefold(): v for k, v in aliases.items()}
    pattern = r'(?<!\w)(?:' + '|'.join(re.escape(k) for k in sorted(aliases, key=len, reverse=True)) + r')(?!\w)'
    return re.sub(pattern, lambda m: mapping[m.group().casefold()], text, flags=re.I)

def phrase_parts(text):
    # Metadata only: the whole paragraph is still synthesized in one request.
    return [s.strip() for s in re.split(
        r'(?<=[.!?;:,])\s+|\s+(?=e habilidades de invasão|e armas de fogo|e implantes)', text)
        if s.strip()]

def measured_phrases(text, metadata, start, duration, paragraph):
    """Map speech word events back to unchanged editorial clauses.

    Never claim estimated word counts are measured timestamps. Unrecognized
    tokenization blocks before rendering instead of inventing timing evidence.
    """
    def tokens(s): return re.findall(r'\w+', s.casefold())
    words=[]
    for event in metadata:
        if event.get('type') != 'WordBoundary': continue
        for token in tokens(event['text']):
            words.append((token, float(event['offset'])/1e7))
    parts=phrase_parts(text)
    expected=[t for part in parts for t in tokens(spoken_text(part))]
    if [w[0] for w in words] != expected:
        raise RuntimeError('QUALITY_BLOCK: limites de palavras do TTS não correspondem ao texto; revisar alinhamento')
    rows=[]; count=0
    for i, part in enumerate(parts,1):
        n=len(tokens(spoken_text(part)))
        if not n: continue
        begin=0.0 if not rows else words[count][1]
        count+=n
        end=words[count][1] if count<len(words) else duration
        if not 0 <= begin < end <= duration+0.08:
            raise RuntimeError('QUALITY_BLOCK: timestamps TTS inválidos')
        rows.append({'paragraph':paragraph,'sentence':i,'start':round(start+begin,3),
                     'end':round(start+end,3),'duration':round(end-begin,3),
                     'text':part,'timing_evidence':'tts_word_boundaries'})
    return rows
