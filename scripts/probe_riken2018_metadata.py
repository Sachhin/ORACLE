#!/usr/bin/env python3
"""Inspect the public RIKEN 2018 supercentenarian metadata mirror.

This is a provenance/schema probe only. It does not infer participant labels.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

URL = "https://huggingface.co/datasets/longevity-db/riken2018/resolve/main/riken2018/sample_metadata.parquet"
EXPECTED_SHA256 = "40884e40921bb32ecde184085bcb3240f10f790bab85a9a246302c0a3a842798"
EXPECTED_BYTES = 622904


def main() -> None:
    out = Path("artifacts/riken2018")
    out.mkdir(parents=True, exist_ok=True)
    path = out / "sample_metadata.parquet"
    request = Request(URL, headers={"User-Agent": "ORACLE-model-free-longevity-audit/1.0"})
    with urlopen(request, timeout=180) as response, path.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.stat().st_size != EXPECTED_BYTES or digest != EXPECTED_SHA256:
        raise RuntimeError(
            f"RIKEN metadata mirror checksum/size mismatch: bytes={path.stat().st_size}, sha256={digest}"
        )

    frame = pd.read_parquet(path)
    report = {
        "status": "METADATA_SCHEMA_PROBED",
        "source_url": URL,
        "expected_bytes": EXPECTED_BYTES,
        "actual_bytes": path.stat().st_size,
        "sha256": digest,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "dtypes": {str(k): str(v) for k, v in frame.dtypes.items()},
        "preview": frame.head(20).astype(object).where(pd.notna(frame.head(20)), None).to_dict(orient="records"),
        "unique_values": {
            str(col): frame[col].dropna().astype(str).unique().tolist()[:100]
            for col in frame.columns
            if frame[col].nunique(dropna=True) <= 100
        },
    }
    (out / "metadata_probe.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "rows", "columns", "dtypes", "unique_values")}, indent=2))


if __name__ == "__main__":
    main()
