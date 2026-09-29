import json
fix = json.load(open("data/part_title_fixes.json", encoding="utf-8-sig"))
arts = json.load(open("data/processed/ne_articles.json", encoding="utf-8"))
changed = 0
for a in arts:
    if a["part_title"] in fix:
        a["part_title"] = fix[a["part_title"]]
        changed += 1
json.dump(arts, open("data/processed/ne_articles.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"part titles fixed on {changed} articles")
