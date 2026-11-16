#!/usr/bin/env python3
"""Verify and inspect the public RIKEN SC2018 processed H5AD mirror."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

import anndata as ad
import pandas as pd

URL = "https://huggingface.co/datasets/longevity-db/riken2018/resolve/main/riken2018_processed.h5ad"
EXPECTED_SHA256 = "2b0ce324e3cf29363a68689ac8772f122221728a11db0a3e50314c2e0b06553a"


def main() -> None:
    out = Path("artifacts/riken2018-h5ad")
    out.mkdir(parents=True, exist_ok=True)
    path = out / "riken2018_processed.h5ad"
    req = Request(URL, headers={"User-Agent": "ORACLE-model-free-longevity-audit/1.0"})
    digest = hashlib.sha256()
    with urlopen(req, timeout=1200) as response, path.open("wb") as handle:
        while True:
            chunk = response.read(8 * 1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != EXPECTED_SHA256:
        raise RuntimeError(f"H5AD checksum mismatch: expected {EXPECTED_SHA256}, got {actual}")

    adata = ad.read_h5ad(path, backed="r")
    obs = adata.obs
    var = adata.var
    report = {
        "status": "H5AD_CHECKSUM_VERIFIED_SCHEMA_INSPECTED",
        "source_url": URL,
        "bytes": path.stat().st_size,
        "sha256": actual,
        "shape": [int(adata.n_obs), int(adata.n_vars)],
        "obs_rows": int(len(obs)),
        "obs_columns": list(obs.columns),
        "obs_dtypes": {str(k): str(v) for k, v in obs.dtypes.items()},
        "obs_unique_values": {
            str(col): obs[col].dropna().astype(str).unique().tolist()[:100]
            for col in obs.columns
            if obs[col].nunique(dropna=True) <= 100
        },
        "var_columns": list(var.columns),
        "var_dtypes": {str(k): str(v) for k, v in var.dtypes.items()},
        "var_names_preview": [str(x) for x in var.index[:30]],
        "var_symbol_candidates": {
            col: var[col].dropna().astype(str).unique().tolist()[:30]
            for col in ("gene_name", "gene_symbol", "gene_symbols", "symbol", "feature_name", "gene_ids")
            if col in var.columns
        },
        "matrix_is_backed": bool(adata.isbacked),
        "limitations": [
            "Schema inspection only; no expression analysis or differential-expression result is produced.",
            "Donor-level pseudobulk must use patient as the biological replicate, never individual cells as independent samples.",
            "The community mirror's published SHA-256 is verified; the original RIKEN source remains the primary provenance reference."
        ],
    }
    (out / "h5ad_schema.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    adata.file.close()
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
