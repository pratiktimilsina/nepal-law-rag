import json, re
PERIOD = re.compile(r"(?<=[\u0900-\u097F)])\.(?=\s|$)")
with open("eval/punctuation_report.txt", "w", encoding="utf-8") as f:
    for tag in ["gemma3_4b", "gemma3_12b"]:
        rows = [json.loads(l) for l in open(f"eval/answers_{tag}.jsonl", encoding="utf-8")]
        ne = [r for r in rows if r["lang"] == "ne"]
        period = [r["id"] for r in ne if PERIOD.search(r["answer"])]
        danda = [r["id"] for r in ne if "।" in r["answer"]]
        article = [r["id"] for r in ne if re.search(r"\bArticles?\b", r["answer"])]
        f.write(f"{tag}: Nepali answers = {len(ne)}\n")
        f.write(f"  uses '.' after Devanagari: {len(period)} {period}\n")
        f.write(f"  uses '।':                  {len(danda)}\n")
        f.write(f"  writes 'Article':          {len(article)} {article}\n\n")
print("done")
