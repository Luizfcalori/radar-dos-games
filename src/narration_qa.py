#!/usr/bin/env python3
"""QA editorial da narração: bloqueia linguagem meta e conversa privada com o operador."""
import json
import re
import sys
from pathlib import Path

FORBIDDEN = [
    r"\bestou mostrando\b",
    r"\bestamos mostrando\b",
    r"\bna minha tela\b",
    r"\bo que est[aá] na tela\b",
    r"\beste trecho mostra\b",
    r"\bneste trecho\b.{0,50}\bmostra",
    r"\baqui,? a tela\b",
    r"\ba tela fica\b",
    r"\bo v[ií]deo tenta mostrar\b",
    r"\bo v[ií]deo mostra exatamente\b",
    r"\bimagem correspondente ao que est[aá] sendo falado\b",
    r"\bo radar prioriza\b",
    r"\bo radar considera\b",
    r"\ba gente sempre confere\b",
    r"\baqui a gente separa\b",
    r"\bessa [ée] a pauta que entrou no topo do radar\b",
    r"\bsem depender s[oó] de cards ou textos na tela\b",
    r"\b(?:we['’]re|today, we|eagle-eyed fans)\b",
    r"\bentre os principais destaques est[aã]o\s+[^.]{0,140},\s*[^.]{0,100}\.",
]

def main(path):
    p=Path(path)
    text=p.read_text(encoding="utf-8")
    low=text.casefold()
    hits=[]
    for pat in FORBIDDEN:
        m=re.search(pat,low,re.I|re.S)
        if m:
            hits.append({"pattern":pat,"match":text[m.start():m.end()]})
    # "Você" é tratamento normal de audiência em português brasileiro e não
    # caracteriza, por si só, conversa privada/meta. Só padrões explícitos acima
    # devem bloquear; registrar a contagem para diagnóstico sem reprovar o roteiro.
    voce=len(re.findall(r"\bvoc[eê]\b",low))
    report={
        "status":"BLOCKED" if hits else "APPROVED",
        "policy":"audience_first_no_meta_narration",
        "file":str(p),
        "violations":hits,
        "audience_address_count":voce,
        "audience_address_policy":"informational_only; natural Brazilian Portuguese audience address is allowed",
    }
    out=p.parent/"narration-qa.json"
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if hits:
        raise RuntimeError("QUALITY_BLOCK: narração contém linguagem meta/privada")

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("uso: narration_qa.py ROTEIRO.txt")
    main(sys.argv[1])
