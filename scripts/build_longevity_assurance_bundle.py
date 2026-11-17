#!/usr/bin/env python3
"""Freeze the source-backed longevity prior-art seed into an ORACLE assurance bundle.

This adapter deliberately keeps previously reported numerical audits as provenance
records rather than coercing unlike endpoints into a cross-dataset meta-analysis.
It performs no network access and invokes no model/API.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build(seed_path: Path, audit_path: Path, quality_path: Path, validation_path: Path) -> dict[str, Any]:
    seed = load(seed_path)
    if seed.get("mission_id") != "human-longevity":
        raise ValueError("Unexpected mission_id in prior-art seed")
    sources = seed.get("sources", [])
    if not isinstance(sources, list) or not sources:
        raise ValueError("Prior-art seed has no source records")
    source_ids = {row.get("source_id") for row in sources if row.get("source_id")}
    evidence, claims, links = [], [], []
    for source in sources:
        sid = source["source_id"]
        for index, statement in enumerate(source.get("claims", []), start=1):
            eid, cid = f"ev:{sid}:{index}", f"claim:{sid}:{index}"
            evidence.append({"evidence_id": eid, "source_id": sid, "kind": "source",
                             "claim": statement, "locator": source.get("url") or source.get("doi")})
            claims.append({"claim_id": cid, "statement": statement})
            links.append({"claim_id": cid, "evidence_id": eid, "strength": 1.0})
    hypotheses = []
    for index, item in enumerate(seed.get("hypothesis_audit", []), start=1):
        support = [f"ev:{sid}:1" for sid in item.get("supporting_prior_art", []) if sid in source_ids]
        opposition = [f"ev:{sid}:1" for sid in item.get("opposing_or_qualifying_evidence", []) if sid in source_ids]
        hypotheses.append({"hypothesis_id": item.get("id", f"H{index}"),
                            "statement": item.get("statement", ""),
                            "supporting_evidence_ids": support,
                            "opposing_evidence_ids": opposition,
                            "predictions": item.get("falsifiable_tests", [])})
    numerical_audit = load(audit_path)
    validation = load(validation_path)
    if numerical_audit.get("status") != "EXPLORATORY_MIXED_NO_VALIDATED_DISCOVERY":
        raise ValueError("Numerical audit status is missing or unexpected")
    if validation.get("status") != "PASS":
        raise ValueError("Artifact-backed numerical snapshot validation did not pass")
    quality_text = quality_path.read_text(encoding="utf-8")
    if "Differential-expression analyses | 0" not in quality_text:
        raise ValueError("Frozen mission quality audit no longer matches expected zero-DE baseline")
    frozen = (seed_path, audit_path, quality_path, validation_path)
    return {
        "bundle_schema": "oracle-frozen-longevity-assurance/1.1",
        "mission_id": "human-longevity",
        "freeze_policy": "No network calls; preserve source IDs; do not infer missing labels; do not pool incompatible cohort endpoints.",
        "frozen_inputs": {str(path.relative_to(ROOT)): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in frozen},
        "sources": sources, "evidence": evidence, "claims": claims, "evidence_claim_links": links,
        "hypotheses": hypotheses, "prior_art": sources,
        "differential_expression_analyses": [], "dataset_analyses": [],
        "numerical_audit_snapshot": numerical_audit,
        "numerical_validation_report": validation,
        "baseline_mission_quality_audit": {
            "path": str(quality_path.relative_to(ROOT)), "sha256": sha256(quality_path),
            "known_limitation": "The original frozen research run had zero differential-expression and zero dataset analyses; separate GSE16717 and RIKEN SC2018 audits are not silently merged into that historical run."
        },
        "external_blockers": {
            "CRA000515_individual_age_and_cohort_manifest": "BLOCKED_SOURCE_AUTHENTICATION_REQUIRED",
            "PXD047528_15_alias_to_13_participant_crosswalk": "BLOCKED_SOURCE_AUTHENTICATION_REQUIRED",
            "independent_blinded_expert_reviews": "PENDING_REAL_REVIEWERS"
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", default="data/missions/longevity/prior_art_seed.json")
    parser.add_argument("--numerical-audit", default="data/missions/longevity/numerical_audit_snapshot.json")
    parser.add_argument("--quality-audit", default="artifacts/longevity/run_a19934cc2692_quality_audit.md")
    parser.add_argument("--numerical-validation", default="artifacts/longevity/numerical_validation_report.json")
    parser.add_argument("--output", default="artifacts/longevity/frozen_assurance_bundle.json")
    args = parser.parse_args()
    bundle = build(ROOT / args.seed, ROOT / args.numerical_audit, ROOT / args.quality_audit, ROOT / args.numerical_validation)
    target = ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(bundle, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "FROZEN", "output": str(target.relative_to(ROOT)),
                      "source_count": len(bundle["sources"]), "evidence_count": len(bundle["evidence"]),
                      "claim_count": len(bundle["claims"]), "hypothesis_count": len(bundle["hypotheses"]),
                      "differential_expression_analyses": 0, "frozen_inputs": bundle["frozen_inputs"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
