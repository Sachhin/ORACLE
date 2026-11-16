# ORACLE longevity hypothesis: independent expert review brief

**Version:** 1.0  
**Prepared:** 2026-11-16  
**Review status:** Awaiting independent reviewers; no expert scores have been received.

## Purpose

Request independent scientific scrutiny of ORACLE's current longevity research directions. This is not a request to endorse ORACLE and not a claim that a new mechanism has been discovered. Reviewers should evaluate whether the hypotheses are novel relative to the cited literature, whether the evidence supports them, and whether the proposed tests can falsify them.

A separate ORACLE v1.0 engineering evaluation requires blinded paired baseline-versus-candidate answers. This brief is a domain-specific scientific review and does not substitute for that paired evaluation.

## Hypotheses to review

### H1 — Compartment-specific translation allocation

Long-lived individuals may preserve a selected mitochondrial ribosomal-protein transcript program above its age-expected trajectory while broader cytosolic ribosome biogenesis declines. This may help maintain mitochondrial protein synthesis while reducing global translation burden.

**Prior art and context**
- 2026 Cell Reports Medicine: 8-mRPG signature in long-lived cohorts, with reported association to transcriptomic aging and an independent Leiden cohort pattern (DOI 10.1016/j.xcrm.2026.102767).
- 2022 Science Advances: ETS1-associated reduction of cytosolic ribosomal-protein expression in long-lived individuals (DOI 10.1126/sciadv.abf2017).
- 2022 Genome Research: Mendelian-randomization evidence relating translation-machinery expression to human longevity (DOI 10.1101/gr.275636.121).
- 2021 human skeletal-muscle ribosome profiling: age-associated decline in translation of mitochondrial-genome-encoded OXPHOS transcripts (DOI 10.1080/15476286.2021.1875647).

### H2 — Dose-, tissue- and time-dependent mitonuclear stress hormesis

Partial or transient mitochondrial translation perturbation may activate mitonuclear protein imbalance and UPRmt in some contexts, while preservation of selected mRPGs may be associated with late-life mitochondrial function in humans.

**Prior art and context**
- 2013 Nature: MRPS5/MRP perturbation, mitonuclear imbalance, UPRmt and lifespan effects in model organisms (DOI 10.1038/nature12188).
- 2026 human LLI transcriptomic signature (DOI 10.1016/j.xcrm.2026.102767).

The intervention direction differs across these studies. The review should assess whether the proposed dose/tissue/time reconciliation is scientifically coherent or merely an ad hoc explanation.

### H3 — Bulk-blood composition or health-status confounding

The 8-mRPG bulk-blood association may partly reflect leukocyte subtype proportions, immune activation, medication, nutrition, chronic disease, region, or cohort selection rather than a cell-intrinsic longevity mechanism.

The 2026 study includes cell-composition modelling in parts of its age-related analysis, but independent within-cell-type replication remains important.

### H4 — Autophagy–lysosome maintenance in long-lived humans

A stronger autophagy–lysosomal expression program may contribute to cellular maintenance in some long-lived populations. This is already published prior art, not a new ORACLE hypothesis discovery.

**Prior art and context**
- 2018 Genome Research: in 76 Hainan centenarians, 54 offspring and 41 spouses, the autophagy–lysosomal pathway was upregulated in centenarians. CTSB, ATP6V0C, ATG4D and WIPI1 overexpression promoted autophagy and delayed senescence in IMR-90 cells; Drosophila Atg18a overexpression extended fly lifespan (DOI 10.1101/gr.220780.117).
- The 171-person Hainan cohort in that paper is the same cohort represented by the 171 CRA000515 records audited by ORACLE. These data must not be counted as an independent cohort replication of one another. Individual CRA000515 alias-to-cohort labels remain unavailable.

The review should assess whether autophagy is a separate mechanistic arm, an upstream/downstream correlate of the mRPG signal, or a shared consequence of cell composition and health status. Human causal evidence remains absent.

## Questions for each reviewer

1. Is each hypothesis clearly distinguished from published prior art? Identify any claim that is not novel.
2. Does the evidence support the stated confidence level, or is it overstated?
3. Are mitochondrial ribosomal proteins, cytosolic ribosomal proteins, and mitochondrial-genome-encoded OXPHOS translation correctly distinguished?
4. What is the strongest alternative explanation or confounder?
5. What single experiment or analysis would most efficiently falsify the hypothesis?
6. Are the proposed tests feasible and sufficiently controlled?
7. Should any hypothesis be rejected, narrowed, or reframed?

## Suggested scoring rubric

Score each dimension from 1 (poor) to 5 (excellent), with a short written rationale:
- prior-art coverage and novelty calibration;
- evidence quality and source fidelity;
- biological plausibility;
- handling of contradictory evidence;
- confounder analysis;
- falsifiability and experimental design;
- uncertainty calibration and claim restraint.

Reviewers should also provide a categorical recommendation for each hypothesis: reject, major revision, retain as low-confidence candidate, or advance to experimental testing.

## Independence and record keeping

- Recruit at least two independent reviewers with relevant expertise in ageing biology, mitochondrial biology, transcriptomics, bioinformatics, or causal inference.
- Collect expertise and conflict-of-interest declarations outside any blinded model-comparison packet.
- Give each reviewer the same frozen source set and hypothesis text.
- Preserve each returned score file, reviewer identity record, date, and SHA-256.
- Adjudicate disagreements before publishing an anonymized aggregate.
- Do not invent reviewer identities, scores, agreement statistics, or endorsements.

## Current ORACLE status

- The 8-mRPG signature is **published prior art**.
- The independent evidence map and three hypotheses are stored in `data/missions/longevity/prior_art_seed.json`.
- GSE58137/GSE65219 are age-association checks on a different candidate panel; they do not independently reproduce the 8-mRPG signature.
- No ORACLE longevity mechanism has passed independent replication or functional validation.
- This brief is prepared; **human expert evaluation is still pending**.
