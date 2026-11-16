#!/usr/bin/env python3
"""Probe the PMC Open Access package for the 2018 CRA000515 cohort supplement.

The workflow preserves the OA response and archive file manifest. It does not
infer CHHA-to-cohort labels from file ordering or aggregate demographics.
"""
from __future__ import annotations

import hashlib
import json
import re
import tarfile
import urllib.error
import urllib.request
import zipfile
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

PMCID = "PMC6211641"
OA_URL = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={PMCID}"


def fetch(url: str, target: Path) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "ORACLE-CRA000515-provenance-audit/1.0"})
    with urllib.request.urlopen(request, timeout=600) as response, target.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
        return response.status, response.headers.get("Content-Type", "")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    out = Path("artifacts/cra000515-pmc-supplements")
    out.mkdir(parents=True, exist_ok=True)
    xml_path = out / "pmc_oa_response.xml"
    try:
        status, content_type = fetch(OA_URL, xml_path)
    except urllib.error.HTTPError as exc:
        xml_path.write_bytes(exc.read())
        status, content_type = exc.code, exc.headers.get("Content-Type", "")

    raw_xml = xml_path.read_text(encoding="utf-8", errors="replace")
    links = []
    try:
        root = ET.fromstring(raw_xml)
        for node in root.iter("link"):
            links.append({
                "format": node.attrib.get("format", ""),
                "href": node.attrib.get("href", ""),
            })
    except ET.ParseError:
        root = None

    archive_links = [x for x in links if x["format"].lower() in {"tgz", "tar.gz", "tar"}]
    archive_info = None
    extracted_files = []
    if archive_links:
        href = archive_links[0]["href"]
        download_url = href.replace("ftp://ftp.ncbi.nlm.nih.gov/", "https://ftp.ncbi.nlm.nih.gov/", 1)
        archive_path = out / "pmc_oa_package.tar.gz"
        archive_status, archive_type = fetch(download_url, archive_path)
        archive_info = {
            "url": download_url,
            "http_status": archive_status,
            "content_type": archive_type,
            "bytes": archive_path.stat().st_size,
            "sha256": sha256(archive_path),
        }
        extract_dir = out / "extracted"
        extract_dir.mkdir(exist_ok=True)
        with tarfile.open(archive_path, "r:*") as archive:
            for member in archive.getmembers():
                name = member.name
                if name.startswith("/") or ".." in Path(name).parts:
                    continue
                if member.isfile():
                    target = extract_dir / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(member)
                    if source:
                        target.write_bytes(source.read())
                        extracted_files.append({
                            "path": str(target.relative_to(out)),
                            "bytes": target.stat().st_size,
                            "sha256": sha256(target),
                        })

    europe_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{PMCID}/fullTextXML"
    europe_xml_path = out / "europepmc_fulltext.xml"
    europe_status = None
    europe_content_type = None
    supplement_links = []
    downloaded_supplements = []
    try:
        europe_status, europe_content_type = fetch(europe_url, europe_xml_path)
        europe_root = ET.parse(europe_xml_path).getroot()
        xlink = "{http://www.w3.org/1999/xlink}href"
        for node in europe_root.iter():
            href = node.attrib.get(xlink) or node.attrib.get("href")
            if href and re.search(r"(supp|table|sample|metadata|xlsx|csv|tsv|zip|pdf|txt)", href, flags=re.I):
                supplement_links.append(urljoin("https://europepmc.org/articles/PMC6211641/bin/", href))
        for link in sorted(set(supplement_links)):
            filename = link.rsplit("/", 1)[-1].split("?", 1)[0] or "supplement"
            target = out / "europepmc_supplements" / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                link_status, link_type = fetch(link, target)
                downloaded_supplements.append({
                    "url": link, "file_name": filename, "http_status": link_status,
                    "content_type": link_type, "bytes": target.stat().st_size,
                    "sha256": sha256(target), "local_path": str(target.relative_to(out)),
                })
            except Exception as exc:
                downloaded_supplements.append({"url": link, "error": str(exc)})
    except Exception as exc:
        europe_status = "unavailable"
        europe_content_type = str(exc)

    supplementary_api_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{PMCID}/supplementaryFiles"
    supplementary_api_path = out / "europepmc_supplementary_files.zip"
    supplementary_api_status = None
    supplementary_api_type = None
    supplementary_archive_files = []
    try:
        supplementary_api_status, supplementary_api_type = fetch(supplementary_api_url, supplementary_api_path)
        if zipfile.is_zipfile(supplementary_api_path):
            extract_dir = out / "europepmc_supplementary_archive"
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(supplementary_api_path) as archive:
                for info in archive.infolist():
                    name = info.filename
                    if name.startswith("/") or ".." in Path(name).parts or info.is_dir():
                        continue
                    target = extract_dir / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(info))
                    supplementary_archive_files.append({
                        "path": str(target.relative_to(out)),
                        "bytes": target.stat().st_size,
                        "sha256": sha256(target),
                    })
        else:
            supplementary_api_type = f"{supplementary_api_type}; response is not a ZIP archive"
    except Exception as exc:
        supplementary_api_status = "unavailable"
        supplementary_api_type = str(exc)

    candidate_files = [
        x for x in extracted_files
        if re.search(r"(supp|table|sample|metadata|data)", x["path"], flags=re.I)
    ]
    summary = {
        "pmcid": PMCID,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "oa_api_url": OA_URL,
        "oa_http_status": status,
        "oa_content_type": content_type,
        "oa_response_sha256": sha256(xml_path),
        "response_text": raw_xml[:5000],
        "links": links,
        "europepmc_fulltext_url": europe_url,
        "europepmc_http_status": europe_status,
        "europepmc_content_type": europe_content_type,
        "europepmc_supplement_links": sorted(set(supplement_links)),
        "downloaded_europepmc_supplements": downloaded_supplements,
        "europepmc_supplementary_api_url": supplementary_api_url,
        "europepmc_supplementary_api_status": supplementary_api_status,
        "europepmc_supplementary_api_content_type": supplementary_api_type,
        "europepmc_supplementary_archive_files": supplementary_archive_files,
        "archive": archive_info,
        "extracted_file_count": len(extracted_files),
        "extracted_files": extracted_files,
        "candidate_supplement_or_metadata_files": candidate_files,
        "cohort_mapping_status": "NOT_ESTABLISHED_UNTIL_SUPPLEMENT_CONTENT_IS_INSPECTED",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
