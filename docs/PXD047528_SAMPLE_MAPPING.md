# PXD047528 clinical sample mapping status

## What is verified

- The ORACLE preparation workflow uses the PEPerMINT example tables for
  `datasets/blood_hiv_dda_dia` from Zenodo record 11216899.
- The prepared DDA and DIA tables contain 15 matching sample aliases:
  `1_Slot1` through `15_Slot1`.
- The frozen paired-assay report scores 8,859 DDA-missing cells that have a
  paired DIA value (67.9% of 13,043 DDA-missing cells).
- The PEPerMINT publication describes 15 processed samples, while the
  original Ahmed et al. clinical paper reports 13 plasma participants:
  8 HIV and 5 herpes; the HIV HAND sub-analysis has 5 HAND and 3 cognitively
  normal participants.

## Why clinical outcome validation is still blocked

No public source inspected so far authenticates the mapping from the 15
processed aliases to the 13 clinical participants. The `Slot1` aliases do
not encode phenotype. ORACLE must not infer patient labels from filenames,
sample order, abundance patterns, or aggregate group counts.

This is a data-provenance blocker, not a missing feature. A blank sample-map
template is deliberately retained until a submitter-authenticated crosswalk
is supplied.

## New automated crosswalk validator

`oracle.clinical_mapping` now validates a supplied tab-separated manifest.
It requires all 15 aliases, 13 distinct patient identifiers, 8 HIV and 5
HERPES patients, and the published 5 HAND / 3 cognitively-normal HIV split.
Every row must cite its raw acquisition file(s), source reference, and a
64-character SHA-256 digest of the source manifest.

Run:

```bash
python -m oracle.clinical_mapping --mapping sample_map.tsv --output clinical_mapping_report.json
```

The status `READY_FOR_CLINICAL_VALIDATION` means only that the crosswalk
passes structural and provenance checks. Biological outcome concordance must
still be recomputed from the frozen mapping and paired DDA/DIA results.
Synthetic test fixtures are never valid clinical labels.

## Required external evidence

Obtain a source-authenticated sample manifest from the dataset submitter or
original study records that maps every processed alias to:
- raw acquisition filename(s) and DDA/DIA pairing;
- unique patient/sample identifier;
- HIV versus herpes phenotype;
- for HIV samples, HAND versus cognitively-normal status where documented;
- technical replicate or exclusion status, with rationale.

If the 15 aliases cannot be mapped unambiguously to the 13 clinical
participants, retain the reconstruction-only result and report clinical
concordance as unavailable.

## Sources

- ProteomeXchange PXD047528: https://proteomecentral.proteomexchange.org/cgi/GetDataset?ID=PXD047528
- Ahmed et al. 2022, PMID 35639337, PMCID PMC9945916:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC9945916/
- PEPerMINT benchmark paper, Table 2:
  https://academic.oup.com/bioinformatics/article/40/Supplement_2/ii70/7749076
- PEPerMINT example data source: Zenodo record 11216899,
  https://zenodo.org/records/11216899
