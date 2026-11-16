# GEO age-metadata and numerical audit — 2026-11-16

## Frozen execution provenance

- GitHub Actions run: [43869439810](https://github.com/Sachhin/ORACLE/actions/runs/43869439810)
- Run completed successfully; artifact: `oracle-human-aging-geo-candidate-gene-analysis`
- Artifact ID: `14226709472`
- Artifact SHA-256: `d3dc198ad7b654e6c39f0cbe3b1cf1a07991a318f1dc8ffe8a41032acd3ccf09`
- The GEO R script and workflow at the executed commit were byte-identical to those in the current GEO/Qwen PR branch.
- Analysis used NCBI GEO processed series matrices, GPL annotations, sample metadata, GEOquery 2.80.1 and limma 3.68.5 under R 4.6.2.

## Age metadata and cohort accounting

| Accession/platform | Samples analysed | Exact age values | Age range | Design | Sex adjustment |
|---|---:|---:|---:|---|---|
| GSE58137 / GPL10558 | 106 | 106 | 18.1766–62.5 | Continuous age | No; sex unavailable |
| GSE58137 / GPL6947 | 253 | 253 | 15.948–77.8453 | Continuous age | No; sex unavailable |
| GSE65219 / GPL15988 | 176 | 176 | 19–90 | Explicit older vs younger title groups | Yes; 124 female, 52 male |

GSE58137 therefore contributes 359 samples across two platforms, not one 359-sample expression matrix. All 359 exact-age fields were accepted; no implausible ages were retained. The two platforms are separate analyses and must not be treated as independent biological cohorts without considering their shared accession/study provenance.

For GSE65219, the explicit title-based contrast contains 146 older/nonagenarian-labelled samples and 30 young controls. The design is adjusted for sex and has 173 residual degrees of freedom. All 176 exact-age fields were accepted; the observed age range is 19–90 years.

## Numerical results

The pre-specified candidate panel contains 19 autophagy/lysosomal, growth-signalling and inflammatory genes.

- GSE58137 GPL10558: 17 candidate genes detected; **0** passed transcriptome-wide Benjamini–Hochberg FDR < 0.05.
- GSE58137 GPL6947: 17 detected; **0** passed FDR < 0.05.
- GSE65219 GPL15988: 18 detected; **14** passed FDR < 0.05 in the sex-adjusted older-versus-younger contrast.

The 14 GSE65219 candidates with reported FDR < 0.05 are ATG4D, CTSB, WIPI1, BCL2L1, IGF1R, IRS1, DDIT4, ABCA2, CD68, LAMP1, LAMP2, MAP1LC3B, IFNG and TNF. Directions are mixed: for example, IGF1R and IRS1 are lower in the older group, while ATG4D, CTSB, WIPI1, DDIT4 and several inflammatory/lysosomal markers are higher.

No probe-level or gene-level expression measurements were missing after the GEO preprocessing and gene-symbol aggregation in these three successful platform analyses. This is a property of the downloaded processed matrices, not evidence that the original studies had no missingness at every upstream stage.

## Interpretation and scientific limits

1. This is an exploratory, cross-sectional age-association analysis, not direct centenarian replication or a survival analysis.
2. GSE58137 provides no FDR-significant candidate-panel replication on either platform. Its lack of sex metadata also prevents sex adjustment.
3. GSE65219 shows a strong older-versus-younger expression contrast for 14 pre-specified candidates, but this cannot distinguish cell-composition shifts from cell-intrinsic regulation. No cell-type deconvolution or causal perturbation was performed.
4. The candidate panel is not the 2026 8-mitochondrial-ribosomal-protein (8-mRPG) signature. These GEO results do not independently validate that published signature.
5. The result supports age-associated changes in selected autophagy/lysosomal, growth-signalling and inflammatory transcripts in one nonagenarian-labelled cohort. It does **not** identify a previously unknown longevity mechanism or establish exceptional longevity biology.

## Release gate

- GEO data retrieval and numerical analysis: **PASS for this frozen exploratory workflow**.
- Age-field parsing and plausible-range checks: **PASS for the fields reported above**.
- Independent replication of candidate effects: **NOT PASS**.
- Direct centenarian cohort validation (CRA000515): **BLOCKED pending source-authenticated sample metadata**.
- Cell-composition-adjusted and functional validation: **NOT DONE**.

The raw artifact contains the complete JSON report, per-platform candidate-gene CSVs, all-gene limma tables and execution log. Preserve the artifact and its SHA-256 above as the reproducibility record; do not upgrade this exploratory result to a longevity-discovery pass.
