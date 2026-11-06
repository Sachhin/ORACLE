"""Paired human evaluation of model answers against a deterministic baseline."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path
from statistics import mean
from .answer_benchmark import DIMENSIONS, validate_answer_review

def evaluate_paired_answers(cases: list[dict], *, bootstrap_samples: int = 2000,
                            seed: int = 1729) -> dict:
    if not isinstance(cases, list) or not cases:
        raise ValueError("At least one paired case is required.")
    if bootstrap_samples < 100:
        raise ValueError("Use at least 100 bootstrap samples.")
    deltas = {d: [] for d in DIMENSIONS}
    case_ids = set()
    reviewer_ids = set()
    for i, case in enumerate(cases):
        if not isinstance(case, dict) or not case.get("case_id"):
            raise ValueError(f"Case {i} requires case_id.")
        if case["case_id"] in case_ids:
            raise ValueError("case_id values must be unique.")
        case_ids.add(case["case_id"])
        if not case.get("source_packet_sha256") or len(case["source_packet_sha256"]) != 64:
            raise ValueError(f"Case {i} requires the frozen source packet SHA-256.")
        if case.get("prompt_version") is None or case.get("model_version") is None:
            raise ValueError(f"Case {i} requires prompt_version and model_version.")
        reviewers = case.get("reviewer_ids")
        if not isinstance(reviewers, list) or len(set(reviewers)) < 2:
            raise ValueError(f"Case {i} requires at least two distinct reviewers.")
        reviewer_ids.update(reviewers)
        baseline = validate_answer_review(case.get("baseline_scores", {}))
        candidate = validate_answer_review(case.get("candidate_scores", {}))
        for dimension in DIMENSIONS:
            deltas[dimension].append(candidate[dimension] - baseline[dimension])
    rng = random.Random(seed)
    summaries = {}
    for dimension, values in deltas.items():
        point = mean(values)
        sampled = []
        for _ in range(bootstrap_samples):
            sampled.append(mean(rng.choice(values) for _ in values))
        sampled.sort()
        low = sampled[int(0.025 * (bootstrap_samples - 1))]
        high = sampled[int(0.975 * (bootstrap_samples - 1))]
        summaries[dimension] = {
            "mean_paired_delta_candidate_minus_baseline": round(point, 4),
            "bootstrap_95_percent_interval": [round(low, 4), round(high, 4)],
            "candidate_wins": sum(v > 0 for v in values),
            "ties": sum(v == 0 for v in values),
            "baseline_wins": sum(v < 0 for v in values),
        }
    return {
        "benchmark_type": "paired_human_scored_model_comparison",
        "case_count": len(cases), "reviewer_count": len(reviewer_ids),
        "dimensions": summaries, "bootstrap_samples": bootstrap_samples, "seed": seed,
        "interpretation": "Paired descriptive comparison on the supplied cases only. Human rubric scores are subjective and ordinal; bootstrap intervals do not establish calibrated scientific accuracy or general superiority. Keep source packets, prompts, review conditions and model versions fixed, and report disagreements and dataset composition.",
    }

def run_paired_answer_benchmark(path: str | Path, *, bootstrap_samples: int = 2000,
                                seed: int = 1729) -> dict:
    raw = Path(path).read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError("Comparison file must be a JSON object containing cases.")
    report = evaluate_paired_answers(payload["cases"],
                                     bootstrap_samples=bootstrap_samples, seed=seed)
    report["benchmark_id"] = payload.get("benchmark_id", "unspecified")
    report["benchmark_sha256"] = hashlib.sha256(raw).hexdigest()
    return report
