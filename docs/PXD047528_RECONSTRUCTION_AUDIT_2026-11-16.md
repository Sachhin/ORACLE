# PXD047528 reconstruction and provenance audit

Audit date: 2026-11-16  
GitHub Actions run: [43884078275](https://github.com/Sachhin/ORACLE/actions/runs/43884078275)  
Artifact ID: `14233687625` (`oracle-pxd047528-real-missingness-preparation`)

## Frozen source and preparation

The workflow fetched only four selected TSV members from PEPerMINT Zenodo record [11216899](https://zenodo.org/records/11216899), using HTTP Range rather than downloading the complete 3.7 GB archive. The paired DDA/DIA peptide tables contained 15 aliases (`1_Slot1` through `15_Slot1`).

- DDA source rows / unique peptide sequences: 3,366 / 3,366
- DIA source rows / unique peptide sequences: 3,824 / 2,779
- Shared peptides retained for evaluation: 2,170
- DDA-only peptides excluded: 590
- DIA-only peptides excluded: 3
- DDA genuine missing cells: 13,043
- Of those, paired DIA measurements existed for 8,859 (67.92%)
- Paired observed cells used for assay alignment: 18,768
- DIA-to-DDA global mean scale factor recorded by preparation: 2.971246202864775

Source table SHA-256:
- DDA peptides TSV: `85cd87d908b6b3bf4bfc3fb8ff958dfbdb708315feb5770213627bad312c4362`
- DIA peptides TSV: `d73ebebfdeae9ea057924d633a480f18e7400c79031d3319c705de78441b2864`

Prepared matrices:
- Observed DDA log matrix: `28c566e3e0f865bd42f79ca9bd353e81bbd388da51c6144ed5d4b24ae2bd0d25`
- Orthogonal DIA log matrix: `7b8df097f603080a1ace39313ee663b5e926f6d6d2c4feeb7f712bd890abceb4`
- Row-median imputed matrix: `94077f49c0ae8b28bfc792ecc1e920724e17eb3d5ecaf450883d177174ac8b14`
- KNN imputed matrix: `07454c4515ca5616a8fdba29ddcd78995072f7f0259655e1a10d6db061e4c2ea`

## Reconstruction results

The validator scored only genuine DDA-missing cells for which the paired DIA assay had a value. DIA values were aligned to DDA using per-feature median offsets when at least two paired observed cells existed, with a global median fallback otherwise.

| Imputer | MAE | RMSE | Pearson r | Mean signed error |
|---|---:|---:|---:|---:|
| Row-median baseline | 1.1382 | 1.4675 | 0.2503 | +1.0669 |
| Sample-neighbour KNN | 1.0981 | 1.4259 | 0.2625 | +1.0201 |

KNN modestly improves the reported reconstruction metrics over the row-median baseline on this frozen comparison. However, both methods show a substantial positive mean signed error and low correlation with the aligned DIA reference. This should be treated as a weak reconstruction result, not a strong imputation success. The KNN workflow reports that all observed cells were preserved and all 13,043 missing cells were imputed without median fallback.

## Critical limitations

1. DIA is an orthogonal assay reference, not error-free absolute ground truth.
2. Only 8,859 of the 13,043 DDA-missing cells had a DIA value and entered the scored set. Coverage is 67.92%, so results do not describe every missing cell.
3. Per-feature additive offset alignment is an assumption; it does not prove the assays are biologically interchangeable.
4. The benchmark is reconstruction-only. No phenotype or clinical outcome column was supplied.
5. The live PRIDE API inventory is 30 RAW files (15 DDA + 15 DIA acquisitions) plus one SEARCH report, 31 files total. The 15 raw DDA/DIA pairs share suffixes but those suffixes do not map to the processed 1_Slot1 through 15_Slot1 aliases.
6. The downloaded 113,569-byte SEARCH report contains 15 HIVPCA1–HIVPCA15 protein-group quantity columns, but no authenticated crosswalk to the processed aliases, raw suffixes, or clinical participants.
7. The 15 processed aliases remain unmapped to the 13 clinical participants reported in Ahmed et al. (2022). The PEPerMINT paper lists 15 samples and 15 biological samples, so the discrepancy remains unresolved.
8. The sample-map template is deliberately blank. No patient identity, HIV/herpes label, or HAND status was inferred.

## Clinical provenance gate

**BLOCKED.** A source-authenticated manifest is still required for every processed alias, including raw DDA/DIA filenames, patient/sample ID, phenotype, HAND subgroup where applicable, alias-to-patient relationship, rationale, source URL and source-document checksum. The repository validator checks completeness and consistency of such a manifest but cannot independently authenticate the submitter or clinical truth.

The submitter request is recorded in `docs/PXD047528_SUBMITTER_METADATA_REQUEST.md`. A draft request has been prepared for the public dataset submitter; it has not been sent.

## Decision

- Real missingness preparation: **PASS**
- Reconstruction evaluation against paired DIA where available: **COMPLETED, WEAK/EXPLORATORY**
- Strong imputation validation: **NOT ESTABLISHED**
- Clinical alias-to-patient mapping: **BLOCKED**
- HIV-versus-herpes and HAND outcome concordance: **NOT RUN**
- Clinical or causal interpretation: **NOT PERMITTED**

Do not convert a successful preparation workflow into a clinical-validation pass.
