# Requested ORACLE scientific-validation blockers

This file separates engineering work from evidence that requires external
records or independent people. No task is marked PASS without its required
evidence.

## PXD047528 clinical sample mapping

**Status: BLOCKED — source-authenticated alias-to-patient crosswalk unavailable.**

Verified:
- PEPerMINT's paired DDA/DIA processed tables contain aliases
  `1_Slot1` through `15_Slot1`; its published Zenodo archive preview lists
  these 15 per-sample HDF5 files but no alias-to-patient crosswalk.
- PRIDE lists 32 raw files (DDA/DIA acquisitions), with opaque file suffixes
  such as `03M`, `23Y`, `32S`, `41S`, and `44S`; the filenames alone do not
  authenticate phenotype or participant identity.
- The frozen reconstruction benchmark scores 8,859 genuinely DDA-missing
  peptide cells with paired DIA observations (67.9% of 13,043 missing cells).
- A range-based audit of the complete PEPerMINT ZIP directory for this
  dataset found only the DDA/DIA peptide and protein tables plus a lock file;
  no README, clinical metadata, patient manifest, or sample crosswalk was
  present. The archive scan is frozen as an Actions artifact.
- Row-median baseline on the same held-out missing cells: MAE 1.1382,
  RMSE 1.4675, Pearson r 0.2503. The sample-neighbour KNN candidate modestly
  improves these to MAE 1.0981, RMSE 1.4259, Pearson r 0.2625; absolute
  reconstruction correlation remains weak, so this is not a validated
  clinical imputer.
- The original Ahmed et al. clinical paper reports 13 plasma participants
  (8 HIV and 5 herpes); its HAND subgroup is 5 HAND versus 3 cognitively
  normal participants among people with HIV.

The processed PEPerMINT aliases do not encode patient identity or phenotype.
The public source records inspected so far do not establish which aliases
correspond to the 13 clinical participants, nor whether the two additional
aliases represent a different cohort, extra acquisitions, or a version
difference. Do not infer labels from alias order, abundance patterns, or
aggregate group counts.

Required unblock: a source-authenticated manifest from the dataset submitter
or original study records mapping each alias to raw DDA/DIA file(s), patient
ID, phenotype, HAND status where applicable, and technical-replicate/exclusion
status. Freeze and hash that manifest before outcome concordance analysis.

Sources:
- PXD047528 and its 32 raw-file listing: https://proteomecentral.proteomexchange.org/cgi/GetDataset?ID=PXD047528
- Zenodo PEPerMINT archive and sample-file inventory: https://zenodo.org/records/11216899/preview/data.zip?include_deleted=0
- Public dataset submitter contact: saima.ahmed@childrens.harvard.edu
- Ahmed et al. 2022: https://pmc.ncbi.nlm.nih.gov/articles/PMC9945916/
- PEPerMINT data: https://zenodo.org/records/11216899

## SciFact Qwen3 local-model benchmark

**Engineering action added:** `.github/workflows/scifact-qwen3-local-benchmark.yml`
runs a pinned Qwen3-0.6B GGUF through a local llama.cpp server and attempts
the complete 300-claim labelled dev evaluation over the full SciFact corpus.
The resulting report and predictions must be inspected after the workflow
finishes; workflow creation alone is not a benchmark result.

## Expert blinded evaluation

**Status: BLOCKED — no independent expert annotations received.**

The blinded packet builder and paired-score validator are implemented and
tested. They can hide system identity and verify reviewer score completeness,
but cannot recruit experts or create human judgements. At least two independent
reviewers must score the same frozen baseline/candidate answer pairs and
source packets. Their returned score files must be frozen before unblinding.

No reviewer identities, scores, agreement statistics, or superiority claims
may be fabricated. A real evaluation also requires a frozen paired-answer
corpus; the starter question set alone contains questions, not gold answers.

## Human longevity research mission

**Status: INCOMPLETE — direct centenarian data have now been analyzed
descriptively, but the mission has not established a new biological mechanism.**

The first full ORACLE literature mission completed three cycles and retrieved
257 source records, 53 evidence records, and 451 claims. Its two generated
hypotheses were marked very-low confidence and had no linked supporting or
opposing evidence IDs. The run downloaded GSE351605, which is a human
ketogenic-diet pre/post intervention dataset rather than a
centenarian/exceptional-longevity cohort. It produced no differential
expression or pathway analyses. The mission's "completed" workflow status
must therefore not be mistaken for a completed mechanism-discovery result.

A new direct GEO workflow now downloads and analyzes the public GSE32493
centenarian miRNA supplementary tables. It compared 231 shared miRNAs between
three centenarians and three controls after library-size CPM normalization.
The deposited tables contain one group-level count per miRNA, not the
individual sample-level replicates; accordingly the workflow reports
descriptive log2-CPM fold changes only and computes no p-values or FDR. The
largest descriptive effects include hsa-miR-122 (+2.33 log2 CPM),
hsa-miR-363* (+2.28), hsa-miR-345 (+1.96), hsa-miR-20b (+1.96), and
hsa-miR-151-3p (-1.62). These are exploratory leads, not statistically
validated findings, mechanisms, or evidence of causality. The cohort is very
small and uses EBV-transformed B-cells. Workflow artifact:
oracle-gse32493-centenarian-mirna.

A separate exploratory workflow tests a pre-specified centenarian-candidate
gene set against ordinary age trends in two independent GEO cohorts:
GSE58137 (359 whole-blood samples, ages 16–78) and GSE65219 (176 PBMC
samples: 146 nonagenarians aged 90–99 and 30 young controls aged 19–30).
A false-positive age parser was identified in the first GSE65219 report
("percentage" was being matched as an age field); the parser now requires
whole-word age labels, rejects impossible ages, and has a regression check.
The corrected numerical report is pending. These cohorts provide
cross-sectional aging comparisons, not direct centenarian validation.

A larger directly relevant published human centenarian transcriptome study is
Xiao et al. (2018): 76 centenarians, 54 centenarian offspring, and 41 offspring
spouses (171 people); its RNA-seq data are deposited under GSA accession
CRA000515. The paper reports autophagy/lysosomal pathway enrichment and
experimental follow-up for selected genes.

A newer 2026 public resource, "Transcriptomic Analysis of Chinese Longevity
Cohorts" (Mendeley DOI 10.17632/fpf4y72kfz.1), reports 1,751 individuals
(811 long-lived individuals and 940 younger controls) and a gene-level
expression matrix. ORACLE now has a version-pinned acquisition and RData/
tabular-inventory workflow at
`.github/workflows/longevity-cohort-2026.yml`. The workflow is queued;
until the archive has been downloaded and its phenotype/matrix schema
verified, no differential-expression or pathway result is claimed. A valid
analysis must account for region, sex, age, library preparation, and cohort
structure and must preserve a truly independent validation cohort. Sources:
https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE32493
https://pubmed.ncbi.nlm.nih.gov/22846614/
https://genome.cshlp.org/content/28/11/1601
https://pubmed.ncbi.nlm.nih.gov/30352807/

## Final release criterion

The release report must keep these statuses separate:
1. software implemented and unit-tested;
2. external benchmark executed with frozen inputs and outputs;
3. independent scientific replication;
4. human expert review completed.

A green CI run only supports the first or second category for the workflow
that actually ran. It does not imply categories three or four.


### CRA000515 acquisition/provenance update (2026-11-14)

A targeted check of the current CNCB-NGDC public GSA pages found that CRA000515
is browseable at run level. For example, GSA run CRR022098 is associated with
BioSample SAMC016783 (alias CHHA67), library CRX019999, paired-end RNA-seq on
Illumina HiSeq 4000, and exposes an HTTPS BAM download URL. The displayed BAM
size is 5,420.55 MB. A second example, CRR022179, exposes the same class of
run/BioSample/library metadata and a 5,144.74 MB BAM. The BioSample page for
SAMC016790 exposes submitter, tissue, sex, project and related-sample fields;
its age attribute is blank in the returned public record. These examples prove
that public run-level acquisition and metadata inspection are possible for at
least some records; they do not constitute a complete cohort manifest.

Reproducible acquisition must therefore be staged, not treated as one small
GEO-style matrix download:
1. Enumerate every run under CRA000515 from the GSA project/run listing and
   freeze the complete run-to-experiment-to-BioSample table.
2. Save the raw metadata response/page for each run and BioSample, recording
   retrieval time, source URL, HTTP status and SHA-256.
3. Validate expected sample count and cohort labels against the Xiao et al.
   study design (76 centenarians, 54 offspring, 41 offspring spouses); do not
   infer age/group from alias strings such as CHHA67.
4. Check library strategy/layout, reference genome, BAM integrity and whether
   all samples are comparable. Resolve any missing ages, duplicated people,
   technical replicates and group inconsistencies from source records.
5. Only after a complete manifest passes those checks, acquire all required
   BAMs (multi-GB each), quantify consistently against a pinned hg19-compatible
   annotation/reference, and freeze the count matrix plus checksums.

The currently verified example URLs are:
- https://ngdc.cncb.ac.cn/gsa/browse/CRA000515/CRR022098
- https://download.cncb.ac.cn/gsa3/CRA000515/CRR022098/CRR022098.bam
- https://ngdc.cncb.ac.cn/gsa/browse/CRA000515/CRR022179
- https://ngdc.cncb.ac.cn/biosample/browse/SAMC016790

**Current status remains BLOCKED for a reproducible cohort-level reanalysis:**
the examples above are not a complete enumerated manifest, no full cohort
download or integrity audit has been run, and the available sample page
example has no age value. This update narrows the blocker from "no acquisition
route known" to "cohort-wide enumeration, metadata validation and large-file
acquisition not yet executed". GSE58137/GSE65219 remain age-association checks,
not direct centenarian replication.
