import csv, json, os, re, statistics, sys
import ollama
from rag import answer

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemma3:4b"
TAG = MODEL.replace(":", "_")
DEV = str.maketrans("०१२३४५६७८९", "0123456789")
CITE = re.compile(r"(?:धारा|articles?)\s*((?:[०-९0-9]{1,3}(?:\s*(?:,|and|र|तथा|&)\s*)?)+)", re.IGNORECASE)

def cited(text):
    out = set()
    for m in CITE.finditer(text):
        for d in re.findall(r"[०-९0-9]{1,3}", m.group(1)):
            out.add(int(d.translate(DEV)))
    return sorted(out)

def refused(text):
    return any(p in text.lower() for p in ["could not find", "does not specify", "does not explicitly", "does not state", "does not mention", "not mentioned", "no information"]) or any(p in text for p in ["फेला परेन", "जानकारी पाइदैन", "जानकारी पाइँदैन", "उल्लेख छैन", "उल्लेख गरिएको छैन"])

ollama.chat(model=MODEL, messages=[{"role": "user", "content": "hi"}],
            options={"num_ctx": 4096}, keep_alive="30m")  # warm-up

qs = [json.loads(l) for l in open("eval/questions.jsonl", encoding="utf-8-sig") if l.strip()]
rows = []
for i, q in enumerate(qs, 1):
    r = answer(q["q"], model=MODEL)
    a = r["answer"].strip()
    rows.append({
        **q, "answer": a, "cited": cited(a), "refused": refused(a),
        "retrieved": [h["article"] for h in r["hits"]],
        "latin_words": re.findall(r"[A-Za-z]{2,}", a) if q["lang"] == "ne" else [],
        "has_devanagari": bool(re.search(r"[\u0900-\u097F]", a)) if q["lang"] == "en" else False,
        "generate_s": r["generate_s"], "output_tokens": r["output_tokens"],
    })
    print(f"{i}/{len(qs)}", end="\r")

with open(f"eval/answers_{TAG}.jsonl", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

def report(rs, f, label):
    ans = [r for r in rs if r["gold"]]
    neg = [r for r in rs if not r["gold"]]
    ne = [r for r in rs if r["lang"] == "ne"]
    en = [r for r in rs if r["lang"] == "en"]
    all_cites = [c for r in ans for c in r["cited"]]
    pct = lambda x, n: f"{x}/{n} ({x / n:.0%})" if n else "n/a"
    f.write(f"--- {label} (n={len(rs)}) ---\n")
    f.write(f"refusal on negatives:      {pct(sum(r['refused'] for r in neg), len(neg))}\n")
    f.write(f"false refusals:            {pct(sum(r['refused'] for r in ans), len(ans))}\n")
    f.write(f"citation recall:           {pct(sum(1 for r in ans if set(r['cited']) & set(r['gold'])), len(ans))}\n")
    f.write(f"citation precision:        {pct(sum(1 for c, r in [(c, r) for r in ans for c in r['cited']] if c in r['gold']), len(all_cites))}\n")
    f.write(f"latin words in ne answers: {pct(sum(1 for r in ne if r['latin_words']), len(ne))}\n")
    f.write(f"devanagari in en answers:  {pct(sum(1 for r in en if r['has_devanagari']), len(en))}\n")
    f.write(f"mean generate time:        {statistics.mean(r['generate_s'] for r in rs):.1f}s | "
            f"mean output tokens {statistics.mean(r['output_tokens'] or 0 for r in rs):.0f}\n\n")

with open(f"eval/results_answers_{TAG}.txt", "w", encoding="utf-8") as f:
    f.write(f"model: {MODEL}\n\n")
    report(rows, f, "ALL")
    report([r for r in rows if r["lang"] == "ne"], f, "Nepali")
    report([r for r in rows if r["lang"] == "en"], f, "English")
    f.write("flagged answers:\n")
    for r in rows:
        flags = []
        if r["gold"] and not set(r["cited"]) & set(r["gold"]):
            flags.append(f"no gold cite (cited {r['cited']}, gold {r['gold']})")
        if not r["gold"] and not r["refused"]:
            flags.append("negative NOT refused")
        if r["gold"] and r["refused"]:
            flags.append("false refusal")
        if r["latin_words"]:
            flags.append(f"latin words {r['latin_words']}")
        if r["has_devanagari"]:
            flags.append("devanagari in English answer")
        if flags:
            f.write(f"  {r['id']} [{r['lang']}/{r['type']}] {'; '.join(flags)}\n     Q: {r['q']}\n     A: {r['answer'][:300]}\n")

manual_path = f"eval/manual_{TAG}.csv"
if os.path.exists(manual_path):
    manual_path = f"eval/manual_{TAG}_new.csv"  # never overwrite a scored sheet
with open(manual_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "lang", "type", "gold", "cited", "question", "answer", "correct (1/0.5/0)", "notes"])
    for r in rows:
        w.writerow([r["id"], r["lang"], r["type"], r["gold"], r["cited"], r["q"], r["answer"], "", ""])
print("\ndone")
