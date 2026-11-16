#!/usr/bin/env python3
"""Print a small, non-identifying public SRA FASTQ QC preview."""
from __future__ import annotations

import gzip
import json
from pathlib import Path


def main() -> None:
    path = Path("fastq/SRR350239.fastq.gz")
    if not path.exists():
        raise FileNotFoundError(path)
    records = []
    with gzip.open(path, "rt", encoding="ascii") as handle:
        for index in range(10):
            lines = [handle.readline().rstrip("\n") for _ in range(4)]
            if not lines[0]:
                break
            if len(lines) != 4 or not lines[0].startswith("@") or not lines[2].startswith("+"):
                raise ValueError(f"Malformed FASTQ record at preview index {index}")
            records.append({
                "read_header": lines[0],
                "sequence": lines[1],
                "sequence_length": len(lines[1]),
                "quality_ascii_min": min(map(ord, lines[3])) if lines[3] else None,
                "quality_ascii_max": max(map(ord, lines[3])) if lines[3] else None,
                "quality_string": lines[3],
                "contains_truseq_small_rna_3prime_adapter": "TGGAATTCTCGGGTGCCAAGG" in lines[1],
                "contains_truseq_adapter_prefix": "TGGAATTCTCGGGTG" in lines[1],
            })
    report = {"run": "SRR350239", "preview_records": len(records), "records": records}
    Path("artifacts/gse32493-sra").mkdir(parents=True, exist_ok=True)
    Path("artifacts/gse32493-sra/fastq_preview.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
