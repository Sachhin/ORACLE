#!/usr/bin/env python3
"""Build donor-level pseudobulk counts for RIKEN SC2018 from the verified H5AD."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

import h5py
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

H5AD_URL = "https://huggingface.co/datasets/longevity-db/riken2018/resolve/main/riken2018_processed.h5ad"
H5AD_SHA256 = "2b0ce324e3cf29363a68689ac8772f122221728a11db0a3e50314c2e0b06553a"
META_URL = "https://huggingface.co/datasets/longevity-db/riken2018/resolve/main/riken2018/sample_metadata.parquet"
META_SHA256 = "40884e40921bb32ecde184085bcb3240f10f790bab85a9a246302c0a3a842798"
META_BYTES = 622904


def download(url: str, path: Path) -> str:
    req = Request(url, headers={"User-Agent": "ORACLE-model-free-longevity-audit/1.0"})
    digest = hashlib.sha256()
    with urlopen(req, timeout=1200) as response, path.open("wb") as handle:
        while True:
            chunk = response.read(8 * 1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def decode_strings(values) -> list[str]:
    result = []
    for value in values:
        if isinstance(value, bytes):
            result.append(value.decode("utf-8"))
        else:
            result.append(str(value))
    return result


def categorical(h5: h5py.File, column: str):
    codes = h5[f"obs/{column}/codes"][:]
    categories = decode_strings(h5[f"obs/{column}/categories"][:])
    values = [categories[int(code)] if int(code) >= 0 else "" for code in codes]
    return codes, categories, values


def main() -> None:
    out = Path("artifacts/riken2018-mrpg")
    out.mkdir(parents=True, exist_ok=True)
    h5ad_path = out / "riken2018_processed.h5ad"
    meta_path = out / "sample_metadata.parquet"

    h5ad_hash = download(H5AD_URL, h5ad_path)
    if h5ad_hash != H5AD_SHA256:
        raise RuntimeError(f"H5AD SHA-256 mismatch: {h5ad_hash}")
    meta_hash = download(META_URL, meta_path)
    if meta_path.stat().st_size != META_BYTES or meta_hash != META_SHA256:
        raise RuntimeError(f"Metadata parquet checksum/size mismatch: bytes={meta_path.stat().st_size}, sha256={meta_hash}")

    metadata = pd.read_parquet(meta_path)
    with h5py.File(h5ad_path, "r") as h5:
        shape = tuple(int(x) for x in h5["X"].attrs["shape"])
        n_cells, n_genes = shape
        obs_index = decode_strings(h5["obs/_index"][:])
        gene_names = decode_strings(h5["var/_index"][:])
        patient_codes, patient_categories, patients = categorical(h5, "patient")
        _, group_categories, groups = categorical(h5, "centenarian_status")
        _, batch_categories, batches = categorical(h5, "batch")
        _, assay_categories, assays = categorical(h5, "assay_simple")
        _, cell_type_categories, cell_types = categorical(h5, "cell_type")

        if len(metadata) != n_cells or len(obs_index) != n_cells:
            raise RuntimeError(f"Metadata/H5AD row count mismatch: parquet={len(metadata)}, obs={n_cells}")
        for col, values in {
            "patient": patients,
            "centenarian_status": groups,
            "batch": batches,
            "assay_simple": assays,
            "cell_type": cell_types,
        }.items():
            if metadata[col].astype(str).tolist() != values:
                raise RuntimeError(f"Parquet and H5AD obs differ row-by-row for {col}")

        data = h5["X/data"][:]
        indices = h5["X/indices"][:]
        indptr = h5["X/indptr"][:]
        if np.any(data < 0) or not np.allclose(data, np.rint(data)):
            raise RuntimeError("H5AD X matrix is not non-negative integer-valued UMI counts")
        matrix = csr_matrix((data, indices, indptr), shape=shape, copy=False)

        donor_rows = []
        donor_counts = []
        donor_rows_firstrun = []
        donor_counts_firstrun = []
        for patient in patient_categories:
            rows = np.flatnonzero(np.asarray(patients) == patient)
            if len(rows) == 0:
                continue
            donor_groups = sorted(set(groups[i] for i in rows))
            if len(donor_groups) != 1:
                raise RuntimeError(f"Donor {patient} has inconsistent group labels: {donor_groups}")
            donor_batch = sorted(set(batches[i] for i in rows))
            total = np.asarray(matrix[rows].sum(axis=0)).ravel().astype(np.int64)
            donor_counts.append(total)
            donor_rows.append({
                "patient": patient,
                "group": donor_groups[0],
                "cells": int(len(rows)),
                "batch": ";".join(donor_batch),
                "assay": ";".join(sorted(set(assays[i] for i in rows))),
                "cell_type": ";".join(sorted(set(cell_types[i] for i in rows))),
                "library_size": int(total.sum()),
            })

            common_rows = rows[np.asarray(batches)[rows] == "firstrun"]
            if len(common_rows) == 0:
                raise RuntimeError(f"Donor {patient} has no cells in the common firstrun batch")
            common_total = np.asarray(matrix[common_rows].sum(axis=0)).ravel().astype(np.int64)
            donor_counts_firstrun.append(common_total)
            donor_rows_firstrun.append({
                "patient": patient,
                "group": donor_groups[0],
                "cells": int(len(common_rows)),
                "batch": "firstrun",
                "assay": ";".join(sorted(set(assays[i] for i in common_rows))),
                "cell_type": ";".join(sorted(set(cell_types[i] for i in common_rows))),
                "library_size": int(common_total.sum()),
            })

    donor_meta = pd.DataFrame(donor_rows)
    donor_meta_firstrun = pd.DataFrame(donor_rows_firstrun)
    for label, frame in (("all batches", donor_meta), ("firstrun only", donor_meta_firstrun)):
        if set(frame["group"]) != {"SC", "CT"}:
            raise RuntimeError(f"Unexpected RIKEN groups in {label}: {sorted(set(frame['group']))}")
        if int((frame.group == "SC").sum()) != 7 or int((frame.group == "CT").sum()) != 5:
            raise RuntimeError(f"Expected 7 SC and 5 CT donors in {label}, found {frame.group.value_counts().to_dict()}")
    if len(set(gene_names)) != len(gene_names):
        raise RuntimeError("Duplicate gene symbols in var index; resolve annotation before pseudobulk")

    counts = np.vstack(donor_counts).T
    counts_df = pd.DataFrame(counts, index=gene_names, columns=donor_meta["patient"].tolist())
    counts_df.index.name = "gene_symbol"
    counts_df.to_csv(out / "pseudobulk_counts.tsv", sep="\\t")
    donor_meta.to_csv(out / "donor_metadata.tsv", sep="\\t", index=False)

    counts_firstrun = np.vstack(donor_counts_firstrun).T
    counts_firstrun_df = pd.DataFrame(counts_firstrun, index=gene_names, columns=donor_meta_firstrun["patient"].tolist())
    counts_firstrun_df.index.name = "gene_symbol"
    counts_firstrun_df.to_csv(out / "pseudobulk_counts_firstrun.tsv", sep="\\t")
    donor_meta_firstrun.to_csv(out / "donor_metadata_firstrun.tsv", sep="\\t", index=False)

    report = {
        "status": "PSEUDOBULK_COUNTS_BUILT",
        "dataset": "RIKEN SC2018",
        "h5ad_url": H5AD_URL,
        "h5ad_sha256": h5ad_hash,
        "h5ad_bytes": h5ad_path.stat().st_size,
        "metadata_url": META_URL,
        "metadata_sha256": meta_hash,
        "metadata_bytes": meta_path.stat().st_size,
        "metadata_rows": int(len(metadata)),
        "h5ad_shape": [n_cells, n_genes],
        "parquet_h5ad_obs_metadata_rowwise_equal": True,
        "raw_umi_count_matrix_nonnegative_integer_verified": True,
        "gene_symbols_directly_in_var_index": True,
        "donors": donor_rows,
        "donor_counts": donor_meta.group.value_counts().to_dict(),
        "firstrun_only_donors": donor_rows_firstrun,
        "firstrun_only_donor_counts": donor_meta_firstrun.group.value_counts().to_dict(),
        "batch_sensitivity": "Primary comparison uses only firstrun cells shared by all 12 donors; all-batches aggregation is a secondary sensitivity analysis.",
        "mRPG8_genes": ["MRPL3", "MRPL32", "MRPL42", "MRPL45", "MRPL50", "MRPS10", "MRPS33", "MRPS35"],
        "mRPG8_genes_present": [
            gene for gene in ["MRPL3", "MRPL32", "MRPL42", "MRPL45", "MRPL50", "MRPS10", "MRPS33", "MRPS35"]
            if gene in gene_names
        ],
        "mRPG8_genes_missing": [
            gene for gene in ["MRPL3", "MRPL32", "MRPL42", "MRPL45", "MRPL50", "MRPS10", "MRPS33", "MRPS35"]
            if gene not in gene_names
        ],
        "obs_columns": ["patient", "centenarian_status", "batch", "assay_simple", "cell_type"],
        "individual_age_available": False,
        "individual_sex_available": False,
        "cell_type_resolution": sorted(set(cell_types)),
        "interpretation_limits": [
            "Patient is the biological replicate; 69,844 cells are not independent replicates.",
            "Only broad PBMC labels are present; cell-subtype deconvolution is unavailable.",
            "No individual age or sex is present in the matrix metadata. The source paper reports group-level means only.",
            "The cohort is small (7 supercentenarians, 5 controls) and has a large age difference; no individual-level age adjustment is possible.",
            "This is an independent Japanese cohort relative to the Chinese Hainan and Leiden datasets, but is reused across the 2019, 2023 and 2025 papers; count it once."
        ],
        "pseudobulk_counts_file": "pseudobulk_counts.tsv",
        "donor_metadata_file": "donor_metadata.tsv",
        "firstrun_pseudobulk_counts_file": "pseudobulk_counts_firstrun.tsv",
        "firstrun_donor_metadata_file": "donor_metadata_firstrun.tsv",
    }
    if report["mRPG8_genes_missing"]:
        raise RuntimeError(f"Missing mRPG genes in RIKEN var index: {report['mRPG8_genes_missing']}")
    (out / "pseudobulk_manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    # Source files are checksum-recorded above; keep the workflow artifact compact.
    h5ad_path.unlink()
    meta_path.unlink()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
