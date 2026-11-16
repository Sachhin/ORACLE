# GSE16717 independent signature reanalysis

GSE16717 is the Leiden Longevity Study microarray cohort on GPL2895. GEO reports 150 samples: 50 long-lived siblings (mean age 93.4 years), 50 offspring (mean age 60.8 years), and 50 controls/offspring partners (mean age 61.9 years). The 2026 human-longevity paper already cites GSE16717 as a validation cohort, so an ORACLE reanalysis is a reproducibility check of published validation, not a new independent cohort discovery.

The exact 2026 Figure 4B gene panels are now available:
- mRPG-8: MRPL3, MRPL32, MRPL42, MRPL45, MRPL50, MRPS10, MRPS33, MRPS35
- cRPG-7: RPL10A, RPL22, RPL4, RPL5, RPS13, RPS23, RPS6

The deterministic workflow downloads the GEO series matrix and GPL2895 annotation, maps probes to the pre-specified genes, aggregates multiple probes by median, standardizes each gene across the 150 samples, computes unweighted panel scores, and reports Welch group comparisons with Benjamini–Hochberg correction. It also records whether individual age/sex metadata are actually present.

Limitations: the GEO series is the same cohort already used by the 2026 paper; it is not a new cohort. The analysis is based on normalized microarray expression, not RNA-seq counts, and the unadjusted Welch comparisons do not control family structure or covariates. Results are exploratory and cannot establish causality.

Workflow: .github/workflows/gse16717-mrpg-validation.yml  
Script: scripts/analyze_gse16717_mrpg_signature.py  
Artifact: oracle-gse16717-mrpg-signature-validation
