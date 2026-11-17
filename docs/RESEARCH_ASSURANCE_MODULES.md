# Model-free research assurance modules

ORACLE now includes five deterministic, offline-capable replacement modules. They are
screening and planning tools, not substitutes for missing source-authenticated records,
human expert review, or experiments.

## Modules

1. **Evidence Integrity Engine** — checks source/evidence/claim IDs, dangling links,
   source locators and link-strength bounds.
2. **Cross-Dataset Validation Engine** — summarizes feature-level effect directions and
   adjusted-p values across distinct dataset accessions. It de-duplicates repeated
   analyses within an accession and flags directional conflicts.
3. **Mechanism Discovery Engine** — elevates only directionally concordant, FDR-screened
   multi-dataset features to *association candidates*. It does not claim mechanisms.
4. **Novelty Screen + Skeptic Review** — compares candidate text with supplied prior-art
   records and generates falsification questions. Text overlap is not an exhaustive
   novelty search; automated skepticism is not human peer review.
5. **Experiment Prioritization Engine** — ranks proposed validation work with transparent
   weights: feasibility 30%, information gain 30%, falsifiability 25%, data readiness 15%.
   Scores are planning heuristics and do not mean an experiment was run.

## Input contract

The JSON input may be an ORACLE run object or an object containing `run`. The run may
include `sources`, `evidence`, `claims`, `evidence_claim_links`, `hypotheses`,
and `differential_expression_analyses`. Optional top-level arrays are `prior_art`,
`annotations`, and `experiment_candidates`.

Each differential-expression result should include a feature identifier,
`log2_fold_change` (or `logFC`) and BH-adjusted p-value
(`p_value_adjusted_bh`, `padj`, or `adj.P.Val`). Each analysis must identify its
`dataset_accession`. Distinct accessions are not proof of independent participants.

Example:

```bash
python scripts/run_research_assurance.py --input run_bundle.json \
  --output artifacts/research_assurance/report.json
python -m unittest tests.test_research_assurance -v
```

## Scientific safeguards

- Missing CRA000515 individual age/cohort labels remain missing; aggregate cohort totals
  are never used to assign participant labels.
- PXD047528 technical DDA/DIA analyses do not create a clinical alias-to-patient mapping.
- Automated reviews are never represented as independent human reviews.
- Candidate associations are never labelled causal mechanisms or proven novel discoveries.
- This implementation adds no model runtime, API client, Qwen3 dependency, or Gemini API dependency.

## Status semantics

`SCREEN_COMPLETE` means the deterministic code completed on the supplied input. It does
not mean all scientific validation gates passed. A report must retain the limitations
and unresolved external blockers.
