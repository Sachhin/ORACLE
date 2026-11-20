# PXD047528 clinical sample mapping status

## What is verified

- The ORACLE preparation workflow uses the PEPerMINT example tables for
  `datasets/blood_hiv_dda_dia` from Zenodo record 11216899.
- The prepared DDA and DIA tables contain 15 matching sample aliases:
  `1_Slot1` through `15_Slot1`.
- The frozen paired-assay report scores 8,859 DDA-missing cells that have a
  paired DIA value (67.9% of 13,043 DDA-missing cells).
- The PEPerMINT publication's benchmark table also describes PXD047528 as
  15 samples, 15 biological samples, and one technical replicate per
  biological sample.

## Why clinical outcome validation is still blocked

The original Ahmed et al. clinical paper reports 13 plasma samples: 8 people
with HIV and 5 with herpes infection. Its HAND sub-analysis uses 5 HAND and
3 cognitively normal HIV participants. These cohort counts do not establish
which of the 15 PEPerMINT sample aliases correspond to which clinical
participants, nor whether two additional aliases reflect another acquisition,
a different processed cohort, or a data-version discrepancy.

No clinical phenotype is encoded reliably in the `Slot1` aliases. The
current public PEPerMINT sample map is blank. The public PXD record and paper
metadata inspected so far do not provide an alias-to-patient crosswalk.
Therefore ORACLE must not infer labels from filenames, sample order, intensity
patterns, or the paper's aggregate group sizes.

## Required evidence to unblock

Obtain a source-authenticated sample manifest from the dataset submitter or
the original study records that maps each processed alias to:
- raw acquisition filename(s) and DDA/DIA pairing;
- unique patient/sample identifier;
- HIV versus herpes phenotype;
- for HIV samples, HAND/MND/HAD/cognitively-normal classification where
  explicitly documented;
- technical replicate or exclusion status, with rationale.

After that, freeze the manifest with a checksum and rerun the outcome
concordance evaluator. If the 15 processed aliases cannot be mapped
unambiguously to the 13 clinical participants, retain the reconstruction-only
result and report clinical concordance as unavailable.

## Sources

- ProteomeXchange PXD047528: https://proteomecentral.proteomexchange.org/cgi/GetDataset?ID=PXD047528
- Ahmed et al. 2022, PMID 35639337, PMCID PMC9945916:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC9945916/
- PEPerMINT benchmark paper, Table 2:
  https://academic.oup.com/bioinformatics/article/40/Supplement_2/ii70/7749076
- PEPerMINT example data source: Zenodo record 11216899,
  https://zenodo.org/records/11216899

This is a data-provenance blocker, not a missing software feature. No synthetic
or guessed labels should be used to turn this task green.


## Source-count discrepancy requiring explicit resolution (2026-11-16)

A fresh cross-source check found a material mismatch that must be preserved
rather than normalized away:

- Ahmed et al. (2022), the clinical study linked to PXD047528, reports **13
  plasma samples** in the proteomics analysis: 8 HIV and 5 herpes. Its HAND
  sub-analysis is 5 HAND (3 MND + 2 HAD) versus 3 cognitively normal HIV
  participants.
- The PEPerMINT publication's Table 2 reports PXD047528 as **15 samples, 15
  biological samples, and one technical replicate per biological sample**.
- The live PRIDE Archive v3 API returns 31 deposited files: 30 RAW files (15 DDA and 15 DIA acquisitions) plus one SEARCH report. The 30 RAW files form 15 DDA/DIA pairs with matching opaque suffixes (03M, 23Y, 32S, 41S, 44S, 47Y, 50V, 590, 60P, 61Q, 62R, 67W, 74D, 77K, 9T2). PRIDE returns no sampleAccession value for these files, and none of the raw filenames contains the processed Slot aliases. The count and filenames establish technical acquisitions, not clinical participant labels.

The one SEARCH report (20200510_SAAV_7g_15min_HIVPlasmaPCA_Report.txt; SHA-256 632c074117c15b48567c6b041b80f2281774097bc22959257fae9bb6dfce366b) contains 15 protein-group quantity columns labelled HIVPCA1 through HIVPCA15. Those labels are not mapped to the processed Slot aliases, the 15 raw acquisition suffixes, or clinical participants. The HIV token in a filename or report column is not accepted as a source-authenticated phenotype. These statements do not currently establish a valid 15-alias-to-13-patient crosswalk. In particular, ORACLE must **not assume** that two of the 15
processed aliases are technical repeats merely to force agreement with the
13-person clinical paper. The 15-biological-sample statement may indicate a
broader or version-different analysis set; the submitter must explain the
difference and provide the corresponding sample manifest.

The current validator deliberately retains the strict 15-alias/13-clinical-
participant acceptance target because the clinical outcome analysis is tied
to the 2022 paper. A manifest that maps 15 distinct biological samples, or
that cannot document the relationship of two aliases to the clinical cohort,
must remain blocked for clinical outcome concordance. Reconstruction-only
DDA/DIA benchmarking remains valid independently of clinical labels.

Required submitter clarification:
1. Are all 15 PEPerMINT aliases part of the same 13-participant clinical
   cohort, or is the processed set broader/different?
2. If there are 15 biological samples, provide the participant/sample IDs and
   explain how those differ from the 13 plasma samples reported in the paper.
3. Identify any QC samples, excluded samples, repeated acquisitions, or
   additional samples, with DDA/DIA raw filenames and reasons.
4. Provide the mapping from each processed alias to raw DDA and DIA files and
   to the original clinical table row, where applicable.

Until this is source-authenticated, clinical validation remains **BLOCKED**.


## Live PRIDE API evidence (2026-11-16)

The full file manifest and SEARCH report are preserved in docs/PXD047528_PRIDE_FILE_MANIFEST_AUDIT.md and the oracle-pxd047528-pride-metadata workflow artifact. The previous 32-raw-file count was incorrect. No clinical labels were inferred from the 15 raw DDA/DIA pairs or HIVPCA search-report columns.


## Independent file-index discrepancy

OmicsDI's public PXD047528 page displays 32 total file entries, whereas the live PRIDE Archive v3 files/all API returned 31 records (30 RAW + 1 SEARCH). ORACLE now probes the paginated PRIDE endpoint as a second check. The former statement “32 raw files” was incorrect: 32 is the external index's total entry count, not a verified raw-file count. The one-record difference remains under investigation.


## Clinical-paper reference cohort (13 reported participants)

Ahmed et al. (2022) Table 1 reports 13 participants: 8 virally suppressed people with HIV (3 cognitively normal, 3 MND, 2 HAD) and 5 herpes CNS infection participants (HSV-1 n=1, HSV-2 n=2, VZV n=2). The cohort is 11 male and 2 female; median age 53 years (IQR 39–64). The published table provides group, age and sex but no accession IDs that can be joined to the 15 processed aliases.

| Clinical group | Age | Sex |
|---|---:|---|
| Cognitively normal PWH | 51 | M |
| Cognitively normal PWH | 52 | M |
| Cognitively normal PWH | 29 | M |
| MND | 53 | M |
| MND | 67 | M |
| MND | 64 | M |
| HAD | 78 | M |
| HAD | 61 | M |
| HSV-1 | 25 | M |
| HSV-2 | 39 | F |
| HSV-2 | 54 | F |
| VZV | 85 | M |
| VZV | 33 | M |

The PRIDE project was announced on 2024-03-05 and its metadata was updated on 2024-10-22, after the 2022 article. PEPerMINT reports 15 samples and 15 biological samples for PXD047528. The 15 raw DDA/DIA acquisition pairs and 15 HIVPCA labels in the SEARCH report are not linked to the 13 clinical-paper rows. The two-count difference could reflect additional samples or a different data scope, but the public evidence does not resolve it.

Source: Ahmed et al. 2022, Table 1, DOI 10.1007/s13365-022-01077-0; PRIDE/ProteomeXchange project PXD047528; PEPerMINT Table 2.

## Newly established technical alias clue (not a clinical crosswalk)

The PEPerMINT source code's `load_blood_hiv_dda_dia_dataset()` explicitly uses processed columns `1_Slot1` through `15_Slot1` (see `DILiS-lab/pepermint/datasets.py`). The PRIDE SEARCH report header contains 15 DIA-NN sample columns named `HIVPCA1_Slot1-5` through `HIVPCA15_Slot1-19` (in a non-sequential header order). The numeric suffix relationship is consistent with the candidate technical alias pattern:

`n_Slot1` ↔ `HIVPCA n` ↔ `Slot1-(n+4)`, for n = 1…15.

This is a useful technical hypothesis, but it is **not** yet a source-authenticated mapping to the 2019 PRIDE RAW pairs or to clinical participants. The SEARCH report's DIA-NN column names contain 2020 run identifiers, whereas PRIDE's raw DDA/DIA files are named with 2019 acquisition suffixes (03M, 23Y, 32S, 41S, 44S, 47Y, 50V, 590, 60P, 61Q, 62R, 67W, 74D, 77K, 9T2). No public file currently bridges those two naming systems or supplies HIV/herpes/HAND labels for each alias.

The clinical paper reports 13 plasma samples (8 HIV and 5 herpes), while PEPerMINT/PRIDE expose 15 processed biological-sample aliases and 15 DDA/DIA acquisition pairs. The two-sample discrepancy remains unresolved. Do not promote the numeric alias pattern to a patient identity or phenotype assignment without submitter confirmation.


## Deterministic clinical-crosswalk validator

The model-free validator `oracle/clinical_mapping.py` now checks the 15 aliases against the published 13-participant clinical design without creating any labels. It requires raw DDA/DIA filenames, mapping rationale, source URL and a SHA-256 for the source document. It distinguishes primary clinical samples, technical replicates, repeated biological samples, QC, excluded and unresolved aliases. Only source-authenticated primary samples can enter HIV-versus-herpes or HAND-versus-cognitively-normal comparisons.

The validator expects the published clinical totals (8 HIV, 5 herpes; among HIV, 5 HAND and 3 cognitively normal) at the **unique-patient** level. It blocks technical/repeat aliases from being counted as independent participants and blocks all unverified rows from carrying phenotype labels. Synthetic unit tests are fixtures only; they are not a proposed or actual PXD047528 mapping.

Run when the submitter-authenticated TSV is received:

```bash
python -m oracle.clinical_mapping --mapping data/pxd047528/sample_map.tsv --output artifacts/pxd047528/clinical_mapping_validation.json
```

The current real sample-map template remains blank and the validator correctly returns BLOCKED until the authors provide the source manifest.


## ORACLE use boundary — technical benchmark only (2026-11-19)

PXD047528 is **not a human-longevity cohort**. It is retained in ORACLE only as a paired plasma-proteomics DDA/DIA technical benchmark for missing-value and assay-reconstruction methods. Its 2022 clinical labels concern HIV and herpes CNS infection, not longevity or healthy aging.

Consequences:

- DDA/DIA paired missingness and reconstruction metrics may be reported as a technical-method benchmark, with the processed-data provenance and limits stated.
- PXD047528 must not contribute evidence for human longevity mechanisms, age trajectories, longevity candidate ranking, or validation of the 8-mRPG signature.
- HIV/herpes/HAND clinical concordance is a separate, optional clinical reconstruction task and remains blocked until the 15 processed aliases, 15 raw acquisition pairs, and 13-person clinical paper are reconciled by a source-authenticated manifest.
- A successful technical missingness benchmark does not imply that its clinical labels are mapped or that the dataset validates longevity biology.

This boundary prevents a technically useful but biologically unrelated dataset from contaminating the longevity evidence graph. The public Mendeley Data API is being re-probed separately for the 2026 longevity cohort's expression matrix; no Mendeley file or sample manifest is considered acquired until the live API inventory and file contents are inspected and checksummed.

References:
- Ahmed et al. 2022, clinical proteomics study: https://pmc.ncbi.nlm.nih.gov/articles/PMC9945916/
- ProteomeXchange PXD047528: https://www.ebi.ac.uk/pride/archive/projects/PXD047528
- PEPerMINT benchmark: https://academic.oup.com/bioinformatics/article/40/Supplement_2/ii70/7749076
