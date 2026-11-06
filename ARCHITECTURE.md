# ORACLE 2.0 Architecture Specification

## Product direction
Integrated Deep Research + Autonomous Discovery. Balanced priority: scientific accuracy, useful exploration, reasoning quality, and autonomy. No external model/API integration in the initial build.

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
Agents are replaceable components implementing a common `run(context) -> result` contract. Baseline agents are deterministic and deliberately conservative. The optional Gemini suite implements the same contract for planning, research synthesis, exploration, hypothesis generation, skeptic review, and experiment proposal. It is opt-in through `--agent-provider gemini`; deterministic agents remain the default. Model-generated research statements are always typed as inference, never source evidence. The structural auditor and novelty assessor remain deterministic until provider-backed evaluation is validated.

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
- Proposed, simulated, and performed experiments are distinct statuses.
- Conflicting evidence is retained, not overwritten.
- Confidence is an explicit qualitative assessment, not fabricated precision.
- Novelty assessments are provisional; no unsupported priority claim.
- Stop decisions preserve state and a reason.

## Research memory and gap assessment
Saved runs can be browsed as a portfolio. A transparent heuristic reports missing source coverage, unreviewed claims, hypotheses without evidence links, unresolved contradiction candidates, and incomplete tasks. Related-run lookup is lexical only; it does not merge claims or assert scientific connections.

## Failure and autonomy controls
Cycle budgets, task budgets, checkpoint persistence, deterministic IDs, error events, and explicit stop reasons prevent unbounded loops. Repeated no-progress cycles should trigger re-planning or a safe stop.

## Future provider boundary
Provider adapters will be introduced only after offline lifecycle tests pass. API credentials must be environment variables or a secret store, never committed to source control.
