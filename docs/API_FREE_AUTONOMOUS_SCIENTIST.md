# ORACLE hybrid autonomous AI Scientist

## Product decision
ORACLE is a hybrid system with a model-independent scientific core and an optional language-reasoning layer.

- **Native core:** research orchestration, public-source retrieval, evidence extraction/provenance, knowledge graph, statistical analysis, computational experiments, skeptic/auditor checks, checkpoints, and decisions.
- **Language layer:** an open-weight LLM running on a computer/server controlled by the operator. The phone is the control device; no model weights or inference runtime need to be installed on the Pixel.
- **No Gemini integration:** no Gemini SDK, Gemini API key, paid hosted inference service, vendor endpoint, or automatic provider fallback.
- **Self-hosted connection:** the initial adapter speaks the common OpenAI-compatible HTTP protocol to an explicitly configured self-hosted runtime such as llama.cpp, Ollama, or vLLM. This is a network connection to the operator's own server, not a commercial hosted-model API. The user must provide and control the compute host; ORACLE does not provision free compute.
- **Graceful degradation:** if the model is not configured or unavailable, the native scientific core remains usable and clearly reports that language-assisted reasoning is unavailable.

## Trust boundary
The LLM proposes interpretations, plans, summaries, and candidate hypotheses. It is not a source of scientific evidence. Model output must be tied back to retrieved evidence, remain labelled as a proposal, and pass deterministic validation. It cannot directly mark a claim as established, mark an experiment as performed, or execute arbitrary code/tools. Store model identity and non-secret settings for reproducibility; never store credentials in run logs.

## Current implementation slice
`oracle/language_model.py` provides a small optional client for an explicitly configured self-hosted OpenAI-compatible chat-completion endpoint. It has no vendor SDK, no API-key field, no automatic endpoint, and no dependency beyond Python's standard library. It validates message shape, enforces request bounds, and reports connection failures without affecting the native core.

This adapter is wired through an optional structured `LanguageReasoningAgent` into the research cycle. It receives only source-backed evidence, accepts strict JSON proposals, and records language-generated hypotheses as very-low-confidence candidates. Malformed output or model unavailability degrades to the deterministic workflow. It does not install, download, or host a model.

## Runtime options
Self-hosted inference servers commonly expose compatible HTTP endpoints:
- llama.cpp server
- Ollama OpenAI-compatible endpoint
- vLLM server

Choose the runtime according to the actual host hardware. vLLM is designed around GPU-backed serving; llama.cpp supports CPU and GPU inference; Ollama offers a simpler model-management experience. ORACLE does not assume a particular runtime or model.

## Implementation sequence
1. Finalize the hybrid architecture and trust boundary.
2. Add the optional self-hosted model adapter and tests (no Gemini or paid provider).
3. Add typed model task contracts and structured response validation (initial strict-JSON language agent added).
4. Extend optional language reasoning into Planner, Explorer, Hypothesis, and synthesis roles while preserving deterministic fallback (initial cycle-level hypothesis/direction integration added).
5. Add adversarial tests: malformed output, hallucinated citations, unavailable model, prompt injection in retrieved papers, and attempted tool escalation.
6. Add evaluation against deterministic baselines and human-reviewed research tasks.
7. Only then select and benchmark a suitable open-weight model against the actual compute host.

## Acceptance gates
- A fresh install runs the native scientific pipeline without any model setup.
- No Gemini dependency, paid hosted inference, API key, or model weights on the phone.
- The language layer connects only to an explicitly configured operator-controlled server.
- The adapter is optional, bounded, and fails closed without disabling native research.
- Model proposals cannot bypass evidence provenance, statistical validation, skeptic review, or auditor checks.
- All outputs distinguish source evidence, deterministic analysis, and model-generated proposals.
- Real scientific claims and benchmarks remain pending until executed and independently validated.
