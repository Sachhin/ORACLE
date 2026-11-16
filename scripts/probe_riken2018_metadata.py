#!/usr/bin/env python3
"""Inspect source-checksummed RIKEN 2018 supercentenarian metadata and H5AD schema.

This is a provenance/schema probe only. It does not infer participant labels.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

import anndata as ad
import pandas as pd

METADATA_URL = "https://huggingface.co/datasets/longevity-db/riken2018/resolve/main/riken2018/sample_metadata.parquet"
METADATA_SHA256 = "40884e40921bb32ecde184085bcb3240f10f790bab85a9a246302c0a3a842798"
METADATA_BYTES = 622904
H5AD_URL = "https://huggingface.co/datasets/longevity-db/riken2018/resolve/main/riken2018_processed.h5ad"
H5AD_SHA256 = "2b0ce324e3cf29363a68689ac8772f122221728a11db0a3e50314c2e0b06553a"


def download_and_hash(url: str, path: Path) -> str:
    request = Request(url, headers={"User-Agent": "ORACLE-model-free-longevity-audit/1.0"})
    digest = hashlib.sha256()
    with urlopen(request, timeout=600) as response, path.open("wb") as handle:
        while True:
            chunk = response.read(4 * 1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def small_unique(series: pd.Series, limit: int = 100):
    values = series.dropna().astype(str).unique().tolist()
    return values if len(values) <= limit else values[:limit]


def main() -> None:
    out = Path("artifacts/riken2018")
    out.mkdir(parents=True, exist_ok=True)

    metadata_path = out / "sample_metadata.parquet"
    metadata_hash = download_and_hash(METADATA_URL, metadata_path)
    if metadata_path.stat().st_size != METADATA_BYTES or metadata_hash != METADATA_SHA256:
        raise RuntimeError(
            f"RIKEN metadata mirror checksum/size mismatch: bytes={metadata_path.stat().st_size}, sha256={metadata_hash}"
        )
    metadata = pd.read_parquet(metadata_path)

    h5ad_path = out / "riken2018_processed.h5ad"
    h5ad_hash = download_and_hash(H5AD_URL, h5ad_path)
    if h5ad_hash != H5AD_SHA256:
        raise RuntimeError(f"RIKEN H5AD checksum mismatch: sha256={h5ad_hash}")

    adata = ad.read_h5ad(h5ad_path, backed="r")
    obs = adata.obs
    var = adata.var
    obs_columns = list(obs.columns)
    var_columns = list(var.columns)

    obs_summary = {}
    for col in obs_columns:
        values = small_unique(obs[col])
        if len(values) <= 100:
            obs_summary[col] = values

    patient_col = next((c for c in ("patient", "patient_id", "sample_id", "donor", "donor_id") if c in obs), None)
    group_col = next((c for c in ("centenarian_status", "group", "condition", "status") if c in obs), None)
    donor_counts = None
    if patient_col and group_col:
        grouped = obs.groupby([patient_col, group_col], observed=False).size()
        donor_counts = [
            {"patient": str(index[0]), "group": str(index[1]), "cells": int(count)}
            for index, count in grouped.items()
        ]

    report = {
        "status": "SOURCE_CHECKSUMS_VERIFIED_SCHEMA_PROBED",
        "metadata_source_url": METADATA_URL,
        "metadata_bytes": metadata_path.stat().st_size,
        "metadata_sha256": metadata_hash,
        "metadata_rows": int(len(metadata)),
        "metadata_columns": list(metadata.columns),
        "metadata_unique_values": {
            str(col): small_unique(metadata[col])
            for col in metadata.columns
            if len(small_unique(metadata[col])) <= 100
        },
        "h5ad_source_url": H5AD_URL,
        "h5ad_bytes": h5ad_path.stat().st_size,
        "h5ad_sha256": h5ad_hash,
        "h5ad_shape": [int(adata.n_obs), int(adata.n_vars)],
        "h5ad_obs_rows": int(len(obs)),
        "h5ad_obs_columns": obs_columns,
        "h5ad_obs_unique_values": obs_summary,
        "h5ad_var_columns": var_columns,
        "h5ad_var_names_preview": [str(x) for x in var.index[:20]],
        "donor_cell_counts": donor_counts,
        "metadata_vs_h5ad_obs_row_count_equal": len(metadata) == len(obs),
        "symbol_column_candidates": [
            c for c in ("gene_name", "gene_symbol", "gene_symbols", "symbol", "feature_name")
            if c in var.columns
        ],
        "limitations": [
            "This is a community mirror of the RIKEN 2018 dataset, not the original repository host; source checksums are verified against the public mirror's published Xet/LFS metadata.",
            "The metadata parquet and H5AD observation metadata must be reconciled before any per-donor expression analysis.",
            "No mRPG differential-expression result is produced by this schema probe."
        ],
    }
    (out / "metadata_probe.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    adata.file.close()
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
