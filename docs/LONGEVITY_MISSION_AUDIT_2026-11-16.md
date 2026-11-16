# ORACLE human-longevity mission: independent artifact audit

Audit date: 2026-11-16

## Source artifact and reproducibility

- GitHub Actions run: https://github.com/Sachhin/ORACLE/actions/runs/42831918629
- Run ID inside ORACLE: `run_a19934cc2692`
- Artifact: `oracle-longevity-research-42831918629`
- Research JSON SHA-256: `0d3cf182ee14176127e99343b78536ab52e736b3d54272529f1d018e3a6fcf50`
- Separate centenarian miRNA report SHA-256: `933adcabe5bfb663610d62355a8b19c11264231e2aaf65ac9a266550a30d0b09`

The workflow completed three of three cycles. The artifact contains 256 source records, 51 evidence records, 435 claims, two hypotheses, and one proposed experiment.

## Hypothesis audit

Both hypotheses are generic competing framings of the question, not mechanism-level discoveries:

1. Multiple interacting mechanisms may be needed to explain longevity.
2. A dominant single mechanism may explain most observations.

Both have:
- status `proposed`;
- confidence `very low`;
- zero supporting evidence IDs;
- zero opposing evidence IDs;
- no reviewer note or review timestamp.

Therefore neither hypothesis has source-linked support in the frozen run. Neither has passed novelty review, independent replication, or biological validation. The single experiment is only a proposed generic protocol; it was not performed or simulated.

## Numerical and dataset audit

- `differential_expression_analyses`: 0
- `dataset_analyses`: 0
- `contradiction_candidates`: 0
- The downloaded `GSE351605` normalized-count file is a human ketogenic-diet pre/post dataset, not a centenarian cohort. It was present in the artifact but was not parsed into a verified design or analysed for differential expression.
- The run therefore does not contain a reproducible numerical analysis that tests exceptional human longevity.

## Separate GSE32493 centenarian miRNA analysis

The same workflow generated a separate group-level report for GSE32493:

- 3 centenarians and 3 controls; B-cell samples; Ashkenazi Jewish population.
- 231 shared miRNA features.
- The deposited supplementary data retained one numeric summary column per group, not per-person replicate values.
- The report explicitly computes descriptive CPM and log2 fold changes only. It does not calculate inferential statistics or adjusted p-values.
- The largest reported descriptive effect was hsa-miR-122 (log2 CPM fold change +2.33), but it cannot be treated as statistically significant or independently replicated.

This is a small, exploratory, group-level signal—not evidence of a newly discovered mechanism.

## Release interpretation

The actual mission result is **literature discovery and hypothesis generation only**. It does not establish a previously unknown biological mechanism, causal pathway, or longevity intervention.

Required next evidence:
1. Complete CRA000515 sample-level metadata acquisition and source reconciliation.
2. Reanalyse a validated centenarian cohort with a pre-registered statistical design and appropriate covariates.
3. Independently replicate candidate findings in a separate cohort with comparable tissue and phenotype.
4. Test mechanism-level predictions with validated perturbation/functional evidence.
5. Obtain at least two independent blinded expert reviews.

Do not mark the longevity discovery gate PASS based on this run.


## High-priority prior art missed by the frozen ORACLE run

A direct literature cross-check found a highly relevant paper published before
the ORACLE mission artifact was generated:

- Xiao et al., *Preserved mitochondrial ribosomal protein gene expression
  marks a youthful transcriptional state in Chinese nonagenarians and
  centenarians*, Cell Reports Medicine, 19 May 2026.
- DOI: `10.1016/j.xcrm.2026.102767`
- PMID: `42030936`; PMCID: `PMC13198318`.
- Public article: https://pmc.ncbi.nlm.nih.gov/articles/PMC13198318/

The paper analyzes 1,751 individuals (811 long-lived individuals aged 90–113
and 940 younger controls) and reports an eight-mitochondrial-ribosomal-protein
gene (8-mRPG) expression signature that deviates upward from the typical
age-related decline. It reports associations with transcriptomic aging
indicators and validation across other cohorts, including the Leiden
Longevity Study. The authors explicitly state that functional experiments
are still needed to establish causality and that the upstream regulatory
processes remain unclear.

The frozen ORACLE run JSON was searched for the paper title, DOI, PMID, and
Mendeley DOI; none were present. This is a material literature-recall failure:
256 source records did not guarantee coverage of the most relevant recent
prior art. The 8-mRPG signature itself must not be claimed as a new ORACLE
discovery. It is now a required prior-art seed for the next mission run.

### Updated research direction

The meaningful open question is not whether the 8-mRPG signature exists; that
has been reported. More defensible follow-up questions include:

1. Which upstream regulators maintain mitochondrial ribosomal gene
   expression in long-lived people?
2. Does the signal remain after robust adjustment for leukocyte composition,
   region, sequencing/library batch, sex, and age?
3. Is the expression signature associated with mitochondrial translation,
   respiratory function, or proteostasis in independent sample-level data?
4. Which perturbations would distinguish a causal maintenance mechanism from
   a correlated marker of cell composition or health status?

These are candidate research directions, not established novel mechanisms.
Each must pass independent evidence retrieval, sample-level numerical
replication, and functional validation.

### Data access implications

The article identifies 171 samples from CRA000515 and 271 from HRA000656 as
previously reported data, with 1,310 newly included samples under HRA000721,
HRA015371, and HRA015372. It links a 1,751-sample expression matrix to
Mendeley Data DOI `10.17632/fpf4y72kfz.1`. The integrated matrix is a promising
route for reproducible analysis, but its sample annotation and mapping to the
public CRA aliases must be verified before using the cohorts as independent
replication.
