#!/usr/bin/env python3
"""Conservative ORACLE v1.0 release gate over frozen validation artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: str) -> dict[str, Any]:
    if not path:
        raise ValueError("required artifact path was not supplied")
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def verify(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"gate": name, "status": "PASS" if passed else "BLOCKED", "detail": detail})

    try:
        ci = load_json(args.ci_summary)
        required = ci.get("required_checks", {})
        expected = {"offline_tests", "geo", "qwen3"}
        ci_ok = expected.issubset(required) and all(required.get(key) == "success" for key in expected)
        add("release_critical_ci", ci_ok, f"required={sorted(expected)}; observed={required}")
    except Exception as exc:
        add("release_critical_ci", False, str(exc))

    try:
        report = load_json(args.qwen_report)
        run = report.get("prediction_run", {})
        provenance = load_json(args.qwen_provenance)
        qwen_ok = (
            report.get("scored_claim_count") == 300
            and float(report.get("prediction_coverage", 0)) == 1.0
            and run.get("requested_claims") == 300
            and run.get("gold_evidence_exposed_to_model") is False
            and bool(run.get("predictions_sha256"))
            and bool(run.get("corpus_sha256"))
            and bool(run.get("claims_sha256"))
            and bool(provenance.get("model_sha256"))
            and provenance.get("download_sha256_verified") is True
            and provenance.get("model_sha256") == provenance.get("verified_model_sha256")
        )
        add("qwen3_full_frozen_benchmark", qwen_ok,
            f"scored={report.get('scored_claim_count')}/300; coverage={report.get('prediction_coverage')}; "
            f"invalid={run.get('invalid_model_response_count')}; model={run.get('model')}")
    except Exception as exc:
        add("qwen3_full_frozen_benchmark", False, str(exc))

    try:
        geo = load_json(args.geo_report)
        cohorts = geo.get("successful_platforms", [])
        accessions = set(geo.get("accessions_requested", []))
        all_ages_valid = all(
            float(item.get("age_max_years", 0) or 0) <= 120
            and int(item.get("invalid_age_samples", 0) or 0) == 0
            for item in cohorts
        )
        geo_ok = (
            geo.get("status") == "EXPLORATORY_ANALYSIS_COMPLETE"
            and not geo.get("failures")
            and {"GSE58137", "GSE65219"}.issubset(accessions)
            and len(cohorts) >= 2
            and all_ages_valid
        )
        add("geo_numerical_metadata_audit", geo_ok,
            f"status={geo.get('status')}; platforms={len(cohorts)}; failures={len(geo.get('failures', []))}; all_ages_valid={all_ages_valid}")
    except Exception as exc:
        add("geo_numerical_metadata_audit", False, str(exc))

    try:
        cra = load_json(args.cra_audit)
        design = cra.get("cohort_design_check", {})
        join = cra.get("biosample_join", {})
        enrichment = cra.get("biosample_page_enrichment", {})
        cra_ok = (
            cra.get("status") in {"cohort_manifest_validated", "metadata_acquired_and_cohort_validated"}
            and design.get("all_expected_group_labels_explicitly_present") is True
            and join.get("unmatched_runs", 1) == 0
            and enrichment.get("samples_with_age", 0) >= 150
        )
        add("cra000515_cohort_provenance", cra_ok,
            f"status={cra.get('status')}; explicit_groups={design.get('all_expected_group_labels_explicitly_present')}; "
            f"unmatched_runs={join.get('unmatched_runs')}; samples_with_age={enrichment.get('samples_with_age')}")
    except Exception as exc:
        add("cra000515_cohort_provenance", False, str(exc))

    try:
        pxd = load_json(args.pxd_audit)
        pxd_ok = (
            pxd.get("status") == "PROVENANCE_VALIDATED_READY_FOR_OUTCOME_ANALYSIS"
            and pxd.get("alias_count") == 15
            and pxd.get("distinct_patient_count") == 13
            and not pxd.get("errors")
        )
        add("pxd047528_clinical_crosswalk", pxd_ok,
            f"status={pxd.get('status')}; aliases={pxd.get('alias_count')}; patients={pxd.get('distinct_patient_count')}")
    except Exception as exc:
        add("pxd047528_clinical_crosswalk", False, str(exc))

    try:
        longevity = load_json(args.longevity_audit)
        longevity_ok = (
            longevity.get("overall_assessment") == "screening_only_no_validated_discovery"
            and "hypothesis_reviews" in longevity
            and "gates" in longevity
        )
        add("longevity_claim_scope_audit", longevity_ok,
            f"assessment={longevity.get('overall_assessment')}; discovery claims must remain unvalidated unless independently replicated")
    except Exception as exc:
        add("longevity_claim_scope_audit", False, str(exc))

    try:
        expert = load_json(args.expert_review)
        reviewers = expert.get("reviewers", [])
        completed = [r for r in reviewers if r.get("status") == "completed" and r.get("frozen_score_file_sha256")]
        expert_ok = (
            len({r.get("reviewer_id") for r in completed if r.get("reviewer_id")}) >= 2
            and expert.get("blinded") is True
            and expert.get("paired_corpus_frozen") is True
            and expert.get("adjudication_complete") is True
        )
        add("independent_blinded_expert_review", expert_ok,
            f"completed_reviewers={len(completed)}; blinded={expert.get('blinded')}; adjudication={expert.get('adjudication_complete')}")
    except Exception as exc:
        add("independent_blinded_expert_review", False, str(exc))

    blocked = [item for item in checks if item["status"] != "PASS"]
    return {
        "release_gate_version": "1.0",
        "status": "READY_FOR_V1_TAG" if not blocked else "BLOCKED",
        "passed_gate_count": len(checks) - len(blocked),
        "total_gate_count": len(checks),
        "checks": checks,
        "release_note": (
            "A passing engineering gate does not establish that ORACLE is a validated autonomous scientist. "
            "Scientific novelty and causality require independent replication and human review."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ci-summary", "qwen-report", "qwen-provenance", "geo-report",
                 "cra-audit", "pxd-audit", "longevity-audit", "expert-review"):
        parser.add_argument("--" + name, default="", help=f"Path to frozen {name} JSON artifact")
    parser.add_argument("--output", default="artifacts/oracle_v1_release_gate.json")
    args = parser.parse_args()
    report = verify(args)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "READY_FOR_V1_TAG" else 2


if __name__ == "__main__":
    raise SystemExit(main())
