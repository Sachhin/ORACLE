# Frozen longevity assurance and v1.0 gate — 2026-11-17

## Execution provenance

- Repository branch: `feat/longevity-frozen-assurance-bundle`
- Pull request: [#167](https://github.com/Sachhin/ORACLE/pull/167)
- Assurance workflow: [run 44043709720](https://github.com/Sachhin/ORACLE/actions/runs/44043709720) — success
- Workflow artifact: `oracle-frozen-longevity-assurance`, artifact ID `14309883429`
- Artifact SHA-256: `744aaeb60376225092d24dd9284749ed836d30d7df98299f2f38ed0bfb92d18d`
- Frozen bundle schema: `oracle-frozen-longevity-assurance/1.1`
- Numerical summary validation: 14/14 checks passed
- The workflow performs no network calls and invokes no LLM/API.

## Actual numerical artifacts inspected

The analysis summaries below were read from the uploaded GitHub Actions artifacts, not reconstructed from prose-only notes.

### GSE16717 (Leiden; published validation cohort reanalysis)

- Workflow run: [43912408479](https://github.com/Sachhin/ORACLE/actions/runs/43912408479)
- Artifact ID: `14248412268`; SHA-256: `871ea0d4993a2392d261a895992de97892dc8aec8863c6c19372fe386a0e931d`
- 150 samples: 50 long-lived siblings, 50 controls and 50 offspring; age and sex metadata available for all 150.
- All eight published mRPG genes were present.
- Long-lived sibling minus control mRPG-8 composite: `-0.1625991` z units; Welch `p=0.315922`; BH `q=0.667099`.
- No individual mRPG gene reached BH FDR < 0.05.
- Long-lived sibling ages (89.27–102.19) do not overlap control ages (43.71–78.76). This is not an age-trajectory replication; regression adjustment would extrapolate outside common age support.
- cRPG-7 score was withheld because RPS6 is absent from GPL2895.

This cohort was already cited by the 2026 paper as a validation cohort; this is a reproducibility check, not a new independent cohort.

### RIKEN SC2018 (Japanese supercentenarian PBMC cohort)

- Workflow run: [43911857872](https://github.com/Sachhin/ORACLE/actions/runs/43911857872)
- Artifact ID: `14248282108`; SHA-256: `bd527a7710b8d0541271be7f05de794b7b283a0b18fc3be9a475dc6fe1d79eeb`
- Checksum-verified H5AD and metadata; 69,844 cells aggregated to 12 donor-level biological replicates (7 supercentenarians, 5 controls).
- All eight mRPG genes were present.
- All-batches panel difference (SC minus CT): `-0.737092` z units; exact donor-label permutation `p=0.010101`.
- Common-firstrun panel difference: `-0.691270` z units; exact permutation `p=0.031566`.
- No individual mRPG gene reached edgeR BH FDR < 0.05 in either analysis.
- Common-batch leave-one-donor-out p-values ranged 0.0182–0.1061; only 6/12 remained nominally below 0.05.
- Individual age/sex and refined leukocyte-subtype labels were unavailable.

The direction is opposite to the published Chinese 8-mRPG association. The donor count is small and the panel significance is sensitive to individual donors. The cohort is counted once despite reuse in several publications.

### GEO context only — not an 8-mRPG test

- Workflow run: [43914355105](https://github.com/Sachhin/ORACLE/actions/runs/43914355105)
- Artifact ID: `14249224272`
- GSE58137 and GSE65219 tested a separate autophagy/lysosomal/inflammatory candidate panel. Three platforms completed with valid age parsing and no missing expression measurements. This cannot be presented as mRPG-8 validation.

## Upstream-regulator candidate triage

- **ETS1:** indirect prior-art candidate only. The cited study concerns cytosolic ribosomal activity and fibroblast senescence. A direct regulatory relationship to the eight mitochondrial ribosomal genes has not been demonstrated.
- **MRPS5:** pathway/perturbation context from model-organism work, not an upstream regulator of the 8-mRPG panel.
- **No validated upstream regulator was identified.** The next discriminating test is direct occupancy/expression plus graded perturbation and rescue of candidate regulators in relevant human cell types, measuring the exact eight genes and mitochondrial translation/function.

## Frozen assurance result

The assurance pipeline completed successfully:

| Module | Result |
|---|---|
| Evidence integrity | PASS |
| Cross-dataset validation | NOT_RUN — incompatible estimands were intentionally not pooled |
| Mechanism discovery | NO_REPLICATED_CANDIDATES |
| Novelty screen | SCREEN_COMPLETE; novelty not established |
| Skeptic review | SCREEN_COMPLETE |
| Experiment prioritization | NO_CANDIDATES supplied |

The bundle includes the prior-art seed, source-backed claim/evidence links, hypothesis records, numerical snapshot, and SHA-256 hashes for each frozen input. It explicitly preserves the original mission's zero differential-expression and zero dataset-analysis counts; the separate numerical audits are not retroactively attributed to that old run.

## v1.0 release gate

The actual verifier executed and returned:

- **4/7 gates PASS**
- **3/7 gates BLOCKED**
- Overall: `BLOCKED`

Passed: release-critical CI, GEO numerical/metadata audit, CRA000515 accession-level provenance, and conservative longevity claim scope.

Still blocked:
1. CRA000515 has 171 cross-referenced run/BioSample/alias records but zero individual age values and zero explicit cohort labels.
2. PXD047528 has 15 processed aliases and a 13-participant study description, but no source-authenticated clinical crosswalk.
3. No completed independent blinded expert reviews or adjudication files have been received.

The release verifier is deliberately configured to exit successfully only when it confirms this expected blocked state in CI; it does not falsely turn a blocked scientific release into a failed engineering workflow.

## Decision

**Engineering execution: PASS. Scientific discovery gate: NOT PASSED. ORACLE v1.0 scientific release: BLOCKED.**

The 8-mRPG signature remains published prior art. The available independent numerical checks are mixed/opposite-direction and exploratory. No new human longevity mechanism, causal regulator, or functional intervention has been validated. No Qwen3 or Gemini API runtime/dependency was added.
