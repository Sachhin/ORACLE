# External evidence acquisition and scientific review

Updated: 2026-11-17

## CRA000515 — authenticated individual manifest

**Current evidence:** public accession provenance reconciles 171 records, but retrieved metadata has no source-authenticated individual ages or explicit cohort labels. No sample labels are inferred.

**Authoritative route:** corresponding/lead author Qing-Peng Kong (published contact: kongqp@mail.kiz.ac.cn) or the study data custodian.

**Request prepared:** a de-identified manifest mapping public CRA run/BioSample/accession/sample alias to participant key, age or age band, group/cohort/region, permitted sex metadata, and any excluded sample with reason. The request excludes direct identifiers and asks for provenance and access requirements.

**Outreach status:** Request email sent to the published lead-author contact on 2026-11-17. Awaiting response; no authenticated source file has been received.

## PXD047528 — authenticated clinical crosswalk

**Current evidence:** 15 processed aliases are present in the dataset file inventory; the analysis context refers to 13 participants. The alias-to-participant relation and clinical labels are not authenticated. No mapping or outcome is guessed.

**Authoritative route:** primary submitter Saima Ahmed (published contact: saima.ahmed@childrens.harvard.edu) or the study data custodian.

**Request prepared:** a de-identified mapping of each processed alias/raw filename to participant key, aliquot/technical-replicate relation, permitted clinical group/outcome, exclusions and provenance. Direct identifiers are excluded.

**Outreach status:** Request email sent to the published primary-submitter contact on 2026-11-17. Awaiting response; no authenticated crosswalk has been received.

## Independent scientific reviewers

A public call for at least two independent reviewers is open in [GitHub issue #89](https://github.com/Sachhin/ORACLE/issues/89). Desired expertise includes human transcriptomics/statistical genomics, mitochondrial biology, longevity/geroscience, and reproducible bioinformatics. The protocol requires conflict disclosure, blinded paired scoring, frozen corpus, independent scores and adjudication. Three individual invitations were sent on 2026-11-17 to potential reviewers (Albert Higgins-Chen, T. Em Arpawong, and Raghav Sehgal) using publicly listed contact addresses. These are invitations only; acceptance, availability, conflicts and suitability remain unconfirmed. No reviewers are yet recruited and no reviews are complete.

## Published age-trajectory model — reproduction specification

Primary paper: Xiao et al., Cell Reports Medicine (2026), DOI 10.1016/j.xcrm.2026.102767.
- Article: https://pmc.ncbi.nlm.nih.gov/articles/PMC13198318/
- Authors' analysis-code repository: https://github.com/xiaofuhui/longevity_transcriptomics
- Mendeley expression matrix and code package: https://data.mendeley.com/datasets/fpf4y72kfz/1
- Public source script: https://github.com/xiaofuhui/longevity_transcriptomics/blob/main/03.trajectory_analysis.r

The source script implements 10-year age bins, retaining bins with at least 20 samples; per-bin gene expression means; four-cluster Mfuzz trajectory clustering with seed 123; 75% and 85% stratified resampling sensitivity checks; a GAM-based nonlinear trajectory analysis (mgcv) on age-bin means; and a separate 5-year-bin GAM sensitivity path.

The broader age-association analysis uses a linear mixed-effects model on younger controls: expression ~ age + gender + (1 | region), followed by cell-composition adjustment using nine CIBERSORT/LM22 cell fractions and region random effect. The paper reports 8-mRPG GSVA scores compared with a YC-only linear age-prediction model. These are distinct stages and must not be collapsed into a simple group comparison.

### Reproduction inputs and acceptance criteria

Required source files: versioned expression matrix, phenotype/sample manifest with age, group, sex and region, original sample IDs, and code/data release checksums. Obtain data from the Mendeley release or authors and reconcile to CRA/HRA accessions before analysis.

Reproduce in order:
1. Raw-count filtering (>=10 reads in >90% samples per cohort), edgeR TMM normalization, log2-CPM.
2. Pre-correction YC LME with age + gender + region random intercept.
3. Regional batch correction as described, retaining original pre/post-correction variants.
4. CIBERSORT LM22 deconvolution and cell-fraction-adjusted age model.
5. 10-year bin Mfuzz clustering (4 clusters, seed 123), minimum bin n=20.
6. 75%/85% resampling sensitivity, all samples and LLI-only.
7. Nonlinear GAM and 5-year-bin sensitivity.
8. 8-mRPG GSVA and YC-only age trajectory, plus 7-cRPG comparator where all seven genes are measurable.
9. Exact cohort/sample inclusion tables and sensitivity to sex, region, batch and leukocyte composition.

Do not call this a successful reproduction until the source matrix and sample manifest are authenticated, dependencies are version-pinned, cohort inclusion rules match, and key figures/tables can be regenerated within prespecified tolerances.

## Upstream regulators — experimental plan, not completed experiments

No upstream regulator is currently validated. ETS1 evidence in the cited paper concerns cytosolic ribosome activity; MRPS5 is mitochondrial-translation perturbation/longevity context, not a demonstrated transcriptional regulator of the eight genes.

Prioritized hypothesis classes: mitochondrial integrated stress response (ATF4/ATF5/CHOP) and mitochondrial unfolded protein response; PGC-1alpha/NRF1/TFAM-linked mitochondrial biogenesis and nuclear-encoded mitochondrial translation coordination; mTORC1/4E-BP/eIF2alpha translational control as potentially indirect regulation; immune-cell composition/state as a non-cell-autonomous explanation for bulk-blood expression.

Minimum experiment: relevant human primary cells or characterized models; graded CRISPRi/siRNA or validated pharmacological perturbation; measure all eight mRPG transcripts and proteins, mitochondrial translation, respiration, membrane potential and stress markers; include non-targeting, viability, dose/time, rescue/epistasis controls; replicate across independent donors/cell batches and pre-register primary outcomes.

This is a proposed protocol only. ORACLE cannot perform wet-lab perturbations or report results without a collaborating laboratory and real experimental data.

## GSE16717 age-trajectory feasibility audit (actual artifact)

ORACLE downloaded and inspected the source analysis artifact from workflow run 43912408479 (artifact 14248412268; SHA-256 871ea0d4993a2392d261a895992de97892dc8aec8863c6c19372fe386a0e931d). The artifact contains all 150 samples, individual ages/sex/groups, and a 14-gene targeted panel.

Applying the authors' 10-year binning rule and minimum n=20 yields only three eligible bins:
- 50–60: n=31 (19 offspring, 12 controls)
- 60–70: n=55 (29 controls, 26 offspring)
- 90–100: n=44 (44 long-lived siblings)

The 5-year sensitivity similarly has only three bins meeting n>=20: 55–60 (n=22), 60–65 (n=40), and 90–95 (n=34). The 80–90 decade contains only four people; 100+ contains two. There is no overlap of long-lived-sibling ages with the younger control/offspring ages.

Therefore this Leiden cohort cannot support the paper's four-cluster Mfuzz and GAM (k=5 / k=8) trajectory model under the published bin eligibility rule. In addition, the available artifact is a 14-gene panel, not the full transcriptome needed for genome-wide clustering. We did not fit an unstable spline, extrapolate across the age gap, or label this as a reproduction. The exact bin counts and descriptive mRPG gene means are frozen in `data/missions/longevity/gse16717_age_trajectory_feasibility.json`.

**Conclusion:** the published model's exact replication still requires the original 1,751-sample matrix plus authenticated phenotype/sample manifest and the authors' analysis data object. This is a concrete failed-feasibility result, not a negative biological result.
