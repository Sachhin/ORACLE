# CRA000515 2018 cohort supplementary metadata probe

The 2018 Genome Research article (PMCID PMC6211641; DOI 10.1101/gr.220780.117) identifies the 171-person Hainan cohort and links Supplemental Table S1 and Supplemental File S1. The main article reports cohort-level counts and sex totals, but the public GSA BioSample metadata does not provide the individual alias-to-cohort mapping.

## Retrieval result

- PMC OA package endpoint: HTTP 404 for this article.
- Europe PMC fullTextXML endpoint: retrieved successfully.
- Europe PMC supplementaryFiles endpoint: retrieved a 3,533,965-byte ZIP archive.
- Archive SHA-256: 42f9cc8ab450cd0330a27cfc20d0c6e56d714cf4b8d4457ec1370f5e83a74da0
- Archive contents: 17 Word documents (Supplemental Figures S1–S7, Supplemental Tables S1–S8, Supplemental File S1, and Supplemental Materials).

## What the supplement establishes

Supplemental Table S1 (SHA-256 6a824134cd121b03aefe6b2a6e2b8373c115bbbb1f0eb6824582a6f4c091d143) contains only aggregate sequencing counts by group, region, library type and read type:

| Dataset/library group | CEN | F1 | F1SP |
|---|---:|---:|---:|
| Data 1, Poly(A)+, PE100 | 27 | 18 | 18 |
| Data 2, Poly(A)+, PE150 | 28 | 19 | 11 |
| Data 3, rRNA(-), PE150 | 21 | 17 | 12 |
| Total | 76 | 54 | 41 |

It contains no individual sample IDs, age values, CHHA aliases, CRR run accessions or SAMC BioSample accessions.

Supplemental File S1 (SHA-256 08bbdb6fe54f49d20c708d83bcf7f00303a59e6785906f65b0027050f8c02176) describes the DESeq2 workflow and explicitly reads a file named samples_information.csv. The code shows that this missing file must contain sample row names/IDs and the fields condition (CEN/F1/F1SP), read_type and library_type. That CSV is not included in the downloaded supplement archive. The public GitHub code repository contains the analysis scripts but not samples_information.csv or the count matrix.

## Consequence for CRA000515

The public CRA000515 metadata acquisition cross-references 171 CRR runs, 171 SAMC BioSamples and 171 CHHA aliases. Tissue and sex fields are checked; the aggregate sex totals reconcile with the 2018 paper. However, the published supplement provides only group-level counts, not the sample-level crosswalk. We therefore cannot assign any individual CHHA alias to CEN, F1 or F1SP, or attach individual age values.

The most precise outstanding author request is now the missing samples_information.csv plus the mapping from its row names to CHHA aliases and CRR/SAMC accessions, and the individual ages. The 2026 Mendeley Data landing page is visible (DOI 10.17632/fpf4y72kfz.1), but its Files section is blank in the public page and our metadata-only API probe could not enumerate file IDs or retrieve the expression matrix.

## Workflow and artifact

- Workflow: .github/workflows/cra000515-pmc-supplement-probe.yml
- Script: scripts/probe_cra000515_pmc_supplements.py
- Artifact: oracle-cra000515-pmc-supplement-probe

No individual labels are inferred from aggregate counts or sample order. The cohort crosswalk remains blocked pending the source-authenticated sample_information.csv/author manifest.
