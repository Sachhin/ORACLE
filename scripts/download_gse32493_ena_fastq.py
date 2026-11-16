#!/usr/bin/env python3
"""Download GSE32493 single-end FASTQ files from ENA and verify source MD5s."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RUNS = ["SRR350239", "SRR350240", "SRR350241", "SRR350242", "SRR350243", "SRR350244"]
FIELDS = "run_accession,fastq_ftp,fastq_md5,fastq_bytes"


def digest(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for run in RUNS:
        query = urllib.parse.urlencode({
            "accession": run,
            "result": "read_run",
            "fields": FIELDS,
            "format": "tsv",
        })
        api_url = f"https://www.ebi.ac.uk/ena/portal/api/filereport?{query}"
        request = urllib.request.Request(api_url, headers={"User-Agent": "ORACLE-GSE32493-reanalysis/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = response.read().decode("utf-8")
        rows = list(csv.DictReader(payload.splitlines(), delimiter="\t"))
        if len(rows) != 1 or rows[0].get("run_accession") != run:
            raise RuntimeError(f"ENA did not return exactly one record for {run}: {rows!r}")
        row = rows[0]
        urls = [x for x in (row.get("fastq_ftp") or "").split(";") if x]
        md5s = [x for x in (row.get("fastq_md5") or "").split(";") if x]
        byte_sizes = [x for x in (row.get("fastq_bytes") or "").split(";") if x]
        if len(urls) != 1 or len(md5s) != 1 or len(byte_sizes) != 1:
            raise RuntimeError(f"Expected one single-end FASTQ file for {run}; ENA row: {row!r}")
        url = urls[0]
        if url.startswith("ftp://"):
            url = "https://" + url[len("ftp://"):]
        elif not url.startswith("https://"):
            url = "https://" + url.lstrip("/")
        target = args.outdir / f"{run}.fastq.gz"
        req = urllib.request.Request(url, headers={"User-Agent": "ORACLE-GSE32493-reanalysis/1.0"})
        with urllib.request.urlopen(req, timeout=900) as response, target.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        actual_md5 = digest(target, "md5")
        if actual_md5.lower() != md5s[0].lower():
            raise RuntimeError(f"MD5 mismatch for {run}: expected {md5s[0]}, got {actual_md5}")
        records.append({
            "run_accession": run,
            "ena_api_url": api_url,
            "fastq_url": url,
            "library_layout": row.get("library_layout"),
            "expected_bytes": int(byte_sizes[0]),
            "downloaded_bytes": target.stat().st_size,
            "expected_md5": md5s[0],
            "verified_md5": actual_md5,
            "sha256": digest(target, "sha256"),
            "local_file": target.name,
        })
        if records[-1]["expected_bytes"] != records[-1]["downloaded_bytes"]:
            raise RuntimeError(f"Byte-count mismatch for {run}: {records[-1]}")

    manifest = {
        "accession": "GSE32493",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "source": "European Nucleotide Archive read-run file report and FASTQ",
        "runs": records,
        "all_source_md5_checks_passed": True,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
