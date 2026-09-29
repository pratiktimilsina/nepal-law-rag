import json
with open("data/script_mix_check.txt", "w", encoding="utf-8") as f:
    for tag in ["gemma3_4b", "gemma3_12b"]:
        rows = [json.loads(l) for l in open(f"eval/answers_{tag}.jsonl", encoding="utf-8")]
        ne = [r for r in rows if r["lang"] == "ne"]
        bad = [r["id"] for r in ne if any(0x0980 <= ord(c) <= 0x0DFF for c in r["answer"])]
        f.write(f"{tag}: Nepali answers with characters from other Indic scripts: {len(bad)}/30 {bad}\n")
print("done")
