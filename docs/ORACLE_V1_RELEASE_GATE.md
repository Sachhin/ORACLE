# ORACLE v1.0 release verification

The release gate is intentionally conservative. It reads frozen JSON artifacts
and never treats workflow creation, a proposed experiment, or an inferred
clinical label as validation.

## Inputs

- `--ci-summary`: JSON object with `required_checks` containing `offline_tests`,
  `geo`, and `qwen3`, each set to `success`.
- `--qwen-report` and `--qwen-provenance`: frozen 300-claim SciFact report,
  prediction/input hashes, and pinned model provenance.
- `--geo-report`: complete GEO report for GSE58137 and GSE65219, with no
  invalid ages or unreviewed failures.
- `--cra-audit`: complete CRA000515 cohort-level source metadata audit with
  explicit group labels, complete BioSample joins, and age metadata.
- `--pxd-audit`: output from
  `scripts/validate_pxd047528_clinical_manifest.py`.
- `--longevity-audit`: output from `oracle.quality_audit`. It must preserve
  the distinction between literature screening and validated discovery.
- `--expert-review`: frozen independent reviewer summary. It must identify at
  least two completed reviewers, a frozen paired corpus, blinded scoring, and
  completed adjudication.

## Run

```bash
python scripts/verify_v1_release.py \
  --ci-summary artifacts/ci_summary.json \
  --qwen-report artifacts/qwen3_300_claim_report.json \
  --qwen-provenance artifacts/model_provenance.json \
  --geo-report artifacts/human_aging_geo_candidate_gene_report.json \
  --cra-audit artifacts/CRA000515.metadata_audit.json \
  --pxd-audit artifacts/clinical_crosswalk_audit.json \
  --longevity-audit artifacts/oracle_quality_audit.json \
  --expert-review artifacts/blinded_expert_review_summary.json \
  --output artifacts/oracle_v1_release_gate.json
```

The command exits non-zero and writes a per-gate BLOCKED report if any
acceptance criterion is missing. It does not create a GitHub release or tag.

A passing v1.0 engineering gate still does not prove that ORACLE is a validated
autonomous scientist. Novelty, causal mechanisms, and clinical relevance
require independent biological replication and real expert review.
