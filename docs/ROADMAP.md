# Implementation Roadmap

Status reflects code currently present on the main branch. Checked items are implemented and covered by tests; they do not imply scientific validity or live-provider verification. Gemini auditor and novelty behavior has unit-level contract tests, but live model quality remains unvalidated.

## Milestone 1 — Offline foundation
- [x] Domain models and integrity-oriented statuses
- [x] SQLite run persistence, normalized knowledge records, and event log
- [x] Replaceable agent contract and deterministic baseline agents
- [x] Integrated research/discovery orchestration
- [x] Bounded cycle policy and resumable checkpoints
- [x] CLI and offline integration tests

## Milestone 2 — Research intelligence
- [x] Evidence graph with claim-to-source relationships
- [x] Hypothesis ledger, source-backed support/opposition links, and human-gated status transitions
- [x] Explicit uncertainty assessments and contradiction review candidates
- [x] Provenance, claim revisions, dependence-aware evidence accounting, and human source-quality review
- [x] Literature retrieval from Europe PMC, Crossref, and NCBI GEO metadata
- [x] Optional source ingestion into the full autonomous research cycle
- [x] Quote-validated Gemini claim extraction and cross-paper comparison candidates
- [x] Quote-grounded support/refute/contextual evidence-review suggestions with a human acceptance gate
- [x] Measured progress, duplicate suppression, critical integrity checks, bounded replanning, and safe no-progress stopping
- [x] Persisted no-progress state and explicit resume of safely stopped runs

## Milestone 3 — Discovery quality
- [x] Transparent knowledge-gap scoring based on source, claim-review, hypothesis, contradiction, and task coverage
- [x] Literature-grounded novelty triage with validated source IDs (provisional; never a priority claim)
- [x] Gemini-proposed cross-domain connections with validated source IDs and a human review gate
- [x] Hybrid domain-specialist routing across nine scientific domains, with explicit user override and persisted routing provenance; specialist profiles guide planning but do not imply that every domain-specific external tool ran
- [x] Research portfolio for saved runs and lexical retrieval of related prior questions
- [x] Shared cross-run scientific knowledge graph with source-backed claim-pair retrieval, dedicated SQLite persistence, provenance revalidation, and human review gates
- [x] Task acceptance criteria, source-backed completion, blocked/retry states, and bounded attempt counts

## Milestone 4 — Real research capabilities
- [x] Common run(context) -> result contract with optional Gemini suite for planner, researcher, explorer, hypothesis, skeptic, experiment, auditor, and novelty agents
- [x] Provider-backed provisional auditor and literature-grounded novelty triage
- [x] Bounded transient retries, timeouts, and quota-exhaustion detection for Gemini
- [x] Ordered Gemini/Groq/OpenRouter routing with explicit transient-failure fallback policy and environment-only credentials
- [x] Bounded Europe PMC open-access full-text retrieval with strict Creative Commons licence checks
- [x] Scientific resource registry distinguishes implemented providers from catalog-only resources; implemented literature adapters include Europe PMC, Crossref, GEO, arXiv and PubChem
- [x] GEO Series supplementary file discovery and size-capped download with SHA-256 checksums
- [x] Bounded descriptive parsing of downloaded GEO TSV/CSV expression matrices with checksums, per-sample summaries, and source-linked dataset records
- [x] Per-sample missingness/variance quality-control flags that preserve all original samples and never silently filter
- [x] Preserve GEO sample accessions, titles, and characteristics for later explicitly defined group comparisons
- [x] Explicit GEO quantile normalization for continuous microarray-like matrices and CPM/log2-CPM transforms for integer raw counts (separate output with checksums)
- [x] TMM effective-library-size CPM/log2-CPM adapter with deterministic tests and factor provenance; optional same-matrix edgeR factor comparison CLI added (live edgeR 4.10.7 comparison now runs in CI with a numerical tolerance assertion)
- [x] Optional limma-voom adapter with explicit two-group raw-count design, R/edgeR/limma version provenance, checksum, and mocked-subprocess tests
- [x] Live adapter parity test against a separately executed limma/edgeR reference script on a fixed 300-feature count matrix (same Bioconductor implementation; checks serialization/reproducibility, not independent algorithm accuracy)
- [x] Provenance-checked external reference comparison tooling for expression matrices and differential-expression tables (MAE/RMSE/correlation and DE call concordance; external reference datasets/results still pending)
- [x] Independent real-dataset limma-voom validation: GSE176260 submitter E/weights comparison PASS; GSE64099 independent GEO experiment published DE-table comparison PASS; GSE176261 same-study validation cohort PASS after calculating TMM factors on all 93 batch-2 QC-passing samples and subsetting the 53 validation samples (expression RMSE 0.0397, Pearson 0.9999; weights RMSE 0.0412, Pearson 0.9998; fixed thresholds retained; frozen in Actions run 42331013427). GSE176261 Bioconductor 3.22 sensitivity audit PASS (expression RMSE 0.0397, weights RMSE 0.0412); Bioconductor 3.13 sensitivity audit PASS after fixing the GEOquery vroom buffer failure (expression RMSE 0.0397, weights RMSE 0.0188; Actions run 42331013024).
- [x] Optional Affymetrix CEL RMA adapter for explicit affy/oligo package families, with input checksums, software/platform provenance, exact sample-identity validation, expected-platform guard, bounded execution, and mocked contract tests; two-sample GPL96 smoke/reference run PASS; full GSE12837 24-sample GPL96 comparison PASS against the submitter GEO RMA matrix (22,283/22,283 probes, 534,792 values, MAE 3.66e-10, RMSE 7.14e-10, Pearson r 1.0000; fixed thresholds RMSE <=0.25 and Pearson >=0.995; Actions run 42331958329). This validates same-study/same-platform preprocessing reproducibility, not universal platform accuracy.
- [x] Explicit row-median imputation for continuous matrices with a separate SHA-256 missingness mask and recorded imputation values; reproducible MCAR/MAR/MNAR masking, synthetic downstream Welch/BH sensitivity diagnostics, and observed-cell holdout comparison of row/column/global median reconstruction added
- [x] Paired orthogonal-assay missingness evaluator: PXD047528 processed DDA/DIA tables verified paired at 15 shared sample aliases and frozen; reconstruction-only baseline scored on 8,859 genuine DDA-missing cells with DIA observations; clinical labels/outcome concordance remain pending because the 15 processed aliases do not map to the 13 clinical participants in the original paper
- [x] Genuine missing-cell reconstruction evaluated on PXD047528: 8,859 of 13,043 DDA-missing cells had paired DIA observations (67.9% coverage); row-median baseline RMSE 1.4675 / Pearson 0.2503 and sample-neighbour KNN candidate RMSE 1.4259 / Pearson 0.2625 (Actions run 42332145750). KNN improves modestly but remains weak; DIA is an orthogonal reference, not error-free absolute truth. [ ] Validate independent biological outcome concordance after source-verified 15-alias-to-13-participant clinical mapping.
- [x] PXD000279 controlled-mixture benchmark executed on the published MaxLFQ output: 5,019 proteins, 612/30,114 LFQ cells missing; expected E. coli log2 fold change 1.585, observed-only median 1.219, row-median 1.205, MinProb 1.226. Status is SCORED_KNOWN_MIXTURE_RATIO, not a claim that any method passed universally or that one imputer is superior.
- [x] Count-aware DESeq2 raw-count analysis with explicit categorical batch/covariate designs, rank-deficiency checks, and default median-of-ratios size-factor normalization
- [x] Optional DESeq2 adapter for explicitly mapped raw integer-count two-group designs (external R runtime; CI subprocess mocked)
- [x] Explicit-design Welch contrasts with BH-FDR for user-declared continuous log2 GEO matrices; raw counts rejected
- [x] Bounded first-degree reference discovery from DOI-backed Crossref works
- [x] Bounded incoming citation discovery for DOI-backed works via OpenAlex, with persisted source-linked citation records
- [x] DOI-resolved directed citation graph ranking with degree counts and bounded PageRank
- [x] Bounded multi-hop citation traversal with incoming/outgoing direction, shortest paths, and depth/node limits
- [x] Bounded multi-hop incoming citation discovery via OpenAlex and outgoing reference discovery via Crossref, adding DOI-backed metadata-only external nodes
- [x] Explicit experiment lifecycle recording for proposed, simulated, performed, and evaluated states with execution provenance
- [x] Domain-specific proposed protocol templates for plant, molecular, cell, and computational biology
- [x] Deterministic GEO normalization adapters with input/output checksums and same-runtime byte-identical rerun check
- [x] Cross-Python-version golden-byte normalization check exercised by the Python 3.10–3.14 CI matrix (does not replace an independent implementation comparison)
- [x] Independent edgeR TMM factor comparison against `edgeR::calcNormFactors` on the same raw-count matrix (live numerical tolerance assertion in CI)
- [x] External-reference comparison CLI with provenance enforcement, file hashes, feature overlap checks, expression-matrix metrics, and DE call concordance
- [x] External trusted limma-voom comparisons against published GSE176260 expression/weight matrices, same-study GSE176261 expression/weight matrices (PASS after full-cohort TMM correction; expression RMSE 0.0397, weights RMSE 0.0412; Bioconductor 3.13 and 3.22 sensitivity audits PASS), and independent GSE64099 published DE results; [ ] complete real Affymetrix CEL/RMA reference comparison

## Milestone 5 — Evaluation and scientific validation
- [x] Cross-domain golden-question integrity benchmark for the deterministic baseline
- [x] Human answer-quality rubric, score validation, source-ID checks, persistence, and per-run aggregation workflow
- [x] Evidence benchmark reviewer-agreement (Cohen's kappa), source/quote coverage, and conditional validity reporting
- [x] Machine-validated benchmark ingestion requirements for frozen source packets, two independent reviewers, adjudication, and paired baseline/candidate scores
- [ ] Curated expert-scored scientific answer benchmark set with multiple reviewers and adjudicated labels (rubric, starter questions, and adjudication protocol exist; real labels remain pending)
- [x] Evidence benchmark requires two named human annotations per case, records reviewer agreement, and validates adjudication on disagreement
- [x] SciFact 20-claim live Gemini pilot generated, scored and uploaded (coverage 6.67% of the 300-claim dev split; pilot metrics are not treated as full-split performance); [ ] full 300-claim dev prediction/scoring run 42332253805 in progress after changing main-push default to MAX_CLAIMS=0.
- [ ] Empirical evidence attribution, entailment, contradiction, and hallucination benchmark results (frozen ORACLE predictions and expert adjudication remain pending)
- [x] Reproducibility and regression suite across Python 3.10–3.14 CI matrix
- [x] High-impact claim review requires independent source groups, reviewer identity, and rationale
- [x] Performed-experiment execution provenance requires independent human acceptance before evaluation
- [x] Paired model evaluator requires per-reviewer scores for both systems and bootstraps paired cases rather than treating reviewer ratings as independent samples
- [x] Blinded A/B review packet generation with reviewer-specific randomization, separate private unblinding keys, frozen source/model/prompt provenance, and strict score unblinding validation
- [ ] Empirical validation that model outputs improve scientific reasoning over deterministic baselines (populated blinded evaluations and independent scoring remain pending)

## Explicit non-goals until validated
- No automatic promotion of model-generated candidates to facts.
- No simulated or proposed experiment is represented as performed.
- No novelty or scientific-priority guarantee.
- No calibrated probability is inferred from the evidence-balance indicator.
