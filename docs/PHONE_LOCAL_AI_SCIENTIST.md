# Phone-local AI Scientist implementation

## Product decision

Upgrade this repository in place. The existing evidence graph, public scientific
connectors, analysis adapters, provenance checks, checkpoints, and deterministic
agents remain the scientific execution and verification foundation.

The target is a maximum-autonomy research system whose reasoning model runs on
the user's Android phone. Hosted model APIs, Gemini integration, API keys, and
paid inference services are not required.

## Architecture

1. **Local inference boundary** — a replaceable local model runtime, initially
   llama.cpp with a loopback-only endpoint. ORACLE must never send prompts to a
   non-loopback model host.
2. **Reasoning agents** — Planner, Researcher, Explorer, Hypothesis Generator,
   Skeptic, Experiment Designer, Auditor, and Novelty Assessor receive role
   prompts and structured context from the existing research lifecycle.
3. **Scientific tool layer** — existing literature/data connectors and analysis
   adapters execute independently of the model. A model may propose a tool call;
   only registered, validated tools may execute it.
4. **Evidence integrity** — every model-produced statement is provisional until
   linked to source records, observations, or explicitly labelled inference.
   The model cannot promote a hypothesis to a scientific fact.
5. **Autonomy controller** — bounded task/cycle budgets, checkpoints, progress
   measurement, no-progress stopping, and human approval for consequential
   external actions remain mandatory.
6. **Phone resource policy** — small context windows, bounded output tokens,
   sequential agent execution, checkpointing, and graceful deterministic
   fallback when local inference is unavailable.

## First implementation slice

oracle/local_model.py provides a dependency-free client for a local
llama.cpp-compatible runtime. It defaults to 127.0.0.1:8080, rejects non-loopback
hosts, has no API-key field or hosted fallback, and returns explicit errors
instead of silently substituting fabricated reasoning.

This is only the runtime boundary. The built-in agents are still deterministic
until each is deliberately integrated and covered by tests. The local model
must not be described as a completed autonomous scientist until that work and
end-to-end evaluation pass.

## Acceptance gates

- Local runtime can be started and queried on Android/Termux without cloud model credentials.
- Every agent can produce schema-validated structured output and expose model uncertainty/limitations.
- Tool execution is allowlisted, bounded, and logged with inputs and outputs.
- Evidence and hypotheses retain provenance and review status.
- Interrupted runs resume from checkpoints.
- The local-model workflow passes tests on a low-memory Android device and does not claim an experiment was performed when it was only proposed or simulated.
- Benchmarks compare model-backed agents against the deterministic baseline; no intelligence or discovery claim is made without measured improvement.
