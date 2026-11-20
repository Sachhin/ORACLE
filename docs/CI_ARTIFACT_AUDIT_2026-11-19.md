# ORACLE CI artifact audit — 2026-11-19

## Scope and provenance

This note records direct inspection of GitHub Actions artifacts produced from PR #167 head `07e6eec12695d5beb63210abab3f766d673761b5`. It distinguishes workflow success from scientific validation.

## Completed workflow results

- Frozen longevity assurance, run [44473964999](https://github.com/Sachhin/ORACLE/actions/runs/44473964999): **SUCCESS**. Artifact `14505431875`, SHA-256 `ee97e7a37d9a86419e421321df5bb4a7eaa6a2735f9dd0fac826c2f8a059422c`.
- Mendeley public metadata probe, run [44473965096](https://github.com/Sachhin/ORACLE/actions/runs/44473965096): **SUCCESS as a probe**. Artifact `14505213712`, SHA-256 `5b25e4007c5a835bf2f8ef8d4c5f8cbcf2fa755404f4b5974438406588961a46`.
- Offline tests, run [44473964885](https://github.com/Sachhin/ORACLE/actions/runs/44473964885): all five Python versions (3.10–3.14) passed package tests/build/CLI smoke tests; RIKEN metadata provenance job passed; live R/Bioconductor reference-check job passed. At inspection, the workflow remained `in_progress` while the GEO candidate-analysis workflow was also still running.
- Human-aging GEO candidate analysis, run [44473964909](https://github.com/Sachhin/ORACLE/actions/runs/44473964909): still `in_progress`; package installation was running, analysis had not started. No result is claimed.

## Frozen assurance findings

The numerical validator reports 14/14 checks passed, but explicitly labels its validation type `artifact_summary_integrity_not_raw_matrix_recomputation`. This is not raw-matrix recomputation.

- GSE16717: n=150; eight published 8-mRPG genes present; zero gene-level FDR-significant results; composite p=0.3159219781669193 and q=0.6670988058260628; long-lived sibling and control age ranges do not overlap.
- RIKEN SC2018: 7 supercentenarian donors and 5 controls; eight genes present; no gene-level FDR signal. The common-batch leave-one-out composite p range remains 0.0182–0.1061, so the nominal signal is sensitivity-dependent.
- GSE16717 and RIKEN remain distinct estimands and must not be pooled as a single replicated effect.
- ETS1 remains indirect prior-art only; MRPS5 remains pathway context, not a proven upstream regulator.
- Scientific conclusion: mixed/non-replication evidence; zero validated new human longevity mechanisms.

The deterministic assurance report is `SCREEN_COMPLETE`, not a mechanism discovery. Cross-dataset validation is `NOT_RUN`; mechanism discovery has zero replicated candidates; novelty is `NOT_ESTABLISHED`; the skeptic pass is deterministic prompting, not independent peer review.

## Release gate

The frozen release gate remains **BLOCKED: 4/6 passed, 2/6 blocked**.

1. CRA000515 accession provenance: 171 runs and 171 BioSamples retrieved — accession-level acquisition passes.
2. CRA000515 authenticated individual ages/cohort labels: **BLOCKED** — zero samples with age and no explicit cohort labels. Public BioSample retrieval does not authenticate the phenotype manifest.
3. Independent blinded expert review: **BLOCKED** — zero completed reviewers, no blinded scoring, no frozen paired corpus and no adjudication.
4. PXD047528 alias-to-clinical crosswalk remains source-authentication blocked, but is explicitly optional and not required for the longevity release.

## Source-acquisition findings

### Mendeley dataset DOI 10.17632/fpf4y72kfz.1

The landing page returned HTTP 200 and identifies “Transcriptomic Analysis of Chinese Longevity Cohorts” (1,751 individuals: 811 long-lived and 940 younger controls). However, the dataset API, metadata endpoint and public-files endpoint each returned HTTP 401 Unauthorized. No expression matrix, file inventory, participant-level phenotype manifest or authenticated sample mapping was downloaded. The successful workflow means the limitation was reproducibly recorded, not that data were acquired.

### RIKEN SC2018 metadata

The source-checksummed metadata probe verified a 622,904-byte Parquet file with SHA-256 `40884e40921bb32ecde184085bcb3240f10f790bab85a9a246302c0a3a842798`, 69,844 cell-level rows and columns `patient`, `centenarian_status`, `batch`, `assay_simple`, `cell_type`. The metadata schema contains 12 donor IDs (SC1–SC7 and CT1–CT5), confirming that cells must not be treated as independent biological replicates. This probe is provenance/schema validation; it does not create a new independent cohort.

## Next actions

1. Allow the GEO candidate-analysis and offline-test workflows to finish; inspect their final conclusions and artifacts before updating scientific claims.
2. Continue the non-email route: inspect the authorized ELITE Portal ILO Blood Transcriptomics access path and the NECS Synapse project inventory. Do not bypass controlled access or invent file IDs.
3. If a genuinely independent permitted matrix plus donor/phenotype metadata is obtained, run donor-level pseudobulk and exact 8-mRPG/7-cRPG tests with cell-composition and leave-one-donor-out sensitivity.
4. Keep computational adversarial review separate from independent human review.
5. Do not mark the scientific release gate passed, and do not merge PR #167 without explicit user approval.

No Qwen3 or Gemini API dependency is used or proposed.


## Follow-up provenance check on PR head 0b3b3dd27bdb7e2b93f2df5dd89ff86df3f6e11d

A second Actions execution was inspected on this head:

- Frozen assurance run [44474232242](https://github.com/Sachhin/ORACLE/actions/runs/44474232242): success; artifact `14505287595`.
- Mendeley probe run [44474232238](https://github.com/Sachhin/ORACLE/actions/runs/44474232238): success as a probe; artifact `14505597465`. The three API endpoints (dataset, metadata, public files) each returned HTTP 401; the landing page returned HTTP 200. No data files or participant manifest were downloaded.
- Offline tests run [44474232346](https://github.com/Sachhin/ORACLE/actions/runs/44474232346): success. Python 3.10–3.14, live R/Bioconductor reference checks and RIKEN metadata provenance all passed.
- GEO candidate analysis run [44474232247](https://github.com/Sachhin/ORACLE/actions/runs/44474232247): still in progress at inspection; GEOquery/limma installation step was active. No result is claimed from this run.

### Frozen gate snapshot provenance caveat

The frozen assurance artifact's `oracle_v1_release_gate.json` is still **BLOCKED (4/6)**. Its embedded `ci_summary.json` points to earlier workflow run IDs 44043297155 (offline tests), 43914355105 (GEO) and 43911857872 (RIKEN), rather than the current head's runs 44474232346 and 44474232247. The GEO report in that frozen input also describes the earlier autophagy/lysosomal/inflammatory panel (GSE58137/GSE65219), not the current head's later candidate-gene run. The current head's fresh GEO workflow had not completed when inspected.

Therefore:
- Treat the frozen gate as a reproducible snapshot of its explicitly recorded inputs, not as a live aggregation of the latest Actions state.
- Do not claim the current GEO candidate-gene execution has passed until run 44474232247 completes and its artifact is inspected.
- A follow-up release-gate refresh should consume immutable artifacts from the exact current head SHA and record each workflow run ID, artifact ID and SHA-256. It should fail closed when a required current-head run is pending, missing or from another commit.
