# ORACLE model-free autonomous research engine

## Product decision

ORACLE is a deterministic, model-independent scientific research system. It has no AI-model integration and no optional model layer.

- No hosted or local LLM runtime, model weights, model downloads, inference server, or model SDK.
- No API keys, model-provider endpoints, quotas, automatic fallback, prompts, or context-window dependencies.
- Public literature and dataset services are ordinary research-data connectors, not AI-model providers.
- Core work uses deterministic task planning, source retrieval, evidence/provenance management, reproducible statistics, dataset validation, hypothesis templates, skeptic/auditor rules, and experiment-protocol templates.

## Scientific capability boundary

ORACLE can retrieve published sources, preserve their provenance, compare data, run reproducible statistical workflows, identify evidence gaps, and generate explicitly provisional hypotheses from deterministic templates.

It is not an open-ended creative AI scientist. Template-generated hypotheses are not equivalent to human scientific reasoning. ORACLE must not claim novelty, causal mechanism discovery, clinical validation, or experimental success unless the corresponding independent evidence exists.

## Current architecture

1. Planner: bounded deterministic task decomposition and domain routing.
2. Researcher: literature, registry, and public dataset retrieval.
3. Evidence ledger: source-backed claims, citations, evidence links, uncertainty, and contradiction tracking.
4. Explorer: deterministic evidence-gap and alternative-explanation generation.
5. Hypothesis ledger: provisional, traceable candidate mechanisms; no automatic promotion to facts.
6. Skeptic/Auditor: provenance, data-quality, missingness, statistical, and alternative-explanation checks.
7. Experiment planner: falsifiable computational or laboratory protocol templates. Physical experiments remain proposed until an external execution record proves they were performed.

## Acceptance guarantees

- A fresh install and research run require no model setup or model credentials.
- All scientific data operations record source URLs, hashes, methods, and software versions where applicable.
- Missing or unauthenticated sample metadata stays unresolved; aliases and aggregate counts are never used to guess clinical labels.
- Deterministic candidate hypotheses remain provisional and visibly distinct from source evidence.
- A CI pass demonstrates software checks only; it does not establish scientific novelty or biological validity.
