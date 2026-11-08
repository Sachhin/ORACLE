# ORACLE 2.0 Architecture Specification

## Product direction: hybrid autonomous AI Scientist
ORACLE combines two independent reasoning layers:
1. **Native scientific core** — deterministic, auditable research planning, evidence/provenance, knowledge graphs, statistical analysis, computational experiments, validation, checkpoints, and safe orchestration.
2. **Optional language intelligence** — an open-weight LLM running on a user-controlled computer/server, connected through a provider-neutral adapter. It supports language-heavy planning, synthesis, cross-domain interpretation, and candidate generation.

The native scientific core must run without the language model. The model is an optional reasoning assistant, never the source of scientific truth. ORACLE must not require Gemini, a paid hosted-model service, vendor API keys, or an installed LLM on the phone. No vendor endpoint or model fallback is enabled by default.

## Layered architecture
1. **Core** — configuration, run lifecycle, orchestration, checkpoints, event log.
2. **Research planning** — question decomposition, task planning, strategy selection, and adaptive task prioritization.
3. **Discovery** — evidence mapping, knowledge-gap detection, cross-domain search, and candidate-direction enumeration.
4. **Language reasoning (optional)** — open-weight model on operator-controlled compute; produces structured proposals and interpretations with explicit uncertainty.
5. **Scientific reasoning** — explicit rule-based argument construction, competing hypothesis generation, causal/model comparison, and uncertainty tracking.
6. **Validation** — evidence quality, provenance, uncertainty, contradiction and claim audits, statistical robustness, and independent dataset replication.
7. **Experiment** — proposed protocols, measurable predictions, bounded computational experiments/simulations, and evaluation.
8. **Knowledge** — evidence store, hypothesis ledger, research portfolio, provenance, and transparent gap assessments.
9. **Decision** — continue, re-plan, investigate gap, reject, or conclude.

## Agent contracts
Agents implement a common `run(context) -> result` contract. Deterministic agents require no model credentials or model runtime. Optional language-model output must be distinguishable from source evidence and deterministic analysis. Research statements must be grounded in retrieved source records or explicitly labelled as provisional inferences. Auditor findings are warnings only and never mutate evidence links or claim status. Novelty assessment remains provisional rather than a priority claim.

## Research cycle
QUESTION → PLAN → RETRIEVE SOURCES → EXTRACT EVIDENCE → MAP GAPS → LANGUAGE-ASSISTED INTERPRETATION (OPTIONAL) → GENERATE COMPETING HYPOTHESES → CHALLENGE → COMPUTATIONAL TEST / EXPERIMENT DESIGN → INDEPENDENT VALIDATION → UPDATE KNOWLEDGE → DECIDE.

## Modes
- `deep_research`: evidence-first planning and investigation.
- `autonomous_discovery`: prioritize gap analysis, structured hypothesis search, and testable directions.
- `both`: interleave evidence-first and discovery tasks.

## Language model boundary
- The optional model must be open-weight and run on infrastructure selected and controlled by the operator (for example, a personal workstation or self-managed server).
- The phone remains the control interface; no model weights or inference runtime are required on the Pixel.
- The first adapter supports an explicitly configured OpenAI-compatible HTTP interface used by self-hosted runtimes such as llama.cpp, Ollama, and vLLM. This is a transport protocol to the user's own server, not a dependency on a hosted commercial AI API.
- No endpoint is selected automatically. No API key, vendor SDK, cloud account, or external model-provider fallback is used by the adapter.
- If the self-hosted model is not configured or is offline, the native scientific core continues and marks language-assisted capabilities unavailable.
- Model output is untrusted proposal text. It cannot directly write evidence, promote claims, execute arbitrary tools, or mark experiments as performed.
- All scientific outputs must pass deterministic provenance, statistical, skeptic, and auditor checks. Preserve prompts/model identity/configuration for reproducibility without storing secrets.

## API-free scientific reasoning strategy
- Prefer deterministic, inspectable methods: literature co-occurrence and citation analysis, ontology/path expansion, knowledge-graph traversal, causal graph candidate generation, statistical model comparison, sensitivity analysis, meta-analysis where compatible data exist, and reproducible computational simulations.
- Generate hypotheses from explicit, inspectable operators over observed gaps and relationships; retain competing explanations and record the rule/data that generated each candidate.
- Rank candidates using transparent criteria (evidence coverage, testability, contradiction burden, independent replication, and data availability). Never label a heuristic score as biological truth or probability unless calibrated.
- Use adaptive search: each completed tool result updates the evidence/gap ledger and the next task selection. Every action is bounded, logged, and resumable.

## Integrity invariants
- Every evidence item has a source/provenance description and evidence type.
- A claim without supporting evidence is marked as inference or hypothesis.
- Hypotheses are never silently promoted to facts.
- Proposed, simulated, performed, and evaluated experiments retain a separate execution-kind field and provenance; evaluation does not erase whether the record was simulated or performed.
- Conflicting evidence is retained, not overwritten.
- Confidence is explicit and qualitative unless a validated statistical/calibration method supports a numeric value.
- Novelty assessments and cross-domain connection proposals remain provisional; no unsupported priority claim or automatic fact promotion.
- Stop decisions preserve state and a reason.
- Language-model output is never treated as source evidence and never bypasses the auditor.

## Research memory and gap assessment
Saved runs can be browsed as a portfolio. A transparent heuristic reports missing source coverage, unreviewed claims, hypotheses without evidence links, unresolved contradiction candidates, and incomplete tasks. Related-run lookup is lexical or graph-based only; it does not assert scientific connections without evidence.

## Failure and autonomy controls
Cycle budgets, task budgets, checkpoint persistence, deterministic IDs, event logs, and no-progress stopping prevent unbounded loops. Failed external data retrieval must be visible and retryable under bounded policies. Consequential external actions require human approval. Language-model failure must degrade gracefully to native-only operation.

## Provider boundary
The core research loop has no dependency on a hosted-model provider, vendor SDK, API key, or local phone model runtime. An optional, explicitly configured adapter may send prompts to the operator's own self-hosted inference server using its HTTP protocol. Scientific retrieval uses public data services independently of model inference; some data services may have optional provider-specific credentials.

## External research connectors
Europe PMC and Crossref metadata/abstract retrieval, licence-gated Europe PMC full text, NCBI GEO metadata, size-capped GEO supplementary downloads, and bounded first-degree Crossref reference discovery are opt-in. Downloaded GEO files are stored with checksums and may be parsed into descriptive dataset records. Affymetrix CEL RMA preprocessing records input/output checksums and software versions but leaves platform annotation and reference validation to the operator. Differential-expression outputs are persisted as analyses and provisional candidate findings, never automatically promoted to scientific claims.
