# Qwen3 local-model SciFact benchmark

This workflow performs real inference with a pinned Qwen3-1.7B GGUF model
served locally by llama.cpp on a GitHub Actions CPU runner. It does not use
Gemini, a hosted inference API, or an API key.

## Frozen configuration

- Model: Qwen3-1.7B, Q4_K_M GGUF
- Hugging Face repository: `ggml-org/Qwen3-1.7B-GGUF`
- Revision: `daeb8e2d528a760970442092f6bf1e55c3b659eb`
- Pinned file: `Qwen3-1.7B-Q4_K_M.gguf`
- Model SHA-256: `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`
- Download checksum is verified before model provenance is written.
- Inference: llama.cpp CPU server, loopback only
- Retrieval: deterministic BM25 over the full 5,183-abstract SciFact corpus
- Evaluation: all 300 labelled dev claims, no gold evidence supplied to retrieval or model prompts
- Candidate abstracts per claim: top 20 for retrieval diagnostics; top 4 in model context

## What is measured

The existing ORACLE evaluator reports prediction coverage, SUPPORT/CONTRADICT
stance accuracy, abstract-level evidence precision/recall/F1, sentence-level
evidence precision/recall/F1, and post-inference retrieval recall. The workflow
stores the frozen predictions, input datasets, report, model file, and server
log as a 90-day artifact.

A run is scientifically complete only if all 300 dev claims receive validated
predictions and the report is uploaded. A failed or incomplete run is not
re-labelled as PASS.

## Interpretation

Qwen3-1.7B is a deliberately small edge model chosen to prove that the
self-hosted inference path actually works on CPU. Its scores are a baseline
for this model, quantization, prompt, and retrieval configuration—not evidence
that ORACLE has general scientific reasoning, causal inference, or discovery
capability. The hidden-label SciFact test split is not scored locally.

Official references:
- Pinned GGUF repository and revision: https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/tree/daeb8e2d528a760970442092f6bf1e55c3b659eb
- Qwen3 llama.cpp instructions: https://github.com/QwenLM/Qwen3/blob/main/docs/source/run_locally/llama.cpp.md
- SciFact dataset and split definitions: https://huggingface.co/datasets/allenai/scifact


### Runtime-bounded prompt configuration (2026-11-16)

The full CPU benchmark uses BM25 top-20 for retrieval diagnostics, but exposes
only the top 3 documents to Qwen3. Each document's abstract is capped at 1,600
characters and generated output is capped at 192 tokens. This keeps prompt
size bounded below the 8,192-token llama.cpp context window and makes a
300-claim run more likely to finish inside the 360-minute Actions limit.
The report records both broad retrieval metrics and the smaller model-context
evidence metrics. The narrower context is part of the benchmark configuration
and must be frozen alongside its results; accuracy must be interpreted at
this setting, not as a model-independent score.


### Output-budget consistency check

The five-claim format preflight and the full 300-claim run both use a
192-token generation cap. This is a conservative ceiling for the compact
stance/evidence JSON schema; if outputs are truncated, the run records them
as invalid rather than silently accepting partial evidence. The cap is frozen
as part of this benchmark configuration.
