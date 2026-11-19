#!/usr/bin/env python3
"""Probe Mendeley public metadata, landing page, and file inventory without downloading data."""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

DATASET_ID = "fpf4y72kfz"
VERSION = "1"
DOI = "10.17632/fpf4y72kfz.1"
BASE = "https://api.data.mendeley.com"
LANDING_PAGE = f"https://data.mendeley.com/datasets/{DATASET_ID}/{VERSION}"
OUT = Path("artifacts/mendeley")
OUT.mkdir(parents=True, exist_ok=True)

ENDPOINTS = {
    "dataset": f"{BASE}/datasets/{DATASET_ID}?version={VERSION}",
    "dataset_metadata": f"{BASE}/datasets/{DATASET_ID}/metadata?version={VERSION}",
    "public_files": f"{BASE}/datasets/publics/{DATASET_ID}/files?version={VERSION}&$limit=500",
}


class VisiblePageParser(HTMLParser):
    """Extract visible text and anchors from the public HTML landing page."""

    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href") or ""
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.text.append(value)
            if self._href is not None:
                self._anchor_text.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append({"text": " ".join(self._anchor_text), "href": self._href})
            self._href = None
            self._anchor_text = []


def fetch_response(name: str, url: str, accept: str = "application/json") -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "ORACLE-reproducible-research/1.2 (public metadata audit)",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            status = response.status
            content_type = response.headers.get("Content-Type")
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
        content_type = exc.headers.get("Content-Type")
    except Exception as exc:
        return {"name": name, "url": url, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "name": name,
        "url": url,
        "http_status": status,
        "content_type": content_type,
        "response_bytes": len(raw),
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "body": raw.decode("utf-8", errors="replace"),
    }


def probe_json(name: str, url: str) -> dict[str, Any]:
    result = fetch_response(name, url)
    body = result.get("body")
    if body is None:
        return result
    try:
        parsed = json.loads(body)
        result["parsed"] = parsed
        file_items = parsed if isinstance(parsed, list) else (
            parsed.get("results") if isinstance(parsed, dict) else None
        )
        if isinstance(file_items, list):
            result["file_count"] = len(file_items)
            result["files"] = [
                {
                    "id": item.get("id"),
                    "filename": item.get("filename"),
                    "size": item.get("size"),
                    "description": item.get("description"),
                    "folder_id": item.get("folder_id"),
                    "content_details": item.get("content_details"),
                }
                for item in file_items if isinstance(item, dict)
            ]
    except json.JSONDecodeError:
        result["json_parse_error"] = True
    return result


def probe_landing_page() -> dict[str, Any]:
    result = fetch_response("landing_page", LANDING_PAGE, "text/html")
    body = result.get("body")
    if body is None:
        return result
    html_path = OUT / "mendeley_landing_page.html"
    html_path.write_text(body, encoding="utf-8")
    parser = VisiblePageParser()
    parser.feed(body)
    text = parser.text
    try:
        start = text.index("Files") + 1
        end = text.index("Institutions", start)
        file_section = text[start:end]
    except ValueError:
        file_section = []
    result["page_title_text"] = text[:8]
    result["files_section_text"] = file_section
    result["files_section_visible_text_count"] = len(file_section)
    result["anchors"] = parser.links
    result["html_artifact"] = str(html_path)
    result["html_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    result["download_all_button_visible"] = any("Download All" in item for item in text)
    result["visible_file_entries"] = [
        link for link in parser.links
        if link["href"] and any(token in link["href"].lower() for token in ("/files/", "download"))
    ]
    return result


def main() -> None:
    results = {name: probe_json(name, url) for name, url in ENDPOINTS.items()}
    results["landing_page"] = probe_landing_page()
    api_file_inventory = any(
        item.get("http_status") == 200 and isinstance(item.get("files"), list)
        for name, item in results.items() if name != "landing_page"
    )
    visible_files = results["landing_page"].get("visible_file_entries", [])
    summary = {
        "dataset_doi": DOI,
        "dataset_id": DATASET_ID,
        "version": VERSION,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Public metadata and file-inventory probe only; no expression or patient-level files downloaded.",
        "api_documentation": "https://data.mendeley.com/api/docs/",
        "results": results,
        "decision": {
            "api_file_inventory_confirmed": api_file_inventory,
            "landing_page_http_200": results["landing_page"].get("http_status") == 200,
            "visible_file_entries_found": len(visible_files),
            "sample_manifest_authenticated": False,
            "expression_matrix_downloaded": False,
            "note": "A public landing page or API listing does not authenticate sample age/cohort labels. File contents and source provenance must be inspected separately.",
        },
    }
    target = OUT / "mendeley_public_metadata_probe.json"
    target.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "dataset_doi": DOI,
        "results": {
            name: {
                "http_status": item.get("http_status"),
                "file_count": item.get("file_count"),
                "visible_file_entries": len(item.get("visible_file_entries", [])),
                "response_bytes": item.get("response_bytes"),
                "error": item.get("error"),
            }
            for name, item in results.items()
        },
        "sample_manifest_authenticated": False,
        "report": str(target),
    }, indent=2))


if __name__ == "__main__":
    main()
