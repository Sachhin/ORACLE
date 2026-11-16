# ORACLE v1.0 release verification — model-free scope

The release gate checks the deterministic research engine and its scientific evidence boundaries. It does not require or evaluate an AI model.

## Inputs

- --ci-summary: JSON object with required_checks containing offline_tests, geo, and riken2018, each set to success.
- --geo-report: completed source-backed GEO analysis report for GSE58137 and GSE65219, with valid age parsing and no unreviewed workflow failures.
- --cra-audit: public CRA000515 metadata acquisition audit. The gate separately reports accession-level provenance and the still-required age/cohort-label authentication.
- --pxd-audit: output from scripts/validate_pxd047528_clinical_manifest.py; clinical outcome validation remains blocked until a source-authenticated manifest is supplied.
- --longevity-audit: independent evidence audit. It must preserve the distinction between exploratory associations, mixed/non-replication results, and validated discoveries.
- --expert-review: frozen independent reviewer summary. At least two real reviewers, a frozen paired corpus, blinded scoring, and completed adjudication are required for this gate.

## Run

    python scripts/verify_v1_release.py --ci-summary artifacts/ci_summary.json --geo-report artifacts/human_aging_geo_candidate_gene_report.json --cra-audit artifacts/CRA000515.metadata_audit.json --pxd-audit artifacts/clinical_crosswalk_audit.json --longevity-audit artifacts/longevity_independent_audit.json --expert-review artifacts/blinded_expert_review_summary.json --output artifacts/oracle_v1_release_gate.json

The command exits non-zero and writes a per-gate BLOCKED report if required evidence is absent. It does not create a GitHub release or tag.

A passing engineering gate does not prove that ORACLE is a validated autonomous scientist. Novelty, causality, and clinical relevance require independent biological replication and real expert review.
