import json, re

RULES = [
    (r"\u0947\u091b\u0941(?=[\s।,]|$)", "\u0947\u091b"),  # -ेछु -> -ेछ (OCR adds spurious ु)
]

arts = json.load(open("data/processed/ne_articles.json", encoding="utf-8"))
total = 0
for a in arts:
    for pat, rep in RULES:
        a["text"], n = re.subn(pat, rep, a["text"])
        total += n
json.dump(arts, open("data/processed/ne_articles.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"normalization replacements: {total}")
