"""Optional Affymetrix CEL RMA adapter.

Uses Bioconductor for background correction, quantile normalization and
summarization. Caller must select the package family; platform is never guessed.
"""
from __future__ import annotations
import csv, hashlib, math, shutil, subprocess, tempfile
from pathlib import Path
from typing import Sequence

class AffymetrixUnavailableError(RuntimeError):
    """Rscript or the requested Bioconductor package is unavailable."""

_SCRIPT = r'''
args <- commandArgs(trailingOnly=TRUE)
backend <- args[1]
manifest <- read.delim(args[2], stringsAsFactors=FALSE, check.names=FALSE)
cel <- as.character(manifest$path)
if (!length(cel) || any(!file.exists(cel))) stop("A CEL input is missing.")
if (backend == "affy") {
 if (!requireNamespace("affy", quietly=TRUE)) stop("Bioconductor package affy is not installed.")
 raw <- affy::ReadAffy(filenames=cel)
 eset <- affy::rma(raw)
 package_version <- as.character(packageVersion("affy"))
} else if (backend == "oligo") {
 if (!requireNamespace("oligo", quietly=TRUE)) stop("Bioconductor package oligo is not installed.")
 raw <- oligo::read.celfiles(cel, verbose=FALSE)
 eset <- oligo::rma(raw)
 package_version <- as.character(packageVersion("oligo"))
} else stop("Unsupported backend.")
expr <- Biobase::exprs(eset)
if (is.null(rownames(expr)) || is.null(colnames(expr))) stop("RMA output identifiers are missing.")
out <- data.frame(feature=rownames(expr), expr, check.names=FALSE)
write.table(out, file=args[3], sep="\t", quote=FALSE, row.names=FALSE, na="NA")
cat(as.character(getRversion()), "\t", package_version, sep="")
'''

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

class AffymetrixRMAAnalyzer:
    """Run explicit affy or oligo RMA on caller-supplied CEL files."""
    def analyze(self, cel_files: Sequence[str | Path], output_path: str | Path, *,
                backend: str, rscript: str = "Rscript", timeout_seconds: int = 1800,
                max_files: int = 200, max_total_bytes: int = 2_000_000_000) -> dict:
        if backend not in {"affy", "oligo"}:
            raise ValueError("backend must be explicitly selected as affy or oligo.")
        if timeout_seconds < 1 or max_files < 2 or max_total_bytes < 1:
            raise ValueError("Timeout, file-count and byte limits must be positive.")
        paths = [Path(item).expanduser().resolve() for item in cel_files]
        if len(paths) < 2:
            raise ValueError("RMA requires at least two CEL files.")
        if len(paths) > max_files:
            raise ValueError(f"CEL input count exceeds the {max_files}-file limit.")
        if len({str(path) for path in paths}) != len(paths):
            raise ValueError("Duplicate CEL input paths are not allowed.")
        if any(not path.is_file() for path in paths):
            raise ValueError("Every CEL input must be an existing regular file.")
        sizes = [path.stat().st_size for path in paths]
        if any(size <= 0 for size in sizes) or sum(sizes) > max_total_bytes:
            raise ValueError("CEL inputs are empty or exceed the configured total byte limit.")
        destination = Path(output_path).expanduser().resolve()
        if destination in paths:
            raise ValueError("Output path must differ from every CEL input.")
        exe = shutil.which(rscript)
        if not exe:
            raise AffymetrixUnavailableError(f"Cannot find {rscript!r}.")
        input_records = [{"path": str(path), "size_bytes": size, "sha256": _sha256(path)}
                         for path, size in zip(paths, sizes)]
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="oracle-affy-rma-") as temp:
            root = Path(temp)
            manifest, script, result = root / "cel.tsv", root / "rma.R", root / "rma.tsv"
            with manifest.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
                writer.writerow(["path"])
                for path in paths:
                    writer.writerow([str(path)])
            script.write_text(_SCRIPT, encoding="utf-8")
            try:
                process = subprocess.run(
                    [exe, "--vanilla", str(script), backend, str(manifest), str(result)],
                    capture_output=True, text=True, timeout=timeout_seconds, check=False)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("Affymetrix RMA analysis timed out.") from exc
            if process.returncode:
                detail = (process.stderr or process.stdout or "RMA failed").strip()
                if "not installed" in detail:
                    raise AffymetrixUnavailableError(detail[-2000:])
                raise RuntimeError(f"Affymetrix RMA failed: {detail[-4000:]}")
            versions = (process.stdout or "").strip().split("\t")
            if len(versions) != 2 or not all(versions):
                raise RuntimeError("R/Bioconductor package version provenance is missing.")
            if not result.is_file():
                raise RuntimeError("RMA did not produce an expression matrix.")
            with result.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle, delimiter="\t")
                header = next(reader, [])
                if len(header) != len(paths) + 1 or header[0] != "feature":
                    raise RuntimeError("RMA output sample columns do not match CEL inputs.")
                rows = 0
                for row in reader:
                    if len(row) != len(header) or not row[0]:
                        raise RuntimeError("RMA output contains a malformed row.")
                    for value in row[1:]:
                        number = float(value)
                        if not math.isfinite(number):
                            raise RuntimeError("RMA output contains a non-finite expression value.")
                    rows += 1
                if rows == 0:
                    raise RuntimeError("RMA output contains no probe-set rows.")
            destination.write_bytes(result.read_bytes())
        return {
            "method": "Affymetrix RMA background correction + quantile normalization + summarization",
            "backend": backend, "input_files": input_records, "input_file_count": len(paths),
            "output_path": str(destination), "output_sha256": _sha256(destination),
            "features": rows, "samples": len(paths),
            "software": {"r": versions[0], backend: versions[1]},
            "limitations": (
                "The affy/oligo backend must be selected explicitly for the known array family. "
                "No platform detection, probe annotation mapping, batch correction, differential "
                "testing, or biological interpretation is performed. Confirm CEL compatibility, "
                "array design, annotation release, sample quality and study design independently."
            ),
        }
