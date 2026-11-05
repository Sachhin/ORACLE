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

## Literature search (network opt-in)

ORACLE can search Europe PMC and Crossref public REST APIs without API keys or third-party Python packages. Network access occurs only when --literature is supplied.

    python -m oracle --literature "embryonic development cell fate signaling" --limit 10
    python -m oracle --literature "plant nonsense-mediated mRNA decay" --provider europepmc --limit 15 --json

Each work is stored with DOI/PMID when available, authors, journal, date, provider, landing URL, licence/open-access metadata, and abstract text. Abstracts are source evidence with the exact "Abstract" locator. Sentence splitting produces unreviewed statement candidates only: it does not prove a claim or decide whether a paper supports/refutes it. Initial evidence links are contextual with zero weight until reviewed.

Full-text retrieval, dataset-specific APIs, semantic claim extraction, entailment/contradiction review, citation-network exploration, and LLM reasoning are not yet included. Publisher copyright may apply to abstract text.

## Scope of this milestone

Included: offline research foundation, provenance-aware SQLite knowledge graph, public scholarly metadata/abstract search, deterministic candidate sentence extraction, and offline tests. Real LLM providers and autonomous scientific discovery are not claimed.
