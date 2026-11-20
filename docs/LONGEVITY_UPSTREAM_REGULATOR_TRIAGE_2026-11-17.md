# Upstream-regulator evidence triage for the published 8-mRPG panel

Updated: 2026-11-17  
Target panel (published prior art): MRPL3, MRPL32, MRPL42, MRPL45, MRPL50, MRPS10, MRPS33, MRPS35.

## Executive finding

**No upstream regulator currently has direct, source-verified evidence of binding or causally controlling all (or a defined subset) of this exact eight-gene panel in a relevant human longevity context.** The candidates below are pathway-level hypotheses for testing, not discovered regulators. Existing evidence for mitochondrial stress responses and mitochondrial biogenesis cannot be silently upgraded into direct regulation of the 8-mRPG panel.

## Evidence tiers

| Candidate axis | What primary evidence supports | What it does not establish for the 8-mRPG panel | Current classification |
|---|---|---|---|
| OMA1–DELE1–HRI–eIF2α–ATF4 | Mitochondrial stress can signal through OMA1-dependent DELE1 cleavage to HRI/eIF2α and ATF4 in mammalian cells. A multi-omics study identified ATF4 as a major response regulator under several mitochondrial stressors. | Does not show ATF4 occupancy at, or direct regulation of, MRPL3/MRPL32/MRPL42/MRPL45/MRPL50/MRPS10/MRPS33/MRPS35. ATF4 responses vary by stressor and experimental system. | High-priority pathway hypothesis; direct panel regulation unproven. |
| ATF5 / CHOP (DDIT3) / UPRmt | ATF5 and CHOP participate in mammalian mitochondrial proteostasis responses; ATF5 activity can depend on mitochondrial import. | UPRmt activation is not equivalent to regulation of these eight transcripts. The literature is context-dependent: some mitochondrial stress models show ATF4-dominant responses without canonical ATF5-UPRmt activation; other human-cell work reports partially separable ISR and UPRmt arms. | High-priority pathway hypothesis; direct panel regulation unproven. |
| PPARGC1A (PGC-1α)–NRF1/GABPA–mitochondrial biogenesis | Curated human pathway evidence supports NRF1/NRF2 working with PGC-1 coactivators to regulate nuclear-encoded mitochondrial-targeted genes, including TFAM, TFB1M and TFB2M. PGC-1α is a coactivator, not a sequence-specific DNA-binding factor. | This is not proof that the eight mRPG promoters are direct NRF1 targets or that the pathway explains human longevity-associated blood expression. | Medium-priority biogenesis hypothesis; exact panel occupancy required. |
| mTORC1–4E-BP / eIF2α translation control | Broad translational and nutrient-stress regulation may alter mitochondrial protein synthesis and proteostasis. | Primarily indirect at this stage; no exact 8-gene transcriptional control established. | Secondary mechanistic comparator, not a direct TF claim. |
| Immune-cell composition/state | Existing human longevity single-cell work and the ORACLE RIKEN analysis make cell composition/state a credible explanation for bulk-blood differences. | It is a competing explanation, not an upstream regulator. | Mandatory confounder/control axis. |

## Important contradictory/contextual evidence

1. Quirós et al. (2017; J Cell Biol; PMID 28566324; DOI 10.1083/jcb.201702058) found ATF4 to be a major regulator of the mitochondrial stress response in their mammalian-cell stressor panel; canonical ATF5-mediated UPRmt genes were not activated in that specific setting. Mitochondrial stress also reduced mitochondrial ribosomal proteins and mitochondrial translation. This supports stress-response biology, not direct activation of the longevity 8-mRPG panel.
2. Guo et al. (2020; Nature; DOI 10.1038/s41586-020-2078-2) identified the OMA1–DELE1–HRI relay from mitochondrial dysfunction to eIF2α/ATF4. This supplies an upstream signal-transduction route, not evidence that the eight mRPG genes are direct downstream targets.
3. The 2023 Nature study “A cytosolic surveillance mechanism activates the mitochondrial UPR” (DOI 10.1038/s41586-023-06142-0) reports that ISR and UPRmt can be partly separable; ATF4/CHOP knockout did not abolish UPRmt induction in the tested system. This cautions against treating ATF4 as a universal UPRmt master regulator.
4. Reactome human pathway R-HSA-2151201 describes PGC-1α as a coactivator with NRF1/NRF2 for mitochondrial-biogenesis genes including TFAM, TFB1M and TFB2M. Those examples do not establish direct regulation of the eight mRPG genes.

## Falsifiable validation protocol

### Stage A — computational direct-evidence screen (no causal claims)

For each of the eight genes, freeze the canonical transcript, promoter window (for example, -2 kb to +500 bp from the TSS), relevant enhancers, genome build and cell context. Retrieve:
- ENCODE/Cistrome or equivalent ChIP-seq/CUT&RUN peaks for ATF4, ATF5, DDIT3/CHOP, NRF1 and GABPA;
- promoter/enhancer accessibility (ATAC-seq), motif evidence and enhancer-to-gene links;
- perturbation expression datasets for ATF4, ATF5, DDIT3, DELE1/HRI and PPARGC1A/NRF1;
- cell-type-resolved expression in PBMC subsets and relevant human tissues.

Require a reproducible peak-to-gene link in a biologically relevant human cell type, with source accession, genome build, peak coordinates, antibody/assay and replicate QC. Motif presence or co-expression alone is not direct binding evidence. Negative/absent datasets must be recorded as unavailable, not as negative evidence.

### Stage B — causal cell-model test

Use at least two relevant human cell contexts (initially primary PBMC-derived monocytes or sorted immune subsets, plus a non-immune human cell model with intact mitochondrial translation). Across at least three independent donors or biological batches:
- perturb ATF4, ATF5, DDIT3, DELE1/HRI and NRF1/PPARGC1A separately using graded CRISPRi/siRNA; include non-targeting controls;
- include a calibrated mitochondrial stress positive control and a non-mitochondrial ISR control to distinguish general stress from mitochondria-specific signaling;
- measure all eight transcripts and proteins, plus canonical pathway controls (p-eIF2α, ATF4, CHOP, HSPD1, HSPE1, CLPP, LONP1), mitochondrial translation, OXPHOS proteins, oxygen-consumption/respiration, ATP, membrane potential, viability and cell-state composition;
- perform CUT&RUN/ChIP-qPCR at each candidate gene's promoter/enhancer for any TF whose perturbation changes the panel;
- rescue with perturbation-resistant regulator expression or downstream epistasis where feasible.

### Stage C — preregistered decision rules

Call a candidate a **direct regulator of a specific mRPG gene** only if (i) reproducible occupancy is demonstrated at a linked regulatory element in the relevant human cell context, (ii) perturbation changes that gene's expression in a dose/time-consistent manner across independent biological replicates, and (iii) rescue restores the effect. Call a candidate an **upstream regulator of the 8-gene program** only if the criterion is met for a prespecified, biologically coherent subset and the result survives cell-state/viability controls. Functional relevance to mitochondrial translation requires concordant protein/translation or respiration evidence. Longevity causality requires additional human cohort replication and cannot be inferred from cell culture alone.

## Current ORACLE decision

- ETS1 remains an indirect cytosolic-ribosome prior-art candidate only; no direct 8-mRPG relationship is established.
- MRPS5 remains a mitochondrial-translation/UPRmt pathway perturbation comparator, not an upstream regulator of the panel.
- ATF4/ATF5/CHOP and PPARGC1A–NRF1/GABPA are prioritized for direct-evidence screening and future perturbation tests, not reported as validated regulators.
- No wet-lab perturbation or direct occupancy experiment has been performed by ORACLE.
- The current scientific status remains **no validated upstream regulator and no validated new human longevity mechanism**.

## Sources

- Quirós PM et al. 2017. *Multi-omics analysis identifies ATF4 as a key regulator of the mitochondrial stress response in mammals.* J Cell Biol. PMID: 28566324. DOI: https://doi.org/10.1083/jcb.201702058
- Guo X et al. 2020. *Mitochondrial stress is relayed to the cytosol by an OMA1-DELE1-HRI pathway.* Nature. DOI: https://doi.org/10.1038/s41586-020-2078-2
- *A cytosolic surveillance mechanism activates the mitochondrial UPR.* Nature (2023). DOI: https://doi.org/10.1038/s41586-023-06142-0
- Reactome human pathway R-HSA-2151201: https://reactome.org/content/detail/R-HSA-2151201
- PGC-1α promoter occupancy study (2023): https://doi.org/10.1038/s41467-023-41304-8
