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
