# Implementation Roadmap

Status reflects code currently present on the main branch plus the literature-in-cycle work in review. A checked item means implemented and covered by tests; it does not imply scientific validity or live-provider verification.

## Milestone 1 — Offline foundation
- [x] Domain models and integrity-oriented statuses
- [x] SQLite run persistence, normalized knowledge records, and event log
- [x] Replaceable agent contract and deterministic baseline agents
- [x] Integrated research/discovery orchestration
- [x] Bounded cycle policy and resumable checkpoints
- [x] CLI and offline integration tests

## Milestone 2 — Research intelligence
- [x] Evidence graph with claim-to-source relationships
- [x] Hypothesis ledger and support/opposition link model
- [x] Explicit uncertainty assessments and contradiction review candidates
- [x] Provenance, claim revisions, and dependence-aware evidence accounting
- [x] Literature retrieval from Europe PMC, Crossref, and NCBI GEO metadata
- [x] Optional source ingestion into the full autonomous research cycle
- [x] Quote-validated Gemini claim extraction and cross-paper comparison candidates
- [x] Measured progress, duplicate suppression, critical integrity checks, and safe no-progress stopping
- [x] Persisted no-progress state and explicit resume of safely stopped runs

## Milestone 3 — Discovery quality
- [ ] Transparent knowledge-gap scoring based on evidence coverage
- [ ] Literature-grounded novelty assessment (provisional; never a priority claim)
- [ ] Provenance-backed cross-domain connection proposals
- [ ] Research portfolio and shared cross-run memory
- [ ] Task-level completion criteria and task-budget enforcement

## Milestone 4 — Real research capabilities
- [x] Common run(context) -> result contract with optional Gemini suite for planner, researcher, explorer, hypothesis, skeptic, and experiment agents
- [ ] Provider-backed auditor and literature-grounded novelty assessment
- [ ] Adaptive model routing with quota-aware retries and fallback policy (Gemini request timeout is implemented)
- [ ] Legal open-access full-text retrieval with licence checks
- [ ] GEO supplementary/raw data discovery and safe dataset ingestion
- [ ] Citation-network exploration and source-level quality assessment
- [ ] Domain-specific experiment protocols and reproducible analysis adapters

## Milestone 5 — Evaluation and scientific validation
- [ ] Golden research-question benchmark set
- [ ] Evidence attribution, entailment, contradiction, and hallucination evaluations
- [ ] Reproducibility and regression suite across supported Python versions
- [ ] Human review gates for high-impact claims and real experiments
- [ ] Independent validation that model outputs improve scientific reasoning over deterministic baselines

## Explicit non-goals until validated
- No automatic promotion of model-generated candidates to facts.
- No simulated or proposed experiment is represented as performed.
- No novelty or scientific-priority guarantee.
- No calibrated probability is inferred from the evidence-balance indicator.
