# Legacy mixed PR triage: retain GEO fixes, exclude Qwen3

Date: 2026-11-16  
Repository: `Sachhin/ORACLE`

## Decision

PRs #88, #90 and #94 mixed useful GEO/data-provenance changes with Qwen3/local-model runtime and inference changes. The useful deterministic research pieces were separated; no Qwen3 workflow, model client, model weights, inference server or provider dependency was restored.

## Retained or replaced GEO/data work

| Legacy area | Decision | Current model-free implementation |
|---|---|---|
| Human-aging GEO workflow dependency fixes and PR triggers | Retained | `.github/workflows/human-aging-geo-analysis.yml` installs required R/Bioconductor system libraries and runs the GEO analysis on relevant changes |
| GEO age metadata parsing | Retained in deterministic form | `scripts/analyze_human_aging_geo.R` reads explicit age attributes, validates numeric age ranges and avoids treating unrelated text such as percentages as age |
| GSE58137/GSE65219 limma checks | Retained | Live R/Bioconductor workflow and frozen numerical artifacts; GSE58137 had no FDR-significant candidate genes and GSE65219 had 14/18 candidate-panel genes at FDR <0.05 |
| GSE32493 group-aggregate miRNA workflow | Superseded | PR #133's model-free analyzer was retained, then PR #149 added raw-SRA per-sample reanalysis (six source-mapped runs, three controls and three centenarians). No miRNA passed BH FDR <0.05; the study is EBV-transformed B-cell lines and is not a direct mRPG test |
| CRA000515/Mendeley acquisition code | Not carried forward as an operational dependency | The public Mendeley file API requires authorization; alternative public GSA/BioSample metadata acquisition and provenance audit were implemented. Individual age/CEN/F1/F1SP labels remain unavailable and are requested from the authors |
| PXD047528 archive/sample preparation | Retained and extended | PRIDE v3 manifest audit, DDA/DIA pair inventory, SEARCH-report alias clue, blank clinical map template and deterministic source-authenticated clinical crosswalk validator |
| GSE16717 age/sex metadata | Retained and numerically audited | 150 GEO samples, age/sex recovered for all; mRPG-8 simple group comparisons were not significant; cRPG-7 composite withheld because RPS6 is absent |

## Explicitly excluded

- Qwen3 and any other LLM runtime, local model weights, inference endpoint, provider SDK/API key, model fallback or prompt/context-window dependency.
- Qwen3-backed SciFact predictions and paired model-versus-baseline evaluation.
- Any workflow step whose only purpose is to run or benchmark a model.
- Any clinical sample-to-patient/phenotype assignment inferred from alias order or filenames.

## Important corrections from the new audits

1. GEO group-aggregate tables are not biological replicates. GSE32493 was therefore reanalysed from six raw SRA runs with per-sample counts and edgeR.
2. The archived GSE32493 FASTQ records carry Q0–Q10 quality strings and the Illumina SRA 3′ adapter. The model-free pipeline supplies the explicit adapter and disables quality filtering; this is documented as a limitation.
3. The RIKEN SC2018 H5AD was checksum-verified and aggregated by donor, not by cell. Its 8-mRPG composite is directionally lower in supercentenarians than controls, but the small cohort and leave-one-donor-out sensitivity prevent a strong replication/refutation claim.
4. PXD047528's 15 processed aliases have a candidate numeric relationship to 15 SEARCH-report columns, but no source-authenticated bridge to 2019 raw-file suffixes or clinical phenotypes exists. The validator remains blocked until the submitter manifest is supplied.

## Legacy PR status

PRs #88, #90 and #94 remain closed as mixed legacy work. Their useful GEO/data logic is retained or replaced in the current main branch as listed above. No Qwen3 component from those PRs is part of the current architecture.
