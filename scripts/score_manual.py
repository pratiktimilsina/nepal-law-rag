import csv, glob, statistics
from collections import defaultdict

COL = "correct (1/0.5/0)"
with open("eval/results_manual.txt", "w", encoding="utf-8") as out:
    for path in sorted(glob.glob("eval/manual_*.csv")):
        rows = [r for r in csv.DictReader(open(path, encoding="utf-8-sig")) if r[COL].strip()]
        if not rows:
            continue
        s = lambda rs: f"{statistics.mean(float(r[COL]) for r in rs):.3f} (n={len(rs)})"
        out.write(f"== {path} ==\nALL        {s(rows)}\n")
        for key in ["lang", "type"]:
            groups = defaultdict(list)
            for r in rows:
                groups[r[key]].append(r)
            for k in sorted(groups):
                out.write(f"{key}={k:11s}{s(groups[k])}\n")
        out.write("\n")
print("done")
