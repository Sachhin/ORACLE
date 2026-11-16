# PXD047528 PRIDE file-manifest and search-report audit

Audit date: 2026-11-16  
PRIDE project: https://www.ebi.ac.uk/pride/archive/projects/PXD047528  
PRIDE API: https://www.ebi.ac.uk/pride/ws/archive/v3/projects/PXD047528/files/all

## Public PRIDE inventory

A live PRIDE Archive v3 API query returned **31 files**:

| Category | Count |
|---|---:|
| RAW | 30 |
| SEARCH | 1 |
| Total | 31 |

The 30 RAW files form 15 paired acquisition suffixes: 03M, 23Y, 32S, 41S, 44S, 47Y, 50V, 590, 60P, 61Q, 62R, 67W, 74D, 77K, and 9T2. Each suffix has one 2019 DDA raw file and one 2020 DIA raw file. This establishes 15 technical DDA/DIA pairs. PRIDE's file metadata returned no sampleAccession value for any file, and none of the raw filenames contains the processed-table aliases 1_Slot1 through 15_Slot1.

The earlier informal statement that PRIDE listed 32 raw files was incorrect. The current API inventory is 30 RAW + 1 SEARCH = 31 total files.

## Additional SEARCH file downloaded and inspected

The sole SEARCH file was downloaded without downloading any of the 30 multi-GB raw acquisitions:

- Filename: 20200510_SAAV_7g_15min_HIVPlasmaPCA_Report.txt
- Size: 113,569 bytes
- SHA-256: 632c074117c15b48567c6b041b80f2281774097bc22959257fae9bb6dfce366b

Its header contains 15 protein-group quantity columns labeled HIVPCA1 through HIVPCA15 (the column order is not numeric). Each same column header also contains a `Slot1-N` token. Thus the report itself directly records these report-internal label pairs (HIVPCA → Slot1 token): HIVPCA8→12, HIVPCA15→19, HIVPCA5→9, HIVPCA4→8, HIVPCA7→11, HIVPCA10→14, HIVPCA3→7, HIVPCA11→15, HIVPCA14→18, HIVPCA12→16, HIVPCA1→5, HIVPCA2→6, HIVPCA13→17, HIVPCA6→10, HIVPCA9→13. The column order is not numeric.

This is a stronger source-grounded technical bridge than the label count alone: each DIA-NN quantity column explicitly names both the HIVPCA label and a Slot1-N token. However, the processed benchmark's aliases are written as `1_Slot1` through `15_Slot1`, while the report headers encode `Slot1-5` through `Slot1-19`. Without the original export/sample sheet, the equivalence between those naming schemes is not yet authenticated. The report also does not map these DIA search columns to the 15 opaque DDA/DIA raw suffix pairs or to the 13 clinical participants.

The report therefore supplies a useful additional technical inventory but does not resolve the clinical mapping. The string HIVPCA is not treated as sufficient evidence for clinical participant identity, HAND status, or an authenticated phenotype label.

## Reproducible files and workflow

- Workflow: .github/workflows/pxd047528-pride-manifest.yml
- Script: scripts/audit_pxd047528_pride_manifest.py
- Artifact: oracle-pxd047528-pride-metadata
- Artifact includes the full API project/file JSON, normalized TSV manifest, downloaded SEARCH report and summary JSON.

## Decision

- Public PRIDE file inventory: **PASS**
- Fifteen DDA/DIA technical acquisition pairs: **PASS**
- Additional 15-column SEARCH report retrieved: **PASS**
- Mapping HIVPCA labels to Slot1-N tokens within the SEARCH report: **PASS**
- Equivalence of SEARCH Slot1-N tokens to processed `1_Slot1..15_Slot1` aliases: **NOT ESTABLISHED**
- Mapping processed Slot1 aliases to raw acquisition suffixes: **NOT ESTABLISHED**
- Mapping to 13 clinical participants and HIV/herpes/HAND labels: **BLOCKED**

A source-authenticated submitter manifest remains required. No clinical labels are inferred from raw suffixes, file order, HIVPCA labels, or processed-table column order.


## Independent file-index count discrepancy

The OmicsDI PXD047528 page currently displays 1–5 of 32 file entries, while the live PRIDE Archive v3 files/all endpoint returned 31 records (30 RAW + 1 SEARCH) on 2026-11-16. This is a one-record discrepancy between an external index and the live PRIDE API. The PRIDE audit workflow now also queries the paginated PRIDE endpoint to compare both API representations. Until that cross-check is complete, 31 is the observed files/all API count, not a claim that every historical mirror has exactly 31 entries. The older phrase “32 raw files” is unsupported: the external index shows 32 total entries, not 32 raw files.
