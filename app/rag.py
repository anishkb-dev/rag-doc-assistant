"""Retrieval + grounded answering with citations."""
import hashlib
import os
from pathlib import Path

import chromadb
from openai import OpenAI

from app.ingest import to_chunks

DB_DIR = os.getenv("DB_DIR", "data/chroma")
TOP_K = int(os.getenv("TOP_K", "6"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.2"))
# Any OpenAI-compatible endpoint: OpenAI, Groq, Together, or a local Ollama / vLLM server.
llm = OpenAI(
    base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
    api_key=os.getenv("LLM_API_KEY", "not-needed-for-local"),
)
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Chroma's built-in embedding model (all-MiniLM-L6-v2, runs locally, no API key).
collection = chromadb.PersistentClient(DB_DIR).get_or_create_collection(
    "docs", metadata={"hnsw:space": "cosine"}
)

NOT_FOUND = "I couldn't find this in the uploaded documents."

ANSWER_PROMPT = """You answer questions using ONLY the numbered excerpts below from company documents.
Rules:
- Every factual sentence must end with the number of the excerpt it came from, in square brackets.
  The only valid numbers are: {valid}. Never cite any other number.
- If the excerpts do not contain the answer, reply exactly: "{not_found}"
- Do not use outside knowledge. Do not guess numbers, dates or names.

Excerpts:
{context}

Question: {question}"""


def ingest(path: Path) -> int:
    chunks = to_chunks(path)
    collection.delete(where={"source": path.name})  # re-uploading a file replaces it
    if not chunks:
        return 0
    collection.add(
        ids=[hashlib.sha1(f"{path.name}:{i}:{c['text']}".encode()).hexdigest() for i, c in enumerate(chunks)],
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"], "location": c["location"]} for c in chunks],
    )
    return len(chunks)


def list_documents() -> list[str]:
    metas = collection.get(include=["metadatas"])["metadatas"]
    return sorted({m["source"] for m in metas})


def retrieve(question: str, source: str | None = None) -> list[dict]:
    if collection.count() == 0:
        return []
    res = collection.query(
        query_texts=[question],
        n_results=min(TOP_K, collection.count()),
        where={"source": source} if source else None,
    )
    hits = [
        {"text": t, "source": m["source"], "location": m["location"], "score": round(1 - d, 3)}
        for t, m, d in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]
    # Drop weak matches: fewer distractors means fewer wrong citations.
    floor = max(MIN_SCORE, hits[0]["score"] * 0.5)
    return [h for i, h in enumerate(hits) if i == 0 or h["score"] >= floor]


def _chat(prompt: str) -> str:
    r = llm.chat.completions.create(
        model=MODEL, temperature=0, messages=[{"role": "user", "content": prompt}]
    )
    return (r.choices[0].message.content or "").strip()


def ask(question: str, source: str | None = None) -> dict:
    hits = retrieve(question, source)
    if not hits:
        return {"answer": NOT_FOUND, "citations": []}
    context = "\n\n".join(
        f"[{i}] ({h['source']}, {h['location']})\n{h['text']}" for i, h in enumerate(hits, 1)
    )
    valid = ", ".join(f"[{i}]" for i in range(1, len(hits) + 1))
    answer = _chat(ANSWER_PROMPT.format(not_found=NOT_FOUND, valid=valid, context=context, question=question))
    # Return only the excerpts the model actually cited, so every reference is checkable.
    cited = [
        {"n": i, "source": h["source"], "location": h["location"], "excerpt": h["text"][:300]}
        for i, h in enumerate(hits, 1)
        if f"[{i}]" in answer
    ]
    return {"answer": answer, "citations": cited}


def summarize(source: str) -> dict:
    got = collection.get(where={"source": source}, include=["documents", "metadatas"])
    if not got["documents"]:
        raise KeyError(source)
    # Keep document order and cap the input; for very long docs this would become map-reduce.
    text = "\n\n".join(f"({m['location']}) {d}" for d, m in zip(got["documents"], got["metadatas"]))[:24000]
    summary = _chat(
        "Summarize this document for a busy manager. Give: a 3-sentence overview, then "
        "'Key facts' as bullet points (numbers, dates, names, obligations), each ending with "
        f"its location in parentheses. Use only the text below.\n\nDocument: {source}\n\n{text}"
    )
    return {"source": source, "summary": summary}
