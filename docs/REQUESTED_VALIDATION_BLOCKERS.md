# ORACLE validation blockers — current evidence status (2026-11-19)

This file records scientific and provenance blockers separately from software checks. No sample label, expert score, biological mechanism, or experimental result is invented.

## CRA000515 human centenarian cohort

**Accession-level metadata acquisition: PASS. Individual cohort validation: BLOCKED.**

Verified public acquisition:
- 171 CRR run accessions, 171 SAMC BioSamples, 171 CRX experiments, and 171 CHHA aliases cross-referenced.
- All 171 records identify peripheral blood.
- Raw sex codes were independently checked against each BioSample page: 171/171 concordant (70 male, 101 female).
- Aggregate sex totals reconcile with the 2018 paper's CEN/F1/F1SP totals.
- No individual ages or explicit CEN/F1/F1SP group labels are present in the public BioSample records.

The 2018 supplement contains aggregate group counts only (76 CEN, 54 F1, 41 F1SP). Supplemental File S1 references a required samples_information.csv, but that file is absent from the public supplement archive. The 2026 Mendeley dataset landing page is visible, but its documented API endpoints returned HTTP 401; captured HTML had a disabled Download All control and no file IDs, filenames, or download URLs. This does not prove the dataset is empty.

Required to unblock: a source-authenticated 171-row mapping from CHHA aliases to age, CEN/F1/F1SP group, sex, region, library/read type, and CRR/SAMC accessions. The repository's 2026-11-17 outreach log records that the initial de-identified author request was sent to the published lead-author contact. No authenticated response or source file is recorded as of 2026-11-19. A follow-up template is available in docs/CRA000515_SUBMITTER_REQUEST_DRAFT_2026-11-19.md; check the user's email thread before sending any follow-up. No individual group or age values are inferred.

Detailed records: docs/CRA000515_PUBLIC_METADATA_AUDIT_2026-11-16.md, docs/CRA000515_PMC_SUPPLEMENT_PROBE.md, docs/LONGEVITY_2026_SUPPLEMENT_PROBE.md, and the draft request above.

## PXD047528 proteomics and clinical outcomes

**DDA/DIA reconstruction: completed, weak/exploratory. Clinical mapping: BLOCKED but OPTIONAL for the longevity release.**

Verified:
- PEPerMINT processed tables contain 15 aliases (1_Slot1–15_Slot1).
- Live PRIDE API inventory returned 30 RAW files (15 DDA/DIA technical acquisition pairs) plus one SEARCH report.
- The SEARCH report contains 15 HIVPCA quantity columns with report-internal Slot1 tokens. This is a candidate technical alias bridge only.
- DDA had 13,043 missing cells; 8,859 (67.9%) had paired DIA measurements for reconstruction scoring.
- KNN modestly improved over a row-median baseline (MAE 1.0981 vs 1.1382; Pearson r 0.2625 vs 0.2503), but correlation remains weak and mean signed error is high.

Ahmed et al. report 13 clinical participants (8 HIV, 5 herpes; HIV HAND subgroup 5 HAND and 3 cognitively normal), while PEPerMINT exposes 15 processed biological-sample aliases. Public files do not authenticate the 15-alias-to-13-participant mapping. Do not assume two aliases are technical repeats or assign HIV/herpes/HAND labels from filenames, report columns, sample order, or abundance patterns.

A submitter-authenticated manifest is still required for any clinical reconstruction. This is not a core longevity release blocker. Keep the paired DDA/DIA technical benchmark separate from clinical claims.

## Human longevity evidence

**Independent evidence is mixed; no new mechanism is validated.**

- The 2026 Chinese paper's 8-mRPG association is published prior art, not a novel ORACLE discovery.
- GSE16717 is the Leiden cohort already cited in the 2026 paper. ORACLE's simple group comparison did not find a significant mRPG-8 composite (long-lived siblings vs controls: difference -0.163, p=0.316, FDR=0.667). It is not an exact replication of the paper's age-trajectory model.
- RIKEN SC2018 is a distinct Japanese supercentenarian cohort (7 SC, 5 controls). Source-checksummed PBMC donor-pseudobulk analysis found a lower mRPG-8 score in SC than controls in both all-batches and common-batch analyses; no individual mRPG gene reached BH FDR<0.05. This is an exploratory directionally opposite result, not definitive refutation or causal evidence.
- The 2025 three-cohort single-cell atlas supports immune-cell composition/state as a plausible bulk-blood confounder; it does not directly test the 8-mRPG panel.
- GSE58137/GSE65219 are age-association checks, not direct centenarian replication.
- The 2026 Mendeley integrated expression matrix remains inaccessible through the unauthenticated API route tested; it has not been analyzed by ORACLE.

Hypotheses remain provisional. No new causal or previously unknown human longevity mechanism is validated. No physical experiment has been performed.

## Expert evaluation

**BLOCKED — no independent expert reviews received.**

The rubric and review-validation tooling can validate submitted reviews, but cannot recruit reviewers or generate human judgments. At least two real independent reviewers must score a frozen paired corpus, with blinded scoring and adjudication. No reviewer identities or scores are fabricated.

The repository's 2026-11-17 outreach log records that individual invitations were sent to Albert Higgins-Chen, T. Em Arpawong, and Raghav Sehgal. As of the latest recorded status, none had accepted; expertise fit/COI clearance, score files, and adjudication remain unconfirmed. A follow-up template is available in docs/INDEPENDENT_REVIEWER_INVITATION_DRAFT_2026-11-19.md; check the user's email thread before sending any follow-up. No reviewer endorsement, score, or adjudication is claimed.

## Model-free architecture and release scope

ORACLE has no AI-model dependency. It uses deterministic planning, retrieval, evidence/provenance management, statistical computation, provisional hypothesis templates, and audit rules. Deterministic hypothesis templates are not equivalent to open-ended AI reasoning.

A successful Python/R CI run establishes engineering checks only. It does not establish clinical cohort mapping, independent biological replication, expert review, novelty, or causality. The model-free release gate reports these separately. CRA000515's authenticated age/cohort manifest and real independent blinded expert evaluation remain core release blockers. PXD047528's clinical crosswalk is optional and cannot block the longevity release; its paired DDA/DIA technical benchmark remains separate.

## Exact next actions requiring external participation

1. Repository owner reviews and explicitly sends the CRA000515 request to the study lead or obtains the manifest through an authorized authenticated download.
2. Repository owner approves and sends reviewer invitations or obtains volunteers through the public issue. Screen expertise and conflicts before sharing frozen packets.
3. On receipt, hash and provenance-check the manifest; validate every alias/accession join. For reviewers, freeze the corpus, issue blinded packets, validate two independent score files, and adjudicate.
4. Rerun the v1 release gate only after source-authenticated data and actual expert outputs exist.
