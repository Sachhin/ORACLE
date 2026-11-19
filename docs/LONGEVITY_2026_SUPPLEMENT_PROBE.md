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


## Observed public-access result and HTML fallback (2026-11-19)

The first run of the corrected API probe completed successfully as a workflow, but all three Mendeley API requests returned **HTTP 401** (80-byte responses). This is an API access/authentication result, not evidence that the dataset is empty or that the files do not exist. The probe has therefore been extended to fetch the public dataset landing page as HTML and preserve its checksum, visible text, anchors, and any visible file/download links.

The landing page is publicly readable at https://data.mendeley.com/datasets/fpf4y72kfz/1 and identifies the dataset as “Transcriptomic Analysis of Chinese Longevity Cohorts”, version 1, published 18 March 2026. Its rendered page displays a “Download All” control and a “Files” heading, but the publicly rendered file section contains no visible filenames or file links. This is not sufficient to conclude that no files exist; the page may require an authenticated browser session or client-side file inventory. See the page directly and the official API documentation.

- Public landing page: https://data.mendeley.com/datasets/fpf4y72kfz/1
- Official API documentation: https://data.mendeley.com/api/docs/
- Latest probe script: `scripts/probe_mendeley_longevity_dataset.py`
- Landing-page HTML is saved in the workflow artifact as `mendeley_landing_page.html`.

**Current decision:** metadata-only evidence confirms the dataset identity and public landing page, but does not yet provide an authenticated downloadable matrix or sample-level annotation manifest. The CRA000515 age/cohort blocker remains open. Next legitimate route is submitter/lead-contact access to the file inventory or a public direct-download route that returns a verifiable file, followed by checksum and schema inspection. Do not mark the data acquired from a landing-page button alone.


## HTML source inspection and original-code cross-check (2026-11-19)

The PR-triggered HTML fallback run completed successfully (workflow run 44464125398; artifact 14501805192). Inspection of the captured 121,404-byte landing-page HTML established:

- The dataset landing page returns HTTP 200.
- The page's `Download All` button is rendered with the `disabled` attribute.
- The file tree is rendered as `file-list loading` with a loading spinner in the server-delivered HTML.
- No file IDs, filenames, file UUIDs, or download URLs are embedded in the captured HTML.
- The three documented API endpoints still return HTTP 401.

This is a stronger and more precise result than saying that the Files section is simply blank: the server-rendered page has not supplied a completed file listing, and its download control is disabled. It still does not prove that the dataset contains zero files; the client-side file inventory may be failing or may require an authenticated session.

The linked original analysis repository was also inspected through its recursive Git tree. It contains only three R scripts:
- `01.age-related-analysis.r`
- `02.transcriptional_clock_analysis.r`
- `03.trajectory_analysis.r`

The trajectory script loads `03.data.rda`, but that data object is not present in the public GitHub repository. Therefore the public code repository alone cannot reproduce the published matrix-level analysis.

**Status:** the Mendeley record and study identity are confirmed; the actual expression matrix and sample-level phenotype manifest remain unavailable to ORACLE through the unauthenticated public endpoints tested. Do not claim full-data access or sample-level replication. Continue via the lead contact identified in the paper or an authenticated user-mediated download, then verify the archive, checksums, schema, sample IDs, ages, cohorts, and exclusions before analysis.

Evidence:
- Mendeley landing page: https://data.mendeley.com/datasets/fpf4y72kfz/1
- Original analysis repository: https://github.com/xiaofuhui/longevity_transcriptomics
- Trajectory script: https://github.com/xiaofuhui/longevity_transcriptomics/blob/main/03.trajectory_analysis.r
- Article resource availability and lead contact: https://pmc.ncbi.nlm.nih.gov/articles/PMC13198318/
