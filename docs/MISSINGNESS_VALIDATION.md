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

PEPerMINT (Bioinformatics, 2024) describes six proteomics benchmark datasets
and explicitly distinguishes masked-value proxies from genuine missingness.
Its B1/B2 datasets use DDA measurements with orthogonal DIA measurements;
B2 is an HIV blood dataset (PXD047528) with 15 biological samples. The paper
also includes a mixture dataset with known organism spike-in ratios for
downstream differential-abundance checks. Dataset choice, download URLs,
sample-to-sample pairing, feature mapping, acquisition settings, and the
published HIV outcome metadata must be verified before any score is reported.

The evaluator does not download or infer labels. It rejects mismatched sample
or feature identifiers and records SHA-256 hashes for every input. DIA is an
orthogonal reference, not a perfect physical truth; outcome association is not
causality. No benchmark is considered empirically complete until the public
raw/processed data, sample pairing, biological labels, and provenance have
been independently checked.
