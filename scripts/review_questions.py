import json
en = {a["num"]: a for a in json.load(open("data/processed/en_articles.json", encoding="utf-8"))}
qs = [json.loads(l) for l in open("eval/questions.jsonl", encoding="utf-8-sig") if l.strip()]
with open("eval/review_sheet.txt", "w", encoding="utf-8") as f:
    for q in qs:
        if q["lang"] != "en":
            continue
        f.write(f"{q['id']}  Q: {q['q']}\n")
        if not q["gold"]:
            f.write("   (negative: should NOT be answerable from the Constitution)\n\n")
            continue
        for g in q["gold"]:
            a = en[g]
            f.write(f"   gold {g}: {a['title']}\n   {a['text'][:400]}...\n")
        f.write("\n")
print("done")
