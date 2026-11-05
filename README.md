# ORACLE 2.0

**An autonomous scientific research and discovery system.**

ORACLE combines Deep Research and Autonomous Discovery under a balanced operating policy: evidence quality and intellectual honesty constrain exploration, while the system actively searches for knowledge gaps, alternative explanations, and testable hypotheses.

## Current build status

This is a clean, API-free foundation. It uses deterministic local agents so the complete research lifecycle can be exercised without network access or model-provider credentials. These agents are scaffolding, not claims of genuine AI-level scientific reasoning.

## Quick start

Requires Python 3.10+ and no third-party dependencies.

```bash
python -m oracle "How does a fertilized egg develop into a whole organism?"
python -m unittest discover -s tests -v
```

## Modes

- `deep_research`: prioritize structured investigation and evidence assessment.
- `autonomous_discovery`: prioritize gaps, competing hypotheses, and new research directions.
- `both`: integrate both modes (default).

## Scientific integrity

ORACLE distinguishes source-backed evidence, inference, hypotheses, proposed experiments, simulated experiments, and experiments actually performed. A simulation is never represented as a real-world experiment. Unknowns and conflicting evidence remain explicit.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) and [docs/ROADMAP.md](docs/ROADMAP.md).

## Scope of this milestone

Included: domain models, SQLite persistence, agent contracts, deterministic baseline agents, research-cycle orchestration, decision policy, CLI, and offline tests.

Not included yet: external literature search, real LLM providers, API keys, wet-lab integrations, or claims of autonomous scientific discovery.
