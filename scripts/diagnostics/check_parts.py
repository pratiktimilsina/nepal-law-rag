import json
from collections import Counter

ne = {a["num"]: a for a in json.load(open("data/processed/ne_articles.json", encoding="utf-8"))}
en = {a["num"]: a for a in json.load(open("data/processed/en_articles.json", encoding="utf-8"))}

titles = {}
for n in range(1, 309):
    titles.setdefault(en[n]["part"], Counter())[ne[n]["part_title"]] += 1

with open("data/part_report.txt", "w", encoding="utf-8") as f:
    prev_top = None
    for p in sorted(titles):
        top = titles[p].most_common(1)[0][0]
        flag = ""
        if len(titles[p]) > 1:
            flag += " MIXED"
        if top == prev_top:
            flag += " SAME-AS-PREVIOUS"
        en_title = next(en[n]["part_title"] for n in range(1, 309) if en[n]["part"] == p)
        f.write(f"part {p}{flag} | {dict(titles[p])} | EN: {en_title}\n")
        prev_top = top
print("done")
