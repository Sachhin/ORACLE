# GSE65219 age-by-sex interaction results — 2026-11-19

## Execution and provenance

- Repository branch: `feat/longevity-frozen-assurance-bundle`
- Analyzed commit: `d29dce3ff6e626a60f356b6e3e4d99212d318e8e`
- GitHub Actions workflow: [run 44466872343](https://github.com/Sachhin/ORACLE/actions/runs/44466872343) — **success**
- Artifact: [oracle-human-aging-geo-candidate-gene-analysis](https://github.com/Sachhin/ORACLE/actions/runs/44466872343/artifacts/14503066506)
- Artifact SHA-256: `230fa3fcc12ba226a7580b797633c776baa14b9e5e7ceeee6dce7a23c5878d41`
- Software: R 4.6.2, GEOquery 2.80.1, limma 3.68.5
- Result: `EXPLORATORY_ANALYSIS_COMPLETE`; 3 platform analyses succeeded; no cohort retrieval or analysis failures.

The workflow's source-composition guard passed for all 176 GSE65219 samples:

| Group | Female | Male | Total |
|---|---:|---:|---:|
| Young controls | 21 | 9 | 30 |
| Nonagenarians | 103 | 43 | 146 |
| Total | 124 | 52 | 176 |

## Model

For GSE65219 GPL15988, limma fitted `expression ~ age_group * sex`, with young and female as reference levels. The interaction is the difference-in-differences:

`(older − younger in males) − (older − younger in females)`

Interaction and each sex-specific contrast were BH-adjusted across all 22,452 tested gene symbols. The design had 172 residual degrees of freedom. The separate female and male contrasts are obtained from the same factorial fit.

## Results

### Preselected candidate panel

- 18 of 19 preselected candidate genes were detected.
- **0/18** had transcriptome-wide FDR < 0.05 for the age-by-sex interaction.
- **11/18** had FDR < 0.05 for the older-versus-younger contrast in females.
- **3/18** had FDR < 0.05 for the older-versus-younger contrast in males: IRS1, DDIT4 and MAP1LC3B.
- These within-sex associations are not evidence that the effects differ between sexes. The interaction test is the relevant test of that difference.

Candidate genes with female-contrast FDR < 0.05: CTSB, WIPI1, IGF1R, IRS1, DDIT4, ABCA2, CD68, LAMP2, MAP1LC3B, IFNG and TNF.

Candidate genes with male-contrast FDR < 0.05: IRS1, DDIT4 and MAP1LC3B.

### Transcriptome-wide interaction

Three genes passed BH FDR < 0.05 across the full transcriptome:

| Gene | Interaction logFC | P value | BH FDR |
|---|---:|---:|---:|
| CYORF15B | -0.293412 | 9.97e-10 | 2.2387e-05 |
| CYORF15A | -0.581789 | 3.32e-09 | 3.7e-05 |
| ZFY | -0.027777 | 3.06e-07 | 0.002290 |

All three are Y-linked genes. Their signal should be interpreted cautiously as a sex-chromosome-associated pattern in this dataset, not as a longevity mechanism. No preselected longevity candidate was among the transcriptome-wide FDR-significant interaction genes.

## Other cohorts in the same run

| GEO series / platform | Design | Samples | Candidate genes detected | Candidate genes FDR < 0.05 |
|---|---|---:|---:|---:|
| GSE58137 / GPL10558 | Continuous age | 106 | 17 | 0 |
| GSE58137 / GPL6947 | Continuous age | 253 | 17 | 0 |
| GSE65219 / GPL15988 | Age-group-by-sex interaction | 176 | 18 | 0 for interaction |

The two GSE58137 platforms are measurements from one GEO series, not independent cohorts.

## Interpretation and limitations

1. The prior pooled sex-adjusted GSE65219 analysis reported 14 candidate genes with FDR < 0.05. The factorial sensitivity analysis shows that **none of the candidate panel's age effects has a significant age-by-sex interaction**. It does not establish that the effects are identical between sexes.
2. The young-male stratum contains only 9 participants. Male-specific estimates and the interaction test therefore have limited precision; non-significance is not proof of equivalence.
3. The female/male contrast significance counts are separate within-sex tests and must not be compared as proof of sex heterogeneity.
4. This is cross-sectional PBMC immune-aging data comparing nonagenarians with young controls. It is not a centenarian survival cohort and cannot establish exceptional longevity, causality, or a newly discovered biological mechanism.
5. These findings do not validate the published 8-mRPG panel, an upstream regulator, or the ORACLE longevity hypotheses. Independent cohorts and direct mechanistic experiments remain necessary.

## Reproduction

```bash
Rscript scripts/analyze_human_aging_geo.R GSE58137,GSE65219 artifacts/human-aging-geo
```

The workflow artifact contains the JSON report, all-gene CSVs, candidate-gene CSVs and run log. The exact artifact digest above identifies the inspected output.
