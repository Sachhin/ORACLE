#!/usr/bin/env python3
"""Probe public Mendeley Data metadata and file inventory without downloading data."""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATASET_ID = "fpf4y72kfz"
VERSION = "1"
DOI = "10.17632/fpf4y72kfz.1"
BASE = "https://api.data.mendeley.com"
OUT = Path("artifacts/mendeley")
OUT.mkdir(parents=True, exist_ok=True)

# The dataset metadata endpoint is /datasets/{id}; the public file listing
# endpoint is /datasets/publics/{id}/files. Probe each independently so a 404
# on one route cannot be misreported as proof that the dataset has no files.
ENDPOINTS = {
    "dataset": f"{BASE}/datasets/{DATASET_ID}?version={VERSION}",
    "dataset_metadata": f"{BASE}/datasets/{DATASET_ID}/metadata?version={VERSION}",
    "public_files": f"{BASE}/datasets/publics/{DATASET_ID}/files?version={VERSION}&$limit=500",
}


def fetch_json(name: str, url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ORACLE-reproducible-research/1.1 (public metadata audit)",
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

    body = raw.decode("utf-8", errors="replace")
    result: dict[str, Any] = {
        "name": name,
        "url": url,
        "http_status": status,
        "content_type": content_type,
        "response_bytes": len(raw),
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "body": body,
    }
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


def main() -> None:
    results = {name: fetch_json(name, url) for name, url in ENDPOINTS.items()}
    summary = {
        "dataset_doi": DOI,
        "dataset_id": DATASET_ID,
        "version": VERSION,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Public metadata and file-inventory probe only; no expression or patient-level files downloaded.",
        "api_documentation": "https://data.mendeley.com/api/docs/",
        "results": results,
        "decision": {
            "file_inventory_confirmed": any(
                item.get("http_status") == 200 and isinstance(item.get("files"), list)
                for item in results.values()
            ),
            "sample_manifest_authenticated": False,
            "expression_matrix_downloaded": False,
            "note": "HTTP success or a file listing does not authenticate sample age/cohort labels; inspect file contents and provenance separately.",
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
