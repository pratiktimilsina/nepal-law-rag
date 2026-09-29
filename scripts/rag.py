import json, re, time
import chromadb
import ollama
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

LLM = "gemma3:4b"
DEV = str.maketrans("०१२३४५६७८९", "0123456789")
_encoder = SentenceTransformer("BAAI/bge-m3", device="cpu")
_col = chromadb.PersistentClient(path="chroma_db").get_collection("constitution")

_chunks = {}
for line in open("data/processed/chunks.jsonl", encoding="utf-8"):
    c = json.loads(line)
    _chunks[c["id"]] = c
_ids = list(_chunks)

# Devanagari block without danda (U+0964/0965); keeps vowel signs inside words
_TOKEN = re.compile(r"[0-9a-z\u0900-\u0963\u0966-\u097F]+")
# "धारा ५१", "Article 51", "art. 51"
_LOOKUP = re.compile(r"(?:धारा|article|art\.?)\s*([०-९0-9]{1,3})", re.IGNORECASE)

def tokenize(text):
    return _TOKEN.findall(text.lower())

_bm25 = BM25Okapi([tokenize(_chunks[i]["text"]) for i in _ids])

SYSTEM = """You are a legal assistant for the Constitution of Nepal.
Answer ONLY using the context excerpts provided. Each excerpt starts with a header naming its Part and Article.
Use only the excerpts that directly answer the question; ignore the rest.
If the answer is not in the context, reply with exactly this sentence and nothing else: "I could not find this in the Constitution." for English questions, or "संविधानमा यस सम्बन्धी व्यवस्था फेला परेन।" for Nepali questions.
Cite only articles whose headers appear in the excerpts. In English answers write citations as (Article <number>); in Nepali answers write them as (धारा <number>) using Devanagari digits. In English answers never use Devanagari script at all, including in citations.
Answer in {lang}. First answer the question directly in 1-3 complete sentences, then give the citations. Do not just list article numbers."""


def is_nepali(text):
    return bool(re.search(r"[\u0900-\u097F]", text))


def _dense(query, pool):
    qe = _encoder.encode([query], normalize_embeddings=True).tolist()
    return _col.query(query_embeddings=qe, n_results=pool)["ids"][0]


def _sparse(query, pool):
    scores = _bm25.get_scores(tokenize(query))
    order = sorted(range(len(_ids)), key=lambda i: -scores[i])[:pool]
    return [_ids[i] for i in order]


def _routed(query):
    m = _LOOKUP.search(query)
    if not m:
        return []
    n = int(m.group(1).translate(DEV))
    if not 1 <= n <= 308:
        return []
    lang = "ne" if is_nepali(query) else "en"
    ids = [cid for cid, c in _chunks.items() if c["article"] == n]
    return sorted(ids, key=lambda cid: (_chunks[cid]["lang"] != lang, int(cid.rsplit("-", 1)[1])))


def retrieve(query, k=5, pool=15, per_article=2, mode="dense", rrf_k=60, route=True):
    if mode == "dense":
        ranked = _dense(query, pool)
    elif mode == "bm25":
        ranked = _sparse(query, pool)
    else:
        fused = {}
        for lst in (_dense(query, pool), _sparse(query, pool)):
            for r, cid in enumerate(lst):
                fused[cid] = fused.get(cid, 0) + 1 / (rrf_k + r + 1)
        ranked = sorted(fused, key=lambda c: -fused[c])
    if route:
        forced = _routed(query)
        ranked = forced + [cid for cid in ranked if cid not in forced]
    hits, count = [], {}
    for cid in ranked:
        c = _chunks[cid]
        a = c["article"]
        if count.get(a, 0) >= per_article:
            continue
        count[a] = count.get(a, 0) + 1
        hits.append({"id": cid, "text": c["text"], "lang": c["lang"], "article": a,
                     "part": c["part"], "title": c["title"], "page": c["page"]})
        if len(hits) == k:
            break
    return hits


def answer(query, model=LLM, mode="dense", hits=None):
    t0 = time.time()
    hits = hits if hits is not None else retrieve(query, mode=mode)
    t1 = time.time()
    context = "\n\n---\n\n".join(h["text"] for h in hits)
    lang = "Nepali" if is_nepali(query) else "English"
    resp = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM.format(lang=lang)},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ],
        options={"temperature": 0, "num_ctx": 4096},
        keep_alive="30m",
    )
    t2 = time.time()
    return {
        "answer": resp["message"]["content"], "hits": hits,
        "retrieve_s": t1 - t0, "generate_s": t2 - t1,
        "context_chars": len(context),
        "prompt_tokens": resp.get("prompt_eval_count"),
        "output_tokens": resp.get("eval_count"),
        "prompt_s": (resp.get("prompt_eval_duration") or 0) / 1e9,
        "output_s": (resp.get("eval_duration") or 0) / 1e9,
    }


if __name__ == "__main__":
    ollama.chat(model=LLM, messages=[{"role": "user", "content": "hi"}],
                options={"num_ctx": 4096}, keep_alive="30m")  # warm-up
    tests = [
        "नेपालको संविधान २०७२ कहिले जारी भएको हो?",
        "Who appoints the Chief Justice of Nepal?",
        "वंशजको आधारमा नेपालको नागरिकता कसले पाउँछ?",
    ]
    with open("data/rag_test.txt", "w", encoding="utf-8") as f:
        for q in tests:
            r = answer(q)
            f.write(f"Q: {q}\n")
            f.write(f"sources: {[h['id'] for h in r['hits']]}\n")
            f.write(f"time: retrieve {r['retrieve_s']:.2f}s | generate {r['generate_s']:.1f}s "
                    f"(prompt {r['prompt_s']:.1f}s, output {r['output_s']:.1f}s)\n")
            f.write(f"tokens: context {r['context_chars']} chars -> prompt {r['prompt_tokens']} tokens "
                    f"| output {r['output_tokens']} tokens\n")
            f.write(f"A: {r['answer']}\n\n{'-' * 60}\n\n")
    print("done")

