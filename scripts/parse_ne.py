import json, re

DEV = str.maketrans("०१२३४५६७८९", "0123456789")
PART = re.compile(r"^भाग\s*[-–—]+\s*([०-९0-9]+)")
ART = re.compile(r"^(द?[०-९]{1,3})(?![०-९])\s*[.,।:]?\s*(\D.{1,150}?)\s*[:ः]\s*(.*)$")
SCHED = re.compile(r"^अनुसूची\s*[-–—]*\s*[०-९0-9]")
NUM_LINE = re.compile(r"^\s*([०-९]{1,3})\s*\.")
TOTAL = 308

def num(s):
    return int(s.replace("द", "८").translate(DEV))

pages = [json.loads(l) for l in open("data/processed/ne_pages.jsonl", encoding="utf-8")]
pages.sort(key=lambda p: p["page"])

layer_page, e = {}, 1
for p in pages:
    for line in p["layer"].splitlines():
        m = NUM_LINE.match(line)
        if m and num(m.group(1)) == e:
            layer_page[e] = p["page"]
            e += 1

blocks, cur, part, part_title, want_title, stop = [], None, None, None, False, False
for p in pages:
    for raw in p["ocr"].splitlines():
        line = raw.replace("\u200c", "").replace("\u200d", "").strip()
        if not line:
            continue
        if re.fullmatch(r"[०-९0-9\s\-–—]{1,12}", line) and re.search(r"[०-९0-9]", line):
            continue  # page number
        if not re.search(r"[\u0900-\u097F]", line) and len(line) < 10:
            continue
        if part is not None and part >= 35 and SCHED.match(line):
            stop = True
            break
        m = PART.match(line)
        if m:
            part, want_title = num(m.group(1)), True
            continue
        if want_title:
            part_title, want_title = line, False
            continue
        m = ART.match(line)
        if m:
            cur = {"num_ocr": num(m.group(1)), "part": part, "part_title": part_title,
                   "title": m.group(2), "page": p["page"], "text": m.group(3)}
            blocks.append(cur)
            continue
        if cur:
            cur["text"] += " " + line
    if stop:
        break

arts, a, missing, uncertain, merged = [], 0, [], [], []
for i, b in enumerate(blocks):
    if a >= TOTAL:
        break
    n = b["num_ocr"]
    nxt = blocks[i + 1]["num_ocr"] if i + 1 < len(blocks) else None
    if n == a + 1:
        new = n
    elif nxt == a + 1 and arts:
        arts[-1]["text"] += f" {b['title']}: {b['text']}"
        merged.append((b["page"], n, b["title"][:30]))
        continue
    elif nxt == a + 2:
        new = a + 1
        uncertain.append((b["page"], new, n, "digit misread"))
    elif a + 1 < n <= TOTAL and nxt == n + 1:
        new = n
        missing.extend(range(a + 1, n))
    else:
        new = a + 1
        uncertain.append((b["page"], new, n, "guessed"))
    b["num"] = new
    arts.append(b)
    a = new

mismatch = [(x["num"], x["page"], layer_page[x["num"]]) for x in arts
            if x["num"] in layer_page and x["page"] != layer_page[x["num"]] and x["num"] > 2]

json.dump(arts, open("data/processed/ne_articles.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

with open("data/parse_report.txt", "w", encoding="utf-8") as f:
    f.write(f"heading candidates: {len(blocks)} | articles assigned: {len(arts)} (target {TOTAL})\n")
    f.write(f"missing: {len(missing)} -> {missing}\n")
    f.write(f"merged false headings: {len(merged)} -> {merged[:10]}\n")
    f.write(f"uncertain: {len(uncertain)}\n")
    for u in uncertain[:30]:
        f.write(f"  page {u[0]}: assigned {u[1]}, OCR read {u[2]} ({u[3]})\n")
    f.write(f"page mismatches vs text layer (3-134): {len(mismatch)} -> {mismatch[:15]}\n")
    for n in [88, 96, 245, 254, 255, 256]:
        hit = [x for x in arts if x["num"] == n]
        if hit:
            x = hit[0]
            f.write(f"\n--- article {n} | page {x['page']} | {len(x['text'])} chars ---\n")
            f.write(f"{x['title']}: {x['text'][:120]}\n")
print("done")
