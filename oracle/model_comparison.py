"""Paired, independently human-scored comparison of model answers."""
from __future__ import annotations
import hashlib, json, random
from pathlib import Path
from statistics import mean
from .answer_benchmark import DIMENSIONS, validate_answer_review


def evaluate_paired_answers(cases: list[dict], *, bootstrap_samples: int = 2000,
                            seed: int = 1729) -> dict:
    """Compare systems using per-reviewer paired scores, resampling whole cases."""
    if not isinstance(cases, list) or not cases:
        raise ValueError("At least one paired case is required.")
    if bootstrap_samples < 100:
        raise ValueError("Use at least 100 bootstrap samples.")
    deltas = {d: [] for d in DIMENSIONS}
    case_ids: set[str] = set()
    reviewer_ids: set[str] = set()
    annotation_count = 0
    for i, case in enumerate(cases):
        if not isinstance(case, dict) or not isinstance(case.get("case_id"), str) or not case["case_id"].strip():
            raise ValueError(f"Case {i} requires a non-empty case_id.")
        if case["case_id"] in case_ids:
            raise ValueError("case_id values must be unique.")
        case_ids.add(case["case_id"])
        packet_hash = case.get("source_packet_sha256")
        if not isinstance(packet_hash, str) or len(packet_hash) != 64 or any(c not in "0123456789abcdef" for c in packet_hash.lower()):
            raise ValueError(f"Case {i} requires the frozen source packet SHA-256.")
        if case.get("prompt_version") is None or case.get("model_version") is None:
            raise ValueError(f"Case {i} requires prompt_version and model_version.")
        reviewers = case.get("reviewer_ids")
        if (not isinstance(reviewers, list) or len(reviewers) < 2
                or any(not isinstance(r, str) or not r.strip() for r in reviewers)
                or len(set(reviewers)) != len(reviewers)):
            raise ValueError(f"Case {i} requires at least two distinct non-empty reviewer IDs.")
        scores_by_reviewer = case.get("reviewer_scores")
        if not isinstance(scores_by_reviewer, dict) or set(scores_by_reviewer) != set(reviewers):
            raise ValueError(f"Case {i} reviewer_scores must contain every reviewer_id exactly once.")
        per_case = {d: [] for d in DIMENSIONS}
        for reviewer in reviewers:
            pair = scores_by_reviewer[reviewer]
            if not isinstance(pair, dict) or set(pair) != {"baseline_scores", "candidate_scores"}:
                raise ValueError(f"Case {i} reviewer {reviewer} must score both baseline and candidate.")
            baseline = validate_answer_review(pair["baseline_scores"])
            candidate = validate_answer_review(pair["candidate_scores"])
            for dimension in DIMENSIONS:
                per_case[dimension].append(candidate[dimension] - baseline[dimension])
            reviewer_ids.add(reviewer)
            annotation_count += 1
        for dimension in DIMENSIONS:
            deltas[dimension].append(mean(per_case[dimension]))
    rng = random.Random(seed)
    summaries = {}
    for dimension, values in deltas.items():
        point = mean(values)
        sampled = [mean(rng.choice(values) for _ in values) for _ in range(bootstrap_samples)]
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
        "reviewer_case_annotations": annotation_count,
        "dimensions": summaries, "bootstrap_samples": bootstrap_samples, "seed": seed,
        "resampling_unit": "paired_case (reviewer-averaged within case)",
        "interpretation": "Paired descriptive comparison on the supplied cases only. Each reviewer scores both systems independently; reviewer scores are averaged within case before case-level bootstrap resampling. Human rubric scores are subjective and ordinal; intervals do not establish calibrated scientific accuracy or general superiority. Keep source packets, prompts, review conditions and model versions fixed, blind system identity where practical, and report dataset composition.",
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
