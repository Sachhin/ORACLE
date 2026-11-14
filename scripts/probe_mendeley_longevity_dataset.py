#!/usr/bin/env python3
"""Probe public Mendeley Data file metadata without downloading expression matrices."""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

DATASET_ID = "fpf4y72kfz"
VERSION = "1"
OUT = Path("artifacts/mendeley")
OUT.mkdir(parents=True, exist_ok=True)

endpoints = {
    "public_files": f"https://api.data.mendeley.com/datasets/publics/{DATASET_ID}/files?version={VERSION}",
    "public_dataset": f"https://api.data.mendeley.com/datasets/publics/{DATASET_ID}?version={VERSION}",
}
results = {}
for name, url in endpoints.items():
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ORACLE-reproducible-research/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read()
            results[name] = {
                "url": url,
                "http_status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "body": raw.decode("utf-8", errors="replace"),
            }
    except urllib.error.HTTPError as exc:
        results[name] = {
            "url": url,
            "http_status": exc.code,
            "content_type": exc.headers.get("Content-Type"),
            "body": exc.read().decode("utf-8", errors="replace"),
        }
    except Exception as exc:
        results[name] = {"url": url, "error": f"{type(exc).__name__}: {exc}"}

for name, item in results.items():
    body = item.get("body")
    if body:
        try:
            parsed = json.loads(body)
            item["parsed"] = parsed
            if isinstance(parsed, list):
                item["file_count"] = len(parsed)
                item["files"] = [
                    {
                        "id": x.get("id"),
                        "filename": x.get("filename"),
                        "size": x.get("size"),
                        "description": x.get("description"),
                        "content_details": x.get("content_details"),
                    }
                    for x in parsed if isinstance(x, dict)
                ]
        except json.JSONDecodeError:
            pass

report = {
    "dataset_id": DATASET_ID,
    "version": VERSION,
    "purpose": "Metadata-only probe; no data files downloaded.",
    "results": results,
}
(OUT / "mendeley_public_metadata_probe.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(json.dumps({
    name: {
        "http_status": value.get("http_status"),
        "file_count": value.get("file_count"),
        "error": value.get("error"),
        "content_type": value.get("content_type"),
    }
    for name, value in results.items()
}, indent=2))
