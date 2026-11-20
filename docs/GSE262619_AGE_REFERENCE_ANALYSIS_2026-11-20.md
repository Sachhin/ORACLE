# GSE262619 source-authenticated age-reference analysis (2026-11-20)

## Status

**Source bundle: PASS. Exploratory analysis: COMPLETE. Longevity replication: NOT TESTED.**

- Pull request: https://github.com/Sachhin/ORACLE/pull/170
- Source/analysis workflow: https://github.com/Sachhin/ORACLE/actions/runs/44684207732
- Immutable workflow artifact: `oracle-gse262619-source-bundle` (artifact ID `14605711817`, expires 2027-02-18)
- Analysis software: R, edgeR TMM normalization, limma-voom, robust empirical Bayes.
- Cohort: 35 healthy human peripheral-blood leukocyte samples, exact ages 22–88; 17 female and 18 male based on GEO submitter title suffixes.

## Source authentication and provenance

The workflow downloaded the official NCBI GEO files:
- `GSE262619_Raw_count.txt.gz`: 6,481,253 bytes; SHA-256 `bb943c6989c3d4fc52a901ccc9d2b2f73fc3034d25a8b9db571d08f89f64049d`.
- `GSE262619_family.soft.gz`: 4,413 bytes; SHA-256 `9c8de775e239b0a608194c6cfc3cb81f04ba54890473136606085d24691a8774`.
- Frozen 35-sample manifest SHA-256: `beb718e76db6f8d610c1d44215f4446fd8995f491b8261bf4176d7541c9f1305`.

Checks:
- 35 unique GEO GSM records.
- 35/35 samples linked to the count matrix by exact submitter sample title.
- Count table: 172,043 data rows × 37 columns (gene ID, gene name, 35 sample columns).
- All 35 records had explicitly labelled age characteristics. GEO SOFT had no explicit sex characteristic; sex was taken only from the `_F`/`_M` sample-title suffix and is labelled as title-derived.
- Age groups from sample titles: 30y n=11 (mean 27.5, SD 2.54), 60y n=10 (mean 60.4, SD 2.22), 75y n=14 (mean 80.5, SD 4.57).

## Prespecified 8-mRPG analysis

The published prior-art panel was tested exactly:
`MRPL3, MRPL32, MRPL42, MRPL45, MRPL50, MRPS10, MRPS33, MRPS35`.

Method:
1. Match count columns to the source-authenticated sample titles.
2. Aggregate count rows by exact submitter `gene_name` symbol (37,804 symbols after aggregation).
3. Apply edgeR TMM normalization and limma-voom.
4. Fit a continuous-age model adjusted for title-derived sex (`age_years + sex`).
5. Compute transcriptome-wide Benjamini–Hochberg FDR across 25,965 tested genes.
6. Compute a prespecified equal-weight panel score as the mean of per-gene standardized voom log-CPM values; regress the score on age and sex.

### Panel score

- Age slope: **0.0014 standardized score units/year**
- 95% CI: **−0.0077 to 0.0104**
- P = **0.7591**

No evidence of a linear association between this 8-mRPG composite and chronological age was detected in this small age-reference cohort.

### Gene-level results

| Gene | log2-CPM slope/year | P value | Transcriptome-wide FDR |
|---|---:|---:|---:|
| MRPL3 | −0.00157 | 0.5005 | 0.8061 |
| MRPL32 | 0.00331 | 0.4967 | 0.8033 |
| MRPL42 | −0.01685 | 0.2940 | 0.6618 |
| MRPL45 | 0.00216 | 0.4641 | 0.7853 |
| MRPL50 | 0.00524 | 0.1075 | 0.4413 |
| MRPS10 | −0.00230 | 0.8422 | 0.9552 |
| MRPS33 | −0.00184 | 0.7528 | 0.9234 |
| MRPS35 | 0.00133 | 0.5085 | 0.8102 |

No mRPG gene reached transcriptome-wide FDR < 0.05. MRPL50 had the smallest nominal P value, but it was not significant after correction.

## 7-cRPG comparator

The published comparator is `RPL10A, RPL22, RPL4, RPL5, RPS13, RPS23, RPS6`.

Only **RPS23 and RPS6 (2/7)** were present in the count table. The 7-gene composite was therefore **withheld**, not calculated from an incomplete panel.

## Interpretation and limitations

1. GSE262619 is an ordinary age-reference cohort, not a centenarian or exceptional-longevity cohort. It cannot replicate the published claim that long-lived individuals preserve mRPG expression above an age-expected trajectory.
2. This analysis tests chronological-age association only. It does not test a long-lived-versus-control residual, survival, lifespan, or causal mechanism.
3. The 8-mRPG composite showed no age association (P=0.7591), and none of its genes was transcriptome-wide FDR-significant. This is a non-detection in a small cohort, not proof that the published longevity result is false.
4. Sex was inferred from sample-title suffixes because GEO SOFT had no explicit sex characteristic. This provenance choice should be retained in any reuse.
5. Counts were aggregated by exact submitter gene symbol. Some mRPG symbols had multiple source rows (MRPS35 22, MRPL50 6, MRPS33 2); a reference-annotation remapping/sensitivity analysis would strengthen gene-level interpretation.
6. The 7-cRPG panel was incomplete and no composite score was produced.
7. No new biological mechanism, upstream regulator, or causal effect is claimed.

## Reproducibility outputs

The workflow artifact contains:
- Original downloaded count table and GEO family SOFT record.
- Frozen sample manifest and source audit JSON.
- `analysis/analysis_report.json`.
- `analysis/mrpg8_age_associations.csv`.
- `analysis/crpg7_completeness.csv`.
- `analysis/all_gene_age_associations.csv`.

The workflow completed successfully. The offline Python test matrix (Python 3.10–3.14) also passed on the PR head.
