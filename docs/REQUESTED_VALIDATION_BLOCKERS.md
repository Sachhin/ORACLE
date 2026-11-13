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
- KNN reconstruction report: MAE 1.0981, RMSE 1.4259, Pearson r 0.2625.
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

**Status: INCOMPLETE — previous run was literature discovery, not a validated
mechanism-discovery analysis.**

The previous run downloaded GSE351605. That accession is a human ketogenic
diet pre/post intervention dataset, not a centenarian/exceptional-longevity
cohort. Its 48 expression columns were not parsed into a verified sample
design, and no differential-expression or pathway analysis was performed.
It must not be presented as direct evidence about exceptional human longevity.

A directly relevant published human centenarian transcriptome study is Xiao
et al. (2018): 76 centenarians, 54 centenarian offspring, and 41 offspring
spouses (171 people); its RNA-seq data are deposited under GSA accession
CRA000515. The paper reports autophagy/lysosomal pathway enrichment and
experimental follow-up for selected genes. The GSA raw-read archive is not
the same as a ready-to-use GEO count matrix. A reproducible raw-read or
submitter-provided processed-matrix acquisition, sample metadata, library
type/covariate handling, and independent replication are still required
before ORACLE can claim a fresh numerical reanalysis. A separate exploratory workflow now tests a pre-specified centenarian-candidate gene set against ordinary age trends in two independent GEO cohorts: GSE58137 (359 whole-blood samples, ages 16–78) and GSE65219 (176 PBMC samples: 146 nonagenarians aged 90–99 and 30 young controls aged 19–30). This is a useful cross-sectional age-association check, not a direct analysis of centenarians, and must not be described as exceptional-longevity validation. Source summaries: https://genepi.qimr.edu.au/contents/p/staff/PETERS_NatComms_allOSI.pdf and https://d-nb.info/1205655395/34.

Sources:
- Xiao et al. 2018: https://genome.cshlp.org/content/28/11/1601
- PubMed record: https://pubmed.ncbi.nlm.nih.gov/30352807/
- GSA accession cited by the paper: CRA000515
- GSE351605 is a human ketogenic-diet pre/post dataset:
  https://www.omicsdi.org/dataset/geo/GSE351605

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
