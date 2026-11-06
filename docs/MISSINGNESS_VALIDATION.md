# Genuine missing-measurement validation

ORACLE's synthetic MCAR/MAR/MNAR masking and observed-cell holdout tests are
useful software checks, but they are not evidence about real missing
measurements. This validation path accepts paired measurements from two
acquisition methods (for example, DDA and DIA mass spectrometry), where the
orthogonal assay supplies a measurement for a cell missing from the primary
assay.

## Inputs

All matrices are tab-separated, with the first column containing stable feature
IDs and remaining columns containing identical sample IDs.

- `observed.tsv`: original assay matrix; missing cells must remain empty/NA.
- `orthogonal.tsv`: paired independent assay matrix, such as DIA.
- `imputed.tsv`: ORACLE output for the observed matrix. Values originally
  observed must be preserved exactly (within 1e-8).
- `labels.tsv`: columns `sample_id` and an independent two-class biological
  outcome (for example, disease/control).

The evaluator scores only cells genuinely missing in the primary assay for
which the orthogonal assay has a measurement. It estimates per-feature
additive DIA-to-DDA offsets from at least two overlapping observed cells, with
a global median fallback, and reports MAE, RMSE, Pearson correlation, and
signed bias on the real missing cells. It also compares two-group feature
effect sizes from the imputed primary matrix with those from the aligned
orthogonal matrix, reporting effect correlation, direction agreement, and
top-effect overlap.

## Run

```bash
python -m oracle.missingness_validation \
  --observed observed.tsv \
  --orthogonal paired_dia.tsv \
  --imputed oracle_imputed.tsv \
  --labels sample_outcomes.tsv \
  --outcome-column phenotype
```

## PXD047528 processed DDA/DIA preparation

The PEPerMINT authors' Zenodo archive (record 11216899) contains the
processed peptide tables at:

- `datasets/blood_hiv_dda_dia/dda/peptides.tsv`
- `datasets/blood_hiv_dda_dia/dia/peptides.tsv`

It also contains the paired `dda/proteins.tsv` and `dia/proteins.tsv`
files. The PEPerMINT loader uses sample columns `1_Slot1` through
`15_Slot1`, groups duplicate peptide sequences by summing available values,
converts zero-sum values to missing, scales DIA to the DDA global mean, and
log-transforms both matrices. ORACLE reproduces that preparation in
`scripts/prepare_pxd047528_missingness.py`.

After downloading and extracting the Zenodo `data.zip`, run:

```bash
python scripts/prepare_pxd047528_missingness.py \
  --dda-peptides data/datasets/blood_hiv_dda_dia/dda/peptides.tsv \
  --dia-peptides data/datasets/blood_hiv_dda_dia/dia/peptides.tsv \
  --output-dir validation/pxd047528
```

This produces DDA observed, DIA orthogonal-reference, row-median-imputed DDA,
a sample-map template, and a hashed preparation manifest. The deterministic
row-median output is a baseline, not a claim that ORACLE has discovered a
superior imputer. ORACLE can now score the real missing DDA cells before
clinical labels are resolved:

```bash
python -m oracle.missingness_validation \
  --observed validation/pxd047528/observed_dda_log.tsv \
  --orthogonal validation/pxd047528/orthogonal_dia_log.tsv \
  --imputed validation/pxd047528/row_median_imputed_dda_log.tsv
```

That reconstruction-only report is explicitly marked
`RECONSTRUCTION_ONLY_LABELS_PENDING`. To add biological outcome concordance,
first complete `sample_map_template.tsv` from source-level clinical metadata,
resolve the 15 processed sample columns versus the original paper's 13
participants, document excluded/QC/technical samples, then pass a complete
two-class label file using `--labels` and `--outcome-column`.

The original clinical paper describes 13 plasma samples (8 HIV and 5 herpes)
and a within-HIV HAND comparison of 5 HAND cases versus 3 cognitively normal
participants. The PEPerMINT loader explicitly uses the same 15 sample aliases for both DDA
and DIA matrices and attaches DIA peptide abundances as the DDA dataset's
`abundance_gt`; therefore the processed files are paired at the shared-alias
level. ORACLE verified 8,859 DDA-missing cells with corresponding DIA values.
However, the aliases `1_Slot1` through `15_Slot1` are not mapped to clinical
participant IDs in the loader or processed tables. The original paper reports
13 clinical participants, so ORACLE must not assign HIV/herpes/HAND labels by
column order or filename. The original study used DDA to build the spectral
library and DIA for identification/quantification; DIA is an orthogonal
reference for this imputation benchmark, not error-free absolute truth.

## Empirical PXD047528 run (2026-11-06)

The GitHub Actions run [42229479296](https://github.com/Sachhin/ORACLE/actions/runs/42229479296)
successfully downloaded the processed peptide matrices from the PEPerMINT
Zenodo archive, prepared the paired assay tables, and completed reconstruction-
only scoring. The frozen artifact reports:

- 15 shared sample aliases and 2,170 shared peptide features.
- 13,043 DDA missing cells; 8,859 have a non-missing DIA value (67.92% coverage).
- 18,768 paired observed cells used for per-feature DIA-to-DDA offset alignment.
- Row-median baseline on the 8,859 evaluable cells: MAE 1.1382, RMSE 1.4675,
  Pearson r 0.2503, mean signed error +1.0669.

This is an actual baseline result on deposited processed matrices, not an
ORACLE-learned imputer result and not a claim of imputation superiority. The
large positive signed bias and modest correlation are warnings that the
row-median baseline is weak on this dataset. Biological-outcome concordance
was not calculated. The artifact contains the input/output SHA-256 hashes and
blank 15-row sample map. Clinical labels remain blocked until the 15-to-13
sample discrepancy and DDA/DIA-to-patient mapping are resolved from source
records.

## Candidate public data

PEPerMINT (Bioinformatics, 2024; DOI 10.1093/bioinformatics/btae389)
explicitly distinguishes synthetic masked-value proxies from genuine
DDA-missing/DIA-observed measurements. Its B2 benchmark table reports
PXD047528 with 15 samples, 2,535 peptides, 435 proteins, and 41.8%
peptide-level missingness. **There is a material sample-count discrepancy
that must be resolved before analysis:** the original Ahmed et al. clinical
paper reports 13 plasma samples (8 HIV and 5 herpes-virus), whereas the
PEPerMINT benchmark reports 15 samples and its public loader enumerates
15 sample aliases. These counts must not be silently reconciled or assumed
equivalent. The original paper's HAND analysis is a within-HIV comparison of
5 HAND cases (3 MND, 2 HAD) against 3 cognitively normal PWH; it is not a
15-sample-wide independent label. Freeze a sample-level mapping only after
matching each assay's raw/processed file identifiers to the clinical cohort
table and documenting any extra samples or exclusions.

The original paper states that DDA runs were used to build a spectral library
and DIA runs were used for identification and quantification. This supports
the biological rationale for orthogonal DDA/DIA evaluation, but it does not by
itself establish that the deposited processed files are paired on identical
sample IDs or that each DDA-missing peptide has a DIA measurement.

Sources:
- PEPerMINT benchmark paper:
  https://academic.oup.com/bioinformatics/article/40/Supplement_2/ii70/7749076
- PXD047528 ProteomeXchange record:
  https://proteomecentral.proteomexchange.org/cgi/GetDataset?ID=PXD047528-1&test=no
- Original HIV plasma proteomics paper DOI: 10.1007/S13365-022-01077-0

Before running, inspect the complete PRIDE file manifest and confirm that it contains
processed, sample-paired DDA and DIA abundance tables (not just raw mass
spectrometry files). The currently indexed PRIDE/OmicsDI view exposes 32 files,
with the first visible entries being raw DDA files; that partial view is not
proof that the processed matrices are present. Verify the complete manifest,
downloaded file hashes, one-to-one assay pairing, peptide/protein keys,
normalization scale, and the 13-versus-15 sample discrepancy. Obtain clinical
labels from the original study's cohort table and document inclusion/exclusion
rules. Do not use filenames as phenotype labels. Preserve the original DDA missingness mask; do not convert
zero abundance to missing or treat unobserved peptides as measured zeros.
The PEPerMINT article also describes a HeLa/E. coli mixture dataset
(PXD000279) with known organism spike-in ratios, which may support a separate
downstream differential-abundance ground-truth check but is not a substitute
for the real-missing-cell HIV benchmark.

The evaluator does not download or infer labels. It rejects mismatched sample
or feature identifiers and records SHA-256 hashes for every input. DIA is an
orthogonal reference, not a perfect physical truth; outcome association is not
causality. No benchmark is considered empirically complete until the public
raw/processed data, sample pairing, biological labels, and provenance have
been independently checked.
