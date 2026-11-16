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


## Independent longevity mission artifact audit (2026-11-16)

The completed Actions artifact from run
[42831918629](https://github.com/Sachhin/ORACLE/actions/runs/42831918629)
was downloaded and inspected. ORACLE run `run_a19934cc2692` completed 3/3
cycles and contains 256 sources, 51 evidence records, 435 claims, two
hypotheses, and one proposed experiment. Both hypotheses are generic
single-mechanism versus multi-mechanism framings with very-low confidence and
zero supporting or opposing evidence IDs. No experiment was performed or
simulated. The run contains zero differential-expression analyses, zero
dataset analyses, and zero contradiction candidates.

The artifact contains a downloaded GSE351605 normalized-count file, but
GSE351605 is a ketogenic-diet intervention dataset, not a centenarian cohort;
it was not parsed into a verified design or analysed. The separate GSE32493
miRNA report is based on three centenarians and three controls with one
group-summary column per arm. It reports descriptive CPM/log2 fold changes
only and no inferential p-values or adjusted significance. These are
exploratory signals, not novel mechanisms.

See `docs/LONGEVITY_MISSION_AUDIT_2026-11-16.md` for artifact hashes,
numerical details, and the independent interpretation. The longevity
discovery gate remains INCOMPLETE.

## PXD047528 source-manifest validation

A strict validator is now available at
`scripts/validate_pxd047528_clinical_manifest.py`. The preparation workflow's
sample-map template now includes patient ID, phenotype, HAND status, raw DDA
and DIA filenames, alias relationship, mapping rationale, source URL,
source-document SHA-256, and provenance status. Run the validator before
clinical outcome concordance. It requires exactly 15 aliases mapped to 13
distinct patients, 8 HIV and 5 HERPES patients, and the documented HIV HAND
split (3 MND, 2 HAD, 3 cognitively normal). It does not authenticate a source
document by itself; the submitter/repository source must still be inspected.

## Release verification

`scripts/verify_v1_release.py` now checks the frozen CI, Qwen3, GEO,
CRA000515, PXD047528, longevity-audit, and blinded-review artifacts. It
returns BLOCKED rather than allowing missing external evidence to be marked
PASS. The command and input schema are documented in
`docs/ORACLE_V1_RELEASE_GATE.md`.


## CRA000515 additional cross-study provenance source (2026-11-16)

A 2026 Cell Reports Medicine paper, DOI
`10.1016/j.xcrm.2026.102767`, explicitly lists 171 RNA-seq samples from
CRA000515 and 271 from HRA000656, plus 1,310 newly generated samples in
HRA000721, HRA015371, and HRA015372. Its public expression matrix is deposited
as Mendeley Data DOI `10.17632/fpf4y72kfz.1`. The paper names Qing-Peng Kong
(`kongqp@mail.kiz.ac.cn`) as lead contact and says additional reanalysis
information is available on request.

This strengthens the source chain and identifies the corresponding 2026
cohort, but it does not itself publish a sample-level crosswalk for all 171
CRA aliases. The public GSA project record lists 171 BioSamples and the study
description's broad groups (centenarians, offspring, spouses), while the
per-sample BioSample records inspected do not provide all required ages and
cohort labels. The Mendeley page's text-accessible view identifies the dataset
and download control but does not expose the file inventory; its documented
API uses OAuth2 for dataset retrieval. Therefore no clinical group labels are
inferred from the 2026 paper's aggregate counts. A submitter-provided or
publicly downloadable sample annotation table is still required.




## Source-count discrepancy requiring explicit resolution (2026-11-16)

A fresh cross-source check found a material mismatch that must be preserved
rather than normalized away:

- Ahmed et al. (2022), the clinical study linked to PXD047528, reports **13
  plasma samples** in the proteomics analysis: 8 HIV and 5 herpes. Its HAND
  sub-analysis is 5 HAND (3 MND + 2 HAD) versus 3 cognitively normal HIV
  participants.
- The PEPerMINT publication's Table 2 reports PXD047528 as **15 samples, 15
  biological samples, and one technical replicate per biological sample**.
- The PRIDE/ProteomeXchange deposit contains 32 raw files. The raw-file count
  alone cannot identify which files are DDA/DIA pairs, clinical participants,
  technical repeats, quality controls, or exclusions.

These statements do not currently establish a valid 15-alias-to-13-patient
crosswalk. In particular, ORACLE must **not assume** that two of the 15
processed aliases are technical repeats merely to force agreement with the
13-person clinical paper. The 15-biological-sample statement may indicate a
broader or version-different analysis set; the submitter must explain the
difference and provide the corresponding sample manifest.

The current validator deliberately retains the strict 15-alias/13-clinical-
participant acceptance target because the clinical outcome analysis is tied
to the 2022 paper. A manifest that maps 15 distinct biological samples, or
that cannot document the relationship of two aliases to the clinical cohort,
must remain blocked for clinical outcome concordance. Reconstruction-only
DDA/DIA benchmarking remains valid independently of clinical labels.

Required submitter clarification:
1. Are all 15 PEPerMINT aliases part of the same 13-participant clinical
   cohort, or is the processed set broader/different?
2. If there are 15 biological samples, provide the participant/sample IDs and
   explain how those differ from the 13 plasma samples reported in the paper.
3. Identify any QC samples, excluded samples, repeated acquisitions, or
   additional samples, with DDA/DIA raw filenames and reasons.
4. Provide the mapping from each processed alias to raw DDA and DIA files and
   to the original clinical table row, where applicable.

Until this is source-authenticated, clinical validation remains **BLOCKED**.

