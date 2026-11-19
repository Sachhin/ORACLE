# Human-aging GEO candidate-gene analysis — 2026-11-19

## Status

The public GEO exploratory workflow completed on PR head `e5e95767b667c65045bbf376c91162a871777fbd`.

- Workflow: [run 44464333024](https://github.com/Sachhin/ORACLE/actions/runs/44464333024)
- Artifact: [oracle-human-aging-geo-candidate-gene-analysis](https://github.com/Sachhin/ORACLE/actions/runs/44464333024/artifacts/14502415699)
- Artifact SHA-256: `da92f303685b48ed742ae25b94b4f6a3e2da52ba6713291c82bf53d4c0e927d9`
- Software: R 4.6.2, GEOquery 2.80.1, limma 3.68.5
- Inputs: NCBI GEO processed series matrices, platform annotations, and sample metadata.
- Result status: `EXPLORATORY_ANALYSIS_COMPLETE`; 3 platform analyses succeeded, no cohort retrieval/analysis failures.

## Numerical results

| GEO accession / platform | Design | Samples | Age coverage in report | Candidate genes detected | Candidate genes FDR < 0.05 |
|---|---|---:|---:|---:|---:|
| GSE58137 / GPL10558 | Continuous age | 106 | 18.18–62.50 | 17 | 0 |
| GSE58137 / GPL6947 | Continuous age | 253 | 15.95–77.85 | 17 | 0 |
| GSE65219 / GPL15988 | Nonagenarian vs young-control; sex-adjusted | 176 (146 older, 30 younger) | 19–90 overall | 18 | 14 |

GSE58137 is one GEO series represented on two platforms (359 samples total), not two independent studies. Neither platform showed FDR-significant association among the tested candidate genes. Sex metadata were unavailable for all samples in these two platform matrices.

GSE65219 is the PBMC study of 146 nonagenarians and 30 young controls. Its GEO series description identifies a sex-specific immune-aging study. The ORACLE analysis used a pooled older-versus-younger limma model adjusted for sex, without an age-group-by-sex interaction term. The 14 candidate genes passing transcriptome-wide Benjamini–Hochberg FDR < 0.05 were:

| Gene | logFC (older − younger) | P value | FDR |
|---|---:|---:|---:|
| IRS1 | -0.014606 | 1.56e-09 | 3.01e-08 |
| DDIT4 | 0.783302 | 1.34e-09 | 2.63e-08 |
| MAP1LC3B | 0.276673 | 1.24e-08 | 2.03e-07 |
| CD68 | 0.412526 | 1.07e-06 | 1.20e-05 |
| WIPI1 | 0.220458 | 6.42e-06 | 5.99e-05 |
| ABCA2 | 0.237770 | 3.11e-05 | 2.45e-04 |
| IFNG | 0.350524 | 6.99e-05 | 5.03e-04 |
| IGF1R | -0.005655 | 2.71e-04 | 0.001650 |
| CTSB | 0.251544 | 5.47e-04 | 0.003027 |
| TNF | 0.485268 | 6.56e-04 | 0.003547 |
| LAMP1 | 0.136210 | 0.001139 | 0.005703 |
| LAMP2 | 0.244323 | 0.002602 | 0.011460 |
| BCL2L1 | 0.221824 | 0.002690 | 0.011779 |
| ATG4D | 0.038262 | 0.005354 | 0.020809 |

Effects are on the GEO processed-expression scale and should not be interpreted as fold changes in raw biological abundance. The candidate-gene FDR values are from limma's transcriptome-wide result table, not an adjustment restricted to the selected panel.

## Interpretation and guardrails

1. This is a cross-sectional immune-cell expression contrast, not a survival analysis and not a direct replication in centenarians/supercentenarians.
2. GSE65219's nonagenarian-versus-young contrast is a very-old-versus-young comparison. It cannot identify mechanisms that cause exceptional longevity or distinguish cause from consequence, immune-cell composition, cohort effects, or survivor selection.
3. GSE58137 tests continuous age associations in a separate blood-expression series; its two platforms are not independent external cohorts. Its candidate panel had zero transcriptome-wide FDR-significant genes on both platforms.
4. The GSE65219 model adjusted for sex but did not test the source study's stated sex-specific effects with a sex interaction or sex-stratified estimates. This is a required sensitivity analysis before interpreting the 14 associations as robust.
5. These results are exploratory follow-up evidence only. They do not validate the 8-mRPG panel, establish a new longevity mechanism, validate an upstream regulator, or change the frozen assurance/release gate.

## Reproducibility files

The workflow artifact contains the JSON report, run log, and candidate/all-gene CSVs for each successful platform. Re-run with:

```bash
Rscript scripts/analyze_human_aging_geo.R GSE58137,GSE65219 artifacts/human-aging-geo
```

## Source records

- [GSE58137 — Transcriptional landscape of aging in humans](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE58137)
- [GSE65219 — Transcriptional analysis of PBMCs reveals sex specific changes in the aging of the immune system](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE65219)

