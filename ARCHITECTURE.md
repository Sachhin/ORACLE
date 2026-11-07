# ORACLE 2.0 Architecture Specification

## Product direction
API-free autonomous scientific research and computational discovery. Priorities are scientific accuracy, useful exploration, transparent reasoning, and bounded autonomy. The core must not require a hosted LLM, model API key, local LLM installation, or paid inference service. Public scientific literature and dataset retrieval are separate from model inference and may use public data-service endpoints.

## Layered architecture
1. **Core** — configuration, run lifecycle, orchestration, checkpoints, event log.
2. **Research planning** — question decomposition, task planning, strategy selection, and adaptive task prioritization.
3. **Discovery** — evidence mapping, knowledge-gap detection, cross-domain search, and candidate-direction enumeration.
4. **Reasoning** — explicit rule-based argument construction, competing hypothesis generation, causal/model comparison, and uncertainty tracking. This is computational reasoning, not free-form LLM reasoning.
5. **Validation** — evidence quality, provenance, uncertainty, contradiction and claim audits, statistical robustness, and independent dataset replication.
6. **Experiment** — proposed protocols, measurable predictions, bounded computational experiments/simulations, and evaluation.
7. **Knowledge** — evidence store, hypothesis ledger, research portfolio, provenance, and transparent gap assessments.
8. **Decision** — continue, re-plan, investigate gap, reject, or conclude.

## Agent contracts
Agents implement a common `run(context) -> result` contract. Built-in agents are deterministic and require no model credentials or model runtime. Research statements must be grounded in retrieved source records or explicitly labelled as provisional inferences. Auditor findings are warnings only and never mutate evidence links or claim status. Novelty assessment remains provisional rather than a priority claim.

## Research cycle
QUESTION → PLAN → RETRIEVE SOURCES → EXTRACT EVIDENCE → MAP GAPS → GENERATE COMPETING HYPOTHESES → CHALLENGE → COMPUTATIONAL TEST / EXPERIMENT DESIGN → INDEPENDENT VALIDATION → UPDATE KNOWLEDGE → DECIDE.

## Modes
- `deep_research`: evidence-first planning and investigation.
- `autonomous_discovery`: prioritize gap analysis, structured hypothesis search, and testable directions.
- `both`: interleave evidence-first and discovery tasks.

## API-free reasoning strategy
- Prefer deterministic, inspectable methods: literature co-occurrence and citation analysis, ontology/path expansion, knowledge-graph traversal, causal graph candidate generation, statistical model comparison, sensitivity analysis, meta-analysis where compatible data exist, and reproducible computational simulations.
- Generate hypotheses from explicit templates/operators over observed gaps and relationships; retain competing explanations and record the rule/data that generated each candidate.
- Rank candidates using transparent criteria (evidence coverage, testability, contradiction burden, independent replication, and data availability). Never label a heuristic score as biological truth or probability unless calibrated.
- Use adaptive search: each completed tool result updates the evidence/gap ledger and the next task selection. Every action is bounded, logged, and resumable.
- No hidden fallback to Gemini, another hosted model, or a downloaded local model. If a task genuinely requires language-model reasoning, mark that capability unavailable rather than pretending a deterministic result is equivalent.

## Integrity invariants
- Every evidence item has a source/provenance description and evidence type.
- A claim without supporting evidence is marked as inference or hypothesis.
- Hypotheses are never silently promoted to facts.
- Proposed, simulated, performed, and evaluated experiments retain a separate execution-kind field and provenance; evaluation does not erase whether the record was simulated or performed.
- Conflicting evidence is retained, not overwritten.
- Confidence is explicit and qualitative unless a validated statistical/calibration method supports a numeric value.
- Novelty assessments and cross-domain connection proposals remain provisional; no unsupported priority claim or automatic fact promotion.
- Stop decisions preserve state and a reason.

## Research memory and gap assessment
Saved runs can be browsed as a portfolio. A transparent heuristic reports missing source coverage, unreviewed claims, hypotheses without evidence links, unresolved contradiction candidates, and incomplete tasks. Related-run lookup is lexical or graph-based only; it does not assert scientific connections without evidence.

## Failure and autonomy controls
Cycle budgets, task budgets, checkpoint persistence, deterministic IDs, event logs, and no-progress stopping prevent unbounded loops. Failed external data retrieval must be visible and retryable under bounded policies. Consequential external actions require human approval.

## Provider boundary
The core research loop has no hosted-model provider, API client, API-key setting, local model runtime, or model-provider fallback. Scientific retrieval uses public data services independently of model APIs; some services may have optional provider-specific credentials. These are data-source access, not LLM inference.

## External research connectors
Europe PMC and Crossref metadata/abstract retrieval, licence-gated Europe PMC full text, NCBI GEO metadata, size-capped GEO supplementary downloads, and bounded first-degree Crossref reference discovery are opt-in. Downloaded GEO files are stored with checksums and may be parsed into descriptive dataset records. Affymetrix CEL RMA preprocessing records input/output checksums and software versions but leaves platform annotation and reference validation to the operator. Differential-expression outputs are persisted as analyses and provisional candidate findings, never automatically promoted to scientific claims.
