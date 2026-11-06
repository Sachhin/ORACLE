# External scientific reference validation

ORACLE can compare its tab-separated outputs with a separately generated,
trusted reference without inventing or silently downloading reference labels.
The comparator records SHA-256 hashes and requires reference provenance.

## Required provenance

Create a JSON file such as `reference-provenance.json`:

```json
{
  "dataset_accession": "GSE000000",
  "reference_method": "RMA / limma-voom / other exact method",
  "software": "R x.y.z; affy x.y.z; hgu133a.db x.y.z",
  "source_url": "https://...",
  "platform": "GPL96 / platform identifier",
  "contrast": "treated minus control",
  "notes": "Frozen reference output; record filtering and annotation versions."
}
```

The first four fields are mandatory. Record platform, contrast, sample
accessions, preprocessing, probe-to-gene mapping, and filtering in notes or
additional fields. Never compare matrices from different sample identities or
platforms as if they were equivalent.

## Compare RMA / expression matrices

Both TSV files must have the same first-column feature-ID header and exactly
the same sample columns. Rows are feature IDs; columns are samples.

```bash
python -m oracle.external_validation expression \
  --oracle oracle-rma.tsv \
  --reference trusted-platform-matched-rma.tsv \
  --provenance-json reference-provenance.json \
  --minimum-overlap 0.8 \
  --output rma-reference-report.json
```

The report includes matched feature fraction, per-sample and pooled MAE, RMSE,
signed error, Pearson correlation, Spearman rank correlation, and both file
hashes. Probe identifiers must be harmonized before comparison. If a reference
uses gene symbols, map both outputs with the same versioned annotation first.

## Compare differential-expression tables

Default columns are ORACLE `feature/log2fc/padj` and reference
`feature/logFC/adj.P.Val`. Both tables must describe the same samples,
contrast direction, design, feature universe, and filtering policy.

```bash
python -m oracle.external_validation de \
  --oracle oracle-de.tsv \
  --reference trusted-limma-de.tsv \
  --provenance-json reference-provenance.json \
  --fdr 0.05 \
  --minimum-overlap 0.8 \
  --output de-reference-report.json
```

Reports log-fold-change MAE/RMSE/correlation and significant-feature
precision, recall, F1, Jaccard, and confusion counts. P-values can differ
legitimately across statistical models; do not interpret disagreement alone
as evidence that one method is wrong.

## Expert answer and evidence benchmark data

Human benchmark scores must come from independent reviewers, not generated
defaults. Keep each case's frozen source packet and SHA-256, question,
prompt/model versions, rubric, reviewer IDs, per-reviewer scores, and
adjudication rationale. For paired system comparisons, each reviewer scores
both baseline and candidate while blinded to system identity where practical.
Use the existing benchmark validators to reject missing reviewer pairs or
unadjudicated disagreements. Store raw annotations separately from aggregate
reports so results can be audited.

## External limma-voom numerical runs (2026-11-06)

Two real external datasets have passed numerical checks in the ORACLE
validation branch:

- **GSE176260 discovery cohort** (138 samples, 11,111 features): recomputed
  expression matrix versus submitter-published GEO expression matrix had
  RMSE 4.31e-15, MAE 2.68e-15, and Pearson r 1.0000. Recomputed voom weights
  versus submitter-published weights had RMSE 0.0478 and Pearson r 0.9998.
  This is a direct full-matrix reference comparison.
- **GSE64099 Smchd1 knockout versus wild type** (7 samples; 12,303 features
  after the published CPM filter): the reproduced top ten stable GeneID
  results had recall 1.00, logFC RMSE 0.0021, and direction agreement 1.00;
  the recomputed FDR<0.05 and FDR<0.01 counts exactly matched the published
  values (12 and 1). This is an independent dataset comparison against the
  published DE table, not a submitter-published E/weights matrix.

The GSE176261 validation cohort belongs to the same publication as GSE176260,
so it is not counted as an independent study. Its first numerical run gave
expression RMSE 0.0580 (pre-set maximum 0.0500), Pearson r 0.9999, and weight
RMSE 0.0471; the expression comparison therefore did **not** pass the
pre-set tolerance. This result must not be relabelled as a pass by relaxing
the threshold after seeing the data. Further investigation is pending.

## What this tooling does not claim

A successful comparator run means only that the supplied outputs were compared
under the declared matching rules. It does not establish reference quality,
biological correctness, model superiority, or causal validity. Real reference
outputs and independent human annotations remain required to publish empirical
validation results.
