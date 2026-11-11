"""Measure answer accuracy, citation correctness, and refusal on unanswerable questions.

Usage: python -m eval.run_eval   (ingests the sample docs first)
"""
import json
from pathlib import Path

from app import rag

CASES = json.loads((Path(__file__).parent / "questions.json").read_text())

for f in sorted((Path(__file__).parent.parent / "samples").glob("*.*")):
    if f.suffix in (".pdf", ".docx", ".xlsx"):
        rag.ingest(f)

passed = 0
for c in CASES:
    r = rag.ask(c["question"])
    ans = r["answer"].lower()
    if c["expect"] == "NOT_FOUND":
        ok = rag.NOT_FOUND.lower() in ans or "couldn't find" in ans
        cite_ok = True
    else:
        ok = all(s.lower() in ans for s in c["expect"])
        cite_ok = any(x["source"] == c["source"] for x in r["citations"])
    passed += ok and cite_ok
    print(f"{'PASS' if ok and cite_ok else 'FAIL'}  {c['question']}\n      -> {r['answer'][:160]}")
print(f"\n{passed}/{len(CASES)} passed")
