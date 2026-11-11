"""FastAPI service: upload documents, ask questions, get cited answers."""
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app import rag

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED = {".pdf", ".docx", ".xlsx", ".xlsm", ".txt", ".md"}

app = FastAPI(title="RAG Document Assistant", version="1.0")


class Question(BaseModel):
    question: str
    source: str | None = None  # optionally restrict to one document


@app.post("/documents")
async def upload(file: UploadFile):
    name = Path(file.filename or "").name
    if Path(name).suffix.lower() not in ALLOWED:
        raise HTTPException(400, f"Supported types: {', '.join(sorted(ALLOWED))}")
    dest = UPLOAD_DIR / name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        n = rag.ingest(dest)
    except Exception as e:
        raise HTTPException(422, f"Could not read {name}: {e}")
    return {"document": name, "chunks": n}


@app.get("/documents")
def documents():
    return {"documents": rag.list_documents()}


@app.post("/ask")
def ask(q: Question):
    return rag.ask(q.question, q.source)


@app.post("/documents/{name}/summary")
def summary(name: str):
    try:
        return rag.summarize(name)
    except KeyError:
        raise HTTPException(404, f"No document named {name}")


@app.get("/", response_class=HTMLResponse)
def ui():
    return (Path(__file__).parent / "ui.html").read_text()
