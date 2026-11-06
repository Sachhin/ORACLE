# ORACLE 2.0 Architecture Specification

## Product direction
Integrated Deep Research + Autonomous Discovery. Balanced priority: scientific accuracy, useful exploration, reasoning quality, and bounded autonomy. The offline deterministic baseline is always available; optional literature, Gemini, and R/Bioconductor analysis integrations are opt-in.

## Layered architecture
1. **Core** — configuration, run lifecycle, orchestration, checkpoints, event log.
2. **Research planning** — question decomposition, task planning, strategy selection.
3. **Discovery** — evidence mapping, knowledge-gap detection, alternative directions.
4. **Reasoning** — hypothesis generation, argument construction, counter-hypothesis generation.
5. **Validation** — evidence quality, provenance, uncertainty, contradiction and claim audits.
6. **Experiment** — proposed protocol, measurable predictions, simulation and evaluation.
7. **Knowledge** — evidence store, hypothesis ledger, research portfolio, provenance, and transparent gap assessments.
8. **Decision** — continue, re-plan, investigate gap, reject, or conclude.

## Agent contracts
Agents are replaceable components implementing a common `run(context) -> result` contract. Baseline agents are deterministic and deliberately conservative. The optional Gemini suite implements the same contract for planning, research synthesis, exploration, hypothesis generation, skeptic review, experiment proposal, provisional integrity auditing, literature-conditioned novelty triage, and source-linked cross-domain connection proposals. It is opt-in through `--agent-provider gemini`; deterministic agents remain the default. Model-generated research statements are always typed as inference, never source evidence. Auditor findings are warnings only and never mutate evidence links or claim status. Novelty triage requires source-backed literature evidence, validates every cited source ID against the supplied context, and remains provisional rather than a priority claim.

## Research cycle
QUESTION → PLAN → RESEARCH → DISCOVER → HYPOTHESIZE → CHALLENGE → EXPERIMENT DESIGN → EVALUATE → UPDATE KNOWLEDGE → DECIDE.

## Modes
- `deep_research`: evidence-first planning and investigation.
- `autonomous_discovery`: prioritize gap analysis and novel directions.
- `both`: interleave evidence-first and discovery tasks.

## Integrity invariants
- Every evidence item has a source/provenance description and evidence type.
- A claim without supporting evidence is marked as inference or hypothesis.
- Hypotheses are never silently promoted to facts.
- Proposed, simulated, performed, and evaluated experiments retain a separate execution-kind field and provenance; evaluation does not erase whether the record was simulated or performed.
- Conflicting evidence is retained, not overwritten.
- Confidence is an explicit qualitative assessment, not fabricated precision.
- Novelty assessments and cross-domain connection proposals remain provisional; no unsupported priority claim or automatic fact promotion.
- Stop decisions preserve state and a reason.

## Research memory and gap assessment
Saved runs can be browsed as a portfolio. A transparent heuristic reports missing source coverage, unreviewed claims, hypotheses without evidence links, unresolved contradiction candidates, and incomplete tasks. Related-run lookup is lexical only; it does not merge claims or assert scientific connections.

## Failure and autonomy controls
Cycle budgets, task budgets, checkpoint persistence, deterministic IDs, error events, and explicit stop reasons prevent unbounded loops. Repeated no-progress cycles should trigger re-planning or a safe stop.

## Provider boundary
Deterministic agents remain the default and require no credentials. An optional Gemini suite replaces selected agents behind the same contract; shared Gemini requests use bounded transient retries and stop immediately when quota exhaustion is explicit. Provider failures are checkpointed rather than silently falling back to a different model. Credentials are read from environment variables and must never be committed to source control.

## External research connectors
Europe PMC and Crossref metadata/abstract retrieval, licence-gated Europe PMC full text, NCBI GEO metadata, size-capped GEO supplementary downloads, and bounded first-degree Crossref reference discovery are opt-in. Downloaded GEO files are stored with checksums and may be parsed into descriptive dataset records. Differential-expression outputs are persisted as analyses and provisional candidate findings, never automatically promoted to scientific claims.
