# Independent evidence audit: human longevity and mitochondrial translation

Audit date: 2026-11-16  
Scope: source-level review of the leading ORACLE longevity directions. This is an evidence synthesis, not a new biological discovery.

## Executive verdict

**No previously unknown human longevity mechanism has been validated by ORACLE.** The most coherent direction in the current evidence is a compartment-specific translation pattern: selected mitochondrial ribosomal protein genes (mRPGs) remain above their age-expected expression trajectory in long-lived individuals, while many cytosolic ribosomal protein genes (cRPGs) continue to decline. This pattern is already published prior art, not an ORACLE discovery.

The important open question is now narrower: **what upstream regulation and functional mitochondrial phenotype maintain the selected mRPG program in long-lived people, and does that program causally improve late-life mitochondrial function?**

## Primary evidence reviewed

### 1. Human long-lived cohorts: 8-mRPG signature

Xiao et al., *Cell Reports Medicine* (2026), DOI [10.1016/j.xcrm.2026.102767](https://doi.org/10.1016/j.xcrm.2026.102767), analyzed bulk peripheral-blood transcriptomes from 811 long-lived individuals aged 90–113 and 940 younger controls across three Chinese regional cohorts. The paper reports eight mRPGs deviating upward from the age-associated decline expected from younger controls, while seven cRPGs continued to follow the decline trajectory. The 8-mRPG score was associated with transcriptomic aging/senescence measures and mitochondrial-function-related expression programs. The authors report a similar 8-mRPG pattern in the independent European Leiden Longevity Study cohort.

The paper also reports cell-composition deconvolution and says the mRPG/cRPG expression trajectories remained after composition adjustment. It reports supporting associations in GTEx whole blood and single-cell datasets, with stronger associations in some cell types (notably monocytes) than others.

**Limitations:** this is observational, cross-sectional transcriptomic evidence. It does not prove that mRPG expression causes exceptional longevity, directly measure mitochondrial translation or respiratory capacity in the participants, or identify the upstream regulators. The authors explicitly call for functional experiments and note residual confounding from medication, BMI, diet, and other incompletely controlled factors. They also note cell-type heterogeneity and the lack of a more refined single-cell atlas for these long-lived cohorts. The article reports 1,751 analyzed individuals in the abstract/summary while parts of the Methods describe 1,752 recruited participants; its prior-data counts also differ (441 vs 442), with one missing-age exclusion mentioned. Reconcile these counts from source manifests before reproducing the integrated cohort.

Sources: [full article](https://pmc.ncbi.nlm.nih.gov/articles/PMC13198318/), [PubMed record](https://pubmed.ncbi.nlm.nih.gov/42030936/).

### 2. Functional model-organism evidence: mitonuclear protein imbalance

Houtkooper et al., *Nature* (2013), DOI [10.1038/nature12188](https://doi.org/10.1038/nature12188), used mouse population genetics and *C. elegans* RNAi to implicate MRPS5 and other mitochondrial ribosomal proteins in lifespan regulation. MRP knockdown induced mitonuclear protein imbalance, reduced mitochondrial respiration, activated the mitochondrial unfolded protein response (UPRmt), and extended worm lifespan. Pharmacological perturbations that impair mitochondrial translation also induced related responses.

**Interpretation:** this establishes that mitochondrial translation perturbation can influence lifespan in model organisms. It does not directly validate the human 8-mRPG signature. In particular, reduced MRP function in worms is not the same intervention as preserving higher-than-age-expected expression of selected nuclear-encoded mRPGs in long-lived humans. Dose, timing, tissue, and intervention direction must be tested rather than assumed to be equivalent.

Source: [Nature article](https://www.nature.com/articles/nature12188).

### 3. Human long-lived cohorts: cytosolic ribosome regulation

The 2022 *Science Advances* study, DOI [10.1126/sciadv.abf2017](https://doi.org/10.1126/sciadv.abf2017), analyzed transcriptomes from 185 long-lived individuals and 86 offspring spouses across two Chinese longevity cohorts. It reported downregulation of the cytosolic ribosome pathway in long-lived individuals and implicated ETS1 as a regulator; ETS1 knockdown reduced cytosolic ribosomal-protein expression and cellular senescence in fibroblast assays.

**Interpretation:** this supports a cytosolic ribosome-reduction arm, but it is not evidence about the specific mitochondrial 8-mRPG signature. The fibroblast assays do not prove organism-level lifespan effects.

Source: [PubMed record](https://pubmed.ncbi.nlm.nih.gov/35476452/).

### 4. Human genetics: translation machinery and longevity

Javidnia et al., *Genome Research* (2022), DOI [10.1101/gr.275636.121](https://doi.org/10.1101/gr.275636.121), used Mendelian-randomization analyses of expression of RNA polymerase I/III machinery and ribosomal-protein genes. It reported tissue-specific associations between genetically proxied translation-machinery expression and human longevity.

**Interpretation:** this supports the broader idea that translation machinery is relevant to human aging, but it is not specific to mitochondrial ribosomal proteins. MR interpretation depends on instrument validity, pleiotropy, and tissue specificity.

Source: [full article](https://pmc.ncbi.nlm.nih.gov/articles/PMC8805714/).

### 5. Human tissue translation measurements

Tharakan et al., *RNA Biology* (2021), DOI [10.1080/15476286.2021.1875647](https://doi.org/10.1080/15476286.2021.1875647), used ribosome profiling in human skeletal muscle and found lower translation/occupancy of several mitochondrial-genome-encoded oxidative-phosphorylation transcripts with older age.

**Interpretation:** mitochondrial translation is age-sensitive in human tissue, but mitochondrial-genome-encoded OXPHOS translation is a different measurement from nuclear-encoded mRPG transcript abundance. This is contextual evidence, not direct replication of the 8-mRPG signature.

Source: [full article](https://pmc.ncbi.nlm.nih.gov/articles/PMC8583053/).

## Hypothesis-by-hypothesis assessment

| Candidate | Evidence status | Novelty assessment | Main unresolved test |
|---|---|---|---|
| H1: compartment-specific translation allocation (selected mRPG preservation with cRPG decline) | Supported as an observational expression pattern by the 2026 study and related prior art | **Not novel as stated**; the key pattern is published | Reproduce exact gene score from frozen sample-level data; identify upstream regulators; directly measure mitochondrial translation/function |
| H2: dose-, tissue- and time-dependent mitonuclear stress hormesis | Plausible synthesis of model-organism perturbation evidence and human observational association | **Speculative, not established** | Graded perturbation and rescue of the exact mRPGs; measure translation, respiration, UPRmt and senescence across dose/time/tissue |
| H3: bulk-blood composition or health-status confounding | A necessary alternative explanation; the 2026 paper partially adjusts cell composition but reports cell-type heterogeneity | Not a novel mechanism; a required robustness challenge | Within-cell-type replication and adjustment for age, sex, region, batch, medication, BMI, diet and clinical status |

## ORACLE-specific evidence status

- The frozen ORACLE mission run retrieved literature but recorded **zero differential-expression analyses and zero dataset analyses**.
- The existing GSE58137/GSE65219 analysis uses an autophagy/lysosomal/inflammatory candidate panel, not the exact 8-mRPG signature. GSE58137 had no FDR-significant candidates on either platform; GSE65219 had 14 of 18 panel genes at FDR < 0.05. These results do not validate the 8-mRPG signature.
- CRA000515 public acquisition now cross-references 171 runs, 171 BioSamples and 171 CHHA aliases; available sex/tissue fields were checked. Public records still provide no individual ages or CEN/F1/F1SP cohort labels. The cohort-level sex totals reconcile, but individual group assignments do not. Status remains `metadata_acquired_needs_manual_provenance_review`.
- GSE32493 contains only three centenarians and three controls; the deposited supplementary data used in the existing audit retain group-level summaries rather than per-person values. Descriptive effects must not be assigned inferential p-values or treated as replication.
- PXD047528 is a separate proteomics provenance blocker and cannot validate the longevity mechanism. Its clinical mapping remains unverified.
- No independent expert scores or functional perturbation results have been received.

## Required next experiments and analyses

1. Obtain the complete Mendeley sample-level expression matrix and its annotation/codebook; reconcile the 1,751/1,752 and 441/442 count discrepancies and map source accessions without guessing.
2. Reproduce the exact published eight-gene score and the seven-gene cytosolic comparison from frozen sample-level counts and published code. Preserve the original training/validation splits.
3. Test the signature in an independent cohort with comparable blood collection, age range and phenotype; distinguish cohort replication from reanalysis of overlapping samples.
4. Repeat the analysis within sorted or single-cell-defined cell types and with explicit covariate adjustment. Test medication, BMI, diet, sex, region and library/batch sensitivity where metadata permit.
5. Identify upstream regulators using source-backed regulatory evidence and independent human genetic evidence; treat candidates as hypotheses until experimentally tested.
6. Perturb individual and combined candidate mRPGs over graded dose/time courses in relevant human cell models, with rescue controls. Measure mitochondrial translation, mitonuclear protein balance, respiration/ATP, UPRmt, and senescence. A transcriptional association alone is insufficient.
7. Obtain at least two independent domain-expert reviews with conflicts disclosed and written rationales.

## Release decision

**Scientific discovery gate: NOT PASSED.**  
**Prior-art audit: UPDATED.**  
**Human observational association: REPORTED IN PUBLISHED LITERATURE.**  
**ORACLE independent numerical replication of exact 8-mRPG signature: NOT DONE.**  
**Causal human mechanism: NOT ESTABLISHED.**  
**Functional validation: NOT DONE.**  
**Expert review: PENDING.**

The current defensible output is a set of testable research directions, not a newly discovered longevity mechanism.


## Additional independent prior art: 2018 Hainan centenarian cohort and autophagy–lysosome function

Xiao et al., *Genome Research* (2018), DOI [10.1101/gr.220780.117](https://doi.org/10.1101/gr.220780.117), analyzed peripheral-white-blood-cell transcriptomes from 171 Hainan longevity-family participants: 76 centenarians (mean age 102.2 ± 2.4 years), 54 centenarian offspring (63.2 ± 7.7 years), and 41 offspring spouses (59.9 ± 6.6 years). The paper reported increased autophagy–lysosomal pathway expression in centenarians, including CTSB, ATP6V0C, ATG4D and WIPI1. Overexpression of selected genes promoted autophagy and delayed senescence in cultured IMR-90 cells; overexpression of the Drosophila WIPI1 homolog Atg18a extended fly lifespan. The authors also reported higher serum BECN1 in centenarians and offspring than spouses.

**Evidence grade:** human observational association plus cell/fly functional support. It is not proof that autophagy enhancement caused human longevity. The paper itself notes the female-heavy centenarian sample and that the findings may be particularly applicable to female centenarians.

**Important cohort-independence correction:** this 171-person Hainan cohort is the same cohort whose 171 CRA000515 run/BioSample/CHHA records are now cross-referenced in ORACLE. The independent public BioSample sex labels reproduce the published aggregate counts (101 female, 70 male), but individual alias-to-CEN/F1/F1SP labels remain unavailable. Therefore, the 2018 autophagy result and any later reanalysis of those same 171 participants must not be counted as independent cohort replications of each other.

This prior art changes the mission's novelty assessment: autophagy–lysosome enhancement is also an already-published longevity-associated direction. It remains a reasonable mechanistic arm to test alongside the 2026 mRPG expression signature, but ORACLE must not present either as a new discovery.

Source: [Xiao et al. 2018 full-text record](https://pmc.ncbi.nlm.nih.gov/articles/PMC6211641/); [full article](https://genome.cshlp.org/content/28/11/1601).


### 2018 supplementary-table detail (newly retrieved)

The full Europe PMC supplementary archive is now retrieved and checksummed. Supplemental Table S5 lists 38 autophagy–lysosomal SDEGs, including CTSD, GABARAPL1, CD63, CLN3, CTSB, ATP6AP1, HEXB, LIPA, MAN2B1, AP1S1, PSAP, GM2A, LAPTM4A, WIPI1, GLB1, ATG10, ATG4D, GUSB, CTSC, HGSNAT, CLTA, CD68, NAGLU, AP1B1, GAA, ARSB, ATP6V0C, HEXA, CTSW, CTSH, ABCA2, NAGA, PLA2G15, AP1S2, ATG101, ACP2, SCARB2 and TPP1. Supplemental Table S6 lists 11 potential autophagy regulators: FOXO1, INSR, IGF1R, IGFBP3, RHEB, AKT1, DDIT4, RPS6KB1, IKBKB, PIK3R1 and IRS1.

Supplemental Table S7 reports age-expression correlations for 38 upregulated autophagy–lysosomal genes in the middle-aged F1/F1SP groups; none of the listed p-values is below 0.05. This does not negate the centenarian-versus-spouse group association, but it does not support a simple monotonic age trend across the middle-aged offspring/spouse subset.

Crucially, Supplemental File S1 references a missing samples_information.csv containing the sample IDs/row names, condition (CEN/F1/F1SP), read_type and library_type. That CSV is not in the public supplement archive. Thus the exact 171-sample individual crosswalk remains unavailable even after the supplement retrieval.


## Exact published gene signatures recovered from Figure 4B (2026 article)

The full Europe PMC supplementary archive was retrieved (PMCID PMC13198318; DOI 10.1016/j.xcrm.2026.102767). Inspection of Figure 4B in the article PDF gives the exact published gene panels:

- **8 mRPG signature:** MRPL3, MRPL32, MRPL42, MRPL45, MRPL50, MRPS10, MRPS33, MRPS35.
- **7 cRPG comparator:** RPL10A, RPL22, RPL4, RPL5, RPS13, RPS23, RPS6.

These are published prior-art signatures, not newly discovered ORACLE genes. The exact gene list removes one blocker for independent numerical replication in non-overlapping public expression cohorts. The Mendeley sample-level matrix and per-sample age/cohort annotations remain unavailable, so the 811-LLI/940-YC Chinese cohort cannot yet be independently reproduced from source data.


## Independent multi-cohort immune-remodelling evidence (2025)

Wang et al., *EBioMedicine* (2025), DOI [10.1016/j.ebiom.2025.105922](https://doi.org/10.1016/j.ebiom.2025.105922), assembled PBMC single-cell data from three centenarian cohorts:
- Lingao, Hainan: 17 centenarians, 9 offspring, 14 controls (new cohort; GSA-Human HRA011570 / PRJCA038980)
- Rugao: 7 centenarians, 6 offspring, 9 controls (reuse of HRA002867, the cohort already reported in the 2022 Rugao study)
- Japan: 7 centenarians, 2 offspring, 3 controls (RIKEN SC2018 public reuse)

The paper reports a combined 31/17/26 count. Across cohorts, it found higher NK-cell proportions and lower B-cell/CD4 T-cell proportions in centenarians; NK cells showed relatively young subset/receptor profiles, with increased RUNX3/KLF4 activity and enhanced NK–T signalling. CyTOF and flow cytometry provided orthogonal validation for selected Lingao findings.

**Interpretation for ORACLE:** this is independent evidence that immune-cell composition and state are major correlates of exceptional longevity. It strengthens H3 (bulk-blood cell-composition/state confounding) and makes cell-type-aware testing essential before interpreting the 8-mRPG bulk signature as cell-intrinsic mitochondrial biology. The study does **not** directly test the 8-mRPG or cRPG gene panels.

**Cohort independence rule:** the 2025 atlas reuses Rugao HRA002867 and Japan RIKEN SC2018; do not count those as new replications on top of their original studies. Lingao is the additional cohort. HRA011570 (Lingao) and HRA002867 (Rugao) are controlled-access; the article says data are available from the corresponding author/GSA-Human. GSA-Human controlled data require DAC authorization, so ORACLE has not downloaded or reanalysed these matrices.

Sources: [Wang et al. 2025 full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC12571583/); [PubMed record](https://pubmed.ncbi.nlm.nih.gov/40945050/); [GSA-Human access policy](https://ngdc.cncb.ac.cn/gsa-human/document/GSA-Human_Request_Guide_for_Users_us.pdf).
