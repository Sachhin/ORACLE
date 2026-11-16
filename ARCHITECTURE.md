# ORACLE 2.0 Architecture Specification

## Product direction: hybrid autonomous AI Scientist
ORACLE combines two independent reasoning layers:
1. **Native scientific core** — deterministic, auditable research planning, evidence/provenance, knowledge graphs, statistical analysis, computational experiments, validation, checkpoints, and safe orchestration.
2. **Optional language intelligence** — an open-weight LLM running on a user-controlled computer/server, connected through a provider-neutral adapter. It supports language-heavy planning, synthesis, cross-domain interpretation, and candidate generation.

ORACLE has no AI-model runtime, model download, inference server, model API, API key, or model-provider fallback. Research execution is deterministic and source/data driven.