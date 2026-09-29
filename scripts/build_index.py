import json, time
import chromadb
from sentence_transformers import SentenceTransformer

chunks = [json.loads(l) for l in open("data/processed/chunks.jsonl", encoding="utf-8")]

model = SentenceTransformer("BAAI/bge-m3", device="cuda")
model.half()
model.max_seq_length = 1024

t = time.time()
emb = model.encode([c["text"] for c in chunks], batch_size=8,
                   normalize_embeddings=True, show_progress_bar=True)
embed_secs = time.time() - t

client = chromadb.PersistentClient(path="chroma_db")
try:
    client.delete_collection("constitution")
except Exception:
    pass
col = client.create_collection("constitution", metadata={"hnsw:space": "cosine"})
col.add(
    ids=[c["id"] for c in chunks],
    embeddings=emb.tolist(),
    documents=[c["text"] for c in chunks],
    metadatas=[{"lang": c["lang"], "article": c["article"], "part": c["part"],
                "title": c["title"], "page": c["page"]} for c in chunks],
)

queries = [
    ("नेपालको सरकारी कामकाजको भाषा कुन हो?", 7),
    ("Who appoints the Chief Justice of Nepal?", 129),
    ("महिलाको हक के के हुन्?", 38),
    ("What is the right against exploitation?", 29),
]
with open("data/index_report.txt", "w", encoding="utf-8") as f:
    f.write(f"indexed {col.count()} chunks | embedding took {embed_secs:.1f}s | dim {emb.shape[1]}\n")
    for q, want in queries:
        qe = model.encode([q], normalize_embeddings=True).tolist()
        r = col.query(query_embeddings=qe, n_results=5)
        f.write(f"\nQ: {q}  (expect article {want})\n")
        for cid, dist, md in zip(r["ids"][0], r["distances"][0], r["metadatas"][0]):
            mark = "  <-- hit" if md["article"] == want else ""
            f.write(f"  {cid:10s} sim={1 - dist:.3f} | {md['title'][:45]}{mark}\n")
print("done")
