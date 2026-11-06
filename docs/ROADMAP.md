# Implementation Roadmap

Status reflects code currently present on the main branch; checked items are implemented and covered by tests, not necessarily scientifically validated. A checked item means implemented and covered by tests; it does not imply scientific validity or live-provider verification.

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
- [ ] Literature-grounded novelty assessment (provisional; never a priority claim)
- [ ] Provenance-backed cross-domain connection proposals
- [x] Research portfolio for saved runs and lexical retrieval of related prior questions
- [ ] Shared cross-run scientific knowledge graph with reviewed cross-run claim/evidence reuse
- [x] Task acceptance criteria, source-backed completion, blocked/retry states, and bounded attempt counts

## Milestone 4 — Real research capabilities
- [x] Common run(context) -> result contract with optional Gemini suite for planner, researcher, explorer, hypothesis, skeptic, and experiment agents
- [ ] Provider-backed auditor and literature-grounded novelty assessment
- [x] Bounded transient retries, timeouts, and quota-exhaustion detection for Gemini
- [ ] Adaptive routing across multiple model providers and explicit fallback policy
- [x] Bounded Europe PMC open-access full-text retrieval with strict Creative Commons licence checks
- [x] GEO Series supplementary file discovery and size-capped download with SHA-256 checksums
- [ ] Automatic parsing/normalization of downloaded GEO matrices and raw data into scientific evidence
- [x] Bounded first-degree reference discovery from DOI-backed Crossref works
- [ ] Incoming citation discovery, graph ranking, and broader citation-network exploration
- [x] Explicit experiment lifecycle recording for proposed, simulated, performed, and evaluated states with execution provenance
- [ ] Domain-specific experiment protocols and reproducible analysis adapters

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
