"""Bounded descriptive parser for downloaded GEO Series expression matrices.

This module does not normalize expression values, run differential-expression
statistics, infer biological effects, or convert numerical summaries into claims
about causation. It only records reproducible structural/descriptive metadata.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import math
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from .models import DatasetAnalysisRecord, Evidence, EvidenceKind, ResearchRun


@dataclass
class GEOAnalysisReport:
    files_examined: int = 0
    files_analyzed: int = 0
    files_skipped: int = 0
    samples_flagged: int = 0
    warnings: list[str] = field(default_factory=list)


class _Accumulator:
    def __init__(self) -> None:
        self.count = 0
        self.missing = 0
        self.total = 0.0
        self.mean_value = 0.0
        self.m2 = 0.0
        self.minimum: float | None = None
        self.maximum: float | None = None

    def add(self, value: float | None) -> None:
        if value is None:
            self.missing += 1
            return
        self.count += 1
        self.total += value
        delta = value - self.mean_value
        self.mean_value += delta / self.count
        self.m2 += delta * (value - self.mean_value)
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)

    @property
    def mean(self) -> float | None:
        return self.total / self.count if self.count else None

    @property
    def sample_variance(self) -> float | None:
        return self.m2 / (self.count - 1) if self.count > 1 else (0.0 if self.count == 1 else None)


class GEOExpressionAnalyzer:
    """Parse bounded TSV/CSV or GEO series_matrix tables from downloaded files."""

    PARSER_VERSION = "oracle-geo-matrix-v1"
    SUPPORTED = (".series_matrix.txt.gz", "_series_matrix.txt.gz",
                 ".tsv.gz", ".csv.gz", ".txt.gz", ".tsv", ".csv", ".txt")
    MISSING = {"", "na", "nan", "null", "n/a", "na_real_", "."}

    def __init__(self, max_uncompressed_bytes: int = 100_000_000,
                 max_rows: int = 100_000, max_samples: int = 5_000,
                 max_cells: int = 2_000_000,
                 max_missing_fraction: float = 0.20):
        if (max_uncompressed_bytes < 1024 or max_rows < 1
                or max_samples < 1 or max_cells < 1):
            raise ValueError("GEO analysis limits must be positive.")
        self.max_uncompressed_bytes = max_uncompressed_bytes
        self.max_rows = max_rows
        self.max_samples = max_samples
        if not 0.0 <= max_missing_fraction <= 1.0:
            raise ValueError("max_missing_fraction must be between 0 and 1.")
        self.max_cells = max_cells
        self.max_missing_fraction = max_missing_fraction

    @classmethod
    def _supported(cls, filename: str) -> bool:
        name = filename.lower()
        return any(name.endswith(ext) for ext in cls.SUPPORTED)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _read_text(self, path: Path) -> str:
        opener = gzip.open if path.name.lower().endswith(".gz") else open
        with opener(path, "rb") as stream:
            raw = stream.read(self.max_uncompressed_bytes + 1)
        if len(raw) > self.max_uncompressed_bytes:
            raise ValueError("Uncompressed dataset exceeds the configured analysis byte limit.")
        return raw.decode("utf-8-sig", "replace")

    @staticmethod
    def _table_text(text: str) -> str:
        lines = text.splitlines()
        begin = next((i for i, line in enumerate(lines)
                      if line.strip().lower() == "!series_matrix_table_begin"), None)
        if begin is not None:
            end = next((i for i in range(begin + 1, len(lines))
                        if lines[i].strip().lower() == "!series_matrix_table_end"), len(lines))
            return "\n".join(lines[begin + 1:end])
        data = [line for line in lines if line.strip()
                and not line.lstrip().startswith(("!", "#"))]
        return "\n".join(data)

    @staticmethod
    def _sample_metadata(text: str, sample_count: int) -> list[dict]:
        """Read per-sample GEO characteristics without inferring experimental groups."""
        metadata = [{} for _ in range(sample_count)]
        for line in text.splitlines():
            if not line.startswith("!Sample_") or "=" not in line:
                continue
            field, _, raw_values = line.partition("=")
            try:
                values = shlex.split(raw_values.strip())
            except ValueError:
                continue
            if len(values) != sample_count:
                continue
            field = field[len("!Sample_"):].strip()
            for index, value in enumerate(values):
                if field.startswith("characteristics_"):
                    if ":" not in value:
                        continue
                    key, _, characteristic = value.partition(":")
                    key = key.strip().lower()
                    if key:
                        metadata[index].setdefault("characteristics", {})[key] = characteristic.strip()
                else:
                    metadata[index][field] = value
        return metadata

    @classmethod
    def _number(cls, raw: str) -> float | None:
        value = raw.strip()
        if value.lower() in cls.MISSING:
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if math.isfinite(parsed) else None

    def _parse(self, text: str) -> tuple[list[dict], int, int, int, float, float, float]:
        table = self._table_text(text)
        if not table.strip():
            raise ValueError("No tabular expression matrix was found.")
        first = table.splitlines()[0]
        delimiter = "\t" if first.count("\t") >= first.count(",") else ","
        reader = csv.reader(io.StringIO(table), delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("Expression matrix has no header row.") from exc
        if len(header) < 2:
            raise ValueError("Expression matrix must have a feature column and at least one sample.")
        sample_names = [name.strip() or f"sample_{i+1}" for i, name in enumerate(header[1:])]
        if len(sample_names) > self.max_samples:
            raise ValueError(f"Matrix has {len(sample_names)} samples; limit is {self.max_samples}.")
        sample_metadata = self._sample_metadata(text, len(sample_names))
        accumulators = [_Accumulator() for _ in sample_names]
        global_stats = _Accumulator()
        feature_rows = 0
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            if row[0].strip().lower() in {"id_ref", "feature_id", "gene_id"}:
                continue
            if len(row) != len(sample_names) + 1:
                continue
            feature_rows += 1
            if feature_rows > self.max_rows:
                raise ValueError(f"Matrix exceeds the {self.max_rows}-row analysis limit.")
            if feature_rows * len(sample_names) > self.max_cells:
                raise ValueError(f"Matrix exceeds the {self.max_cells}-cell analysis limit.")
            for index, raw in enumerate(row[1:]):
                value = self._number(raw)
                accumulators[index].add(value)
                global_stats.add(value)
        if feature_rows == 0 or global_stats.count == 0:
            raise ValueError("No numeric expression cells were found in the matrix.")
        summaries = [{
            "sample": sample_names[index],
            "metadata": sample_metadata[index],
            "numeric_cells": item.count,
            "missing_cells": item.missing,
            "mean": item.mean,
            "minimum": item.minimum,
            "maximum": item.maximum,
            "sample_variance": item.sample_variance,
            "missing_fraction": item.missing / feature_rows if feature_rows else 1.0,
            "qc_flags": (
                (["high_missingness"] if feature_rows and item.missing / feature_rows > self.max_missing_fraction else [])
                + (["no_numeric_values"] if item.count == 0 else [])
                + (["constant_values"] if item.count > 1 and item.sample_variance == 0 else [])
            ),
        } for index, item in enumerate(accumulators)]
        return (summaries, feature_rows, global_stats.count, global_stats.missing,
                float(global_stats.mean), float(global_stats.minimum),
                float(global_stats.maximum))

    def analyze(self, run: ResearchRun) -> GEOAnalysisReport:
        report = GEOAnalysisReport()
        sources = {item.source_id: item for item in run.sources}
        for dataset_file in run.dataset_files:
            if dataset_file.status != "downloaded" or not dataset_file.local_path:
                continue
            if any(item.file_id == dataset_file.file_id for item in run.dataset_analyses):
                continue
            report.files_examined += 1
            if not self._supported(dataset_file.filename):
                report.files_skipped += 1
                report.warnings.append(
                    f"{dataset_file.filename}: format not yet supported (TSV/CSV text matrices only)."
                )
                continue
            source = sources.get(dataset_file.source_id)
            if source is None:
                report.files_skipped += 1
                report.warnings.append(f"{dataset_file.filename}: linked GEO source record is missing.")
                continue
            path = Path(dataset_file.local_path)
            try:
                if not path.is_file():
                    raise ValueError("Downloaded local file is missing.")
                actual_hash = self._sha256(path)
                if dataset_file.sha256 and actual_hash.lower() != dataset_file.sha256.lower():
                    raise ValueError("SHA-256 checksum does not match the downloaded-file record.")
                text = self._read_text(path)
                (samples, rows, numeric, missing, mean, minimum, maximum) = self._parse(text)
                analysis = DatasetAnalysisRecord(
                    file_id=dataset_file.file_id,
                    accession=dataset_file.accession,
                    source_id=dataset_file.source_id,
                    filename=dataset_file.filename,
                    sha256=actual_hash,
                    parser=self.PARSER_VERSION,
                    feature_rows=rows,
                    sample_count=len(samples),
                    numeric_cells=numeric,
                    missing_cells=missing,
                    mean=mean,
                    minimum=minimum,
                    maximum=maximum,
                    sample_summaries=samples,
                )
                run.dataset_analyses.append(analysis)
                report.samples_flagged += sum(bool(item["qc_flags"]) for item in samples)
                summary = (
                    f"Descriptive matrix parse of {dataset_file.filename}: {rows} feature rows, "
                    f"{len(samples)} sample columns, {numeric} finite numeric cells, "
                    f"{missing} missing/non-numeric cells; range {minimum:g} to {maximum:g}, "
                    f"mean {mean:g}. Sample QC flagged {sum(bool(item['qc_flags']) for item in samples)} "
                    f"of {len(samples)} columns. No samples were removed; no normalization or inferential test was performed."
                )
                evidence = Evidence(
                    claim=summary,
                    source=source.title,
                    kind=EvidenceKind.DATASET,
                    method=f"{self.PARSER_VERSION}; checksum-verified local GEO supplementary file",
                    limitations=analysis.limitations,
                    confidence="descriptive_only",
                    source_id=source.source_id,
                    locator=f"Downloaded dataset file: {dataset_file.filename}; SHA-256 {actual_hash}",
                    reliability=source.reliability_score,
                    dependence_group=f"geo-file:{dataset_file.file_id}",
                )
                run.evidence.append(evidence)
                analysis.evidence_id = evidence.evidence_id
                report.files_analyzed += 1
            except Exception as exc:
                report.files_skipped += 1
                report.warnings.append(f"{dataset_file.filename}: {exc}")
        run.findings.append(
            f"GEO matrix analysis: {report.files_analyzed} supported text matrices parsed; "
            f"{report.files_skipped} files skipped or unavailable; {report.samples_flagged} sample columns flagged by descriptive QC. No samples were removed."
        )
        return report
