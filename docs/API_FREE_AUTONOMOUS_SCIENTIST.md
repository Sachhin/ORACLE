# ORACLE API-free autonomous scientist

## Product decision
Upgrade the existing ORACLE repository in place. Do not install a local LLM and do not use Gemini, hosted LLM APIs, paid inference services, or model API keys. The phone is the control and operating device; scientific computation and data retrieval use the existing Python toolchain and public scientific resources.

## What ORACLE can honestly be without an LLM
ORACLE can become an autonomous, reproducible computational research system. It can plan bounded investigations, retrieve papers and datasets, extract and link evidence, identify gaps, generate competing candidate hypotheses using explicit operators, run statistical/computational tests, challenge candidates against counter-evidence, and decide what to investigate next. It cannot claim open-ended language-model creativity or human-level scientific reasoning. Tasks requiring those capabilities must be labelled as unsupported rather than simulated.

## Target architecture
1. **Research controller** — bounded state machine with task budgets, checkpoints, resume, retries, and progress-based stopping.
2. **Source acquisition** — executable connectors for literature, citation networks, ontologies, and public datasets. Record retrieval time, query, source identifiers, licence/access constraints, and checksums.
3. **Evidence pipeline** — normalize records, extract claims/measurements, preserve exact source spans/locators, deduplicate, and attach provenance.
4. **Knowledge and gap engine** — evidence graph, contradiction candidates, missing populations/conditions, under-tested links, and cross-domain candidate links.
5. **Hypothesis search** — explicit, inspectable operators generate alternatives from observed gaps and relationships. Every candidate records its generating rule, input evidence, assumptions, predictions, and falsifiers.
6. **Skeptic and auditor** — deterministic checks for confounding, reverse causality, selection bias, sample-size limitations, multiple testing, leakage, unsupported causal language, source quality, and provenance.
7. **Computational experiment engine** — execute only allowlisted analysis tools; predefine outcomes and controls; record environment, parameters, inputs, outputs, and checksums. Distinguish proposed, simulated, and actually performed experiments.
8. **Decision and learning loop** — prioritize next actions using transparent evidence coverage, testability, uncertainty, cost, and replication criteria. Update the plan after each result.
9. **Phone-first operation** — low-memory sequential tasks, resumable jobs, bounded downloads, and a simple dashboard/CLI. No model weights or local inference server.

## Required agent roles
- Planner: convert a question into bounded, source-specific tasks and measurable success criteria.
- Researcher: retrieve and extract source-backed evidence; never invent citations.
- Explorer: identify gaps, alternative domains, and overlooked testable relationships from the evidence graph.
- Hypothesis: generate multiple falsifiable candidates using named rules/operators and retain alternatives.
- Skeptic: search for counter-evidence and methodological weaknesses.
- Experiment: choose and run registered computational analyses when data and tools permit; otherwise produce a clearly labelled proposal.
- Auditor: validate provenance, calculations, assumptions, and claim status.
- Novelty assessor: compare against retrieved prior art and report coverage limits; never assert absolute novelty.

## Implementation sequence
1. Remove the abandoned local-LLM client and its tests/docs; preserve the existing deterministic scientific core.
2. Audit every existing connector and classify it as metadata-only, full-text, dataset-download, parser, or executable analysis. Do not describe catalogued connectors as operational until tested.
3. Add typed hypothesis-generation operators and provenance for every generated candidate.
4. Add evidence-gap and contradiction scoring with transparent formulas and tests.
5. Connect gap outputs to task selection so later cycles actually investigate newly identified gaps.
6. Add bounded allowlisted computational experiment execution and immutable run manifests.
7. Add end-to-end tests using real public datasets, independent replication, and failure/recovery cases.
8. Benchmark outputs against fixed baselines; report unsupported capabilities and limitations.

## Acceptance gates
- No LLM package, model files, inference server, hosted LLM endpoint, or API-key configuration is required.
- A fresh install can run the deterministic research pipeline without model setup.
- Each agent produces typed, testable outputs with provenance.
- Every generated hypothesis is falsifiable, has competing alternatives, and records its generation method.
- Tool execution is allowlisted, bounded, and logged with inputs/outputs.
- Interrupted runs resume without losing evidence or repeating completed expensive work.
- Real dataset analyses reproduce from recorded manifests and pass independent validation.
- Scientific claims are not promoted from heuristic scores or unvalidated correlations.
- Benchmarks demonstrate measurable capability; no unsupported claim of AGI or human-level autonomous science.
