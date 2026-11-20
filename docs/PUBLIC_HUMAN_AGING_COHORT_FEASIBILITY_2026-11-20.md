# Public human-aging cohort feasibility screen (2026-11-20)

## Purpose

Identify public, source-authenticated expression datasets that can strengthen ORACLE's human-aging analyses without pretending that ordinary aging cohorts replicate exceptional longevity. This screen is a dataset-feasibility assessment, not an analysis result.

## Candidate 1 — GSE262619 (priority for exploratory age-reference analysis)

- GEO title: *Characteristics of Age-Associated Changes in the Whole Transcriptome of Human Peripheral Blood Leukocytes and Establishment of an Aging Clock*.
- Organism/tissue: *Homo sapiens*, peripheral blood leukocytes.
- Assay: whole-transcriptome sequencing (mRNA, lncRNA and miRNA).
- Cohort: 35 healthy participants aged 22–88; reported groups are Young n=11 (mean 27.5 ± 2.54), Middle n=10 (mean 60.4 ± 2.22), Old n=14 (mean 80.5 ± 4.57).
- Public GEO record: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE262619
- PubMed record cited by GEO: PMID 40089807.
- Role in ORACLE: exploratory age-associated expression reference only. It contains no exceptional-longevity/centenarian group and cannot validate a longevity mechanism or serve as an independent longevity replication.
- Required pre-analysis checks: retrieve the current GEO series matrix and supplementary/raw files; preserve exact sample IDs and file versions; verify per-sample age, sex, health criteria, library type and batch from source metadata; identify whether gene-level count data are available and whether mRNA and non-coding RNA assays are mixed; inspect sample exclusions and missingness.
- Analysis gate: proceed only if a source-linked sample manifest and an appropriate expression matrix/count table are both publicly retrievable and checksum-recorded. Test the exact published 8-mRPG and 7-cRPG panels only if all required genes are measurable; use age as a continuous predictor with sex and available technical/clinical covariates. With n=35, label results exploratory and report uncertainty/FDR; do not fit a high-dimensional discovery model.

## Candidate 2 — GSE237029 (low-priority, small-n PBMC age contrast)

- GEO title: *Whole genome microarray gene expression profiling of peripheral blood mononuclear cells (PBMC) isolated from old and middle-aged, voluntary human research participants*.
- Organism/tissue: *Homo sapiens*, PBMC.
- Assay/platform: Affymetrix Human Genome U133 Plus 2.0 (GPL570).
- Cohort: old n=5 (ages 75–89) and middle-aged n=4 (ages 35–50); total n=9.
- Public GEO record: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE237029
- Public sample tables contain processed probe-level signals; supplementary archive lists raw CEL/CHP files. GEO reports GCOS processing and scaling to target intensity 200.
- Role in ORACLE: small exploratory older-versus-middle-aged PBMC reference only. No exceptional-longevity group; n=9 is severely underpowered for broad discovery and vulnerable to individual-donor effects.
- Required pre-analysis checks: retrieve all nine sample records and the GPL570 annotation; confirm individual ages/sex and any batch or clinical covariates; verify raw CEL archive integrity and checksums; compare raw CEL/RMA-derived expression with submitter-provided processed signals rather than treating GCOS signals as RMA; map probe sets to current gene symbols and resolve multiple probes per gene with a prespecified rule.
- Analysis gate: do not use this cohort for transcriptome-wide discovery claims. If all source files are retrievable, run a narrowly prespecified 8-mRPG/7-cRPG probe-level feasibility/sensitivity analysis, report each donor, effect sizes and confidence intervals, and treat every result as exploratory. No cross-cohort pooling with RNA-seq or GSE16717/RIKEN.

## Cohort independence and interpretation rules

1. These are age-reference cohorts, not exceptional-longevity cohorts.
2. Neither dataset can close the CRA000515 authenticated age/cohort manifest blocker.
3. Neither dataset can satisfy the independent blinded human-review gate.
4. Do not pool their expression values with GSE16717 microarray or RIKEN single-cell pseudobulk; assay, tissue, normalization and estimands differ.
5. A candidate dataset becomes an analyzed evidence source only after source files, sample metadata, checksums, preprocessing, gene mapping and per-sample inclusion/exclusion logs are frozen.
6. Keep the published 8-mRPG signature labelled prior art. Any new ORACLE mechanism requires independent replication and causal evidence.

## Recommended execution order

1. GSE262619: authenticate and inventory the 35-sample manifest, count matrix and supplementary files; then assess whether a conservative age-associated panel analysis is feasible.
2. GSE237029: authenticate the nine CEL/CHP files and annotation; run raw-CEL/RMA sensitivity only if source files are intact.
3. Keep both analyses in a separate `age_reference` evidence class. They must not be counted as longevity replication.
4. Refresh the frozen release-gate inputs only from immutable artifacts generated on the exact commit under evaluation; fail closed on pending, missing or stale workflow artifacts.

## Source records

- NCBI GEO GSE262619: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE262619
- NCBI GEO GSE237029: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE237029
- NCBI GEO GSE237029 sample record example (processed probe-level signal and CEL/CHP files): https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM7593234

**Status:** feasibility screen recorded; no source files were downloaded or reanalyzed in this step. No new biological finding is claimed.
