import json
from rag import retrieve

MODES = [("dense", False), ("bm25", False), ("hybrid", False), ("dense", True)]
qs = [json.loads(l) for l in open("eval/questions.jsonl", encoding="utf-8-sig") if l.strip()]
qs = [q for q in qs if q["gold"]]

def run(mode, route):
    rows = []
    for q in qs:
        arts = [h["article"] for h in retrieve(q["q"], k=10, pool=40, per_article=1, mode=mode, route=route)]
        rank = next((i + 1 for i, a in enumerate(arts) if a in q["gold"]), None)
        rows.append({**q, "rank": rank, "top": arts[:5]})
    return rows

def m(rs):
    n = len(rs)
    if n == 0:
        return "n=0"
    hit = lambda k: sum(1 for r in rs if r["rank"] and r["rank"] <= k) / n
    mrr = sum(1 / r["rank"] for r in rs if r["rank"]) / n
    return f"n={n:3d} | hit@1 {hit(1):.2f} | hit@3 {hit(3):.2f} | hit@5 {hit(5):.2f} | MRR {mrr:.3f}"

results = {f"{mo}{'+route' if ro else ''}": run(mo, ro) for mo, ro in MODES}
with open("eval/results_retrieval.txt", "w", encoding="utf-8") as f:
    for mode, rows in results.items():
        f.write(f"===== {mode} =====\n")
        f.write(f"ALL             {m(rows)}\n")
        for lang in ["ne", "en"]:
            f.write(f"lang={lang}         {m([r for r in rows if r['lang'] == lang])}\n")
        for t in sorted({r["type"] for r in rows}):
            f.write(f"type={t:10s} {m([r for r in rows if r['type'] == t])}\n")
        f.write("misses (rank != 1):\n")
        for r in rows:
            if r["rank"] != 1:
                f.write(f"  {r['id']} [{r['lang']}/{r['type']}] gold={r['gold']} rank={r['rank']} top5={r['top']} | {r['q']}\n")
        f.write("\n")
print("done")

