#!/usr/bin/env python3
"""Evaluate model-free sentence retrieval against labelled SciFact rationales.

Ranks individual abstract sentences over the full corpus using BM25. Gold
rationale sentence IDs are read only after rankings are frozen for scoring.
This is a lexical retrieval diagnostic, not stance classification.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from oracle.scifact_benchmark import _jsonl
from scripts.predict_scifact_local import sha256
from scripts.predict_scifact_open_corpus import BM25Index


def flatten_sentences(corpus_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, tuple[str, int]]]:
    rows: list[dict[str, Any]] = []
    locations: dict[str, tuple[str, int]] = {}
    seen: set[str] = set()
    for document in corpus_rows:
        doc_id = str(document.get("doc_id", ""))
        abstract = document.get("abstract")
        if not doc_id or doc_id in seen:
            raise ValueError("SciFact corpus requires unique, non-empty doc_id values")
        seen.add(doc_id)
        if not isinstance(abstract, list) or any(not isinstance(s, str) for s in abstract):
            raise ValueError(f"SciFact document {doc_id} has an invalid abstract")
        for sentence_index, sentence in enumerate(abstract):
            sentence_id = f"{doc_id}::{sentence_index}"
            rows.append({"doc_id": sentence_id, "title": "", "abstract": [sentence]})
            locations[sentence_id] = (doc_id, sentence_index)
    return rows, locations


def gold_rationales(claim: dict[str, Any]) -> list[tuple[str, set[int]]]:
    evidence = claim.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError(f"Claim {claim.get('id')}: evidence must be an object")
    rationales: list[tuple[str, set[int]]] = []
    for doc_id, entries in evidence.items():
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"Claim {claim.get('id')}/{doc_id}: evidence rationales must be a non-empty list")
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("sentences"), list):
                raise ValueError(f"Claim {claim.get('id')}/{doc_id}: invalid rationale")
            indices = entry["sentences"]
            if not indices or any(isinstance(i, bool) or not isinstance(i, int) or i < 0 for i in indices):
                raise ValueError(f"Claim {claim.get('id')}/{doc_id}: invalid sentence indices")
            rationales.append((str(doc_id), set(indices)))
    return rationales


def evaluate_sentence_retrieval(claims_path: str, corpus_path: str, *, top_k: int = 10) -> dict[str, Any]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    claims = _jsonl(claims_path)
    corpus_rows = _jsonl(corpus_path)
    sentence_rows, locations = flatten_sentences(corpus_rows)
    index = BM25Index(sentence_rows)

    predicted_total = gold_total = correct_total = 0
    rationale_total = rationale_hits = 0
    claim_total = claim_hits = 0
    per_claim = []

    for claim in claims:
        cid = str(claim.get("id"))
        rationales = gold_rationales(claim)
        gold_sentences = {
            (doc_id, sentence_index)
            for doc_id, indices in rationales
            for sentence_index in indices
        }
        if not gold_sentences:
            continue
        ranked = index.search(str(claim.get("claim", "")), top_k=top_k)
        predicted = {locations[sentence_id] for sentence_id, _ in ranked}
        correct = predicted.intersection(gold_sentences)
        predicted_total += len(predicted)
        gold_total += len(gold_sentences)
        correct_total += len(correct)
        claim_total += 1
        claim_hits += int(bool(correct))
        rationale_total += len(rationales)
        rationale_hits += sum(
            1 for doc_id, indices in rationales
            if {(doc_id, i) for i in indices}.issubset(predicted)
        )
        per_claim.append({
            "claim_id": cid,
            "gold_sentence_count": len(gold_sentences),
            "retrieved_sentence_count": len(predicted),
            "matched_gold_sentence_count": len(correct),
            "gold_rationale_groups": len(rationales),
            "fully_retrieved_rationale_groups": sum(
                1 for doc_id, indices in rationales
                if {(doc_id, i) for i in indices}.issubset(predicted)
            ),
        })

    precision = correct_total / predicted_total if predicted_total else None
    recall = correct_total / gold_total if gold_total else None
    f1 = (2 * precision * recall / (precision + recall)
          if precision is not None and recall is not None and precision + recall else None)
    return {
        "benchmark_type": "scifact_open_corpus_sentence_retrieval_only",
        "dataset": "SciFact",
        "claim_count": len(claims),
        "scored_claim_count": claim_total,
        "corpus_document_count": len(corpus_rows),
        "corpus_sentence_count": len(sentence_rows),
        "retrieval_method": "BM25 over individual abstract sentences",
        "retrieval_top_k_sentences_per_claim": top_k,
        "sentence_metrics": {
            "precision": precision, "recall": recall, "f1": f1,
            "matched_gold_sentences": correct_total,
            "retrieved_sentences": predicted_total,
            "gold_sentences": gold_total,
        },
        "claim_with_any_gold_sentence_rate": claim_hits / claim_total if claim_total else None,
        "fully_retrieved_rationale_group_rate": rationale_hits / rationale_total if rationale_total else None,
        "rationale_groups_retrieved": rationale_hits,
        "rationale_groups_total": rationale_total,
        "per_claim": per_claim,
        "provenance": {
            "claims_sha256": sha256(claims_path),
            "corpus_sha256": sha256(corpus_path),
        },
        "limitations": (
            "Lexical sentence retrieval only. It does not classify SUPPORT versus CONTRADICT, "
            "judge entailment, assess causal evidence, or generate scientific hypotheses. "
            "Gold rationale sentence IDs are used only after rankings are frozen for scoring."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", required=True, help="Labelled SciFact claims_dev.jsonl or claims_train.jsonl")
    parser.add_argument("--corpus", required=True, help="SciFact corpus.jsonl")
    parser.add_argument("--top-k", type=int, default=10, help="Number of sentences retrieved per claim")
    parser.add_argument("--output", default="", help="Optional JSON report path")
    args = parser.parse_args()
    report = evaluate_sentence_retrieval(args.claims, args.corpus, top_k=args.top_k)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
