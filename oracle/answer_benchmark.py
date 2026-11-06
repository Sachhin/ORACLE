"""Human-scored scientific answer-quality rubric and aggregation."""
from __future__ import annotations

from statistics import mean
from typing import Mapping


DIMENSIONS = (
    "factual_accuracy",
    "evidence_traceability",
    "uncertainty_calibration",
    "reasoning_quality",
    "completeness",
)

RUBRIC = {
    "factual_accuracy": "Are factual statements correct and consistent with the cited source context?",
    "evidence_traceability": "Can important claims be traced to relevant, correctly attributed sources?",
    "uncertainty_calibration": "Are limitations, conflicts, uncertainty, and unsupported inferences stated honestly?",
    "reasoning_quality": "Does the answer connect evidence to conclusions without causal or logical overreach?",
    "completeness": "Does it answer the question and address important alternatives or missing evidence?",
}

SCORE_GUIDE = {
    "1": "Unacceptable: materially wrong, unsupported, or misleading.",
    "2": "Weak: major gaps, attribution problems, or overclaiming.",
    "3": "Mixed: partly useful but with notable omissions or reasoning issues.",
    "4": "Strong: mostly accurate, traceable, and appropriately qualified.",
    "5": "Excellent: rigorous, well-supported, balanced, and complete for the available evidence.",
}


def validate_answer_review(scores: Mapping[str, int]) -> dict[str, int]:
    if set(scores) != set(DIMENSIONS):
        missing = sorted(set(DIMENSIONS) - set(scores))
        extra = sorted(set(scores) - set(DIMENSIONS))
        raise ValueError(f"Scores must cover all rubric dimensions; missing={missing}, extra={extra}.")
    normalized = {}
    for name in DIMENSIONS:
        value = scores[name]
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"{name} score must be an integer from 1 to 5.")
        normalized[name] = value
    return normalized


def summarize_answer_reviews(reviews: list[dict]) -> dict:
    """Aggregate only completed human reviews; never treat ratings as objective truth."""
    averages = {}
    for dimension in DIMENSIONS:
        values = [
            item["scores"][dimension] for item in reviews
            if dimension in item.get("scores", {})
        ]
        averages[dimension] = round(mean(values), 3) if values else None
    return {
        "review_count": len(reviews),
        "dimension_averages": averages,
        "overall_mean": (
            round(mean(value for value in averages.values() if value is not None), 3)
            if any(value is not None for value in averages.values()) else None
        ),
        "limitations": (
            "Human rubric scores are subjective reviewer judgments, not calibrated probabilities, "
            "ground-truth scientific accuracy, or proof of model superiority. Compare answers only "
            "when question, source packet, scoring rubric, and review conditions are held constant."
        ),
    }
