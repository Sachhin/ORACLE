#!/usr/bin/env python3
"""Validate frozen, artifact-derived 8-mRPG statistics and regulator evidence labels.

This checks provenance-linked summaries and statistical invariants. It does not
recompute statistics from raw matrices; the corresponding source workflows do that.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ["MRPL3", "MRPL32", "MRPL42", "MRPL45", "MRPL50", "MRPS10", "MRPS33", "MRPS35"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/missions/longevity/numerical_audit_snapshot.json")
    parser.add_argument("--output", default="artifacts/longevity/numerical_validation_report.json")
    args = parser.parse_args()
    data = json.loads((ROOT / args.input).read_text(encoding="utf-8"))
    checks = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    signature = data.get("published_signature", {})
    check("exact_published_8_mRPG_gene_panel", signature.get("genes") == EXPECTED,
          f"observed={signature.get('genes')}")
    datasets = {row.get("accession"): row for row in data.get("datasets", [])}
    gse = datasets.get("GSE16717", {})
    check("GSE16717_complete_sample_and_panel_metadata",
          gse.get("n") == 150 and gse.get("age_available_n") == 150
          and gse.get("sex_available_n") == 150 and gse.get("mRPG8_complete") is True,
          f"n={gse.get('n')}; age_n={gse.get('age_available_n')}; sex_n={gse.get('sex_available_n')}; complete={gse.get('mRPG8_complete')}")
    gse_genes = gse.get("mRPG8_gene_results_long_lived_vs_control", [])
    check("GSE16717_has_exactly_eight_gene_level_results",
          [x.get("gene") for x in gse_genes] == EXPECTED,
          f"gene_count={len(gse_genes)}")
    check("GSE16717_no_gene_level_FDR_signal",
          len(gse_genes) == 8 and all(float(x.get("fdr", 1)) >= 0.05 for x in gse_genes),
          "All eight long-lived-sibling versus control mRPG gene FDR values must be >= 0.05.")
    check("GSE16717_composite_not_significant_and_age_ranges_nonoverlap",
          abs(float(gse.get("mRPG8_welch_p", 1)) - 0.3159219781669193) < 1e-9
          and float(gse.get("mRPG8_bh_q", 1)) >= 0.05
          and gse.get("age_support_overlap_between_long_lived_and_controls") is False,
          f"p={gse.get('mRPG8_welch_p')}; q={gse.get('mRPG8_bh_q')}; age_overlap={gse.get('age_support_overlap_between_long_lived_and_controls')}")

    riken = datasets.get("RIKEN_SC2018", {})
    check("RIKEN_donor_level_design_and_complete_panel",
          riken.get("donors") == {"supercentenarians": 7, "controls": 5}
          and riken.get("biological_replicate") == "donor"
          and riken.get("mRPG8_genes_present") == 8
          and riken.get("mRPG8_genes_missing") == [],
          f"donors={riken.get('donors')}; genes_present={riken.get('mRPG8_genes_present')}")
    for field in ("gene_results_all_batches", "gene_results_firstrun_only"):
        rows = riken.get(field, [])
        check(f"RIKEN_{field}_contains_exact_8_genes",
              [x.get("gene") for x in rows] == EXPECTED,
              f"gene_count={len(rows)}")
        check(f"RIKEN_{field}_no_gene_level_FDR_signal",
              len(rows) == 8 and all(float(x.get("fdr", 1)) >= 0.05 for x in rows),
              "All eight gene-wise edgeR FDR values must be >= 0.05.")
    loo = riken.get("common_batch_leave_one_donor_out_p_range", [])
    check("RIKEN_common_batch_LOO_sensitivity_is_preserved",
          len(loo) == 2 and abs(float(loo[0]) - 0.0182) < 1e-9
          and abs(float(loo[1]) - 0.1061) < 1e-9
          and riken.get("common_batch_leave_one_donor_out_nominal_p_below_0_05") == 6,
          f"p_range={loo}; nominal_p_below_0.05={riken.get('common_batch_leave_one_donor_out_nominal_p_below_0_05')}")
    check("no_invalid_cross_dataset_pooling",
          data.get("cross_dataset_pooling", {}).get("status") == "NOT_PERFORMED",
          data.get("cross_dataset_pooling", {}).get("reason", "missing pooling rationale"))
    candidates = {x.get("candidate"): x for x in data.get("upstream_regulator_screen", [])}
    check("ETS1_not_misrepresented_as_direct_mRPG_regulator",
          candidates.get("ETS1", {}).get("status") == "INDIRECT_PRIOR_ART_CANDIDATE_ONLY"
          and candidates.get("ETS1", {}).get("relationship_to_8_mRPG") == "NOT_DIRECTLY_TESTED",
          str(candidates.get("ETS1", {})))
    check("MRPS5_not_misrepresented_as_upstream_regulator",
          candidates.get("MRPS5", {}).get("status") == "FUNCTIONAL_PATHWAY_CONTEXT_ONLY"
          and candidates.get("MRPS5", {}).get("relationship_to_8_mRPG") == "NOT_A_PROVEN_UPSTREAM_REGULATOR",
          str(candidates.get("MRPS5", {})))

    failed = [x for x in checks if x["status"] != "PASS"]
    report = {
        "status": "PASS" if not failed else "FAIL",
        "validation_type": "artifact_summary_integrity_not_raw_matrix_recomputation",
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "checks": checks,
        "scientific_conclusion": "Mixed/non-replication evidence; no validated new human longevity mechanism.",
    }
    target = ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
