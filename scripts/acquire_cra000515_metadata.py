"""Acquire and audit public GSA metadata for CRA000515 without downloading BAMs.

The output is a provenance-preserving metadata package. It never infers cohort
labels from sample aliases and never downloads multi-GB sequencing files.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE = "https://ngdc.cncb.ac.cn/gsa"
RUN_URL = f"{BASE}/search/getRunInfoByCra"
XLSX_URL = f"{BASE}/file/exportExcelFile"
USER_AGENT = "ORACLE-CRA000515-metadata-audit/1.0 (reproducible research)"
EXPECTED_GROUP_COUNTS = {
    "centenarian": 76,
    "centenarian offspring": 54,
    "offspring spouse": 41,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _request(session: requests.Session, method: str, url: str, **kwargs: Any) -> bytes:
    response = session.request(method, url, timeout=(20, 180), **kwargs)
    response.raise_for_status()
    data = response.content
    if not data:
        raise RuntimeError(f"Empty response from {url}")
    prefix = data[:500].lstrip().lower()
    if prefix.startswith((b"<!doctype html", b"<html")) or b"browser check" in prefix:
        raise RuntimeError(f"GSA returned an HTML challenge instead of data: {url}")
    return data


def _normalise(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def _find_column(headers: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {_normalise(h): h for h in headers}
    for candidate in candidates:
        if _normalise(candidate) in normalized:
            return normalized[_normalise(candidate)]
    for header in headers:
        h = _normalise(header)
        if any(_normalise(candidate) in h for candidate in candidates):
            return header
    return None


def _read_csv(payload: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = payload.decode("utf-8-sig", errors="strict")
    if text.lstrip().startswith(("{", "[")):
        raise RuntimeError("GSA run metadata endpoint returned JSON, expected CSV")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or not rows[0]:
        raise RuntimeError("GSA run metadata CSV has no data rows")
    headers = list(rows[0])
    if not headers or not any(h and h.strip() for h in headers):
        raise RuntimeError("GSA run metadata CSV has no usable header")
    return headers, rows


def _read_workbook(payload: bytes) -> dict[str, tuple[list[str], list[dict[str, Any]]]]:
    from openpyxl import load_workbook\n    wb = load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    result: dict[str, tuple[list[str], list[dict[str, Any]]]] = {}
    try:
        for ws in wb.worksheets:
            iterator = ws.iter_rows(values_only=True)
            header_row = next(iterator, None)
            if not header_row:
                continue
            headers = [str(v).strip() if v is not None else "" for v in header_row]
            while headers and not headers[-1]:
                headers.pop()
            if not headers:
                continue
            rows = []
            for values in iterator:
                values = list(values[:len(headers)])
                if not any(v is not None and str(v).strip() for v in values):
                    continue
                rows.append({h: ("" if i >= len(values) or values[i] is None else str(values[i]).strip())
                             for i, h in enumerate(headers) if h})
            result[ws.title] = (headers, rows)
    finally:
        wb.close()
    return result


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def acquire_metadata(
    accession: str = "CRA000515",
    output_dir: str | Path = "artifacts/cra000515",
    *,
    session: Any = None,
) -> dict[str, Any]:
    if not re.fullmatch(r"CRA\d{6}", accession):
        raise ValueError("Only a CRA accession such as CRA000515 is accepted.")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if session is None:\n        import requests\n        session = requests.Session()\n    client = session
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}

    run_payload = _request(
        client, "POST", RUN_URL, headers=headers,
        data={"searchTerm": accession, "totalDatas": "9999", "downLoadCount": "9999"},
    )
    xlsx_payload = _request(
        client, "POST", XLSX_URL, headers=headers,
        data={"type": "3", "dlAcession": accession},
    )
    if not xlsx_payload.startswith(b"PK"):
        raise RuntimeError("GSA exportExcelFile response is not an XLSX ZIP workbook")

    run_headers, run_rows = _read_csv(run_payload)
    sheets = _read_workbook(xlsx_payload)
    if not sheets:
        raise RuntimeError("GSA workbook contains no readable worksheets")

    run_id_col = _find_column(run_headers, ("Run", "Run accession", "Run ID", "Accession"))
    sample_id_col = _find_column(run_headers, ("BioSample", "BioSample accession", "Sample accession"))
    if not run_id_col:
        raise RuntimeError(f"Cannot identify run accession column in GSA CSV: {run_headers}")
    if not sample_id_col:
        raise RuntimeError(f"Cannot identify BioSample accession column in GSA CSV: {run_headers}")

    run_ids = [str(r.get(run_id_col, "")).strip() for r in run_rows]
    invalid_runs = [x for x in run_ids if not re.fullmatch(r"CRR\d+", x)]
    if invalid_runs:
        raise RuntimeError(f"Run metadata contains invalid/missing CRR accessions: {invalid_runs[:10]}")
    if len(run_ids) != len(set(run_ids)):
        raise RuntimeError("Duplicate CRR run accessions in run metadata; refusing ambiguous manifest")

    sample_ids = [str(r.get(sample_id_col, "")).strip() for r in run_rows]
    missing_sample_ids = [run_ids[i] for i, sample in enumerate(sample_ids) if not re.fullmatch(r"SAMC\d+", sample)]
    if missing_sample_ids:
        raise RuntimeError(f"Runs without valid SAMC BioSample accession: {missing_sample_ids[:10]}")

    # Save source files exactly as returned, with hashes and retrieval metadata.
    run_path = out / f"{accession}.run_metadata.csv"
    workbook_path = out / f"{accession}.project_metadata.xlsx"
    run_path.write_bytes(run_payload)
    workbook_path.write_bytes(xlsx_payload)

    sheet_audit = {}
    sample_rows: list[dict[str, Any]] = []
    for name, (cols, rows) in sheets.items():
        sheet_audit[name] = {"columns": cols, "rows": len(rows)}
        if _normalise(name) == "sample":
            sample_rows = rows
        _write_csv(out / f"{accession}.{_normalise(name)}.csv", cols, rows)

    sample_sheet_id_col = None
    if sample_rows:
        sample_sheet_id_col = _find_column(
            list(sample_rows[0]), ("BioSample accession", "BioSample", "Sample accession", "Accession")
        )
    sample_lookup: dict[str, dict[str, Any]] = {}
    if sample_sheet_id_col:
        for row in sample_rows:
            key = str(row.get(sample_sheet_id_col, "")).strip()
            if key:
                if key in sample_lookup:
                    raise RuntimeError(f"Duplicate BioSample {key} in Sample worksheet")
                sample_lookup[key] = row

    manifest = []
    for row in run_rows:
        run_id = str(row[run_id_col]).strip()
        sample_id = str(row[sample_id_col]).strip()
        sample_meta = sample_lookup.get(sample_id, {})
        manifest.append({
            "run_accession": run_id,
            "biosample_accession": sample_id,
            "experiment_accession": str(row.get(_find_column(run_headers, ("Experiment", "Experiment accession", "CRX")) or "", "")).strip(),
            "sample_alias": str(sample_meta.get(_find_column(list(sample_meta), ("Sample name", "Sample", "Alias")) or "", "")).strip() if sample_meta else "",
            "raw_group_label": str(sample_meta.get(_find_column(list(sample_meta), ("Group", "Cohort", "Phenotype", "Condition", "Sample group")) or "", "")).strip() if sample_meta else "",
            "metadata_join_status": "matched_biosample" if sample_meta else "biosample_not_found_in_sample_sheet",
            "run_metadata_json": json.dumps(row, ensure_ascii=False, sort_keys=True),
            "sample_metadata_json": json.dumps(sample_meta, ensure_ascii=False, sort_keys=True),
        })
    manifest_headers = list(manifest[0]) if manifest else [
        "run_accession", "biosample_accession", "experiment_accession", "sample_alias",
        "raw_group_label", "metadata_join_status", "run_metadata_json", "sample_metadata_json"
    ]
    _write_csv(out / f"{accession}.run_biosample_manifest.csv", manifest_headers, manifest)

    # No group is inferred from alias or paper-level aggregate counts.
    group_col = None
    group_counts: dict[str, int] = {}
    if sample_rows:
        group_col = _find_column(list(sample_rows[0]), ("Group", "Cohort", "Phenotype", "Condition", "Sample group"))
        if group_col:
            group_counts = dict(Counter(str(r.get(group_col, "")).strip() for r in sample_rows if str(r.get(group_col, "")).strip()))

    age_col = _find_column(list(sample_rows[0]), ("Age", "Age at sampling", "Age years", "Age (years)")) if sample_rows else None
    age_values = [str(r.get(age_col, "")).strip() for r in sample_rows if age_col and str(r.get(age_col, "")).strip()]
    expected_labels_present = bool(group_counts) and all(
        any(_normalise(expected) in _normalise(label) for label in group_counts)
        for expected in EXPECTED_GROUP_COUNTS
    )
    design_check = {
        "published_design_reference_counts": EXPECTED_GROUP_COUNTS,
        "metadata_group_column": group_col,
        "observed_group_counts": group_counts,
        "all_expected_group_labels_explicitly_present": expected_labels_present,
        "metadata_age_column": age_col,
        "samples_with_nonempty_age": len(age_values),
        "sample_sheet_rows": len(sample_rows),
        "unique_biosamples_in_run_csv": len(set(sample_ids)),
        "note": "Published aggregate group counts are comparison targets only. This script never assigns group or age labels from aliases or counts."
    }

    retrieval_time = datetime.now(timezone.utc).isoformat()
    audit = {
        "accession": accession,
        "status": "metadata_acquired_needs_manual_provenance_review",
        "retrieved_at_utc": retrieval_time,
        "source_urls": {"run_csv": RUN_URL, "project_workbook": XLSX_URL},
        "request_parameters": {
            "run_csv": {"searchTerm": accession, "totalDatas": "9999", "downLoadCount": "9999"},
            "project_workbook": {"type": "3", "dlAcession": accession},
        },
        "source_sha256": {
            run_path.name: sha256_bytes(run_payload),
            workbook_path.name: sha256_bytes(xlsx_payload),
        },
        "run_count": len(run_rows),
        "unique_run_count": len(set(run_ids)),
        "unique_biosample_count": len(set(sample_ids)),
        "workbook_sheets": sheet_audit,
        "biosample_join": {
            "sample_sheet_present": bool(sample_rows),
            "sample_sheet_accession_column": sample_sheet_id_col,
            "matched_runs": sum(r["metadata_join_status"] == "matched_biosample" for r in manifest),
            "unmatched_runs": sum(r["metadata_join_status"] != "matched_biosample" for r in manifest),
        },
        "cohort_design_check": design_check,
        "raw_bam_downloaded": False,
        "scientific_analysis_performed": False,
        "limitations": [
            "Metadata acquisition is not sample identity validation or biological replication.",
            "No age or cohort labels are inferred from aliases, run order, or aggregate study counts.",
            "A complete manifest must be reconciled against the paper and submitter records before downloading all multi-GB BAM files.",
            "No raw sequencing files were downloaded by this workflow."
        ],
    }
    audit_path = out / f"{accession}.metadata_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    checksum_lines = []
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            checksum_lines.append(f"{sha256_bytes(path.read_bytes())}  {path.name}")
    (out / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accession", default="CRA000515")
    parser.add_argument("--output-dir", default="artifacts/cra000515")
    args = parser.parse_args(argv)
    try:
        report = acquire_metadata(args.accession, args.output_dir)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
