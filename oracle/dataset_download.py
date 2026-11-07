"""Safe, bounded downloads for openly accessible scientific dataset files.

This module downloads one file only. It never extracts archives or executes content.
Callers must preserve the source record, dataset licence, and citation alongside
the returned SHA-256 digest.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


_ALLOWED_HOSTS = {
    "zenodo.org", "dataverse.harvard.edu", "files.rcsb.org",
    "ftp.sra.ebi.ac.uk", "sra-download.ncbi.nlm.nih.gov", "api.openml.org",\n    "sra-pub-run-odp.s3.amazonaws.com",
    "huggingface.co", "cdn-lfs.huggingface.co", "openml.org",
    "www.openml.org", "www.ebi.ac.uk",
}
_DEFAULT_MAX_BYTES = 2 * 1024 * 1024 * 1024


def _host_allowed(host: str) -> bool:
    host = (host or "").casefold().rstrip(".")
    return host in _ALLOWED_HOSTS or any(
        host.endswith("." + suffix) for suffix in ("zenodo.org", "harvard.edu", "hf.co", "ebi.ac.uk", "noaa.gov", "rcsb.org")
    )


def download_dataset_file(url: str, destination: str | Path, *,
                          max_bytes: int = _DEFAULT_MAX_BYTES,
                          timeout: float = 60.0) -> dict:
    """Download an HTTPS file from a supported research repository.

    Returns path, byte count, SHA-256, and final URL. Rejects unapproved hosts,
    oversized files, and redirects outside the allowlist.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https" or not _host_allowed(parsed.hostname or ""):
        raise ValueError("Dataset URL must use HTTPS and an approved repository host.")
    if max_bytes <= 0 or timeout <= 0:
        raise ValueError("max_bytes and timeout must be positive.")
    request = Request(url, headers={"User-Agent": "ORACLE-Scientific-Dataset-Client/1.0"})
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    written = 0
    try:
        with urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            final = urlparse(final_url)
            if final.scheme != "https" or not _host_allowed(final.hostname or ""):
                raise ValueError("Dataset download redirected outside approved repository hosts.")
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > max_bytes:
                raise ValueError("Dataset file exceeds configured max_bytes.")
            with target.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        raise ValueError("Dataset file exceeds configured max_bytes.")
                    digest.update(chunk)
                    output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {
        "path": str(target), "bytes": written,
        "sha256": digest.hexdigest(), "url": final_url,
    }


def pdb_structure_download_url(pdb_id: str, file_format: str = "cif") -> str:
    """Return the canonical coordinate-file URL for a validated PDB accession."""
    import re
    accession = (pdb_id or "").strip().upper()
    if not re.fullmatch(r"[0-9][A-Z0-9]{3}", accession):
        raise ValueError("Invalid PDB accession.")
    fmt = file_format.casefold()
    if fmt not in {"cif", "pdb", "bcif"}:
        raise ValueError("PDB file format must be cif, pdb, or bcif.")
    suffix = "cif" if fmt == "bcif" else fmt
    return f"https://files.rcsb.org/download/{accession}.{suffix}"
