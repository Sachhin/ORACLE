# GSE16717 mRPG signature reanalysis — numerical audit

Date: 2026-11-16

## Dataset and metadata

The first completed public GEO run retrieved the GPL2895 series matrix and platform annotation and found 150 samples:
- 50 long-lived siblings: mean age 93.40 years (SD 3.01), 24 female / 26 male
- 50 controls: mean age 61.95 years (SD 6.49), 26 female / 24 male
- 50 offspring: mean age 60.79 years (SD 6.05), 25 female / 25 male

All 150 samples have an age and sex field in the GEO metadata. The expression matrix checksum from that run was `33e9cd42c0b3721afe54117d07904b5b78d9e6c78c8c70ca890d03600c788400`; GPL2895 annotation checksum was `91e4f679c2a99e6274583b98906c28d4702146e85c63f26b927dc183d0041ce9`.

## First-pass numerical result (unadjusted group means)

The initial exploratory score used the published eight mRPG genes, standardized gene-wise across all 150 samples, then averaged. Long-lived siblings did not show a higher score than controls:
- mRPG-8 mean difference (long-lived siblings minus controls): -0.1626 z-score units
- Welch p = 0.3159; BH q = 0.6671

This is not evidence of successful replication of the published elevated/age-trajectory mRPG result. It is also not a direct refutation: long-lived siblings are about 31 years older on average, and an unadjusted group mean contrast is not equivalent to the 2026 paper's age-trajectory deviation analysis or its SVM transcriptomic-age model.

The initial script also computed a cRPG-7 composite from only six mapped genes. RPS6 is absent from GPL2895 annotation (0 probes). That partial score is not a valid 7-gene panel and must not be interpreted. The pipeline has now been changed to suppress composite scoring for any incomplete panel and to explicitly report panel completeness. The mRPG-8 panel has all eight genes represented.

## Required next analysis

1. Re-run the updated workflow and verify the complete-panel-only output.
2. Reproduce the paper's age-trajectory approach as closely as the public data permit: model gene/panel expression against chronological age, quantify residuals for long-lived siblings relative to the non-long-lived reference trajectory, and report uncertainty. Because long-lived siblings are older than the controls/offspring, extrapolation beyond the middle-aged reference range must be explicitly flagged.
3. Run age- and sex-adjusted models, and consider family structure only if the published sample metadata exposes the needed family identifiers.
4. Compare results to the 2026 paper's Figure S13 and main Figure 4B without treating GSE16717 as a new independent cohort: it is the Leiden cohort already used by that paper.

## Interpretation

Current status: `REPRODUCIBILITY_CHECK_INCOMPLETE`. The initial unadjusted comparison does not reproduce a higher mRPG-8 score in long-lived siblings. No causal mechanism or novel discovery is validated. This analysis is from normalized microarray expression, not RNA-seq counts.


## Age-overlap audit

The observed age ranges are non-overlapping:
- Long-lived siblings: 89.27–102.19 years
- Controls: 43.71–78.76 years
- Offspring: 42.79–74.83 years

There is therefore no common age support between the long-lived-sibling group and the two comparison groups. A regression-adjusted group effect would require extrapolating the mid-life age-expression trend into the 89–102-year range. ORACLE must not present such an extrapolation as a well-identified age-adjusted replication. The current unadjusted result is a valid descriptive contrast only; age-trajectory validation needs an explicit model with uncertainty and transparent extrapolation diagnostics, or a dataset with overlapping age ranges.
