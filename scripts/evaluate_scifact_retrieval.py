#!/usr/bin/env python3
"""Measure BM25 retrieval recall on labelled SciFact claims without an LLM."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Running ``python scripts/<name>.py`` puts the scripts directory, not the
# repository root, on sys.path. Add the root so the project's namespace
# packages (oracle and scripts) resolve consistently in Termux and CI.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from oracle.scifact_benchmark import _jsonl
from scripts.predict_scifact_local import sha256
from scripts.predict_scifact_open_corpus import BM25Index, retrieval_diagnostics


def evaluate_retrieval(claims_path: str, corpus_path: str, *, top_k: int = 20) -> dict:
    claims = _jsonl(claims_path)
    corpus_rows = _jsonl(corpus_path)
    index = BM25Index(corpus_rows)
    retrieved = {
        str(claim.get("id")): [
            doc_id for doc_id, _ in index.search(str(claim.get("claim", "")), top_k=top_k)
        ]
        for claim in claims
    }
    return {
        "benchmark_type": "scifact_open_corpus_retrieval_only",
        "dataset": "SciFact",
        "split": "labelled claims supplied by caller (normally dev)",
        "claim_count": len(claims),
        "corpus_document_count": len(index.documents),
        "retrieval_method": "BM25",
        "retrieval_top_k": top_k,
        "retrieval_metrics": retrieval_diagnostics(claims, retrieved),
        "provenance": {
            "claims_sha256": sha256(claims_path),
            "corpus_sha256": sha256(corpus_path),
        },
        "limitations": (
            "This is a retrieval-only diagnostic. It does not run a claim verifier, "
            "score stance, or measure evidence-rationale quality. Gold evidence is "
            "used only after retrieval to calculate recall; it is never used in the query."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", required=True, help="Labelled SciFact claims_dev.jsonl")
    parser.add_argument("--corpus", required=True, help="SciFact corpus.jsonl")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--output", default="", help="Optional JSON report path")
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be at least 1")
    report = evaluate_retrieval(args.claims, args.corpus, top_k=args.top_k)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
