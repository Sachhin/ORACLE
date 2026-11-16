#!/usr/bin/env python3
"""Retrieve and checksum the 2026 human-longevity article's public supplements."""
from __future__ import annotations

import hashlib
import json
import tarfile
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

PMCID = "PMC13198318"
BASE = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{PMCID}"


def fetch(url: str, target: Path) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "ORACLE-longevity-supplement-audit/1.0"})
    with urllib.request.urlopen(request, timeout=900) as response, target.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
        return response.status, response.headers.get("Content-Type", "")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    out = Path("artifacts/longevity-2026-supplements")
    out.mkdir(parents=True, exist_ok=True)
    fulltext_url = f"{BASE}/fullTextXML"
    supplements_url = f"{BASE}/supplementaryFiles"
    fulltext_path = out / "fulltext.xml"
    fulltext_status, fulltext_type = fetch(fulltext_url, fulltext_path)

    links = []
    root = ET.parse(fulltext_path).getroot()
    xlink = "{http://www.w3.org/1999/xlink}href"
    for node in root.iter():
        href = node.attrib.get(xlink) or node.attrib.get("href")
        if href and any(token in href.lower() for token in ("supp", "table", ".xlsx", ".csv", ".tsv", ".pdf", ".zip")):
            links.append(href)

    archive_path = out / "supplementary_files.zip"
    archive_status = None
    archive_type = None
    extracted = []
    try:
        archive_status, archive_type = fetch(supplements_url, archive_path)
        if zipfile.is_zipfile(archive_path):
            target_dir = out / "extracted"
            target_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(archive_path) as archive:
                for info in archive.infolist():
                    name = info.filename
                    if info.is_dir() or name.startswith("/") or ".." in Path(name).parts:
                        continue
                    target = target_dir / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(info))
                    extracted.append({
                        "path": str(target.relative_to(out)),
                        "bytes": target.stat().st_size,
                        "sha256": sha256(target),
                    })
        elif tarfile.is_tarfile(archive_path):
            target_dir = out / "extracted"
            target_dir.mkdir(exist_ok=True)
            with tarfile.open(archive_path, "r:*") as archive:
                for member in archive.getmembers():
                    if not member.isfile() or member.name.startswith("/") or ".." in Path(member.name).parts:
                        continue
                    target = target_dir / member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(member)
                    if source:
                        target.write_bytes(source.read())
                        extracted.append({
                            "path": str(target.relative_to(out)),
                            "bytes": target.stat().st_size,
                            "sha256": sha256(target),
                        })
        else:
            archive_type = f"{archive_type}; response is not ZIP or TAR"
    except Exception as exc:
        archive_status = "unavailable"
        archive_type = str(exc)

    summary = {
        "pmcid": PMCID,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "fulltext_url": fulltext_url,
        "fulltext_http_status": fulltext_status,
        "fulltext_content_type": fulltext_type,
        "fulltext_sha256": sha256(fulltext_path),
        "supplementary_files_url": supplements_url,
        "supplementary_files_http_status": archive_status,
        "supplementary_files_content_type": archive_type,
        "supplementary_archive_sha256": sha256(archive_path) if archive_path.exists() else None,
        "fulltext_supplement_links": sorted(set(links)),
        "extracted_file_count": len(extracted),
        "extracted_files": extracted,
        "candidate_gene_or_sample_tables": [
            item for item in extracted
            if any(token in item["path"].lower() for token in ("gene", "mrpg", "ribosom", "table", "supp", "sample", "metadata", "matrix"))
        ],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
