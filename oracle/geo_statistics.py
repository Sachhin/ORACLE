"""Explicit-design differential analysis for continuous log2 GEO matrices.

This adapter is intentionally not a raw-count RNA-seq method. Users must declare
that the supplied values are continuous log2-scale measurements. It performs
per-feature Welch two-sample t-tests and Benjamini-Hochberg correction.
"""
from __future__ import annotations

import csv
import io
import math
from pathlib import Path
from typing import Mapping

from .geo_analysis import GEOExpressionAnalyzer


def _beta_fraction(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Numerical Recipes)."""
    max_iter, epsilon, tiny = 200, 3e-14, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < epsilon:
            break
    return h


def _regularized_beta(x: float, a: float, b: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_fraction(a, b, x) / a
    return 1.0 - front * _beta_fraction(b, a, 1.0 - x) / b


def _welch_test(left: list[float], right: list[float]) -> tuple[float, float, float]:
    """Return t statistic, Welch-Satterthwaite df, and two-sided p-value."""
    n1, n2 = len(left), len(right)
    m1, m2 = math.fsum(left) / n1, math.fsum(right) / n2
    v1 = math.fsum((x - m1) ** 2 for x in left) / (n1 - 1)
    v2 = math.fsum((x - m2) ** 2 for x in right) / (n2 - 1)
    a, b = v1 / n1, v2 / n2
    se2 = a + b
    if se2 == 0.0:
        if m1 == m2:
            return 0.0, float(n1 + n2 - 2), 1.0
        return math.copysign(math.inf, m2 - m1), float(n1 + n2 - 2), 0.0
    t_stat = (m2 - m1) / math.sqrt(se2)
    denominator = (a * a) / (n1 - 1) + (b * b) / (n2 - 1)
    degrees = (se2 * se2) / denominator if denominator else float(n1 + n2 - 2)
    p_value = _regularized_beta(degrees / (degrees + t_stat * t_stat), degrees / 2.0, 0.5)
    return t_stat, degrees, min(1.0, max(0.0, p_value))


def _benjamini_hochberg(p_values: list[float]) -> list[float]:
    count = len(p_values)
    adjusted = [1.0] * count
    running = 1.0
    for index in range(count - 1, -1, -1):
        rank = index + 1
        running = min(running, p_values[index] * count / rank)
        adjusted[index] = min(1.0, running)
    return adjusted


class GEOContrastAnalyzer:
    """Compare two explicitly labelled groups in continuous log2 expression data."""

    def analyze(
        self,
        path: str | Path,
        group_labels: Mapping[str, str],
        group_a: str,
        group_b: str,
        measurement_scale: str,
        min_replicates: int = 2,
    ) -> dict:
        if measurement_scale != "log2_continuous":
            raise ValueError(
                "Only explicitly declared log2_continuous data are supported; "
                "raw counts require a count-aware RNA-seq method."
            )
        if not group_a or not group_b or group_a == group_b:
            raise ValueError("Two distinct non-empty contrast groups are required.")
        if min_replicates < 2:
            raise ValueError("At least two biological replicates per group are required.")
        matrix_path = Path(path)
        text = GEOExpressionAnalyzer()._read_text(matrix_path)
        table = GEOExpressionAnalyzer._table_text(text)
        first = table.splitlines()[0] if table.splitlines() else ""
        delimiter = "\t" if first.count("\t") >= first.count(",") else ","
        reader = csv.reader(io.StringIO(table), delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("Expression matrix has no header.") from exc
        samples = [item.strip() for item in header[1:]]
        if not samples or len(set(samples)) != len(samples):
            raise ValueError("Matrix must contain unique sample column names.")
        if set(group_labels) != set(samples):
            missing = sorted(set(samples) - set(group_labels))
            extra = sorted(set(group_labels) - set(samples))
            raise ValueError(f"Group labels must cover matrix samples exactly; missing={missing}, extra={extra}.")
        left_samples = [s for s in samples if group_labels[s] == group_a]
        right_samples = [s for s in samples if group_labels[s] == group_b]
        unexpected = sorted(set(group_labels.values()) - {group_a, group_b})
        if unexpected:
            raise ValueError(f"Only the two requested groups may be present; found {unexpected}.")
        if len(left_samples) < min_replicates or len(right_samples) < min_replicates:
            raise ValueError(
                f"Insufficient replicates: {group_a}={len(left_samples)}, "
                f"{group_b}={len(right_samples)}; need at least {min_replicates} each."
            )
        left_indices = [samples.index(s) + 1 for s in left_samples]
        right_indices = [samples.index(s) + 1 for s in right_samples]
        raw_results, skipped = [], 0
        max_rows = 100_000
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            if row[0].strip().lower() in {"id_ref", "feature_id", "gene_id"}:
                continue
            if len(row) != len(samples) + 1:
                skipped += 1
                continue
            values = [GEOExpressionAnalyzer._number(value) for value in row[1:]]
            if any(value is not None and value < -1_000_000 for value in values):
                skipped += 1
                continue
            left = [values[i - 1] for i in left_indices if values[i - 1] is not None]
            right = [values[i - 1] for i in right_indices if values[i - 1] is not None]
            if len(left) < min_replicates or len(right) < min_replicates:
                skipped += 1
                continue
            t_stat, degrees, p_value = _welch_test(left, right)
            raw_results.append({
                "feature": row[0].strip(),
                "group_a": group_a,
                "group_b": group_b,
                "n_a": len(left),
                "n_b": len(right),
                "mean_a": math.fsum(left) / len(left),
                "mean_b": math.fsum(right) / len(right),
                "log2_mean_difference_b_minus_a": math.fsum(right) / len(right) - math.fsum(left) / len(left),
                "welch_t": t_stat,
                "welch_df": degrees,
                "p_value": p_value,
            })
            if len(raw_results) > max_rows:
                raise ValueError(f"Matrix exceeds the {max_rows}-feature contrast limit.")
        if not raw_results:
            raise ValueError("No features had sufficient non-missing observations in both groups.")
        order = sorted(range(len(raw_results)), key=lambda i: raw_results[i]["p_value"])
        adjusted = _benjamini_hochberg([raw_results[i]["p_value"] for i in order])
        for rank, index in enumerate(order):
            raw_results[index]["p_value_adjusted_bh"] = adjusted[rank]
        raw_results.sort(key=lambda item: (item["p_value_adjusted_bh"], item["p_value"], item["feature"]))
        return {
            "method": "Welch two-sample t-test; Benjamini-Hochberg FDR",
            "measurement_scale": measurement_scale,
            "contrast": {"group_a": group_a, "group_b": group_b},
            "sample_groups": {group_a: left_samples, group_b: right_samples},
            "features_tested": len(raw_results),
            "features_skipped": skipped,
            "results": raw_results,
            "limitations": (
                "Requires correctly declared continuous log2-scale measurements and independent biological "
                "replicates. This is not a raw-count RNA-seq method, does not normalize data, cannot correct "
                "batch effects, and does not establish causation. Group labels and scale are user-supplied."
            ),
        }
