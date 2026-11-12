#!/usr/bin/env python3
"""Reproducible exploratory comparison of GEO GSE32493 centenarian miRNA data.

The public submission contains three centenarian and three control samples.
The workflow reports effect sizes and only computes exact permutation p-values
when the deposited files actually retain three per-sample values per feature.
It never treats group means as biological replicates.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
import statistics
import urllib.request
from pathlib import Path
from typing import Iterable


BASE_URL = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE32nnn/GSE32493/suppl/"
FILES = {
    "centenarian": "GSE32493_centenarian.txt.gz",
    "control": "GSE32493_control.txt.gz",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "ORACLE-longevity-validation/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    # Verify the compressed stream before parsing.
    with gzip.open(destination, "rt", encoding="utf-8", errors="replace") as handle:
        handle.read(1)


def _number(value: str) -> float | None:
    try:
        result = float(value.strip())
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def read_group_table(path: Path) -> tuple[dict[str, list[float]], list[str]]:
    with gzip.open(path, "rt", encoding="utf-8-sig", errors="replace", newline="") as handle:
        lines = [line for line in handle if line.strip() and not line.lstrip().startswith("#")]
    if not lines:
        raise ValueError(f"{path.name}: no tabular rows")
    delimiter = "\t" if "\t" in lines[0] else ","
    rows = list(csv.reader(lines, delimiter=delimiter))
    header = rows[0]
    header_text = " ".join(header).lower()
    has_header = any(token in header_text for token in ("mirna", "mirna", "read", "count", "sample", "sequence", "name"))
    data_rows = rows[1:] if has_header else rows
    sample_columns = [str(x).strip() for x in header[1:]] if has_header else []
    values: dict[str, list[float]] = {}
    for row in data_rows:
        if len(row) < 2:
            continue
        feature = row[0].strip().strip('"')
        if not feature or feature.lower() in {"id", "name", "mirna", "feature", "sequence"}:
            continue
        nums = [x for cell in row[1:] if (x := _number(cell)) is not None]
        if not nums:
            continue
        values.setdefault(feature, []).extend(nums)
    if not values:
        raise ValueError(f"{path.name}: no feature rows with numeric measurements")
    return values, sample_columns


def exact_permutation_p(a: list[float], b: list[float]) -> float:
    """Two-sided exact permutation p-value for difference in means."""
    combined = a + b
    n_a = len(a)
    observed = abs(statistics.mean(a) - statistics.mean(b))
    extreme = 0
    total = 0
    for chosen in itertools.combinations(range(len(combined)), n_a):
        chosen_set = set(chosen)
        left = [v for i, v in enumerate(combined) if i in chosen_set]
        right = [v for i, v in enumerate(combined) if i not in chosen_set]
        total += 1
        if abs(statistics.mean(left) - statistics.mean(right)) >= observed - 1e-12:
            extreme += 1
    return extreme / total if total else 1.0


def benjamini_hochberg(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 1.0
    for rank in range(m, 0, -1):
        feature, p_value = ordered[rank - 1]
        running = min(running, p_value * m / rank)
        adjusted[feature] = min(1.0, running)
    return adjusted


def analyze(cent_path: Path, control_path: Path) -> dict:
    cent, cent_headers = read_group_table(cent_path)
    control, control_headers = read_group_table(control_path)
    shared = sorted(set(cent) & set(control))
    if len(shared) < 10:
        raise ValueError(f"Only {len(shared)} shared features; expected a miRNA table")
    per_sample = all(len(cent[x]) == 3 and len(control[x]) == 3 for x in shared)
    cent_library_size = sum(sum(values) for values in cent.values())
    control_library_size = sum(sum(values) for values in control.values())
    if cent_library_size <= 0 or control_library_size <= 0:
        raise ValueError("Group-level library sizes must be positive.")
    rows = []
    p_values: dict[str, float] = {}
    for feature in shared:
        a, b = cent[feature], control[feature]
        if per_sample:
            cent_count, control_count = statistics.mean(a), statistics.mean(b)
            cent_total = sum(statistics.mean(v) for v in cent.values())
            control_total = sum(statistics.mean(v) for v in control.values())
        else:
            cent_count, control_count = sum(a), sum(b)
            cent_total, control_total = cent_library_size, control_library_size
        cent_cpm = cent_count / cent_total * 1_000_000
        control_cpm = control_count / control_total * 1_000_000
        log2fc = math.log2((cent_cpm + 0.5) / (control_cpm + 0.5))
        row = {
            "feature": feature,
            "centenarian_group_count": cent_count,
            "control_group_count": control_count,
            "centenarian_cpm": cent_cpm,
            "control_cpm": control_cpm,
            "log2_cpm_fold_change": log2fc,
            "direction": "higher_in_centenarians" if log2fc > 0 else "lower_in_centenarians",
        }
        if per_sample:
            row["exact_permutation_p"] = exact_permutation_p(a, b)
            p_values[feature] = row["exact_permutation_p"]
        rows.append(row)
    if per_sample:
        q_values = benjamini_hochberg(p_values)
        for row in rows:
            row["fdr_bh"] = q_values[row["feature"]]
    rows.sort(key=lambda row: abs(row["log2_cpm_fold_change"]), reverse=True)
    return {
        "status": "EXPLORATORY_REPLICATE_LEVEL_COMPARISON" if per_sample else "EXPLORATORY_GROUP_LEVEL_COMPARISON",
        "accession": "GSE32493",
        "title": "Comprehensive microRNA profiling in B-cells of human centenarians",
        "cohort": {"centenarians": 3, "controls": 3, "tissue": "B-cells", "population": "Ashkenazi Jewish"},
        "features_shared": len(shared),
        "library_sizes": {"centenarian_group_total": cent_library_size, "control_group_total": control_library_size},
        "normalization": "Counts per million (CPM) using each deposited group table total; descriptive group-level comparison only.",
        "per_sample_values_retained": per_sample,
        "centenarian_numeric_columns": len(cent_headers) if cent_headers else (len(cent[shared[0]]) if per_sample else 1),
        "control_numeric_columns": len(control_headers) if control_headers else (len(control[shared[0]]) if per_sample else 1),
        "inferential_statistics": "Exact two-sided permutation test over all 20 assignments and BH FDR; only valid when three per-sample values per group are present." if per_sample else "Not computed: deposited supplementary tables do not retain per-sample biological replicates. Group-level fold changes are descriptive only.",
        "limitations": [
            "Small discovery cohort (3 centenarians and 3 controls).",
            "EBV-transformed B-cell model; findings may not generalize to primary tissues.",
            "Cross-sectional association does not establish causality or a mechanism of organismal longevity.",
            "Group-level summary values must never be treated as biological replicates.",
        ],
        "top_effects": rows[:50],
        "source_files": {
            "centenarian": {"filename": cent_path.name, "sha256": sha256(cent_path)},
            "control": {"filename": control_path.name, "sha256": sha256(control_path)},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/gse32493")
    parser.add_argument("--output", default="artifacts/gse32493-centenarian-mirna-report.json")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    paths = {group: data_dir / filename for group, filename in FILES.items()}
    if args.download:
        for group, filename in FILES.items():
            download(BASE_URL + filename, paths[group])
    for path in paths.values():
        if not path.is_file():
            raise SystemExit(f"Missing {path}; pass --download to retrieve the public GEO files.")
    report = analyze(paths["centenarian"], paths["control"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
