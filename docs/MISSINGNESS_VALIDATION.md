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
and DIA runs were used for identification and quantification. The processed
PEPerMINT matrices are paired by the shared 15 aliases: its loader reads the
same sample columns from both assay tables and explicitly aligns DIA values
to DDA peptide/sample keys. The actual reconstruction-only run found 8,859
DDA-missing cells with a DIA measurement. This establishes processed-table
pairing and evaluable missing cells, not clinical participant identity.

Sources:
- PEPerMINT benchmark paper:
  https://academic.oup.com/bioinformatics/article/40/Supplement_2/ii70/7749076
- PXD047528 ProteomeXchange record:
  https://proteomecentral.proteomexchange.org/cgi/GetDataset?ID=PXD047528-1&test=no
- Original HIV plasma proteomics paper:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC9945916/

The processed PEPerMINT matrices have been downloaded from Zenodo and hashed;
the exact shared peptide/sample keys and 15 DDA/DIA sample aliases were checked
by the preparation script. The PRIDE project page describes 15 submitted
samples, while the original clinical paper reports 13 participants: 8 HIV
(5 HAND and 3 cognitively normal) and 5 herpes-virus cases. Its Table 1
provides clinical categories and demographic descriptors but does not provide
a crosswalk from those patient records to PEPerMINT's numbered `n_Slot1`
aliases. The public PRIDE file list includes raw acquisitions, but the
processed abundance matrices used here come from the PEPerMINT Zenodo archive.
The clinical crosswalk, and therefore HIV/herpes/HAND labels for the 15
processed columns, remains unresolved. Do not infer labels from filenames,
column order, age/sex similarity, or assumed sample counts. Preserve the
original DDA missingness mask; document the PEPerMINT zero-to-missing
preprocessing separately from raw clinical interpretation.
The PEPerMINT article also describes a HeLa/E. coli mixture dataset
(PXD000279) with known organism spike-in ratios, which may support a separate
downstream differential-abundance ground-truth check but is not a substitute
for the real-missing-cell HIV benchmark.

## PXD000279 controlled-mixture missingness benchmark

A second, complementary validation path uses the MaxQuant
`proteinGroups.txt` output from the public PXD000279
`proteomebenchmark.zip` archive. The Cox et al. experiment mixed a fixed
a fixed HeLa background with either 10 or 30 micrograms of E. coli
lysate, with three replicates per mixture. The raw run names contain
"HeLa60", while the DEqMS vignette describes 50 micrograms of human extract;
the benchmark therefore relies on the independently documented relative
E. coli spike-in ratio rather than assuming the HeLa mass from the filename. Therefore the expected Ecoli30
versus Ecoli10 log2 fold change is 0 for unambiguous human proteins and
log2(3) for unambiguous E. coli proteins. The publication describes
protein-level inclusion requiring non-zero intensity in at least two of
three replicates in each condition.

The archive's LFQ headers are run identifiers rather than mixture labels.
ORACLE uses explicit condition labels when available; otherwise it applies
the published PXD000279 DEqMS column contract: proteinGroups columns 89–91
are the first three H replicates and columns 92–94 are the final three L
replicates. The published DEqMS contrast is H-L, and its example reports
positive E. coli log2 fold changes (for example, P0A8V2 logFC +1.291).
Therefore H is the high-spike Ecoli30 group and L is the low-spike Ecoli10
group. ORACLE's initial run #21 had this mapping reversed; its negative
E. coli effects exposed the sign inconsistency. The implementation has now
been corrected and the benchmark must be rerun before numerical results are
accepted. If the six-column contract is absent, the evaluator stops instead
of guessing. Reference:
https://rdrr.io/github/yafeng/DEqMS/f/vignettes/DEqMS-package-vignette.Rmd


The corrected runner evaluates the same eligible protein universe
using three downstream-effect strategies:

- observed-only log2 LFQ values (no imputation);
- per-protein row-median imputation;
- a deterministic left-censored MinProb baseline, with fixed seed.

It reports per-species protein counts, median estimated log2 fold change,
MAE/RMSE from the known mixture ratio, fraction within 0.5 log2 units,
the deposited missing fraction, input SHA-256, and skipped-row counts.

Run locally after downloading and extracting the public MaxQuant output:

```bash
python scripts/benchmark_pxd000279_mixture.py \
  --input data/pxd000279/proteinGroups.txt \
  --output data/pxd000279/known-mixture-report.json
```

GitHub Actions downloads the published archive, runs the evaluator and
offline tests, then uploads a frozen report and source archive. The first
live run (2026-11-06, run 42251562908) completed technically but revealed the
H/L direction error described above; it is not an accepted benchmark result.
The corrected group direction was independently recomputed from the exact
same deposited proteinGroups.txt (SHA-256
d245d4dc5b7ccc1a75eb21d36d89ed3fd1ace01ca858bd8eef9d65e3cc1411ea) using
the corrected H=Ecoli30, L=Ecoli10 assignment. It yielded 5,019 eligible
proteins and the same 612/30,114 missing cells (2.03%). Corrected median
Ecoli30-versus-Ecoli10 effects were +1.2188 (observed-only), +1.2053
(row-median), and +1.2262 (MinProb), versus the published expected +1.585.
Human medians were -0.5097, -0.5039, and -0.5491, respectively, versus
expected 0. Corrected MAE/RMSE were:

| Species | Method | MAE | RMSE |
|---|---|---:|---:|
| Human | Observed-only | 0.5559 | 0.6531 |
| Human | Row-median | 0.5415 | 0.6326 |
| Human | MinProb | 0.8705 | 1.3616 |
| E. coli | Observed-only | 0.4624 | 0.5774 |
| E. coli | Row-median | 0.4716 | 0.5840 |
| E. coli | MinProb | 0.6123 | 0.9831 |

This corrected calculation verifies the sign and shows that all three
methods recover a positive E. coli effect, but they under-recover the
published 3-fold ratio and show a systematic negative human offset. It is a
scored benchmark, not a PASS claim; investigate normalization/MaxLFQ behavior
and predeclare any acceptance tolerance before making a validation claim.
The corrected GitHub Actions artifact still needs to be generated from the
updated branch and inspected. The workflow
is defined in `.github/workflows/pxd000279-known-mixture.yml`.

This is a known biological mixture-ratio check under real deposited LFQ
missingness. It evaluates downstream species-level effect recovery; it does
not reveal exact individual missing-cell abundances. It complements, but
does not replace, PXD047528's paired DDA/DIA cell-level reconstruction
benchmark. Do not interpret it as proof that one imputation method is
universally superior.

The evaluator does not download or infer labels. It rejects mismatched sample
or feature identifiers and records SHA-256 hashes for every input. DIA is an
orthogonal reference, not a perfect physical truth; outcome association is not
causality. No benchmark is considered empirically complete until the public
raw/processed data, sample pairing, biological labels, and provenance have
been independently checked.
