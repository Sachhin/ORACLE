"""Deterministic BM25 retrieval utilities for model-free SciFact evaluation."""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
STOPWORDS = {"a","an","and","are","as","at","be","been","by","for","from","in","is","it","of","on","or","that","the","their","this","to","was","were","with"}

def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS]

def sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

class BM25Index:
    """Small dependency-free BM25 index over document titles and abstracts."""
    def __init__(self, corpus_rows: list[dict[str, Any]], *, k1: float = 1.5, b: float = 0.75):
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("BM25 requires k1 > 0 and 0 <= b <= 1")
        self.k1, self.b = k1, b
        self.documents = {}
        self.term_frequencies = {}
        self.document_lengths = {}
        self.document_frequency = Counter()
        seen = set()
        for row in corpus_rows:
            doc_id = str(row.get("doc_id", ""))
            if not doc_id or doc_id in seen:
                raise ValueError("SciFact corpus requires unique, non-empty doc_id values")
            seen.add(doc_id)
            abstract = row.get("abstract")
            if not isinstance(abstract, list) or any(not isinstance(s, str) for s in abstract):
                raise ValueError(f"SciFact document {doc_id} has an invalid abstract")
            tokens = tokenize(str(row.get("title", "")) + " " + " ".join(abstract))
            if not tokens:
                continue
            frequencies = Counter(tokens)
            self.documents[doc_id] = row
            self.term_frequencies[doc_id] = frequencies
            self.document_lengths[doc_id] = len(tokens)
            self.document_frequency.update(frequencies.keys())
        self.average_length = (sum(self.document_lengths.values()) / len(self.document_lengths)
                               if self.document_lengths else 0.0)

    def search(self, query: str, *, top_k: int = 20) -> list[tuple[str, float]]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        terms = set(tokenize(query))
        if not terms or not self.documents:
            return []
        count = len(self.documents)
        scores = []
        for doc_id, frequencies in self.term_frequencies.items():
            length = self.document_lengths[doc_id]
            score = 0.0
            for term in terms:
                tf = frequencies.get(term, 0)
                if tf:
                    df = self.document_frequency[term]
                    idf = math.log(1.0 + (count - df + 0.5) / (df + 0.5))
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * length / self.average_length)
                    score += idf * tf * (self.k1 + 1.0) / denominator
            if score > 0:
                scores.append((doc_id, score))
        scores.sort(key=lambda item: (-item[1], item[0]))
        return scores[:top_k]

def retrieval_diagnostics(claims: list[dict[str, Any]], retrieved: dict[str, list[str]]) -> dict[str, Any]:
    relevant = hits = gold_total = retrieved_gold = 0
    for claim in claims:
        evidence = claim.get("evidence")
        if not isinstance(evidence, dict) or not evidence:
            continue
        gold = {str(doc_id) for doc_id in evidence}
        relevant += 1
        found = gold.intersection(retrieved.get(str(claim.get("id")), []))
        hits += int(bool(found))
        gold_total += len(gold)
        retrieved_gold += len(found)
    return {
        "gold_evidence_claims": relevant,
        "claims_with_at_least_one_gold_document_retrieved": hits,
        "claim_hit_rate": hits / relevant if relevant else None,
        "gold_evidence_documents": gold_total,
        "retrieved_gold_evidence_documents": retrieved_gold,
        "document_recall": retrieved_gold / gold_total if gold_total else None,
        "note": "Gold evidence is consulted only after rankings are frozen for scoring."
    }
