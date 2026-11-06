"""Conservative cross-dataset directional consistency screen for DE results.

This is not a formal meta-analysis or proof of replication: contrast semantics,
cohort independence, feature annotation equivalence, and batch/design comparability
must be assessed by a scientist.
"""
from __future__ import annotations

from typing import Any


def screen_independent_datasets(
    analyses: list[Any],
    source_analysis_id: str,
    feature: str,
    fdr_threshold: float = 0.05,
) -> dict[str, Any]:
    """Compare one feature across distinct GEO accessions and distinct matrices."""
    if not 0 < fdr_threshold < 1:
        raise ValueError("fdr_threshold must be strictly between 0 and 1")
    source = next((item for item in analyses if item.analysis_id == source_analysis_id), None)
    if source is None:
        raise ValueError(f"DESeq2 analysis not found: {source_analysis_id}")
    source_result = next((item for item in source.results if item.get("feature") == feature), None)
    if source_result is None:
        raise ValueError(f"Feature {feature!r} not found in source analysis results")

    def direction(value: Any) -> str:
        if value is None:
            return "unknown"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "unknown"
        if number > 0:
            return "positive"
        if number < 0:
            return "negative"
        return "zero"

    source_accession = (source.dataset_accession or "").strip().upper()
    source_checksum = (source.matrix_sha256 or "").strip().lower()
    source_direction = direction(source_result.get("log2_fold_change"))
    comparisons = []
    for other in analyses:
        if other.analysis_id == source_analysis_id:
            continue
        accession = (other.dataset_accession or "").strip().upper()
        checksum = (other.matrix_sha256 or "").strip().lower()
        # Unknown provenance or reuse of either dataset identity is not independent.
        if not source_accession or not accession or accession == source_accession:
            continue
        if not source_checksum or not checksum or checksum == source_checksum:
            continue
        other_result = next((item for item in other.results if item.get("feature") == feature), None)
        if other_result is None:
            comparisons.append({
                "analysis_id": other.analysis_id, "dataset_accession": other.dataset_accession,
                "classification": "feature_not_tested", "direction": "unknown",
                "log2_fold_change": None, "adjusted_p_value": None,
            })
            continue
        other_direction = direction(other_result.get("log2_fold_change"))
        adjusted = other_result.get("p_value_adjusted_bh")
        try:
            significant = adjusted is not None and float(adjusted) <= fdr_threshold
        except (TypeError, ValueError):
            significant = False
        if source_direction in ("unknown", "zero") or other_direction in ("unknown", "zero"):
            classification = "direction_unavailable"
        elif significant and other_direction == source_direction:
            classification = "same_direction_significant"
        elif significant:
            classification = "opposite_direction_significant"
        elif other_direction == source_direction:
            classification = "same_direction_not_significant"
        else:
            classification = "opposite_direction_not_significant"
        comparisons.append({
            "analysis_id": other.analysis_id,
            "dataset_accession": other.dataset_accession,
            "matrix_sha256": other.matrix_sha256,
            "contrast": other.contrast,
            "direction": other_direction,
            "log2_fold_change": other_result.get("log2_fold_change"),
            "adjusted_p_value": adjusted,
            "classification": classification,
        })

    significant = [x for x in comparisons if x["classification"] in (
        "same_direction_significant", "opposite_direction_significant"
    )]
    if not comparisons:
        summary = "no_eligible_independent_dataset"
    elif not significant:
        summary = "no_independent_significant_support"
    elif all(x["classification"] == "same_direction_significant" for x in significant):
        summary = "potential_directional_consistency"
    elif all(x["classification"] == "opposite_direction_significant" for x in significant):
        summary = "potential_directional_conflict"
    else:
        summary = "mixed_independent_results"

    return {
        "feature": feature,
        "source_analysis_id": source.analysis_id,
        "source_dataset_accession": source.dataset_accession,
        "source_matrix_sha256": source.matrix_sha256,
        "source_contrast": source.contrast,
        "source_log2_fold_change": source_result.get("log2_fold_change"),
        "source_adjusted_p_value": source_result.get("p_value_adjusted_bh"),
        "source_direction": source_direction,
        "fdr_threshold": fdr_threshold,
        "summary": summary,
        "independent_dataset_comparisons": comparisons,
        "interpretation": (
            "Directional consistency screen only. Different GEO accessions and matrix "
            "checksums do not establish independent cohorts or comparable biological "
            "contrasts. Confirm phenotype, treatment, genotype, tissue, timepoint, "
            "feature annotation, and study design before describing replication. "
            "This is not a meta-analysis, causal result, or validated discovery."
        ),
    }
