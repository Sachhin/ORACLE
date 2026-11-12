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

`.github/workflows/longevity-cohort-2026.yml` attempts the documented
Mendeley ZIP redirect and records the archive hash before inventorying RData
objects and phenotype metadata. The inventory deliberately omits individual
sample identifiers.

**v1.0 scope decision (2026-11-12): deferred.** The previous GitHub Actions
attempt received HTTP 401 from the API download redirect. Mendeley's current
API documentation marks this redirect as OAuth2-authorized. No Mendeley OAuth
credential is configured in this repository, so the workflow now records an
explicit `DEFERRED_AUTH_REQUIRED` artifact for HTTP 401/403 rather than
repeatedly failing CI or pretending the cohort was analyzed. The public
landing page remains available, but API archive acquisition has not been
verified from the CI runner. Do not use this cohort for v1.0 biological
conclusions until a compliant acquisition route is established and the source
archive hash/schema are recorded.

This first workflow is a data-acquisition and schema-validation stage only.
It does not claim differential expression, pathway enrichment, a new
mechanism, or replication. After the actual archive schema is verified, a
separate analysis should use a pre-registered design, account for region,
sex, age and library preparation, control multiple testing, and validate
candidate signals in independent cohorts such as GSE16717 or other
independent longevity cohorts. A result from the same pooled source is not
independent replication.
