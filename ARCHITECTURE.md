# ORACLE 2.0 Architecture Specification

## Product direction
Integrated Deep Research + Autonomous Discovery. Balanced priority: scientific accuracy, useful exploration, reasoning quality, and bounded autonomy. The deterministic research engine is model-API-free; public literature and dataset retrieval plus optional R/Bioconductor analysis are opt-in.

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
Agents implement a common `run(context) -> result` contract. The built-in agents are deterministic, conservative, and require no model credentials. Research statements are grounded in retrieved source records or explicitly labelled as provisional inferences. Auditor findings are warnings only and never mutate evidence links or claim status. Novelty assessment remains provisional rather than a priority claim.

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
The core research loop has no hosted-model provider, API client, API-key setting, or model-provider fallback. Research retrieval uses public scientific data services independently of model APIs; provider-specific public data access may have its own optional credentials.

## External research connectors
Europe PMC and Crossref metadata/abstract retrieval, licence-gated Europe PMC full text, NCBI GEO metadata, size-capped GEO supplementary downloads, and bounded first-degree Crossref reference discovery are opt-in. Downloaded GEO files are stored with checksums and may be parsed into descriptive dataset records. Affymetrix CEL RMA preprocessing records input/output checksums and software versions but leaves platform annotation and reference validation to the operator. Differential-expression outputs are persisted as analyses and provisional candidate findings, never automatically promoted to scientific claims.
