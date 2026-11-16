# ORACLE 2.0 Architecture Specification

## Product direction: deterministic, model-independent scientific research

ORACLE is a source- and data-driven research engine. It does not load, download, call, or require any AI language model.

Its runtime consists of:
1. **Research planning** — bounded, deterministic task decomposition and domain routing.
2. **Literature and source retrieval** — public scholarly metadata and eligible full-text sources through documented connectors.
3. **Evidence management** — provenance-aware claims, citations, evidence links, and explicit uncertainty.
4. **Scientific computation** — reproducible dataset parsing, statistical analysis, differential-expression workflows, missingness evaluation, and numerical validation.
5. **Hypothesis handling** — deterministic, explicitly provisional candidate templates derived from question structure and source-backed evidence gaps.
6. **Skeptic and audit checks** — competing explanations, provenance checks, evidence-type checks, and safe stopping.
7. **Experiment planning** — protocol templates and falsifiable predictions; ORACLE never claims a physical experiment ran unless an external execution record proves it.

## Hard non-dependency guarantees

- No hosted or local LLM inference.
- No model downloads, model weights, model servers, or inference runtimes.
- No model-provider SDKs, API keys, quotas, or provider fallbacks.
- No prompt/context-window or model-generation timeout dependency.
- Research runs must remain useful when every AI model service is unavailable.
- Public research-data connectors may use ordinary HTTP access; they are not AI-model providers.

## Scientific integrity

Deterministic candidate generation is not equivalent to human creativity or general-purpose language reasoning. ORACLE must label generated hypotheses as provisional, preserve source provenance, distinguish observations from inference, and refuse to claim novelty or causal validation without appropriate independent evidence.

Statistical workflows must record input checksums, methods, software versions, cohort definitions, and limitations. Missing or unauthenticated sample metadata must remain unresolved rather than guessed.

## Operating principle

Prefer reproducible source retrieval, explicit computational methods, and independent validation over model-generated narrative. The system must report what it actually retrieved and computed, and clearly mark work that requires a human researcher, submitter metadata, or a physical laboratory.
