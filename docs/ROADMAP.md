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
- [x] Research portfolio for saved runs and lexical retrieval of related prior questions
- [x] Shared cross-run scientific knowledge graph with source-backed claim-pair retrieval, dedicated SQLite persistence, provenance revalidation, and human review gates
- [x] Task acceptance criteria, source-backed completion, blocked/retry states, and bounded attempt counts

## Milestone 4 — Real research capabilities
- [x] Common run(context) -> result contract with optional Gemini suite for planner, researcher, explorer, hypothesis, skeptic, experiment, auditor, and novelty agents
- [x] Provider-backed provisional auditor and literature-grounded novelty triage
- [x] Bounded transient retries, timeouts, and quota-exhaustion detection for Gemini
- [x] Ordered Gemini/Groq/OpenRouter routing with explicit transient-failure fallback policy and environment-only credentials
- [x] Bounded Europe PMC open-access full-text retrieval with strict Creative Commons licence checks
- [x] GEO Series supplementary file discovery and size-capped download with SHA-256 checksums
- [x] Bounded descriptive parsing of downloaded GEO TSV/CSV expression matrices with checksums, per-sample summaries, and source-linked dataset records
- [x] Per-sample missingness/variance quality-control flags that preserve all original samples and never silently filter
- [x] Preserve GEO sample accessions, titles, and characteristics for later explicitly defined group comparisons
- [ ] General GEO matrix normalization beyond DESeq2 raw-count workflows
- [x] Count-aware DESeq2 raw-count analysis with explicit categorical batch/covariate designs, rank-deficiency checks, and default median-of-ratios size-factor normalization
- [x] Optional DESeq2 adapter for explicitly mapped raw integer-count two-group designs (external R runtime; CI subprocess mocked)
- [x] Explicit-design Welch contrasts with BH-FDR for user-declared continuous log2 GEO matrices; raw counts rejected
- [x] Bounded first-degree reference discovery from DOI-backed Crossref works
- [x] Bounded incoming citation discovery for DOI-backed works via OpenAlex, with persisted source-linked citation records
- [ ] Citation graph ranking, traversal, and broader citation-network exploration
- [x] Explicit experiment lifecycle recording for proposed, simulated, performed, and evaluated states with execution provenance
- [x] Domain-specific proposed protocol templates for plant, molecular, cell, and computational biology
- [ ] Reproducible domain-specific analysis adapters and independent rerun verification

## Milestone 5 — Evaluation and scientific validation
- [x] Cross-domain golden-question integrity benchmark for the deterministic baseline
- [ ] Human-scored scientific answer-quality benchmark set
- [ ] Benchmarked evidence attribution, entailment, contradiction, and hallucination evaluations (model review suggestions are implemented but not validated as accurate)
- [x] Reproducibility and regression suite across Python 3.10–3.14 CI matrix
- [ ] Human review gates for high-impact claims and real experiments
- [ ] Independent validation that model outputs improve scientific reasoning over deterministic baselines

## Explicit non-goals until validated
- No automatic promotion of model-generated candidates to facts.
- No simulated or proposed experiment is represented as performed.
- No novelty or scientific-priority guarantee.
- No calibrated probability is inferred from the evidence-balance indicator.
