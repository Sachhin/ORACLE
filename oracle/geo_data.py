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


    @staticmethod
    def sample_directory(accession: str) -> str:
        import re
        match = re.fullmatch(r"GSM(\d+)", accession.upper())
        if not match:
            raise ValueError("Only GEO Sample accessions in GSM format are supported.")
        digits = match.group(1)
        range_name = digits[:-3] + "nnn" if len(digits) > 3 else "nnn"
        return (
            f"https://ftp.ncbi.nlm.nih.gov/geo/samples/"
            f"GSM{range_name}/GSM{digits}/suppl/"
        )

    def download_sample_files(
        self,
        accessions: list[str],
        output_dir: str | Path = "data/geo_samples",
        max_file_bytes: int = 50_000_000,
    ) -> dict:
        """Discover and download supplementary files for explicitly selected GSMs."""
        if not 1_000_000 <= max_file_bytes <= 1_000_000_000:
            raise ValueError("max_file_bytes must be between 1 MB and 1 GB.")
        if not accessions:
            raise ValueError("At least one explicit GSM accession is required.")
        if len({item.upper() for item in accessions}) != len(accessions):
            raise ValueError("GSM accessions must be unique.")
        root = Path(output_dir)
        report = {
            "samples_examined": 0, "files_discovered": 0,
            "files_downloaded": 0, "files_skipped_size": 0,
            "files": [], "warnings": [],
        }
        for raw_accession in accessions:
            accession = raw_accession.upper()
            report["samples_examined"] += 1
            try:
                base_url = self.sample_directory(accession)
                listing = self._fetch_listing(base_url)
                files = self.parse_listing(listing, base_url)
                report["files_discovered"] += len(files)
                if not files:
                    report["warnings"].append(
                        f"{accession}: no supported supplementary files found."
                    )
                    continue
                target_dir = root / accession
                target_dir.mkdir(parents=True, exist_ok=True)
                for filename, url in files:
                    target = target_dir / filename
                    temporary = target.with_name(target.name + ".part")
                    digest = hashlib.sha256()
                    written = 0
                    try:
                        request = Request(
                            url, headers={"User-Agent": "ORACLE-GEO-Sample-Downloader/1.0"}
                        )
                        with urlopen(request, timeout=self.timeout) as response:
                            length = response.headers.get("Content-Length")
                            if length and int(length) > max_file_bytes:
                                report["files_skipped_size"] += 1
                                report["files"].append({
                                    "accession": accession, "filename": filename,
                                    "status": "skipped_size", "size_bytes": int(length),
                                })
                                continue
                            with temporary.open("wb") as output:
                                while True:
                                    chunk = response.read(1024 * 1024)
                                    if not chunk:
                                        break
                                    written += len(chunk)
                                    if written > max_file_bytes:
                                        raise RuntimeError(
                                            f"File exceeded the {max_file_bytes}-byte cap."
                                        )
                                    digest.update(chunk)
                                    output.write(chunk)
                        temporary.replace(target)
                        report["files_downloaded"] += 1
                        report["files"].append({
                            "accession": accession, "filename": filename,
                            "status": "downloaded", "local_path": str(target),
                            "size_bytes": written, "sha256": digest.hexdigest(),
                            "url": url,
                        })
                    except Exception:
                        temporary.unlink(missing_ok=True)
                        raise
            except Exception as exc:
                report["warnings"].append(f"{accession}: {exc}")
        return report


    def download_series_raw_archive(
        self,
        accession: str,
        output_dir: str | Path = "data/geo",
        max_file_bytes: int = 50_000_000,
    ) -> dict:
        """Download a single official NCBI *_RAW.tar archive for a GSE accession."""
        import re
        if not re.fullmatch(r"GSE\d+", accession.upper()):
            raise ValueError("Only GEO Series accessions in GSE format are supported.")
        if not 1_000_000 <= max_file_bytes <= 1_000_000_000:
            raise ValueError("max_file_bytes must be between 1 MB and 1 GB.")
        accession = accession.upper()
        base_url = self.series_directory(accession)
        files = self.parse_listing(self._fetch_listing(base_url), base_url)
        archives = [(name, url) for name, url in files
                    if name.upper() == f"{accession}_RAW.TAR"]
        if len(archives) != 1:
            raise RuntimeError(
                f"Expected exactly one {accession}_RAW.tar archive; found {len(archives)}."
            )
        filename, url = archives[0]
        target_dir = Path(output_dir) / accession
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        temporary = target.with_name(target.name + ".part")
        digest = hashlib.sha256()
        written = 0
        import time
        download_url = url + ("&" if "?" in url else "?") + "tool=geoquery"
        last_error = None
        for attempt in range(3):
            digest = hashlib.sha256()
            written = 0
            try:
                request = Request(download_url, headers={
                    "User-Agent": "ORACLE-GEO-Series-Downloader/1.0",
                    "Accept": "application/octet-stream",
                })
                with urlopen(request, timeout=max(self.timeout, 120)) as response:
                    length = response.headers.get("Content-Length")
                    if length and int(length) > max_file_bytes:
                        raise RuntimeError(
                            f"Archive size {length} exceeds the {max_file_bytes}-byte cap."
                        )
                    with temporary.open("wb") as output:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            written += len(chunk)
                            if written > max_file_bytes:
                                raise RuntimeError(
                                    f"Archive exceeded the {max_file_bytes}-byte cap."
                                )
                            digest.update(chunk)
                            output.write(chunk)
                temporary.replace(target)
                last_error = None
                break
            except Exception as exc:
                temporary.unlink(missing_ok=True)
                last_error = exc
                if attempt < 2:
                    time.sleep(2 ** attempt)
        if last_error is not None:
            raise RuntimeError(
                f"Could not download {filename} from NCBI after 3 attempts: {last_error}"
            ) from last_error
        return {
            "accession": accession, "filename": filename,
            "url": url, "local_path": str(target),
            "size_bytes": written, "sha256": digest.hexdigest(),
        }

    @staticmethod
    def extract_raw_archive(
        archive_path: str | Path,
        output_dir: str | Path | None = None,
        *,
        max_members: int = 5000,
        max_member_bytes: int = 50_000_000,
        max_total_bytes: int = 250_000_000,
    ) -> dict:
        """Safely extract regular files from a GEO tar archive with strict limits."""
        import tarfile
        source = Path(archive_path)
        target_dir = Path(output_dir) if output_dir else source.parent / (source.stem + "_extracted")
        if not source.is_file():
            raise FileNotFoundError(source)
        if not 1 <= max_members <= 100_000:
            raise ValueError("max_members must be between 1 and 100000.")
        if not 1 <= max_member_bytes <= 1_000_000_000:
            raise ValueError("max_member_bytes must be between 1 and 1GB.")
        if not 1 <= max_total_bytes <= 2_000_000_000:
            raise ValueError("max_total_bytes must be between 1 and 2GB.")
        extracted, skipped, total = [], [], 0
        seen = set()
        target_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(source, mode="r:*") as archive:
            members = archive.getmembers()
            if len(members) > max_members:
                raise RuntimeError(f"Archive contains {len(members)} members; cap is {max_members}.")
            for member in members:
                name = member.name
                parts = Path(name).parts
                if (not member.isfile() or Path(name).is_absolute()
                        or any(part in {"..", ""} for part in parts)
                        or "\\" in name or not parts):
                    skipped.append({"name": name, "reason": "not a safe regular file"})
                    continue
                filename = parts[-1]
                if filename in seen:
                    raise RuntimeError(f"Archive contains duplicate output filename: {filename}")
                seen.add(filename)
                if not filename.upper().startswith("GSM"):
                    skipped.append({"name": name, "reason": "not a GSM sample file"})
                    continue
                if member.size < 0 or member.size > max_member_bytes:
                    skipped.append({"name": name, "reason": "member exceeds size limit"})
                    continue
                if total + member.size > max_total_bytes:
                    raise RuntimeError("Archive extraction would exceed total uncompressed size cap.")
                extracted_file = archive.extractfile(member)
                if extracted_file is None:
                    skipped.append({"name": name, "reason": "could not read member"})
                    continue
                destination = target_dir / filename
                temporary = destination.with_name(destination.name + ".part")
                copied = 0
                try:
                    with extracted_file, temporary.open("wb") as output:
                        while True:
                            chunk = extracted_file.read(1024 * 1024)
                            if not chunk:
                                break
                            copied += len(chunk)
                            if copied > member.size or copied > max_member_bytes:
                                raise RuntimeError(f"Member size mismatch or limit exceeded: {name}")
                            output.write(chunk)
                    if copied != member.size:
                        raise RuntimeError(f"Member size mismatch for {name}")
                    temporary.replace(destination)
                except Exception:
                    temporary.unlink(missing_ok=True)
                    raise
                total += copied
                extracted.append({
                    "archive_name": name, "filename": filename,
                    "local_path": str(destination), "size_bytes": copied,
                    "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                })
        return {
            "archive_path": str(source), "output_dir": str(target_dir),
            "files_extracted": len(extracted), "bytes_extracted": total,
            "files": extracted, "skipped": skipped,
            "limitations": "Only regular GSM-prefixed members were extracted. "
                           "Archive metadata and filenames do not establish biological groups.",
        }
