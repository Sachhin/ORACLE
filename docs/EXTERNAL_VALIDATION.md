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

## Real GEO reference datasets

The external validation workflow distinguishes cohorts from the same
publication from a genuinely independent study:

- **GSE176260** is the primary discovery cohort. The submitter deposited QCed
  counts and the exact `voom$E` and `voom$weights` matrices. ORACLE
  reconstructs the documented `~ 0 + phenotype + gender` design and compares
  both matrices numerically.
- **GSE176261** is the validation cohort from the *same* publication, not an
  independent study. It is a same-study cohort replication check only.
- **GSE64099** is a separate Smchd1 knockout-versus-wild-type mouse RNA-seq
  experiment, independent of the GSE176260 host-response cohort. Its public
  R object and original supplementary analysis are available from the
  voomWithQualityWeights authors. ORACLE reproduces the published CPM filter,
  TMM normalization, `~ genotype` design, voom, lmFit, and eBayes workflow,
  then compares stable GeneID-matched logFC values and significant-gene counts
  against the published top-table results. This is a published DE-result
  comparison, not a submitter-published E/weights matrix comparison.

A dataset is not marked passed until its live Actions run completes and the
JSON report artifact has been inspected.

## External limma-voom numerical runs (2026-11-06, refreshed)

The refreshed external-reference workflow completed all three dataset jobs
successfully in GitHub Actions run
[42248659262](https://github.com/Sachhin/ORACLE/actions/runs/42248659262).
The report artifacts include the downloaded source matrices, SHA-256 checksums,
and machine-readable comparison JSON.

- **GSE176260 discovery cohort — PASS** (138 samples, 11,111 features):
  expression RMSE 4.311e-15, MAE 2.677e-15, Pearson r 1.0000;
  voom weights RMSE 0.0478, Pearson r 0.9998.
- **GSE176261 same-study validation cohort — PASS** (53 samples,
  11,111 features; 588,883 matched values): expression RMSE 0.0397,
  MAE 0.0315, Pearson r 0.9999; voom weights RMSE 0.0412,
  MAE 0.0338, Pearson r 0.9998. The original thresholds remain unchanged:
  expression RMSE <=0.0500 and Pearson >=0.999; weights RMSE <=0.1000
  and Pearson >=0.99. The fix uses TMM factors estimated on the documented
  full batch-2 cohort, then subsets factors to the 53 validation samples.
  This is same-publication validation, not independent-study replication.
- **GSE64099 — PASS, independent experiment** (7 samples, 12,303 features
  after the published CPM filter): top-10 stable GeneID recall 1.00,
  logFC RMSE 0.0021, direction agreement 1.00, and FDR<0.05 / FDR<0.01
  significant-gene counts exactly reproduced (12 / 1). This is a published
  differential-expression table comparison, not a submitter-published
  full E/weights matrix comparison.

The GSE176261 version-sensitivity audit also completed in Actions run
[42248659455](https://github.com/Sachhin/ORACLE/actions/runs/42248659455):
both Bioconductor 3.13 and 3.22 independently report PASS for the same
53-sample cohort and unchanged expression thresholds. Bioconductor 3.13
voom weights RMSE was 0.0188 (Pearson 0.9998); Bioconductor 3.22 weights
RMSE was 0.0412 (Pearson 0.9998). Both satisfy the declared weights
thresholds. The report records runtime/package versions and source hashes.

These reproducibility checks do not establish biological correctness,
generalization to all RNA-seq workflows, or model superiority. GSE176260
and GSE176261 are related cohorts from the same study; GSE64099 supplies
the independent-study check.

## What this tooling does not claim

A successful comparator run means only that the supplied outputs were compared
under the declared matching rules. It does not establish reference quality,
biological correctness, model superiority, or causal validity. Real reference
outputs and independent human annotations remain required to publish empirical
validation results.
