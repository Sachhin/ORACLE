"""Merge explicit per-sample GEO raw-count files into a DESeq2 matrix.

No sample grouping is inferred. The caller supplies sample names, paths, and
feature/count column positions; every file must contain the same feature set.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import re
from pathlib import Path
from typing import Mapping


def _read_source(path: Path) -> str:
    if path.name.lower().endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
            return handle.read()
    return path.read_text(encoding="utf-8-sig")


def merge_sample_count_files(
    sample_files: Mapping[str, str | Path],
    output_path: str | Path,
    *,
    feature_column: int = 0,
    count_column: int = -1,
    has_header: bool = True,
    delimiter: str = "auto",
    max_features: int = 100_000,
) -> dict:
    """Merge sample-level count tables, preserving explicit sample order."""
    if len(sample_files) < 2:
        raise ValueError("At least two explicitly named sample files are required.")
    if not 1 <= max_features <= 1_000_000:
        raise ValueError("max_features must be between 1 and 1,000,000.")
    if feature_column < 0 or count_column < -1:
        raise ValueError("Column positions must be non-negative (count_column may be -1 for last).")
    if delimiter not in {"auto", "tab", "comma"}:
        raise ValueError("delimiter must be auto, tab, or comma.")
    samples: dict[str, dict[str, int]] = {}
    checksums: dict[str, str] = {}
    reference_features: list[str] | None = None

    for sample, raw_path in sample_files.items():
        name = str(sample).strip()
        if not name or name in samples:
            raise ValueError("Sample names must be unique and non-empty.")
        path = Path(raw_path)
        raw_bytes = path.read_bytes()
        checksums[name] = hashlib.sha256(raw_bytes).hexdigest()
        text = _read_source(path)
        lines = text.splitlines()
        if not lines:
            raise ValueError(f"{name}: count file is empty.")
        chosen = delimiter
        if chosen == "auto":
            chosen = "tab" if lines[0].count("\t") >= lines[0].count(",") else "comma"
        sep = "\t" if chosen == "tab" else ","
        reader = csv.reader(io.StringIO(text), delimiter=sep)
        if has_header:
            next(reader, None)
        counts: dict[str, int] = {}
        for line_number, row in enumerate(reader, start=2 if has_header else 1):
            if not row or not any(cell.strip() for cell in row):
                continue
            try:
                feature = row[feature_column].strip()
                count_raw = row[count_column].strip()
            except IndexError as exc:
                raise ValueError(f"{name}: missing configured column on line {line_number}.") from exc
            if not feature:
                raise ValueError(f"{name}: empty feature identifier on line {line_number}.")
            if feature in counts:
                raise ValueError(f"{name}: duplicate feature identifier {feature!r}.")
            if not re.fullmatch(r"\\d+", count_raw):
                raise ValueError(
                    f"{name}: count for {feature!r} must be a non-negative integer: {count_raw!r}."
                )
            count = int(count_raw)
            counts[feature] = count
            if len(counts) > max_features:
                raise ValueError(f"{name}: file exceeds {max_features} features.")
        if not counts:
            raise ValueError(f"{name}: no count rows were parsed.")
        features = list(counts)
        if reference_features is None:
            reference_features = features
        elif set(features) != set(reference_features):
            missing = sorted(set(reference_features) - set(features))[:10]
            extra = sorted(set(features) - set(reference_features))[:10]
            raise ValueError(
                f"{name}: feature set differs from other samples; missing={missing}, extra={extra}."
            )
        samples[name] = counts

    assert reference_features is not None
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["feature", *samples.keys()])
        for feature in reference_features:
            writer.writerow([feature, *(samples[sample][feature] for sample in samples)])
    temporary.replace(target)
    matrix_sha = hashlib.sha256(target.read_bytes()).hexdigest()
    return {
        "output_path": str(target),
        "sample_names": list(samples),
        "sample_count": len(samples),
        "feature_count": len(reference_features),
        "matrix_sha256": matrix_sha,
        "source_sha256": checksums,
        "column_configuration": {
            "feature_column_zero_based": feature_column,
            "count_column_zero_based": count_column,
            "has_header": has_header,
            "delimiter": delimiter,
        },
        "limitations": (
            "Files were merged by exact feature identifier only. ORACLE did not infer "
            "sample groups, normalize counts, harmonize gene annotations, remove samples, "
            "or verify that the supplied files represent biological replicates from a "
            "comparable experiment. Confirm source file semantics and column positions."
        ),
    }
