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
