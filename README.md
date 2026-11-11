# RAG Document Assistant

Ask questions about your company's PDF, Word and Excel files and get answers that **cite the exact page, section or sheet** they came from. When the answer isn't in the documents, it says so instead of guessing.

- **Upload** PDF, DOCX, XLSX (plus TXT/MD) through the web UI or the API
- **Ask** in plain English; every sentence carries a citation like `[1]`, and the response includes the cited excerpts
- **Summarize** any document into an overview plus key facts (numbers, dates, obligations) with locations
- **Any LLM**: works with any OpenAI-compatible endpoint, such as OpenAI, Groq, or a local Ollama/vLLM model
- **Local embeddings and vector DB** (ChromaDB + all-MiniLM-L6-v2), so documents are never sent to an embedding API

## How hallucination is kept down

1. **Grounded prompt.** The model may only use the retrieved excerpts, and is told the exact citation numbers it is allowed to use.
2. **Relevance floor.** Weak matches are dropped before the LLM sees them, so it has fewer distractors to mis-cite.
3. **Checkable citations.** The API returns only the excerpts the answer actually cites, so a user can verify every claim.
4. **Explicit refusal.** Out-of-scope questions get "I couldn't find this in the uploaded documents."
5. **Measured, not claimed.** `eval/` holds a question set with expected answers, the expected source document, and unanswerable questions.

```
$ python -m eval.run_eval      # local 7B model (Qwen2.5-7B via Ollama)
...
10/10 passed
```

The eval surfaced a real bug along the way: spreadsheet lines prefixed with `row 3:` led the model to cite `[3]`. Fixed in `app/ingest.py`.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # choose your LLM provider
set -a; source .env; set +a
uvicorn app.main:app --reload   # open http://localhost:8000
```

Sample documents (a fictional company handbook, contract and sales sheet): `python samples/make_samples.py`.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/documents` | multipart `file` | `{document, chunks}` |
| `GET` | `/documents` | | `{documents: [...]}` |
| `POST` | `/ask` | `{"question": "...", "source": "optional.pdf"}` | `{answer, citations: [{n, source, location, excerpt}]}` |
| `POST` | `/documents/{name}/summary` | | `{source, summary}` |

Interactive docs at `/docs`.

## Layout

```
app/ingest.py   text extraction per format (page / heading section / sheet rows) + chunking
app/rag.py      vector store, retrieval, grounded answering, summaries
app/main.py     FastAPI routes
app/ui.html     single-file web UI
eval/           accuracy + refusal test set
```

## Next steps for production

OCR for scanned PDFs, a hybrid keyword + vector search with re-ranking for large corpora, map-reduce summaries for very long documents, per-user auth, and Postgres/pgvector or Pinecone in place of local Chroma.
