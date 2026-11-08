# Qwen3 local-model SciFact benchmark

This workflow performs real inference with a pinned Qwen3-0.6B GGUF model
served locally by llama.cpp on a GitHub Actions CPU runner. It does not use
Gemini, a hosted inference API, or an API key.

## Frozen configuration

- Model: Qwen3-0.6B, Q4_K_M GGUF
- Hugging Face repository: `Qwen/Qwen3-0.6B-GGUF`
- Revision: `8e42d41f70cb6c571f58c3f31bd9287b372d97cc`
- Model SHA-256: `b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e`
- Inference: llama.cpp CPU server, loopback only
- Retrieval: deterministic BM25 over the full 5,183-abstract SciFact corpus
- Evaluation: all 300 labelled dev claims, no gold evidence supplied to retrieval or model prompts
- Candidate abstracts per claim: top 10 by default

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

Qwen3-0.6B is a deliberately small edge model chosen to prove that the
self-hosted inference path actually works on CPU. Its scores are a baseline
for this model, quantization, prompt, and retrieval configuration—not evidence
that ORACLE has general scientific reasoning, causal inference, or discovery
capability. The hidden-label SciFact test split is not scored locally.

Official references:
- Qwen3 llama.cpp instructions: https://github.com/QwenLM/Qwen3/blob/main/docs/source/run_locally/llama.cpp.md
- SciFact dataset and split definitions: https://huggingface.co/datasets/allenai/scifact
