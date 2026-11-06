"""Evaluate imputation at genuinely missing cells against an orthogonal assay.

Inputs are frozen matrices from paired acquisitions (for example DDA and DIA
mass spectrometry), an ORACLE-imputed matrix, and independent sample outcomes.
No artificial masking is performed. DIA is aligned to DDA using only cells
observed in both assays; missing-cell scores use only genuinely absent DDA cells.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Iterable


_MISSING = {"", "NA", "N/A", "NaN", "nan", "null", "NULL"}


def _read_matrix(path: str | Path) -> tuple[list[str], dict[str, dict[str, float | None]]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames or len(reader.fieldnames) < 3:
            raise ValueError(f"{path}: expected feature ID plus at least two sample columns")
        feature_col = reader.fieldnames[0]
        samples = reader.fieldnames[1:]
        if len(set(samples)) != len(samples) or any(not s for s in samples):
            raise ValueError(f"{path}: sample identifiers must be unique and non-empty")
        matrix: dict[str, dict[str, float | None]] = {}
        for line, row in enumerate(reader, start=2):
            feature = (row.get(feature_col) or "").strip()
            if not feature or feature in matrix:
                raise ValueError(f"{path}:{line}: feature identifiers must be unique and non-empty")
            values: dict[str, float | None] = {}
            for sample in samples:
                raw = (row.get(sample) or "").strip()
                if raw in _MISSING:
                    values[sample] = None
                    continue
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise ValueError(f"{path}:{line}: non-numeric value for {sample}") from exc
                if not math.isfinite(value):
                    raise ValueError(f"{path}:{line}: non-finite value for {sample}")
                values[sample] = value
            matrix[feature] = values
    if not matrix:
        raise ValueError(f"{path}: matrix has no feature rows")
    return samples, matrix


def _align(samples: list[str], matrix: dict[str, dict[str, float | None]],
           target_samples: list[str], target_features: set[str], label: str):
    if set(samples) != set(target_samples) or len(samples) != len(target_samples):
        raise ValueError(f"{label}: sample identifiers do not exactly match")
    if set(matrix) != target_features:
        raise ValueError(f"{label}: feature identifiers do not exactly match")
    return {feature: {sample: matrix[feature][sample] for sample in target_samples}
            for feature in sorted(target_features)}


def _pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) < 2:
        return None
    mx, my = statistics.mean(x), statistics.mean(y)
    dx, dy = [v - mx for v in x], [v - my for v in y]
    denom = math.sqrt(sum(v*v for v in dx) * sum(v*v for v in dy))
    return sum(a*b for a, b in zip(dx, dy)) / denom if denom else None


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2
        for k in order[i:j]:
            ranks[k] = rank
        i = j
    return ranks


def _median(values: list[float]) -> float:
    if not values:
        raise ValueError("Cannot compute a median from no values")
    return float(statistics.median(values))


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_labels(path: str | Path, samples: list[str], column: str):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames or not {"sample_id", column}.issubset(reader.fieldnames):
            raise ValueError(f"labels file requires sample_id and {column!r} columns")
        labels = {}
        for line, row in enumerate(reader, start=2):
            sample = (row.get("sample_id") or "").strip()
            label = (row.get(column) or "").strip()
            if not sample or not label or sample in labels:
                raise ValueError(f"{path}:{line}: labels must be unique and non-empty")
            labels[sample] = label
    if set(labels) != set(samples):
        raise ValueError("Outcome labels must cover exactly the matrix sample identifiers")
    groups = sorted(set(labels.values()))
    if len(groups) != 2:
        raise ValueError("This benchmark currently requires exactly two independent outcome groups")
    return labels, groups


def _outcome_effects(matrix, samples, labels, groups):
    effects = {}
    for feature, row in matrix.items():
        a = [float(row[s]) for s in samples if labels[s] == groups[0] and row[s] is not None]
        b = [float(row[s]) for s in samples if labels[s] == groups[1] and row[s] is not None]
        if len(a) < 2 or len(b) < 2:
            continue
        effects[feature] = statistics.mean(b) - statistics.mean(a)
    return effects


def _read_expected_effects(path: str | Path, feature_column: str):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\\t")
        if not reader.fieldnames or not {"feature_id", feature_column}.issubset(reader.fieldnames):
            raise ValueError(f"expected-effects file requires feature_id and {feature_column!r}")
        effects = {}
        for line, row in enumerate(reader, start=2):
            feature = (row.get("feature_id") or "").strip()
            raw = (row.get(feature_column) or "").strip()
            if not feature or feature in effects:
                raise ValueError(f"{path}:{line}: feature IDs must be unique and non-empty")
            if raw in _MISSING:
                continue
            try:
                value = float(raw)
            except ValueError as exc:
                raise ValueError(f"{path}:{line}: expected effect must be numeric") from exc
            if not math.isfinite(value):
                raise ValueError(f"{path}:{line}: expected effect must be finite")
            effects[feature] = value
    if not effects:
        raise ValueError("expected-effects file contains no numeric expected effects")
    return effects


def _evaluate_known_spikein_effects(imputed, samples, labels, groups, expected,
                                    *, effect_tolerance: float):
    observed_effects = _outcome_effects(imputed, samples, labels, groups)
    shared = sorted(set(observed_effects) & set(expected))
    if not shared:
        raise ValueError("No overlap between imputed features and known spike-in effect labels")
    observed = [observed_effects[feature] for feature in shared]
    truth = [expected[feature] for feature in shared]
    ecoli = [observed_effects[feature] for feature in shared if expected[feature] > 0]
    human = [observed_effects[feature] for feature in shared if expected[feature] == 0]
    return {
        "features_scored": len(shared),
        "expected_log2fc_mae": statistics.mean(abs(a-b) for a, b in zip(observed, truth)),
        "expected_log2fc_rmse": math.sqrt(statistics.mean((a-b)**2 for a, b in zip(observed, truth))),
        "expected_log2fc_pearson_r": _pearson(observed, truth),
        "ecoli_positive_direction_accuracy": (
            sum(value > 0 for value in ecoli) / len(ecoli) if ecoli else None
        ),
        "human_background_within_zero_tolerance_rate": (
            sum(abs(value) <= effect_tolerance for value in human) / len(human) if human else None
        ),
        "ecoli_features_scored": len(ecoli),
        "human_features_scored": len(human),
        "human_zero_effect_tolerance_log2fc": effect_tolerance,
        "reference_expected_effects": "E. coli unique peptides +1 log2FC; human unique peptides 0 log2FC for 2x versus 1x",
    }


def evaluate_orthogonal_missingness(
    observed_path: str | Path,
    orthogonal_path: str | Path,
    imputed_path: str | Path,
    labels_path: str | Path,
    *,
    outcome_column: str,
    top_k: int = 20,
    reference_mode: str = "sample_paired",
    expected_effects_path: str | Path | None = None,
    expected_effect_column: str = "expected_log2fc_2x_vs_1x",
    effect_tolerance: float = 0.25,
) -> dict:
    """Score actual missing DDA cells against paired or group-aggregated DIA references."""
    if top_k < 1:
        raise ValueError("top_k must be positive")
    if reference_mode not in {"sample_paired", "group_aggregated_by_outcome"}:
        raise ValueError("reference_mode must be sample_paired or group_aggregated_by_outcome")
    if not math.isfinite(effect_tolerance) or effect_tolerance < 0:
        raise ValueError("effect_tolerance must be finite and non-negative")
    samples, observed = _read_matrix(observed_path)
    features = set(observed)
    dia_samples, dia_raw = _read_matrix(orthogonal_path)
    imp_samples, imp_raw = _read_matrix(imputed_path)
    dia = _align(dia_samples, dia_raw, samples, features, "Orthogonal reference")
    imputed = _align(imp_samples, imp_raw, samples, features, "Imputed matrix")

    missing_cells = []
    overlaps = []
    global_diffs = []
    for feature in sorted(features):
        for sample in samples:
            x, y = observed[feature][sample], dia[feature][sample]
            if x is None and y is not None:
                missing_cells.append((feature, sample))
            elif x is not None and y is not None:
                overlaps.append((feature, sample, x, y))
                global_diffs.append(x - y)
    if not missing_cells:
        raise ValueError("No genuinely missing observed-assay cells have orthogonal reference values")
    if len(overlaps) < 2:
        raise ValueError("At least two paired observed cells are required to align assay scales")

    global_offset = _median(global_diffs)
    feature_offsets = {}
    for feature in features:
        diffs = [x-y for f, _, x, y in overlaps if f == feature]
        feature_offsets[feature] = _median(diffs) if len(diffs) >= 2 else global_offset

    truth, estimates = [], []
    missing_rows = []
    for feature, sample in missing_cells:
        estimate = imputed[feature][sample]
        reference = dia[feature][sample]
        if estimate is None:
            raise ValueError(f"Imputed matrix still has a missing value at {feature}/{sample}")
        aligned_reference = float(reference) + feature_offsets[feature]
        truth.append(aligned_reference)
        estimates.append(float(estimate))
        missing_rows.append((feature, sample, aligned_reference, float(estimate)))

    # Preserve every originally observed measurement; imputation must not rewrite data.
    observed_changed = []
    for feature in features:
        for sample in samples:
            original = observed[feature][sample]
            candidate = imputed[feature][sample]
            if original is not None and (candidate is None or not math.isclose(
                    float(original), float(candidate), rel_tol=0.0, abs_tol=1e-8)):
                observed_changed.append((feature, sample))
    if observed_changed:
        raise ValueError(f"Imputed matrix modified {len(observed_changed)} originally observed cells")

    labels, groups = _read_labels(labels_path, samples, outcome_column)
    known_spikein_effects = None
    expected_effects_hash = None
    if expected_effects_path is not None:
        expected = _read_expected_effects(expected_effects_path, expected_effect_column)
        known_spikein_effects = _evaluate_known_spikein_effects(
            imputed, samples, labels, groups, expected,
            effect_tolerance=effect_tolerance,
        )
        expected_effects_hash = _sha256(expected_effects_path)
    dia_aligned = {
        feature: {sample: (None if dia[feature][sample] is None
                           else float(dia[feature][sample]) + feature_offsets[feature])
                  for sample in samples}
        for feature in features
    }
    imp_effects = _outcome_effects(imputed, samples, labels, groups)
    dia_effects = _outcome_effects(dia_aligned, samples, labels, groups)
    shared = sorted(set(imp_effects) & set(dia_effects))
    effect_x = [dia_effects[f] for f in shared]
    effect_y = [imp_effects[f] for f in shared]
    effect_corr = _pearson(effect_x, effect_y)
    sign_agreement = (sum((a == 0 and b == 0) or (a*b > 0)
                          for a, b in zip(effect_x, effect_y)) / len(shared)
                      if shared else None)
    k = min(top_k, len(shared))
    dia_top = set(sorted(shared, key=lambda f: abs(dia_effects[f]), reverse=True)[:k])
    imp_top = set(sorted(shared, key=lambda f: abs(imp_effects[f]), reverse=True)[:k])
    top_overlap = len(dia_top & imp_top) / k if k else None
    delta = [a-b for a, b in zip(estimates, truth)]
    return {
        "benchmark_type": "paired_orthogonal_assay_real_missingness",
        "status": "SCORED",
        "sample_count": len(samples),
        "feature_count": len(features),
        "outcome_column": outcome_column,
        "outcome_groups": groups,
        "genuine_missing_cells_scored": len(missing_cells),
        "genuine_missing_fraction": len(missing_cells) / sum(
            observed[f][s] is None for f in features for s in samples
        ) if any(observed[f][s] is None for f in features for s in samples) else 0.0,
        "paired_observed_cells_for_assay_alignment": len(overlaps),
        "reference_mode": reference_mode,
        "assay_alignment": "per-feature median DIA-to-DDA offset using >=2 overlapping observed cells; global median fallback otherwise",
        "missing_cell_reconstruction": {
            "mae": statistics.mean(abs(x) for x in delta),
            "rmse": math.sqrt(statistics.mean(x*x for x in delta)),
            "pearson_r": _pearson(truth, estimates),
            "mean_signed_error": statistics.mean(delta),
        },
        "biological_outcome_concordance": {
            "features_with_estimable_two_group_effects": len(shared),
            "effect_size_pearson_r": effect_corr,
            "effect_direction_agreement": sign_agreement,
            "top_absolute_effect_overlap_at_k": top_overlap,
            "k": k,
            "reference_effects": "orthogonal DIA assay, aligned using observed paired cells",
            "candidate_effects": "ORACLE-imputed DDA matrix",
        },
        "known_spikein_effects": known_spikein_effects,
        "provenance": {
            "observed_assay_sha256": _sha256(observed_path),
            "orthogonal_reference_sha256": _sha256(orthogonal_path),
            "imputed_matrix_sha256": _sha256(imputed_path),
            "outcome_labels_sha256": _sha256(labels_path),
            "expected_effects_sha256": expected_effects_hash,
        },
        "limitations": (
            "Scores only real DDA-missing cells for which the paired DIA assay has a measurement. "
            "DIA is an orthogonal measurement, not an error-free absolute truth; per-feature offset "
            "alignment assumes a stable additive scale difference. In group_aggregated_by_outcome "
            "mode, the DIA reference is a condition-level technical-replicate median reused for "
            "DDA samples in that condition, not a one-to-one paired run. Biological outcome "
            "concordance is agreement with supplied two-group labels, not causal proof or clinical "
            "utility. Report acquisition methods, sample pairing or aggregation, normalization, "
            "feature mapping, and label provenance. No synthetic masking is used."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate imputation on genuinely missing cells against paired orthogonal measurements")
    parser.add_argument("--observed", required=True, help="Observed assay TSV with real missing cells")
    parser.add_argument("--orthogonal", required=True, help="Paired orthogonal assay TSV (e.g. DIA)")
    parser.add_argument("--imputed", required=True, help="ORACLE imputed TSV; observed cells must remain unchanged")
    parser.add_argument("--labels", required=True, help="TSV with sample_id and independent outcome labels")
    parser.add_argument("--outcome-column", required=True, help="Column in labels TSV defining the two biological groups")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--reference-mode", choices=["sample_paired", "group_aggregated_by_outcome"], default="sample_paired")
    parser.add_argument("--expected-effects", default="", help="Optional feature_id TSV with known expected log2 fold changes")
    parser.add_argument("--expected-effect-column", default="expected_log2fc_2x_vs_1x")
    parser.add_argument("--effect-tolerance", type=float, default=0.25)
    args = parser.parse_args()
    report = evaluate_orthogonal_missingness(
        args.observed, args.orthogonal, args.imputed, args.labels,
        outcome_column=args.outcome_column, top_k=args.top_k,
        reference_mode=args.reference_mode,
        expected_effects_path=args.expected_effects or None,
        expected_effect_column=args.expected_effect_column,
        effect_tolerance=args.effect_tolerance,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
