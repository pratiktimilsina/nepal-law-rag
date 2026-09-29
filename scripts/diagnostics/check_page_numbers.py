import json, re
checks = {
    "en": (json.load(open("data/processed/en_articles.json", encoding="utf-8")), re.compile(r"\.\s+\d{1,3}\s+[A-Z(]")),
    "ne": (json.load(open("data/processed/ne_articles.json", encoding="utf-8")), re.compile(r"।\s+[०-९0-9]{1,3}\s+\S")),
}
with open("data/page_number_check.txt", "w", encoding="utf-8") as f:
    for lang, (arts, pat) in checks.items():
        hits = [(a["num"], m.group()) for a in arts for m in pat.finditer(a["text"])]
        f.write(f"{lang}: suspected stray page numbers: {len(hits)}\n")
        for n, g in hits[:12]:
            f.write(f"  {n}: {g!r}\n")
        f.write("\n")
print("done")
