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
  centenarians*, Cell Reports Medicine, 23 April 2026 (collection date 19 May 2026).
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


### Published cohort-count discrepancy to reconcile

The paper's abstract reports 1,751 analyzed participants (811 LLIs + 940 YCs),
but the Methods section reports 1,752 recruited participants (811 LLIs + 941
YCs). The key-resources table lists 171 CRA000515 + 271 HRA000656 = 442
previously reported samples, while the Data Availability Statement says 441
samples; the Methods explain that one previously published sample with
missing age was excluded. This may explain the one-sample difference, but the
raw manifest and exclusion record must be checked before treating the counts
as reconciled. ORACLE must preserve this discrepancy in the audit rather than
silently choosing one total.


## Independent evidence audit: mitochondrial translation and ribosome allocation (2026-11-16)

### Evidence reviewed

1. **Human long-lived cohorts (Xiao et al., 2026; DOI 10.1016/j.xcrm.2026.102767).** The study reports 811 long-lived individuals and 940 younger controls, eight mitochondrial ribosomal-protein genes deviating upward from age-related decline, seven cytosolic ribosomal-protein genes continuing to decline, and replication of the 8-mRPG score pattern in the Leiden Longevity Study. The score is associated with transcriptomic aging and senescence measures. This is human observational evidence, not proof of causality. The authors state that upstream regulation remains unclear and functional experiments are needed.

2. **Cross-species functional evidence (Houtkooper et al., 2013; DOI 10.1038/nature12188).** Mouse genetics and C. elegans RNAi experiments implicated MRPS5 and other mitochondrial ribosomal proteins in lifespan regulation. MRP knockdown induced mitonuclear protein imbalance and UPRmt, and extended worm lifespan. This is functional model-organism evidence, but its intervention direction (reduced MRP function) is not the same as the higher-than-age-expected expression of selected mRPGs in long-lived humans.

3. **Human tissue translation evidence (2021; DOI 10.1080/15476286.2021.1875647).** Ribosome profiling in human skeletal muscle found lower translation/occupancy of several mitochondrial-genome-encoded oxidative-phosphorylation transcripts with older age. This supports the broader idea that mitochondrial translation is age-sensitive, but it does not measure the nuclear-encoded 8-mRPG signature or exceptional longevity.

4. **Human translation-machinery genetics (2022; DOI 10.1101/gr.275636.121).** A Mendelian-randomization study reported associations between genetically proxied expression of Pol I/III and ribosomal-protein machinery and human longevity, with reduced translation-machinery expression implicated in several tissues. This is not specific to mitochondrial ribosomal proteins and depends on MR instrument assumptions.

5. **Cytosolic ribosome regulation in long-lived people (2022; DOI 10.1126/sciadv.abf2017).** Transcriptomes from 185 long-lived individuals and 86 offspring spouses in two Chinese cohorts showed downregulation of the cytosolic ribosome pathway. ETS1 was lower in long-lived individuals; ETS1 knockdown reduced cytosolic ribosomal-protein expression and cellular senescence in fibroblast assays. These results concern cytosolic ribosome biogenesis, not the mitochondrial 8-mRPG signature.

### Synthesis: a testable direction, not a discovery claim

The most coherent candidate model is **compartment-specific translation allocation**: selected mitochondrial ribosomal transcripts may be preserved above their age-expected trajectory in long-lived humans while broader cytosolic ribosome biogenesis declines. This could reconcile the 2026 human signature with evidence that reduced global/cytosolic translation and mitochondrial stress responses can promote longevity in other contexts. The evidence does not yet show that the same upstream regulator causes both patterns.

A second possibility is **dose-, tissue- and time-dependent mitonuclear stress hormesis**. Partial/transient mitochondrial translation perturbation can activate UPRmt in model organisms, while preserving selected mRPGs may be associated with late-life mitochondrial function in humans. These are not necessarily mutually exclusive, but the dose-response and tissue-specific mechanism remain untested.

A live alternative is **bulk-blood composition or health-status confounding**. Differences in leukocyte subtype proportions, medication, nutrition, chronic disease, region, and library protocol may explain some of the signature. The 2026 study uses cell-composition estimates in parts of its age-related modelling, but this does not replace independent within-cell-type replication and functional testing of the exact signature.

### ORACLE evidence status

- Published 8-mRPG signature: **KNOWN PRIOR ART**.
- Human independent-cohort association: **reported by the 2026 study (including Leiden)**; ORACLE has not independently reproduced the exact signature from frozen raw sample-level inputs.
- GSE58137/GSE65219 audit: the current exploratory panel tests autophagy/lysosomal and inflammatory candidate genes, not the 8-mRPG signature. GSE58137 had no FDR-significant candidate genes on either platform; GSE65219 had 14/18 panel genes at FDR < 0.05. These results do not validate the 8-mRPG hypothesis.
- Causal mechanism in humans: **NOT ESTABLISHED**.
- Functional perturbation/rescue: **NOT DONE**.
- Novel ORACLE discovery: **NONE VALIDATED**.

The machine-readable source and hypothesis map is
`data/missions/longevity/prior_art_seed.json`. It records source IDs, evidence
type, limitations, alternative explanations and falsifiable tests. All three
candidate hypotheses remain proposed and must not be represented as discovered
mechanisms.
