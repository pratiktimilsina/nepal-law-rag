import json, re, statistics

MAX = 1200
TO_DEV = str.maketrans("0123456789", "०१२३४५६७८९")

ne = {a["num"]: a for a in json.load(open("data/processed/ne_articles.json", encoding="utf-8"))}
en = {a["num"]: a for a in json.load(open("data/processed/en_articles.json", encoding="utf-8"))}

PATS = {
    "ne": [r"(?=\([०-९]+\))", r"(?=\([क-ह]\))", r"(?<=।)\s"],
    "en": [r"(?=\(\d+\))", r"(?=\([a-z]\))", r"(?<=\.)\s"],
}

def clean(t):
    t = re.sub(r"(?<=[।.])[\s0-9०-९\-–—]+$", "", t)
    return re.sub(r"\s+", " ", t).strip()

def chunk(text, pats):
    if len(text) <= MAX:
        return [text]
    if not pats:
        return [text[i:i + MAX] for i in range(0, len(text), MAX)]
    parts = [p for p in re.split(pats[0], text) if p.strip()]
    if len(parts) == 1:
        return chunk(text, pats[1:])
    out, buf = [], ""
    for p in parts:
        if len(p) > MAX:
            if buf:
                out.append(buf)
                buf = ""
            out.extend(chunk(p, pats[1:]))
        elif len(buf) + len(p) > MAX:
            out.append(buf)
            buf = p
        else:
            buf += p
    if buf:
        out.append(buf)
    return [o.strip() for o in out if o.strip()]

# 1) alignment checks
part_mismatch = [(n, ne[n]["part"], en[n]["part"]) for n in range(1, 309) if ne[n]["part"] != en[n]["part"]]
ratios = {n: len(clean(ne[n]["text"])) / max(1, len(clean(en[n]["text"]))) for n in range(1, 309)}
med = statistics.median(ratios.values())
outliers = sorted(ratios.items(), key=lambda kv: abs(kv[1] - med), reverse=True)[:10]

# 2) build chunks
chunks = []
for n in range(1, 309):
    part = en[n]["part"]
    for lang, a in [("ne", ne[n]), ("en", en[n])]:
        body = clean(a["text"])
        if lang == "ne":
            header = f"भाग {str(part).translate(TO_DEV)} – {a['part_title']} | धारा {str(n).translate(TO_DEV)}: {a['title']}"
        else:
            header = f"Part {part} – {a['part_title']} | Article {n}: {a['title']}"
        for i, piece in enumerate(chunk(body, PATS[lang])):
            chunks.append({"id": f"{lang}-{n}-{i}", "lang": lang, "article": n, "part": part,
                           "title": a["title"], "page": a["page"],
                           "text": header + "\n" + piece})

with open("data/processed/chunks.jsonl", "w", encoding="utf-8") as f:
    for c in chunks:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

with open("data/chunk_report.txt", "w", encoding="utf-8") as f:
    f.write(f"part mismatches (ne vs en): {len(part_mismatch)} -> {part_mismatch[:15]}\n")
    f.write(f"median ne/en length ratio: {med:.2f}\n")
    f.write("top 10 ratio outliers (article, ratio, ne chars, en chars):\n")
    for n, r in outliers:
        f.write(f"  {n}: {r:.2f} | {len(clean(ne[n]['text']))} | {len(clean(en[n]['text']))} | {en[n]['title'][:40]}\n")
    for lang in ["ne", "en"]:
        L = [len(c["text"]) for c in chunks if c["lang"] == lang]
        f.write(f"\n{lang}: {len(L)} chunks | mean {statistics.mean(L):.0f} chars | max {max(L)}\n")
    f.write("\nsample chunks:\n")
    for cid in ["ne-42-0", "en-42-0", "ne-51-3", "en-308-0"]:
        c = next((x for x in chunks if x["id"] == cid), None)
        if c:
            f.write(f"\n[{cid}]\n{c['text'][:300]}\n")
print("done")
