"""Evidence attribution and entailment benchmark with human-labelled cases.

The evaluator is deliberately label-driven. It never asks an LLM to grade its
own answer and never creates gold labels from model output.
"""
from __future__ import annotations
import hashlib, json
from itertools import combinations
from pathlib import Path
from typing import Any

LABELS = {"supports", "refutes", "contextual"}


def _cohen_kappa(left: list[str], right: list[str]) -> tuple[float | None, float]:
    """Return Cohen's kappa and observed agreement for paired nominal labels."""
    if len(left) != len(right) or not left:
        return None, 0.0
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    categories = LABELS
    expected = sum(
        (sum(x == label for x in left) / len(left))
        * (sum(x == label for x in right) / len(right))
        for label in categories
    )
    if expected == 1.0:
        return (1.0 if observed == 1.0 else 0.0), observed
    return (observed - expected) / (1.0 - expected), observed


def evaluate_evidence_predictions(cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(cases, list) or not cases:
        raise ValueError("At least one independently labelled case is required.")
    confusion = {gold: {pred: 0 for pred in LABELS} for gold in LABELS}
    quote_checked = quote_valid = source_checked = source_valid = 0
    case_ids = set()
    reviewer_labels: dict[str, dict[str, str]] = {}
    reviewer_pairs: dict[tuple[str, str], tuple[list[str], list[str]]] = {}
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Case {index} must be an object.")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in case_ids:
            raise ValueError(f"Case {index} requires a unique non-empty case_id.")
        case_ids.add(case_id)
        gold, pred = case.get("gold_stance"), case.get("predicted_stance")
        if gold not in LABELS or pred not in LABELS:
            raise ValueError(f"Case {index} requires valid gold_stance and predicted_stance.")
        reviewers = case.get("reviewer_ids")
        if (not isinstance(reviewers, list)
                or any(not isinstance(r, str) or not r.strip() for r in reviewers)
                or len(set(reviewers)) != len(reviewers) or len(reviewers) < 2):
            raise ValueError(f"Case {index} requires at least two distinct reviewers.")
        if len(set(reviewers)) > 2 and not case.get("adjudication_note"):
            raise ValueError(f"Case {index} with multiple reviewers requires adjudication_note.")
        individual = case.get("reviewer_labels")
        if individual is not None:
            if not isinstance(individual, dict) or set(individual) != set(reviewers):
                raise ValueError(f"Case {index} reviewer_labels must contain every reviewer_id exactly once.")
            if any(label not in LABELS for label in individual.values()):
                raise ValueError(f"Case {index} reviewer labels must be supports, refutes, or contextual.")
            for reviewer, label in individual.items():
                reviewer_labels.setdefault(reviewer, {})[case_id] = label
            for left, right in combinations(sorted(reviewers), 2):
                pair = (left, right)
                a, b = reviewer_pairs.setdefault(pair, ([], []))
                a.append(individual[left])
                b.append(individual[right])
        confusion[gold][pred] += 1
        source_id = case.get("predicted_source_id")
        allowed = case.get("allowed_source_ids", [])
        if not isinstance(allowed, list):
            raise ValueError(f"Case {index} allowed_source_ids must be a list.")
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
        if f1 is not None:
            f1s.append(f1)
    agreement = {}
    kappas = []
    for (left, right), (a, b) in sorted(reviewer_pairs.items()):
        kappa, observed = _cohen_kappa(a, b)
        agreement[f"{left}__{right}"] = {
            "paired_cases": len(a), "observed_agreement": observed, "cohen_kappa": kappa,
        }
        if kappa is not None:
            kappas.append(kappa)
    annotated_count = sum(len(v) for v in reviewer_labels.values())
    return {
        "benchmark_type": "human_adjudicated_evidence_entailment",
        "case_count": total, "accuracy": correct/total,
        "macro_f1_present_labels": sum(f1s)/len(f1s) if f1s else None,
        "confusion_matrix_gold_rows_predicted_columns": confusion,
        "per_label": per_label,
        "reviewer_annotation_cases": annotated_count,
        "reviewer_pair_agreement": agreement,
        "mean_pairwise_cohen_kappa": sum(kappas)/len(kappas) if kappas else None,
        "source_attribution_checked": source_checked,
        "source_attribution_coverage": source_checked/total,
        "source_attribution_valid_rate": source_valid/source_checked if source_checked else None,
        "quotes_checked": quote_checked,
        "quote_coverage": quote_checked/total,
        "exact_quote_valid_rate": quote_valid/quote_checked if quote_checked else None,
        "limitations": "Scores apply only to the supplied adjudicated cases and label policy. Cohen's kappa is reported only when individual reviewer labels are supplied; it can be unstable with small or highly imbalanced samples. Source and quote validity rates are conditional on supplied predictions, while coverage reports omissions. Source-packet quality, class balance, organism/assay comparability and leakage must be reported separately. This benchmark is not a universal measure of scientific truth.",
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
