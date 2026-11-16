#!/usr/bin/env python3
"""Build per-sample GSE32493 miRNA counts from public SRA FASTQ reads.

Reads are adapter-trimmed by fastp, then aligned to the human mature-miRNA
reference with Bowtie 1. Only reads with one best human-miRNA target are
counted. Multi-mapping reads are excluded rather than assigned arbitrarily.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

SAMPLES = [
    {"gsm": "GSM804340", "srr": "SRR350239", "sample": "Control_1", "group": "control"},
    {"gsm": "GSM804341", "srr": "SRR350240", "sample": "Control_2", "group": "control"},
    {"gsm": "GSM804342", "srr": "SRR350241", "sample": "Control_3", "group": "control"},
    {"gsm": "GSM804343", "srr": "SRR350242", "sample": "Centenarian_1", "group": "centenarian"},
    {"gsm": "GSM804344", "srr": "SRR350243", "sample": "Centenarian_2", "group": "centenarian"},
    {"gsm": "GSM804345", "srr": "SRR350244", "sample": "Centenarian_3", "group": "centenarian"},
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_sam(path: Path) -> tuple[Counter[str], dict[str, int]]:
    """Count uniquely mapped reads; exclude reads with >1 best target."""
    targets: dict[str, set[str]] = defaultdict(set)
    mapped_qnames: set[str] = set()
    with path.open("rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.startswith("@"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 11:
                raise ValueError(f"Malformed SAM row in {path}: {line[:120]!r}")
            qname, flag_text, rname = fields[0], fields[1], fields[2]
            flag = int(flag_text)
            if flag & 4 or rname == "*":
                continue
            mapped_qnames.add(qname)
            targets[qname].add(rname)

    counts: Counter[str] = Counter()
    ambiguous = 0
    for qname, refs in targets.items():
        if len(refs) == 1:
            counts[next(iter(refs))] += 1
        else:
            ambiguous += 1
    stats = {
        "mapped_reads_with_at_least_one_best_alignment": len(mapped_qnames),
        "uniquely_mapped_reads_counted": sum(counts.values()),
        "multi_mapped_reads_excluded": ambiguous,
    }
    return counts, stats


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fastq-dir", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    trimmed_dir = args.outdir / "trimmed"
    sam_dir = args.outdir / "sam"
    qc_dir = args.outdir / "fastp_qc"
    for folder in (trimmed_dir, sam_dir, qc_dir):
        folder.mkdir(parents=True, exist_ok=True)

    index_prefix = args.outdir / "human_mature_mirna"
    run(["bowtie-build", str(args.reference), str(index_prefix)])

    count_by_sample: dict[str, Counter[str]] = {}
    sample_qc: list[dict] = []
    for sample in SAMPLES:
        run_id = sample["srr"]
        candidates = [args.fastq_dir / f"{run_id}.fastq.gz", args.fastq_dir / f"{run_id}.fastq"]
        raw = next((p for p in candidates if p.exists()), None)
        if raw is None:
            raise FileNotFoundError(f"Missing FASTQ for {run_id}; looked for {candidates}")

        trimmed = trimmed_dir / f"{run_id}.fastq"
        fastp_json = qc_dir / f"{run_id}.json"
        fastp_html = qc_dir / f"{run_id}.html"
        sam = sam_dir / f"{run_id}.sam"

        run([
            "fastp", "-i", str(raw), "-o", str(trimmed),
            "--length_required", "18", "--length_limit", "30",
            "--thread", "2", "--json", str(fastp_json), "--html", str(fastp_html),
        ])
        run([
            "bowtie", "-v", "1", "-a", "--best", "--strata", "-S", "-p", "2",
            str(index_prefix), str(trimmed), str(sam),
        ])

        counts, mapping_stats = parse_sam(sam)
        count_by_sample[sample["sample"]] = counts
        fastp = json.loads(fastp_json.read_text(encoding="utf-8"))
        before = fastp.get("summary", {}).get("before_filtering", {})
        after = fastp.get("summary", {}).get("after_filtering", {})
        adapter = fastp.get("adapter_cutting", {})
        sample_qc.append({
            **sample,
            "raw_fastq": raw.name,
            "raw_fastq_sha256": sha256(raw),
            "trimmed_fastq_sha256": sha256(trimmed),
            "raw_reads": before.get("total_reads"),
            "reads_after_filtering": after.get("total_reads"),
            "adapter_trimmed_reads": adapter.get("adapter_trimmed_reads"),
            "mapping": mapping_stats,
            "fastp_json": str(fastp_json.relative_to(args.outdir)),
            "sam_sha256": sha256(sam),
        })

    features = sorted({feature for counts in count_by_sample.values() for feature in counts})
    matrix_path = args.outdir / "mirna_counts.csv"
    with matrix_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        sample_names = [sample["sample"] for sample in SAMPLES]
        writer.writerow(["mirna_id", *sample_names])
        for feature in features:
            writer.writerow([feature, *[count_by_sample[name].get(feature, 0) for name in sample_names]])

    with (args.outdir / "sample_metadata.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["gsm", "srr", "sample", "group"])
        writer.writeheader()
        writer.writerows(SAMPLES)

    report = {
        "status": "PER_SAMPLE_RAW_READS_QUANTIFIED",
        "accession": "GSE32493",
        "reference": {
            "name": "miRBase human mature miRNA reference",
            "declared_release": "23.1",
            "source_url": "https://mirbase.org/ftp/23.1/mature.fa.gz",
            "source_archive_sha256": sha256(args.reference.parent / "mature.fa.gz"),
            "source_readme_sha256": sha256(args.reference.parent / "README"),
            "file": args.reference.name,
            "sha256": sha256(args.reference),
            "alignment": "Bowtie 1; up to one mismatch; all best-stratum alignments; only uniquely mapped reads counted",
        },
        "adapter_and_length_processing": {
            "tool": "fastp",
            "adapter_detection": "fastp single-end automatic adapter detection",
            "minimum_length": 18,
            "maximum_length": 30,
        },
        "samples": sample_qc,
        "features_counted": len(features),
        "count_matrix": matrix_path.name,
        "count_matrix_sha256": sha256(matrix_path),
        "differential_expression": {
            "status": "PENDING_EDGER",
            "method": "edgeR exact test; control versus centenarian",
            "caution": "Only three biological samples per group; exploratory analysis, not causal evidence.",
        },
        "limitations": [
            "This is a new per-sample reanalysis of public raw reads, not a byte-for-byte reproduction of the 2012 pipeline.",
            "The reference is miRBase 23.1, whereas the original paper's exact miRBase release and adapter-trimming software settings are not fully specified in GEO.",
            "Only uniquely mapped reads are counted; multi-mappers are excluded.",
            "The cohort contains only three centenarians and three controls, and samples are EBV-transformed B-cell lines.",
        ],
    }
    report_path = args.outdir / "raw_read_analysis_manifest.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"features": len(features), "samples": len(sample_qc), "report": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
