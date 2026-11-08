# 2026 Chinese longevity transcriptome cohort

## Source

Mendeley Data DOI: https://doi.org/10.17632/fpf4y72kfz.1
Dataset: https://data.mendeley.com/datasets/fpf4y72kfz/1
The 2026 study reports 1,751 individuals (811 long-lived individuals and
940 younger controls) and a gene-level RNA-seq expression matrix. It combines
cohorts and sequencing-library preparation approaches, so batch, region,
sex, age, and cohort design must be inspected before statistical comparison.

Related source article: https://pmc.ncbi.nlm.nih.gov/articles/PMC13198318/
Original centenarian transcriptome study: https://pubmed.ncbi.nlm.nih.gov/30352807/

## ORACLE acquisition workflow

`.github/workflows/longevity-cohort-2026.yml` downloads the public versioned
Mendeley archive through its documented public ZIP redirect, hashes the
archive, validates the ZIP, and inventories RData objects and phenotype
metadata. The inventory deliberately omits individual sample identifiers.

This first workflow is a data-acquisition and schema-validation stage only.
It does not claim differential expression, pathway enrichment, a new
mechanism, or replication. After the actual archive schema is verified, a
separate analysis should use a pre-registered design, account for region,
sex, age and library preparation, control multiple testing, and validate
candidate signals in independent cohorts such as GSE16717 or other
independent longevity cohorts. A result from the same pooled source is not
independent replication.
