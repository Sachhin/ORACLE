#!/usr/bin/env python3
"""Authenticate and inventory the public GSE262619 count table and GEO SOFT manifest.

This is a source-provenance gate only. It does not perform differential expression
or establish exceptional-longevity evidence.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path


ACCESSION_RE = re.compile(r"^!Sample_geo_accession\s*=\s*(GSM\d+)\s*$")
TITLE_RE = re.compile(r"^!Sample_title\s*=\s*(.*?)\s*$")
CHAR_RE = re.compile(r"^!Sample_characteristics_ch1\s*=\s*(.*?)\s*$")
AGE_RE = re.compile(r"(?:^|[;|,])\s*age(?:\s*\(years?\))?\s*[:=]\s*(\d{1,3}(?:\.\d+)?)\b", re.I)
SEX_RE = re.compile(r"(?:^|[;|,])\s*sex\s*[:=]\s*(female|male)\b", re.I)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_soft(path: Path) -> list[dict[str, str]]:
    samples: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip("\\r\\n")
            if line.startswith("^SAMPLE = "):
                if current and current.get("sample_accession"):
                    samples.append(current)
                current = {
                    "sample_accession": "",
                    "title": "",
                    "characteristics": "",
                }
                continue
            if current is None:
                continue
            match = ACCESSION_RE.match(line)
            if match:
                current["sample_accession"] = match.group(1)
                continue
            match = TITLE_RE.match(line)
            if match:
                current["title"] = match.group(1)
                continue
            match = CHAR_RE.match(line)
            if match:
                value = match.group(1)
                current["characteristics"] = (
                    current["characteristics"] + " | " + value
                ).strip(" |")
    if current and current.get("sample_accession"):
        samples.append(current)
    return samples

def inspect_count_table(path: Path, sample_ids: list[str]) -> dict:
    with gzip.open(path, "rt", encoding="utf-8-sig", errors="replace", newline="") as handle:
        content = handle.read()
    matched = [sample for sample in sample_ids if sample in content]
    rows = list(csv.reader(content.splitlines(), delimiter="\t"))
    nonempty = [row for row in rows if row and any(cell.strip() for cell in row)]
    widths = [len(row) for row in nonempty]
    return {
        "matched_sample_ids": matched,
        "matched_sample_count": len(matched),
        "matrix_rows": len(nonempty),
        "matrix_columns": max(widths, default=0),
        "row_widths_consistent": len(set(widths)) <= 1,
        "first_row_preview": nonempty[0][:8] if nonempty else [],
    }


def build_manifest(samples: list[dict[str, str]]) -> list[dict[str, str]]:
    manifest = []
    for sample in samples:
        characteristics = sample["characteristics"]
        ages = {float(value) for value in AGE_RE.findall(characteristics)}
        sexes = {value.lower() for value in SEX_RE.findall(characteristics)}
        age = str(next(iter(ages))) if len(ages) == 1 and 0 <= next(iter(ages)) <= 120 else ""
        sex = next(iter(sexes)) if len(sexes) == 1 else ""
        title_sex_match = re.search(r"_(F|M)\\d+$", sample["title"], re.I)
        title_sex = (
            {"f": "female", "m": "male"}[title_sex_match.group(1).lower()]
            if title_sex_match else ""
        )
        band_match = re.match(r"^(\\d{2,3})y_", sample["title"], re.I)
        nominal_age_band = band_match.group(1) if band_match else ""
        manifest.append({
            **sample,
            "explicit_age_years": age,
            "explicit_sex": sex,
            "title_sex": title_sex,
            "nominal_age_band_years": nominal_age_band,
        })
    return manifest


def audit(counts: Path, soft: Path, output: Path, manifest_path: Path,
          expected_samples: int = 35) -> dict:
    issues: list[str] = []
    samples = parse_soft(soft)
    ids = [item["sample_accession"] for item in samples]
    if len(ids) != expected_samples:
        issues.append(f"Expected {expected_samples} GEO sample records; found {len(ids)}.")
    if len(set(ids)) != len(ids):
        issues.append("GEO SOFT manifest contains duplicate GSM accessions.")
    table = inspect_count_table(counts, ids)
    with gzip.open(counts, "rt", encoding="utf-8-sig", errors="replace") as handle:
        count_text = handle.read()
    title_matches = [
        item["sample_accession"] for item in samples
        if item["title"] and item["title"] in count_text
    ]
    matched_ids = sorted(set(table["matched_sample_ids"]) | set(title_matches))
    table["matched_sample_ids"] = matched_ids
    table["matched_sample_count"] = len(matched_ids)
    table["matched_by_title_count"] = len(title_matches)
    if table["matched_sample_count"] != len(ids):
        issues.append(
            f"Count table links {table['matched_sample_count']} of {len(ids)} "
            "GEO samples by GSM accession or exact submitter sample title."
        )
    if table["matrix_rows"] < expected_samples or table["matrix_columns"] < 2:
        issues.append("Count table is empty or too small to represent the expected cohort.")
    if not table["row_widths_consistent"]:
        issues.append("Count table is not rectangular TSV data.")
    manifest = build_manifest(samples)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "sample_accession", "title", "characteristics",
            "explicit_age_years", "explicit_sex",
        ], delimiter="\t")
        writer.writeheader()
        writer.writerows(manifest)
    report = {
        "dataset": "GSE262619",
        "evidence_class": "public_human_age_reference_not_exceptional_longevity",
        "status": "PASS_SOURCE_BUNDLE" if not issues else "BLOCKED_SOURCE_BUNDLE",
        "sample_count": len(samples),
        "unique_sample_count": len(set(ids)),
        "matched_sample_count": table["matched_sample_count"],
        "matched_by_title_count": table.get("matched_by_title_count", 0),
        "matrix_rows": table["matrix_rows"],
        "matrix_columns": table["matrix_columns"],
        "row_widths_consistent": table["row_widths_consistent"],
        "matrix_sample_ids": table["matched_sample_ids"],
        "explicit_age_metadata_count": sum(bool(row["explicit_age_years"]) for row in manifest),
        "explicit_sex_metadata_count": sum(bool(row["explicit_sex"]) for row in manifest),
        "title_coded_sex_count": sum(bool(row["title_sex"]) for row in manifest),
        "nominal_age_band_discrepancies": [
            {
                "sample_accession": row["sample_accession"],
                "title": row["title"],
                "explicit_age_years": row["explicit_age_years"],
                "nominal_age_band_years": row["nominal_age_band_years"],
            }
            for row in manifest
            if row["explicit_age_years"] and row["nominal_age_band_years"]
            and abs(float(row["explicit_age_years"]) - float(row["nominal_age_band_years"])) > 10
        ],
        "counts_file_bytes": counts.stat().st_size,
        "soft_file_bytes": soft.stat().st_size,
        "counts_sha256": sha256(counts),
        "soft_sha256": sha256(soft),
        "first_row_preview": table["first_row_preview"],
        "issues": issues,
        "limitations": [
            "This audit authenticates file integrity and sample linkage only.",
            "Age and sex are extracted only from explicitly labelled GEO characteristics.",
            "GSE262619 is an ordinary age-reference cohort, not an exceptional-longevity cohort.",
            "No differential-expression result or new biological mechanism is claimed.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--soft", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-samples", type=int, default=35)
    args = parser.parse_args()
    report = audit(args.counts, args.soft, args.output, args.manifest, args.expected_samples)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS_SOURCE_BUNDLE" else 1


if __name__ == "__main__":
    sys.exit(main())
