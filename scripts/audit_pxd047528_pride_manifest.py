#!/usr/bin/env python3
"""Fetch public PRIDE Archive project/file metadata for PXD047528.

This is a metadata-only provenance audit. It does not download spectra or
infer participant identities from file order or naming conventions.
"""
from __future__ import annotations

import csv
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ACCESSION = "PXD047528"
BASE = "https://www.ebi.ac.uk/pride/ws/archive/v3"


def get_json(url: str):
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "ORACLE-provenance-audit/1.0"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
        return json.loads(payload.decode("utf-8")), response.status


def normalize_files(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("content", "files", "items", "_embedded"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                for nested in ("files", "items"):
                    if isinstance(value.get(nested), list):
                        return value[nested]
    raise ValueError(f"Unrecognized PRIDE files response shape: {type(payload).__name__}")


def file_category(record):
    category = record.get("fileCategory") or record.get("category") or {}
    if isinstance(category, dict):
        return category.get("value") or category.get("name") or ""
    return str(category)


def main():
    out = Path("artifacts/pxd047528-pride")
    out.mkdir(parents=True, exist_ok=True)
    project_url = f"{BASE}/projects/{ACCESSION}"
    files_url = f"{BASE}/projects/{ACCESSION}/files/all"

    project, project_status = get_json(project_url)
    raw_files, files_status = get_json(files_url)
    files = normalize_files(raw_files)
    if not files:
        raise RuntimeError("PRIDE API returned no files; refusing to treat this as an empty valid project")

    full = {
        "accession": ACCESSION,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "api": {"project_url": project_url, "files_url": files_url,
                "project_http_status": project_status, "files_http_status": files_status},
        "project": project,
        "files": files,
    }
    (out / "pride_project_and_file_manifest.json").write_text(
        json.dumps(full, indent=2) + "\n", encoding="utf-8"
    )

    rows = []
    for record in files:
        name = record.get("fileName") or record.get("file_name") or ""
        locations = record.get("publicFileLocations") or []
        urls = [x.get("value", "") for x in locations if isinstance(x, dict)]
        aliases = sorted(set(re.findall(r"(?:^|[^A-Za-z0-9])(?:[0-9]{1,2}_)?Slot[0-9]+", name, flags=re.I)))
        rows.append({
            "file_name": name,
            "category": file_category(record),
            "size_bytes": record.get("fileSize") or record.get("fileSizeBytes") or record.get("size"),
            "accession": record.get("accession", ""),
            "sample_accession": record.get("sampleAccession", ""),
            "alias_tokens": ";".join(aliases),
            "public_locations": ";".join(urls),
        })

    with (out / "pride_file_manifest.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    by_category = {}
    for row in rows:
        by_category[row["category"]] = by_category.get(row["category"], 0) + 1
    summary = {
        "accession": ACCESSION,
        "retrieved_utc": full["retrieved_utc"],
        "project_file_count": len(files),
        "category_counts": by_category,
        "filenames_with_slot_alias_tokens": [r["file_name"] for r in rows if r["alias_tokens"]],
        "files_with_sample_accession": [r["file_name"] for r in rows if r["sample_accession"]],
        "clinical_crosswalk_status": "NOT_ESTABLISHED_BY_FILE_METADATA",
        "interpretation": (
            "File names, raw acquisition records and sample accessions can support technical provenance. "
            "They do not authenticate HIV/herpes/HAND labels or a 15-alias-to-13-person mapping without "
            "a submitter/source manifest."
        ),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
