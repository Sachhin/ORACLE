#!/usr/bin/env python3
"""Build provenance-labelled release inputs and execute ORACLE's v1.0 gate.

Inputs are frozen summaries of named successful Actions artifacts and dated audit
documents. Missing authenticated manifests/reviews remain explicit blockers.
"""
from __future__ import annotations
import json
from argparse import Namespace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_v1_release import verify


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    out = ROOT / "artifacts/longevity/release_gate_inputs"
    ci = {
        "required_checks": {"offline_tests": "success", "geo": "success", "riken2018": "success"},
        "provenance": {
            "offline_tests_run_id": 44043297155,
            "geo_run_id": 43914355105,
            "geo_artifact_id": 14249224272,
            "riken2018_run_id": 43911857872,
            "riken2018_artifact_id": 14248282108,
            "note": "These are completed GitHub Actions runs/artifacts inspected for this release-gate snapshot."
        }
    }
    geo = {
        "status": "EXPLORATORY_ANALYSIS_COMPLETE",
        "accessions_requested": ["GSE58137", "GSE65219"],
        "failures": [],
        "successful_platforms": [
            {"accession": "GSE58137", "platform": "GPL10558", "samples_analyzed": 106, "age_max_years": 62.5, "invalid_age_samples": 0},
            {"accession": "GSE58137", "platform": "GPL6947", "samples_analyzed": 253, "age_max_years": 77.8453, "invalid_age_samples": 0},
            {"accession": "GSE65219", "platform": "GPL15988", "samples_analyzed": 176, "age_max_years": 90, "invalid_age_samples": 0}
        ],
        "provenance": {"workflow_run_id": 43914355105, "artifact_id": 14249224272,
                       "scope_note": "This GEO run evaluates a separate autophagy/lysosomal/inflammatory panel, not the 8-mRPG signature."}
    }
    cra = {
        "unique_run_count": 171,
        "unique_biosample_count": 171,
        "biosample_page_enrichment": {"retrieved_unique_biosamples": 171, "samples_with_age": 0},
        "cohort_design_check": {"all_expected_group_labels_explicitly_present": False},
        "status": "metadata_acquired_needs_manual_provenance_review",
        "provenance": {"audit_document": "docs/CRA000515_PUBLIC_METADATA_AUDIT_2026-11-16.md",
                       "workflow_run_id": 43874634708, "artifact_id": 14228789805}
    }
    pxd = {
        "status": "BLOCKED_SOURCE_AUTHENTICATION_REQUIRED",
        "alias_count": 15,
        "distinct_patient_count": 13,
        "errors": ["No source-authenticated alias-to-clinical-participant crosswalk; do not infer identities or outcomes."],
        "provenance": {"audit_document": "docs/PXD047528_RECONSTRUCTION_AUDIT_2026-11-16.md",
                       "workflow_run_id": 43884078275, "artifact_id": 14233687625}
    }
    longevity = {
        "overall_assessment": "screening_only_no_validated_discovery",
        "validated_new_mechanism_count": 0,
        "provenance": {"audit_document": "docs/LONGEVITY_INDEPENDENT_EVIDENCE_AUDIT_2026-11-16.md",
                       "numerical_snapshot": "data/missions/longevity/numerical_audit_snapshot.json"}
    }
    expert = {
        "reviewers": [], "blinded": False, "paired_corpus_frozen": False, "adjudication_complete": False,
        "status": "AWAITING_INDEPENDENT_REVIEWERS",
        "provenance": {"brief": "docs/LONGEVITY_EXPERT_REVIEW_BRIEF.md"}
    }
    paths = {
        "ci": out / "ci_summary.json", "geo": out / "geo_report.json",
        "cra": out / "cra_audit.json", "pxd": out / "pxd_audit.json",
        "longevity": out / "longevity_audit.json", "expert": out / "expert_review.json"
    }
    for key, value in (("ci", ci), ("geo", geo), ("cra", cra), ("pxd", pxd),
                       ("longevity", longevity), ("expert", expert)):
        write(paths[key], value)

    report = verify(Namespace(
        ci_summary=str(paths["ci"]), geo_report=str(paths["geo"]),
        cra_audit=str(paths["cra"]), pxd_audit=str(paths["pxd"]),
        longevity_audit=str(paths["longevity"]), expert_review=str(paths["expert"])
    ))
    report["input_provenance"] = {key: str(path.relative_to(ROOT)) for key, path in paths.items()}
    target = ROOT / "artifacts/longevity/oracle_v1_release_gate.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    blocked = [row["gate"] for row in report["checks"] if row["status"] == "BLOCKED"]
    expected = {"cra000515_authenticated_age_and_cohort_labels",
                "independent_blinded_expert_review"}
    if report["status"] != "BLOCKED" or set(blocked) != expected:
        raise SystemExit(f"Unexpected release-gate result: status={report['status']}; blocked={blocked}")
    optional = {row["gate"]: row["status"] for row in report.get("optional_checks", [])}
    print(json.dumps({"status": report["status"], "passed_gate_count": report["passed_gate_count"],
                      "total_gate_count": report["total_gate_count"], "blocked_gates": blocked,
                      "optional_checks": optional,
                      "report": str(target.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
