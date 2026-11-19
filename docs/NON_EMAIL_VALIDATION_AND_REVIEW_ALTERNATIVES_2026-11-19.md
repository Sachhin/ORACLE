# Non-email verification and independent-review alternatives (2026-11-19)

## Decision

Continue validation without waiting for email. Use public, source-authenticated datasets and reproducible adversarial computational review. Public reanalysis cannot recover CRA000515's missing individual ages/cohort labels. Automated review strengthens evidence/software assurance but is not independent human expert judgement.

## A. Public/portal alternatives to CRA000515

### Priority 1 — ILO Blood Transcriptomics (Batch 1), ELITE Portal
- ELITE Portal lists a dataset named “ILO Blood Transcriptomics (Batch 1)” with 801 items, human blood RNA-seq, gene-expression data, and controlled access (dataset ID syn74490543; study key ILORNAseq).
- This is the strongest alternative to pursue for a sample-level longevity transcriptomics cohort because it is directly relevant to the Integrative Longevity Omics program. The portal marks access as Controlled, so ORACLE must request/obtain authorized access through the portal; it must not attempt to bypass restrictions.
- Before analysis, inspect the portal's data dictionary and sample metadata, confirm centenarian/offspring/control counts, chronological age, sex, health status, tissue, batch, and sample-level expression file availability. Verify whether this batch overlaps CRA000515 or other published cohorts; do not assume independence from the dataset title.
- If access is not granted, record it as an access-limited candidate, not a completed dataset acquisition.

### Priority 2 — NECS centenarian PBMC single-cell/CITE-seq (2023)
- Karagiannis et al., eBioMedicine 2023, DOI 10.1016/j.ebiom.2023.104514, PMCID PMC10114155.
- Seven centenarians (ages 100–119; 3 male, 4 female) plus two younger references; the study also integrated public PBMC datasets.
- The paper's data statement says NECS data are available through Synapse project UH2AG064704. Availability and permissions for individual files still require verification.
- This is a distinct North American centenarian cohort. If gene-level matrices and donor annotations are accessible, test the exact published 8-mRPG and 7-cRPG panels by donor and cell type.
- Limitations: only seven centenarians; paper reports age ranges; donor mapping and raw-file availability must be validated. Cells are not independent biological replicates.
- Required workflow: record Synapse IDs, file versions, terms and SHA-256; validate donor IDs/age/sex; pseudobulk by donor × cell type; freeze gene panels; test donor-level scores, FDR and leave-one-donor-out sensitivity.

### Priority 3 — GSE276957 longevity bank
- GEO describes over 86 centenarian/offspring blood samples, functional-independence data, methylation arrays and 20 derived iPSC lines.
- Useful as a distinct longevity cohort for methylation/biological-age and phenotype context.
- It is methylation profiling, not transcriptome expression. It cannot directly validate mRPG RNA expression.

### Priority 4 — GSE262619 healthy blood age transcriptome
- Whole-transcriptome sequencing of 35 healthy individuals aged 22–88.
- Useful for age-associated reference trajectories and sex/covariate sensitivity.
- No centenarians or exceptional-longevity phenotype: age-reference only, not longevity replication.

### Priority 5 — GSE237029 older vs middle-aged PBMC arrays
- PBMC expression arrays comparing ages 75–89 with ages 35–50.
- Useful for an additional older-adult age baseline.
- No exceptional-longevity group: not a longevity replication.

### Existing cohorts that must not be double-counted
- RIKEN SC2018: seven Japanese supercentenarians and five controls; already analyzed by ORACLE and directionally discordant for mRPG8. Publications reuse the same donors.
- GSE16717: Leiden cohort already used in the 2026 paper; ORACLE's simple comparison is not an independent replication or exact age-trajectory reproduction.
- 2025 three-cohort atlas: Lingao is a distinct cohort but its matrices are controlled-access; Rugao and Japan are reused cohorts. It supports immune-composition confounding, not direct mRPG8 replication.
- GSE65219/GSE58137: ordinary age/immune-aging cohorts, not exceptional-longevity replication.

## B. Review without email

Run a frozen computational adversarial review with separate evidence channels:
1. Freeze mission bundle, source manifest, claims, scripts, output tables and SHA-256 hashes.
2. Run separate passes for provenance, statistics, biology, novelty/prior art and strongest-skeptic alternatives.
3. Use deterministic validators for machine-checkable criteria. Record input hash, tool/version, findings, severity and resolution.
4. Preserve each pass separately; do not allow one pass to rewrite another's findings.
5. Have the Auditor reconcile disagreements and produce a traceable decision log.
6. Re-run assurance and release-gate workflows on the frozen bundle.

**Status rule:** This is internal computational/adversarial review, not independent human expert review. It may satisfy an engineering assurance requirement only under a separately named gate. The existing independent blinded human-review gate remains BLOCKED until real independent reviewers submit verifiable score files and adjudication. Synthetic personas or model-generated scores must never count as reviewers.

## C. Next execution
1. Inventory the public Synapse project for UH2AG064704; do not bypass access controls or guess file IDs.
2. If NECS matrices and donor annotations are accessible under permitted terms, build donor-level pseudobulk analysis for exact mRPG8/cRPG7 and cell-composition sensitivity.
3. In parallel, build age-reference workflows for GSE262619 and GSE237029, explicitly labelled non-longevity.
4. Run separate provenance/statistical/biology/novelty/skeptic review passes on a frozen evidence bundle.
5. Keep CRA000515 labels and human expert review as unresolved. Consider a separately scoped PUBLIC_DATA_RESEARCH_RELEASE only if its gate passes.

## Sources
- 2023 NECS study: https://pmc.ncbi.nlm.nih.gov/articles/PMC10114155/
- ELITE Portal ILO Blood Transcriptomics Batch 1 listing (dataset syn74490543; controlled access): https://eliteportal.synapse.org/Explore/Datasets
- Synapse project: https://adknowledgeportal.synapse.org/Explore/Projects/DetailsPage?Grant%20Number=UH2AG064704
- GSE276957: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE276957
- GSE262619: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE262619
- GSE237029: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE237029
- 2025 centenarian atlas: https://pmc.ncbi.nlm.nih.gov/articles/PMC12571583/