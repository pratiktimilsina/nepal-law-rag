import json
from collections import Counter

ne = {a["num"]: a["title"] for a in json.load(open("data/processed/ne_articles.json", encoding="utf-8"))}
TYPES = {"fact", "paraphrase", "lookup", "negative"}
problems, qs = [], []
for i, line in enumerate(open("eval/questions.jsonl", encoding="utf-8-sig"), 1):
    if not line.strip():
        continue
    try:
        qs.append(json.loads(line))
    except Exception as e:
        problems.append(f"line {i}: bad JSON ({e})")

for id_, c in Counter(q["id"] for q in qs).items():
    if c > 1:
        problems.append(f"duplicate id {id_}")
for q in qs:
    if q.get("lang") not in ("ne", "en"):
        problems.append(f"{q['id']}: bad lang")
    if q.get("type") not in TYPES:
        problems.append(f"{q['id']}: bad type {q.get('type')}")
    for g in q.get("gold", []):
        if not (1 <= g <= 308):
            problems.append(f"{q['id']}: gold {g} out of range")
    if q.get("type") == "negative" and q.get("gold"):
        problems.append(f"{q['id']}: negative question has gold")
    if q.get("type") != "negative" and not q.get("gold"):
        problems.append(f"{q['id']}: missing gold")

pairs = Counter((q["type"], tuple(q["gold"])) for q in qs)
unpaired = [q["id"] for q in qs if q["type"] != "negative" and pairs[(q["type"], tuple(q["gold"]))] % 2]

with open("eval/validate_report.txt", "w", encoding="utf-8") as f:
    langs = Counter(q["lang"] for q in qs)
    types = Counter(q["type"] for q in qs)
    f.write(f"questions: {len(qs)} | {dict(langs)} | {dict(types)}\n")
    f.write(f"problems: {len(problems)}\n" + "".join(f"  {p}\n" for p in problems))
    f.write(f"possibly unpaired (odd count for same type+gold): {unpaired}\n\n")
    for q in qs:
        titles = " / ".join(ne.get(g, "?") for g in q.get("gold", []))
        f.write(f"{q['id']} [{q['lang']}/{q['type']}] {q['gold']} {titles} | {q['q']}\n")
print("done")
