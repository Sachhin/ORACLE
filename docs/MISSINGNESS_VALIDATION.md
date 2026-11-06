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
