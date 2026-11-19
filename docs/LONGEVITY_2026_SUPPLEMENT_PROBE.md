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


## Cohort-count reconciliation from the published STAR Methods and data statement

The initial count discrepancy can now be reconciled arithmetically from the article itself:

- Recruited: 1,752 people = 811 LLIs + 941 YCs.
- Previously published: 442 samples = 171 CRA000515 + 271 HRA000656.
- One previously published sample had missing age and was excluded from analysis.
- Analyzed previously published samples: 441.
- Newly generated samples: 1,310.
- Total analyzed: 441 + 1,310 = 1,751 = 811 LLIs + 940 YCs.

Thus the abstract's 1,751 analyzed participants and the Methods' 1,752 recruited participants are numerically consistent with the stated one-sample missing-age exclusion. The 441 in the Data Availability statement is also consistent with 442 deposited previously published samples minus one excluded sample.

**What remains unresolved:** the paper does not identify which exact sample was excluded for missing age, whether that sample is among CRA000515 or HRA000656, or its accession/alias. The 171 CRA000515 metadata still contains zero individual age values and zero individual CEN/F1/F1SP labels. Supplemental Table S1 reports only aggregate counts by data batch/library type (76 CEN, 54 F1, 41 F1SP across the 171-person Hainan cohort); Supplemental File S1 references `samples_information.csv` with the required row-level condition/read_type/library_type fields, but that CSV is not included in the public archive.

This closes the arithmetic discrepancy but does not close the individual provenance crosswalk or enable sample-level reanalysis.


## Mendeley public API re-probe correction (2026-11-19)

The earlier metadata-only probe used a non-canonical dataset metadata URL and did not independently distinguish the dataset metadata, custom metadata, and public file-list endpoints. The probe has been corrected to query all three documented routes independently:

- `GET https://api.data.mendeley.com/datasets/fpf4y72kfz?version=1`
- `GET https://api.data.mendeley.com/datasets/fpf4y72kfz/metadata?version=1`
- `GET https://api.data.mendeley.com/datasets/publics/fpf4y72kfz/files?version=1&$limit=500`

The revised script records HTTP status, content type, response byte count and SHA-256 for each endpoint, parses any returned file inventory, and preserves the raw JSON response in the workflow artifact. It does not download expression matrices or claim that a file listing authenticates sample annotations.

- Workflow: `.github/workflows/mendeley-longevity-metadata-probe.yml`
- Script: `scripts/probe_mendeley_longevity_dataset.py`
- Artifact: `mendeley-longevity-metadata-probe`
- Expected report: `artifacts/mendeley/mendeley_public_metadata_probe.json`

**Execution is pending the new PR-triggered GitHub Actions run.** Until its artifact is inspected, file availability remains unverified. Even if files are listed, ORACLE must inspect their contents and provenance, identify the individual sample/age/cohort fields, map them to the published aliases without inference, and checksum the exact source file before closing the CRA000515-related sample annotation blocker.

The Mendeley API documentation states that public dataset metadata and files are retrievable through its public API; the workflow uses the documented endpoint families. See https://data.mendeley.com/api/docs/ and https://data.mendeley.com/archive-process.
