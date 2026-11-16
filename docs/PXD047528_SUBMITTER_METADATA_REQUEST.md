# PXD047528 submitter metadata request

**Subject:** Request for PXD047528 sample-level clinical crosswalk and clarification of 15-versus-13 sample counts

Dear Dr. Ahmed and Dr. Steen,

I am working on a reproducible reanalysis of the public PXD047528 plasma-proteomics dataset and its paired DDA/DIA processed tables.

I found a sample-count discrepancy that I do not want to resolve by assumption: the 2022 clinical paper reports 13 plasma samples (8 people with HIV and 5 with herpes infection), while the PEPerMINT benchmark publication lists PXD047528 as 15 samples and 15 biological samples, with one technical replicate per biological sample. The PRIDE record also lists 32 raw files. These sources do not currently establish how the 15 processed aliases relate to the 13 participants in the clinical paper.

Would you be able to share, or point me to, a source-authenticated manifest that maps each processed alias (`1_Slot1` through `15_Slot1`) to:
- the corresponding raw DDA and DIA acquisition filenames;
- the original participant/sample identifier, where applicable;
- HIV versus herpes phenotype;
- for HIV participants, the documented HAND/MND/HAD/cognitively-normal classification, where available;
- whether each alias is a primary sample, technical replicate, repeat acquisition, QC sample, additional biological sample, or excluded sample;
- the reason and source record supporting that relationship.

In particular, could you clarify whether all 15 processed biological samples belong to the same 13-participant clinical cohort, whether the processed dataset is broader or from a different data version, and how any additional samples should be interpreted? A data dictionary and the exact sample-to-clinical-table mapping would be extremely helpful.

I will preserve the source citation and checksum, will not infer participant identities or phenotype labels from filenames or sample order, and will use the metadata only for reproducible scientific analysis. If some variables cannot be shared, please let me know which fields are available under the repository's data-access policy.

Thank you for your time and for making the dataset available.

Best regards,

[Your name]

---

## Maintainer notes

- Clinical paper: Ahmed et al. 2022, PMID 35639337, DOI 10.1007/s13365-022-01077-0.
- ProteomeXchange: PXD047528.
- PEPerMINT publication, Table 2: PXD047528 is listed as 15 samples / 15 biological samples.
- PEPerMINT example data: Zenodo record 11216899.
- Do not send any synthetic or guessed crosswalk. Clinical outcome validation remains blocked until the submitter's explanation and sample-level manifest are received and checked.
