# 2026 human-longevity article supplementary-data probe

The 2026 Cell Reports Medicine paper on the 8-mRPG signature is available as PMCID PMC13198318. Its exact eight-gene signature, supplementary tables, and cohort annotations are needed for an independent numerical replication.

This workflow retrieves the Europe PMC full-text XML and supplementaryFiles archive, inventories the extracted files, and preserves SHA-256 checksums. It is a public-data-only workflow and does not use any AI model or infer missing sample annotations.

Workflow: .github/workflows/longevity-2026-supplement-probe.yml  
Script: scripts/probe_longevity_2026_supplements.py  
Artifact: oracle-longevity-2026-supplementary-data

The first inspection target is any supplementary table containing the exact 8-mRPG and 7-cRPG gene lists, sample-level expression matrix, cohort/sample metadata, or validation cohort mapping. If the supplements do not contain these data, the Mendeley dataset files and author-provided annotations remain necessary.


## Retrieval findings (2026-11-16)

Europe PMC supplementaryFiles returned a ZIP archive containing two PDF supplements (mmc1.pdf and mmc2.pdf), with SHA-256 checksums preserved in the workflow artifact. The supplements do not provide the sample-level Chinese expression matrix or individual age/cohort manifest. However, visual inspection of Figure 4B in the article PDF recovered the exact published signatures:
- mRPG-8: MRPL3, MRPL32, MRPL42, MRPL45, MRPL50, MRPS10, MRPS33, MRPS35.
- cRPG-7: RPL10A, RPL22, RPL4, RPL5, RPS13, RPS23, RPS6.

The exact gene lists are now stored in data/missions/longevity/prior_art_seed.json. ORACLE also has a deterministic GSE16717 reanalysis workflow to reproduce the published Leiden validation cohort. That cohort was already used by the 2026 article, so this is a reproducibility check, not a new independent cohort.

The Chinese discovery cohort's Mendeley page remains without visible file entries, and the public metadata API probe did not return downloadable file identifiers. The sample-level matrix and age/cohort manifest therefore remain an author-data blocker.
