import json, re
import pymupdf

TOTAL = 308
HEAD = re.compile(r"(?m)^[ \t]*(\d{1,3})\.[ \t]*(?:\n[ \t]*){0,3}([A-Z][^:]{0,250}?)(?::|(?=\s*\(1\)))")
PART = re.compile(r"(?m)^[ \t]*Part[ \t]*[-–][ \t]*(\d+)[ \t]*\n[ \t]*(.+)$")
SCHED = re.compile(r"(?m)^[ \t]*Schedule[ \t]*[-–]?[ \t]*1\b")

doc = pymupdf.open("data/raw/constitution_en.pdf")
full, starts = "", []
for i, page in enumerate(doc):
    r = page.rect
    starts.append(len(full))
    txt = page.get_text(clip=pymupdf.Rect(r.x0, r.y0 + 50, r.x1, r.y1 - 50))
    # drop lines that are only a number: page numbers left after cropping
    full += "\n".join(l for l in txt.splitlines() if not re.fullmatch(r"\s*\d{1,3}\s*", l)) + "\n"

def page_of(pos):
    p = 0
    for i, s in enumerate(starts):
        if s <= pos:
            p = i
        else:
            break
    return p

parts = [(m.start(), int(m.group(1)), m.group(2).strip()) for m in PART.finditer(full)]
body_start = parts[0][0]  # skip front matter (amendment list, preamble)

heads, exp = [], 1
for m in HEAD.finditer(full, body_start):
    if int(m.group(1)) == exp:
        heads.append(m)
        exp += 1
        if exp > TOTAL:
            break

sched = SCHED.search(full, heads[-1].end()) if heads else None
end_of_last = sched.start() if sched else len(full)

ws = lambda s: re.sub(r"\s+", " ", s).strip()
arts = []
for k, m in enumerate(heads):
    end = heads[k + 1].start() if k + 1 < len(heads) else end_of_last
    nxt_part = [pp[0] for pp in parts if m.end() < pp[0] < end]
    if nxt_part:
        end = nxt_part[0]  # don't swallow the next Part heading
    part = [p for p in parts if p[0] < m.start()]
    arts.append({
        "num": int(m.group(1)),
        "part": part[-1][1] if part else None,
        "part_title": part[-1][2] if part else None,
        "title": ws(m.group(2)),
        "page": page_of(m.start()),
        "text": ws(full[m.end():end]),
    })

json.dump(arts, open("data/processed/en_articles.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

with open("data/en_report.txt", "w", encoding="utf-8") as f:
    f.write(f"articles: {len(arts)} (target {TOTAL}) | chain stopped at: {exp - 1}\n")
    f.write(f"parts found: {len(parts)} | schedule start found: {sched is not None}\n")
    odd = [(a["num"], len(a["text"]), a["title"][:50]) for a in arts
           if len(a["text"]) < 40 or len(a["text"]) > 15000 or len(a["title"]) > 150]
    f.write(f"suspicious lengths: {odd}\n")
    if exp <= TOTAL:
        after = heads[-1].end()
        m = re.search(rf"(?m)^[ \t]*{exp}\s*\.", full[after:])
        f.write(f"\n!! chain broke. raw text near next '{exp}.' heading:\n")
        if m:
            f.write(repr(full[after + m.start(): after + m.start() + 250]) + "\n")
        else:
            i = full.find(str(exp), after)
            f.write("no line-start match; first plain occurrence:\n")
            f.write(repr(full[max(0, i - 60): i + 200]) + "\n")
    for n in [1, 2, 125, 242, 245, 308]:
        if n <= len(arts):
            a = arts[n - 1]
            f.write(f"\n{n} | part {a['part']} ({a['part_title']}) | page {a['page']} | {a['title']}\n")
            f.write(f"   {a['text'][:110]}\n")
print("done")
