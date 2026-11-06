"""Evidence attribution and entailment benchmark with human-labelled cases.

The evaluator is deliberately label-driven. It never asks an LLM to grade its
own answer and never creates gold labels from model output.
"""
from __future__ import annotations
import hashlib, json, math
from pathlib import Path
from typing import Any

LABELS = {"supports", "refutes", "contextual"}

def evaluate_evidence_predictions(cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(cases, list) or not cases:
        raise ValueError("At least one independently labelled case is required.")
    confusion = {gold: {pred: 0 for pred in LABELS} for gold in LABELS}
    quote_checked = quote_valid = 0
    source_checked = source_valid = 0
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Case {index} must be an object.")
        gold, pred = case.get("gold_stance"), case.get("predicted_stance")
        if gold not in LABELS or pred not in LABELS:
            raise ValueError(f"Case {index} requires valid gold_stance and predicted_stance.")
        if not case.get("case_id") or not case.get("reviewer_ids"):
            raise ValueError(f"Case {index} requires case_id and reviewer_ids.")
        reviewers = case["reviewer_ids"]
        if not isinstance(reviewers, list) or len(set(reviewers)) < 2:
            raise ValueError(f"Case {index} requires at least two distinct reviewers.")
        if not case.get("adjudication_note") and len(set(reviewers)) > 2:
            raise ValueError(f"Case {index} with multiple reviewers requires adjudication_note.")
        confusion[gold][pred] += 1
        source_id = case.get("predicted_source_id")
        allowed = case.get("allowed_source_ids", [])
        if source_id is not None:
            source_checked += 1
            source_valid += int(source_id in allowed)
        quote = case.get("predicted_quote")
        text = case.get("source_text")
        if quote is not None:
            quote_checked += 1
            quote_valid += int(isinstance(quote, str) and bool(quote.strip())
                               and isinstance(text, str) and quote.strip() in text)
    total = len(cases)
    correct = sum(confusion[label][label] for label in LABELS)
    per_label = {}
    f1s = []
    for label in sorted(LABELS):
        tp = confusion[label][label]
        fp = sum(confusion[g][label] for g in LABELS if g != label)
        fn = sum(confusion[label][p] for p in LABELS if p != label)
        precision = tp/(tp+fp) if tp+fp else None
        recall = tp/(tp+fn) if tp+fn else None
        f1 = (2*precision*recall/(precision+recall)
              if precision is not None and recall is not None and precision+recall else None)
        per_label[label] = {"precision": precision, "recall": recall, "f1": f1,
                            "support": sum(confusion[label].values())}
        if f1 is not None: f1s.append(f1)
    return {
        "benchmark_type": "human_adjudicated_evidence_entailment",
        "case_count": total, "accuracy": correct/total,
        "macro_f1_present_labels": sum(f1s)/len(f1s) if f1s else None,
        "confusion_matrix_gold_rows_predicted_columns": confusion,
        "per_label": per_label,
        "source_attribution_checked": source_checked,
        "source_attribution_valid_rate": source_valid/source_checked if source_checked else None,
        "quotes_checked": quote_checked,
        "exact_quote_valid_rate": quote_valid/quote_checked if quote_checked else None,
        "limitations": "Scores apply only to the supplied adjudicated cases and label policy. Reviewer agreement, source-packet quality, class balance, organism/assay comparability and leakage must be reported separately. This benchmark is not a universal measure of scientific truth.",
    }

def run_evidence_benchmark(path: str | Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError("Benchmark file must be a JSON object containing cases.")
    report = evaluate_evidence_predictions(payload["cases"])
    report["benchmark_id"] = payload.get("benchmark_id", "unspecified")
    report["benchmark_version"] = payload.get("version", "unspecified")
    report["benchmark_sha256"] = hashlib.sha256(raw).hexdigest()
    return report
