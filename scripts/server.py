import json, re, time
from pathlib import Path

import ollama
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

import rag
from rag import answer, retrieve

ROOT = Path(__file__).resolve().parent.parent
NAMES = {"gemma3:4b": "Gemma 3 4B", "gemma3:12b": "Gemma 3 12B"}
DEV = str.maketrans("०१२३४५६७८९", "0123456789")
TO_DEV = str.maketrans("0123456789", "०१२३४५६७८९")
# article numbers, including lists like "238 and 239"; stops at "(" so 20(3) -> 20
CITE = re.compile(r"(?:धारा|articles?)\s*((?:[०-९0-9]{1,3}(?:\s*(?:,|and|र|तथा|&)\s*)?)+)", re.IGNORECASE)
# one article followed by clause brackets, e.g. 20(3), ६४(१)(ख)
CLAUSE = re.compile(r"(?:धारा|articles?)\s*([०-९0-9]{1,3})((?:\s*\([^)\s]{1,4}\))+)", re.IGNORECASE)


def citations_of(text):
    """Ordered (article, clause) pairs; clause is '' when none was given."""
    order = []
    for m in CITE.finditer(text):
        for d in re.findall(r"[०-९0-9]{1,3}", m.group(1)):
            n = int(d.translate(DEV))
            if 1 <= n <= 308 and n not in order:
                order.append(n)
    clauses = {}
    for m in CLAUSE.finditer(text):
        n = int(m.group(1).translate(DEV))
        cl = re.sub(r"\s+", "", m.group(2))
        clauses.setdefault(n, [])
        if cl not in clauses[n]:
            clauses[n].append(cl)
    return [(n, cl) for n in order for cl in clauses.get(n, [""])]


def fmt(n, clause, lang):
    if lang == "ne":
        return "धारा", str(n).translate(TO_DEV), clause.translate(TO_DEV)
    return "Article", str(n), clause.translate(DEV)


def top_marker(clause, lang):
    m = re.match(r"\([^)]+\)", clause or "")
    if not m:
        return ""
    return m.group().translate(TO_DEV) if lang == "ne" else m.group().translate(DEV)


def card_id(n, clause):
    m = re.match(r"\(([०-९0-9]+)\)", clause or "")
    return f"c-{n}-{int(m.group(1).translate(DEV))}" if m else f"c-{n}"


def pick(hits, n, clause):
    cands = [h for h in hits if h["article"] == n]
    for h in cands:
        mk = top_marker(clause, h["lang"])
        if mk and mk in h["text"]:
            return h
    return cands[0] if cands else None


def card(h, clause=""):
    header, _, body = h["text"].partition("\n")
    body = body.strip()
    mk = top_marker(clause, h["lang"])
    if len(body) > 900:
        start = body.find(mk) if mk else -1
        if start > 600:
            body = "… " + body[start:start + 900]
        else:
            body = body[:900]
        body = body.rsplit(" ", 1)[0] + " …"
    word, num, cl = fmt(h["article"], clause, h["lang"])
    return {"article": h["article"], "id": card_id(h["article"], clause), "word": word, "numeral": num,
            "clause": cl, "label": f"{word} {num}{cl}", "title": h["title"],
            "part": header.split(" | ")[0], "body": body, "mark": mk if mk and mk in body else "",
            "retrieved": True}


def clean(text):
    # display only: drop a trailing "Citations:" block some models append
    return re.split(r"\n\s*\**\s*citations?\s*:?", text, flags=re.IGNORECASE)[0].strip()


def nepali_display(text):
    # display only: gemma3:12b sometimes uses English conventions in Nepali answers
    # other Indic scripts (e.g. Gujarati, Bengali) leak into Nepali words; Unicode lays these
    # blocks out in parallel, so map each character to the same position in Devanagari
    text = "".join(chr(0x0900 + (ord(c) & 0x7F)) if 0x0980 <= ord(c) <= 0x0DFF else c for c in text)
    text = re.sub(r"\bArticles?\s*([0-9०-९]{1,3})", lambda m: "धारा " + m.group(1).translate(TO_DEV), text)
    return re.sub(r"(?<=[\u0900-\u097F)])\.(?=\s|$)", "।", text)


class Ask(BaseModel):
    question: str
    model: str = "gemma3:4b"


app = FastAPI()


@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/api/health")
def health():
    try:
        ollama.list()
        ok = True
    except Exception:
        ok = False
    return {"ollama": ok, "passages": rag._col.count(), "models": list(NAMES)}


def line(obj):
    return json.dumps(obj, ensure_ascii=False) + "\n"


@app.post("/api/ask")
def ask(req: Ask):
    q = req.question.strip()[:500]
    model = req.model if req.model in NAMES else "gemma3:4b"

    def events():
        if not q:
            yield line({"error": "Type a question first."})
            return
        t0 = time.time()
        hits = retrieve(q)
        rs = round(time.time() - t0, 2)
        yield line({"stage": "retrieved", "passages": len(hits), "articles": len({h["article"] for h in hits}), "retrieve_s": rs})
        try:
            r = answer(q, model=model, hits=hits)
        except Exception:
            yield line({"error": "Could not reach the local model. Start Ollama and try again."})
            return

        qlang = "ne" if re.search(r"[\u0900-\u097F]", q) else "en"
        cites = citations_of(r["answer"])
        citations = []
        for n, cl in cites:
            h = pick(hits, n, cl)
            if h:
                citations.append(card(h, cl))
            else:
                word, num, c = fmt(n, cl, qlang)
                citations.append({"article": n, "id": card_id(n, cl), "label": f"{word} {num}{c}", "retrieved": False})
        cited = {n for n, _ in cites}
        first = {}
        for h in sorted(hits, key=lambda h: h["lang"] != qlang):  # prefer the question's language
            first.setdefault(h["article"], h)
        other = [card(h) for n, h in first.items() if n not in cited]
        text = clean(r["answer"])
        yield line({
            "stage": "done",
            "answer": nepali_display(text) if qlang == "ne" else text,
            "citations": citations,
            "other": other,
            "meta": {"model": NAMES[model], "passages": len(hits), "articles_cited": len(citations),
                     "grounded": bool(citations) and all(c["retrieved"] for c in citations),
                     "retrieve_s": rs, "generate_s": round(r["generate_s"], 1),
                     "output_tokens": r["output_tokens"]},
        })

    return StreamingResponse(events(), media_type="application/x-ndjson")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
