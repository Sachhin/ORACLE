"""Discover and optionally download bounded GEO Series supplementary files.

Discovery follows NCBI GEO's documented accession-range FTP directory layout.
Downloads are opt-in, size-capped, checksum-recorded, and never parsed as evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .models import DatasetFileRecord, ResearchRun


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.hrefs.append(href)


@dataclass
class GEOFileReport:
    accessions_examined: int = 0
    files_discovered: int = 0
    files_downloaded: int = 0
    files_skipped_size: int = 0
    warnings: list[str] = field(default_factory=list)


class GEOSupplementaryClient:
    ALLOWED_EXTENSIONS = (
        ".tar", ".tar.gz", ".tgz", ".gz", ".zip", ".txt", ".tsv", ".csv",
        ".mtx", ".h5", ".hdf5", ".fastq", ".fastq.gz", ".bam", ".cram",
        ".cel", ".idat", ".xlsx",
    )

    def __init__(self, timeout: float = 30.0, max_listing_bytes: int = 2_000_000):
        if timeout <= 0 or max_listing_bytes < 1024:
            raise ValueError("Invalid GEO retrieval limits.")
        self.timeout = timeout
        self.max_listing_bytes = max_listing_bytes

    @staticmethod
    def series_directory(accession: str) -> str:
        import re
        match = re.fullmatch(r"GSE(\d+)", accession.upper())
        if not match:
            raise ValueError("Only GEO Series accessions in GSE format are supported.")
        digits = match.group(1)
        range_name = digits[:-3] + "nnn" if len(digits) > 3 else "nnn"
        return f"https://ftp.ncbi.nlm.nih.gov/geo/series/GSE{range_name}/{accession.upper()}/suppl/"

    def _fetch_listing(self, url: str) -> str:
        request = Request(url, headers={
            "Accept": "text/html",
            "User-Agent": "ORACLE-GEO-Supplementary/2.0",
        })
        with urlopen(request, timeout=self.timeout) as response:
            payload = response.read(self.max_listing_bytes + 1)
        if len(payload) > self.max_listing_bytes:
            raise RuntimeError("GEO directory listing exceeded the configured size limit.")
        return payload.decode("utf-8", "replace")

    @classmethod
    def parse_listing(cls, html: str, base_url: str) -> list[tuple[str, str]]:
        parser = _Links()
        parser.feed(html)
        files = []
        seen = set()
        base_host = urlparse(base_url).hostname
        for href in parser.hrefs:
            if href.startswith("?") or href in {"../", "./"}:
                continue
            url = urljoin(base_url, href)
            parsed = urlparse(url)
            filename = Path(parsed.path).name
            lower = filename.lower()
            if (parsed.scheme != "https" or parsed.hostname != base_host
                    or parsed.hostname != "ftp.ncbi.nlm.nih.gov"
                    or not filename or filename in {".", ".."}
                    or not any(lower.endswith(ext) for ext in cls.ALLOWED_EXTENSIONS)
                    or url in seen):
                continue
            seen.add(url)
            files.append((filename, url))
        return files

    def discover(self, run: ResearchRun) -> GEOFileReport:
        report = GEOFileReport()
        for source in run.sources:
            accession = (source.dataset_accession or "").upper()
            if not accession.startswith("GSE"):
                continue
            report.accessions_examined += 1
            try:
                base_url = self.series_directory(accession)
                listing = self._fetch_listing(base_url)
                files = self.parse_listing(listing, base_url)
                for filename, url in files:
                    if any(item.source_id == source.source_id and item.url == url
                           for item in run.dataset_files):
                        continue
                    run.dataset_files.append(DatasetFileRecord(
                        accession=accession, source_id=source.source_id,
                        filename=filename, url=url,
                    ))
                    report.files_discovered += 1
                if not files:
                    report.warnings.append(f"{accession}: no supported supplementary files were listed.")
            except Exception as exc:
                report.warnings.append(f"{accession}: {exc}")
        run.findings.append(
            f"GEO supplementary discovery: {report.files_discovered} file records discovered "
            f"across {report.accessions_examined} Series accessions; no data files were downloaded."
        )
        return report

    def download(
        self, run: ResearchRun, output_dir: str | Path = "data/geo",
        max_file_bytes: int = 50_000_000,
    ) -> GEOFileReport:
        if not 1_000_000 <= max_file_bytes <= 1_000_000_000:
            raise ValueError("max_file_bytes must be between 1 MB and 1 GB.")
        report = GEOFileReport()
        root = Path(output_dir)
        for item in run.dataset_files:
            if item.status == "downloaded":
                continue
            parsed = urlparse(item.url)
            if parsed.scheme != "https" or parsed.hostname != "ftp.ncbi.nlm.nih.gov":
                item.status, item.error = "rejected", "Download URL is not an official NCBI GEO HTTPS host."
                report.warnings.append(f"{item.filename}: rejected non-NCBI URL.")
                continue
            filename = Path(item.filename).name
            if filename != item.filename or filename in {"", ".", ".."}:
                item.status, item.error = "rejected", "Unsafe filename."
                report.warnings.append("Rejected unsafe GEO filename.")
                continue
            target_dir = root / item.accession
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / filename
            temporary = target.with_name(target.name + ".part")
            digest = hashlib.sha256()
            written = 0
            try:
                request = Request(item.url, headers={"User-Agent": "ORACLE-GEO-Downloader/2.0"})
                with urlopen(request, timeout=self.timeout) as response:
                    length = response.headers.get("Content-Length")
                    if length and int(length) > max_file_bytes:
                        item.status = "skipped_size"
                        item.size_bytes = int(length)
                        item.error = f"File exceeds the {max_file_bytes}-byte download cap."
                        report.files_skipped_size += 1
                        continue
                    with temporary.open("wb") as output:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            written += len(chunk)
                            if written > max_file_bytes:
                                raise RuntimeError(f"File exceeded the {max_file_bytes}-byte download cap.")
                            digest.update(chunk)
                            output.write(chunk)
                temporary.replace(target)
                item.status = "downloaded"
                item.size_bytes = written
                item.local_path = str(target)
                item.sha256 = digest.hexdigest()
                item.error = ""
                report.files_downloaded += 1
            except Exception as exc:
                temporary.unlink(missing_ok=True)
                item.status = "error"
                item.error = str(exc)
                report.warnings.append(f"{filename}: {exc}")
        run.findings.append(
            f"GEO supplementary downloads: {report.files_downloaded} downloaded; "
            f"{report.files_skipped_size} skipped by size limit."
        )
        return report
