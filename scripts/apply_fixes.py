import json, re

arts = json.load(open("data/processed/ne_articles.json", encoding="utf-8"))
fixes = json.load(open("data/fixes.json", encoding="utf-8-sig"))
by_num = {a["num"]: a for a in arts}

for fx in fixes:
    src = by_num[fx["in"]]
    idx = src["text"].find(fx["marker"])
    if idx < 0:
        raise SystemExit(f"marker for {fx['num']} not found in article {fx['in']}")
    seg = src["text"][idx:]
    src["text"] = src["text"][:idx].rstrip()
    seg = re.sub(r"^\S*?[०-९]+\s*[.,।:]?\s*", "", seg)   # drop the article number
    m = re.search(r"[:ः]", seg)
    title, body = (seg[:m.start()], seg[m.end():]) if m else (seg, "")
    by_num[fx["num"]] = {
        "num": fx["num"], "num_ocr": None,
        "part": fx.get("part", src["part"]), "part_title": fx.get("part_title", src["part_title"]),
        "title": title.strip(), "page": fx.get("page", src["page"]),
        "text": body.strip(), "manual_fix": True,
    }

arts = [by_num[n] for n in sorted(by_num)]
assert [a["num"] for a in arts] == list(range(1, 309)), "numbering is not 1..308"
json.dump(arts, open("data/processed/ne_articles.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

with open("data/fix_report.txt", "w", encoding="utf-8") as f:
    f.write(f"total articles: {len(arts)}\n")
    for n in [95, 96, 142, 143, 244, 245]:
        a = by_num[n]
        f.write(f"\n{n} | part {a['part']} | {a['title']}\n   {a['text'][:100]}\n")
print("done")
