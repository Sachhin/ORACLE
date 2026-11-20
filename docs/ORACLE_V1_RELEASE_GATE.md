# ORACLE v1.0 release verification — model-free scope

The release gate checks the deterministic research engine and its scientific evidence boundaries. It does not require or evaluate an AI model.

## Inputs

- --ci-summary: JSON object with required_checks containing offline_tests, geo, and riken2018, each set to success.
- --geo-report: completed source-backed GEO analysis report for GSE58137 and GSE65219, with valid age parsing and no unreviewed workflow failures.
- --cra-audit: public CRA000515 metadata acquisition audit. The gate separately reports accession-level provenance and the still-required age/cohort-label authentication.
- --pxd-audit: optional output from scripts/validate_pxd047528_clinical_manifest.py. PXD047528 is an HIV/herpes plasma-proteomics dataset, not a longevity cohort; its clinical crosswalk is reported under optional_checks and cannot block the longevity release. Its paired DDA/DIA missingness benchmark is a separate technical-method result.
- --longevity-audit: independent evidence audit. It must preserve the distinction between exploratory associations, mixed/non-replication results, and validated discoveries.
- --expert-review: frozen independent reviewer summary. At least two real reviewers, a frozen paired corpus, blinded scoring, and completed adjudication are required for this gate.

## Run

    python scripts/verify_v1_release.py --ci-summary artifacts/ci_summary.json --geo-report artifacts/human_aging_geo_candidate_gene_report.json --cra-audit artifacts/CRA000515.metadata_audit.json --pxd-audit artifacts/clinical_crosswalk_audit.json --longevity-audit artifacts/longevity_independent_audit.json --expert-review artifacts/blinded_expert_review_summary.json --output artifacts/oracle_v1_release_gate.json

The command exits non-zero and writes a per-gate BLOCKED report if required evidence is absent. It does not create a GitHub release or tag.

A passing engineering gate does not prove that ORACLE is a validated autonomous scientist. Novelty, causality, and clinical relevance require independent biological replication and real expert review.


## Required versus optional evidence

The core longevity release gate requires six checks: critical CI, GEO metadata/numerical audit, CRA000515 accession provenance, CRA000515 authenticated age/cohort labels, conservative longevity claim scope, and independent blinded expert review.

PXD047528 is **not** a longevity cohort. Its HIV/herpes clinical outcome crosswalk is an optional, separate clinical reconstruction task. Missing PXD047528 patient mapping must appear in `optional_checks` as `NOT_REQUIRED_FOR_LONGEVITY_RELEASE`, not as a core release blocker. The paired DDA/DIA missingness benchmark can be reported independently without assigning patient identities or clinical outcomes.

A `READY_FOR_V1_TAG` result remains an engineering release decision only; it does not claim a novel longevity mechanism or causal discovery.
