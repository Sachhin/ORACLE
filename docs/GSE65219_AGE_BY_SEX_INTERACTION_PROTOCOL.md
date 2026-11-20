# GSE65219 age-by-sex interaction analysis protocol

## Purpose

The initial ORACLE analysis of GSE65219 used a pooled nonagenarian-versus-young-control limma model adjusted for sex. The source study explicitly reports sex-dependent immune-aging changes, so a pooled adjusted effect alone is not an adequate sensitivity analysis.

This follow-up tests whether the older-versus-younger expression contrast differs between females and males. It is a cross-sectional immune-aging analysis, not a survival analysis or a test of exceptional human longevity.

## Source-authenticated design

NCBI GEO GSE65219 describes 146 nonagenarians and 30 young controls (ages 19–30), with the following published sex composition:

| Group | Female | Male | Total |
|---|---:|---:|---:|
| Young controls | 21 | 9 | 30 |
| Nonagenarians | 103 | 43 | 146 |
| Total | 124 | 52 | 176 |

The R workflow now checks the observed GEO sample-title age groups and sex annotations against this 2×2 cohort composition before fitting the interaction. A mismatch stops the analysis rather than silently proceeding with a different sample set.

Source: [NCBI GEO GSE65219](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE65219); Marttila et al., [Transcriptional Analysis Reveals Gender-Specific Changes in the Aging of the Human Immune System](https://pmc.ncbi.nlm.nih.gov/articles/PMC3679079/).

## Statistical model

The model is fitted to gene-level processed expression with limma empirical-Bayes moderation:

`expression ~ age_group * sex`

Reference levels are young controls and female. The interaction coefficient is:

`age_groupolder:sexmale`

Its effect is the difference-in-differences:

`(older − younger in males) − (older − younger in females)`

A positive interaction coefficient means the older-versus-younger effect is larger in males; a negative coefficient means it is larger in females. The interaction p-values are adjusted with Benjamini–Hochberg across all tested genes, not just the preselected candidate panel.

The same factorial fit supplies separate older-versus-younger contrasts for females and males. Each contrast receives its own transcriptome-wide BH FDR adjustment. The candidate-gene output records all three effect estimates and their p/FDR values.

## Built-in validation

- Synthetic full-rank model-matrix regression guard checks the interaction coefficient and contrast construction.
- The workflow verifies that all four group-by-sex cells are present and match the published cohort counts.
- The model checks design rank and residual degrees of freedom.
- The analysis preserves missing expression measurements rather than imputing artificial values.
- The original GSE58137 continuous-age analyses remain separate; GSE58137 platforms are not treated as independent cohorts.

## Power and interpretation limits

The young-male reference stratum has only 9 participants. This makes male-specific estimates and the interaction test less precise than the female estimates; a non-significant interaction does not prove equal effects across sexes. Conversely, a significant interaction is evidence of sex heterogeneity in this dataset, not evidence that a gene causes longevity.

The GEO cohort contains nonagenarians and young adults, not a matched centenarian/supercentenarian survival design. Results may reflect immune-cell composition, cohort effects, survivor selection, or consequences of aging. They cannot establish a new longevity mechanism or validate the prior-art 8-mRPG panel.

## Reproduction

Run the workflow:

```bash
Rscript scripts/analyze_human_aging_geo.R GSE58137,GSE65219 artifacts/human-aging-geo
```

The GSE65219 platform CSV and JSON report contain the interaction and sex-stratified statistics. The numerical results should only be considered complete after the GitHub Actions artifact from the updated interaction-enabled commit has been inspected.
