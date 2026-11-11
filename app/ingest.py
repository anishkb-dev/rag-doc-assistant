"""Turn PDF / DOCX / XLSX files into cited text chunks."""
from pathlib import Path

import docx
import openpyxl
import pymupdf

CHUNK_CHARS = 900
OVERLAP = 150


def extract(path: Path) -> list[tuple[str, str]]:
    """Return (location, text) pairs, e.g. ("page 3", "..."), so every chunk can be cited."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        with pymupdf.open(path) as pdf:
            return [(f"page {i + 1}", p.get_text()) for i, p in enumerate(pdf)]
    if ext == ".docx":
        # Group paragraphs under their nearest heading so citations point somewhere useful.
        sections, heading, buf = [], "start", []
        for p in docx.Document(path).paragraphs:
            if p.style.name.startswith("Heading") and p.text.strip():
                if buf:
                    sections.append((f"section '{heading}'", "\n".join(buf)))
                heading, buf = p.text.strip(), []
            elif p.text.strip():
                buf.append(p.text)
        if buf:
            sections.append((f"section '{heading}'", "\n".join(buf)))
        return sections
    if ext in (".xlsx", ".xlsm"):
        out = []
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                continue
            header = [str(h) if h is not None else "" for h in rows[0]]
            # One line per row, "col: value" so the LLM sees which column each number belongs to.
            # No per-line row numbers: models confuse them with citation numbers like [3].
            lines = [
                "; ".join(f"{h}: {v}" for h, v in zip(header, row) if v is not None)
                for row in rows[1:]
            ]
            for i in range(0, len(lines), 25):
                out.append((f"sheet '{ws.title}' rows {i + 2}-{min(i + 26, len(lines) + 1)}", "\n".join(lines[i:i + 25])))
        return out
    if ext in (".txt", ".md"):
        return [("text", path.read_text(errors="ignore"))]
    raise ValueError(f"Unsupported file type: {ext}")


def chunk(text: str) -> list[str]:
    text = " ".join(text.split())
    if len(text) <= CHUNK_CHARS:
        return [text] if text else []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        if end < len(text):  # prefer to cut at a sentence boundary
            cut = text.rfind(". ", start + CHUNK_CHARS // 2, end)
            end = cut + 1 if cut != -1 else end
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = end - OVERLAP
    return chunks


def to_chunks(path: Path) -> list[dict]:
    return [
        {"text": c, "source": path.name, "location": loc}
        for loc, text in extract(path)
        for c in chunk(text)
    ]
