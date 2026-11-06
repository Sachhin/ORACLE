# External scientific reference validation

ORACLE can compare its tab-separated outputs with a separately generated,
trusted reference without inventing or silently downloading reference labels.
The comparator records SHA-256 hashes and requires reference provenance.

## Real external limma-voom reference: GSE176260

A reproducible live validation workflow is provided at
`.github/workflows/limma-external-reference.yml`. It downloads the three
submitter-supplied discovery-cohort files from NCBI GEO:

- `GSE176260_QCed_counts_discovery.txt.gz` — processed integer count matrix
- `GSE176260_Log2_normalized_expression_discovery.txt.gz` — published
  `limma::voom` expression matrix (`E`)
- `GSE176260_Voom_weights_discovery.txt.gz` — published observation-level
  precision weights

The workflow retrieves the GEO sample metadata, selects only samples marked
`discovery_analysis_sample: Yes`, verifies exact sample identity/order, and
recomputes the published design `~ 0 + phenotype + gender` with edgeR TMM and
limma voom. It then compares the recomputed expression matrix and precision
weights with the independently submitted GEO outputs. The report records
input SHA-256 hashes, R/GEOquery/edgeR/limma versions, cohort dimensions, and
MAE/RMSE/bias/Pearson correlation for both matrices. Raw files and the JSON
report are retained as a GitHub Actions artifact.

Run it from GitHub Actions using the workflow-dispatch control, or let the
path-filtered workflow run after changes to the workflow or R script:

https://github.com/Sachhin/ORACLE/actions/workflows/limma-external-reference.yml

Dataset and source provenance:

- GEO series: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE176260
- Associated publication: PMID 34225776
- Platform: GPL24676, human whole-blood RNA-seq
- Published analysis design: `~ 0 + phenotype + gender`

This is an external real-dataset reproducibility check of the published voom
expression and precision-weight outputs. It is not evidence that the adapter
is accurate on every dataset, that the original biological labels are correct,
or that ORACLE has discovered causal mechanisms. The roadmap item remains
pending until a successful run and artifact inspection establish exact sample,
feature, and numerical agreement. A second independent dataset is still
needed before claiming general external validation.

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

## Live GEO limma-voom reference checks

The `limma-external-reference.yml` workflow downloads and hashes the
submitter-published count, log2-expression, and voom-weight matrices for
GSE176260, reconstructs the published discovery-sample design
`~ 0 + phenotype + gender`, and compares recomputed expression and precision
weights against the frozen GEO matrices. It resolves the short sample aliases
from the leading token of each GEO title (for example, `9A4D98` from
`9A4D98 RNA-seq [discovery cohort]`) and requires exact one-to-one identity
matching. It does not infer missing phenotype or gender labels.

GSE176261 is a separate validation cohort from the same publication and
SuperSeries, not an independent study. It is run only after GSE176260 passes.
A passing result on these two cohorts strengthens within-study replication but
does not satisfy the roadmap requirement for a second independent publication
or laboratory. That additional external study remains required.

Artifacts include source matrices, SHA-256 checksums, software versions,
sample accession mapping, cohort composition, numerical comparison metrics,
and explicit acceptance thresholds. A failed sample mapping or numerical
threshold blocks the job; it must not be bypassed by loosening tolerances
without documented scientific justification.

## Expert answer and evidence benchmark data

Human benchmark scores must come from independent reviewers, not generated
defaults. Keep each case's frozen source packet and SHA-256, question,
prompt/model versions, rubric, reviewer IDs, per-reviewer scores, and
adjudication rationale. For paired system comparisons, each reviewer scores
both baseline and candidate while blinded to system identity where practical.
Use the existing benchmark validators to reject missing reviewer pairs or
unadjudicated disagreements. Store raw annotations separately from aggregate
reports so results can be audited.

## What this tooling does not claim

A successful comparator run means only that the supplied outputs were compared
under the declared matching rules. It does not establish reference quality,
biological correctness, model superiority, or causal validity. Real reference
outputs and independent human annotations remain required to publish empirical
validation results.
