# ORACLE 2.0

**An autonomous scientific research and discovery system.**

ORACLE combines Deep Research and Autonomous Discovery under a balanced operating policy: evidence quality and intellectual honesty constrain exploration, while the system actively searches for knowledge gaps, alternative explanations, and testable hypotheses.

## Current build status

The offline research foundation remains usable without credentials. Optional network literature retrieval uses public scholarly APIs; optional Gemini extraction and cross-paper comparison use a real model only when explicitly enabled. The baseline agents remain deterministic scaffolding. The orchestrator now measures whether unique research information was added, suppresses repeated scaffold records, checks core graph invariants, and stops after repeated no-progress cycles. This is safer lifecycle control, not proof of autonomous scientific reasoning.

## Quick start

Requires Python 3.10+ and no third-party dependencies.

```bash
python -m oracle "How does a fertilized egg develop into a whole organism?"
python -m unittest discover -s tests -v
```

### Optional Gemini research agents

The normal run remains deterministic and offline. To explicitly opt in to Gemini-backed planning, research synthesis, exploration, competing hypothesis generation, skeptic review, and experiment proposal:

    export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    python -m oracle "How does a fertilized egg develop?" --agent-provider gemini --gemini-model gemini-2.5-flash --cycles 3

The Gemini agent suite uses the same `run(context) -> result` contract as the deterministic agents. Model-generated research statements are stored only as INFERENCE, never as source evidence. Hypotheses remain provisional and experiment designs remain PROPOSED. The structural auditor and novelty assessor remain conservative deterministic components. The default provider is still `deterministic`; Gemini is never called unless explicitly selected. A provider error fails and checkpoints the run rather than silently pretending that deterministic output came from Gemini.

## Modes

- `deep_research`: prioritize structured investigation and evidence assessment.
- `autonomous_discovery`: prioritize gaps, competing hypotheses, and new research directions.
- `both`: integrate both modes (default).

## Scientific integrity

ORACLE distinguishes source-backed evidence, inference, hypotheses, proposed experiments, simulated experiments, and experiments actually performed. A simulation is never represented as a real-world experiment. Unknowns and conflicting evidence remain explicit.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) and [docs/ROADMAP.md](docs/ROADMAP.md).

## Literature search (network opt-in)

ORACLE can search Europe PMC and Crossref public REST APIs without API keys or third-party Python packages. Network access occurs only when --literature or --research-literature is supplied.

    python -m oracle --literature "embryonic development cell fate signaling" --limit 10
    python -m oracle "How does a fertilized egg develop?" --research-literature --agent-provider gemini --cycles 3
    python -m oracle "How does a fertilized egg develop?" --research-literature --extract-claims --review-evidence --agent-provider gemini --cycles 3
    python -m oracle --literature "plant nonsense-mediated mRNA decay" --provider europepmc --limit 15 --json
    python -m oracle --literature "Arabidopsis heat stress" --provider geo --limit 10
    python -m oracle --literature "embryo development" --provider all --limit 15

Use --literature for a standalone retrieval run, or --research-literature to ingest retrieved sources into the full QUESTION → PLAN → RESEARCH → DISCOVER → HYPOTHESIZE → CHALLENGE → EXPERIMENT DESIGN → DECIDE cycle. The latter makes retrieved abstracts and GEO summaries available to the selected research agents. Each work is stored with DOI/PMID when available, authors, journal, date, provider, landing URL, licence/open-access metadata, and abstract text. Abstracts are source evidence with the exact "Abstract" locator. Sentence splitting produces unreviewed statement candidates only: it does not prove a claim or decide whether a paper supports/refutes it. Initial evidence links are contextual with zero weight until reviewed.

Optional Gemini claim extraction is available with --extract-claims. It creates source-quoted, unreviewed candidates only; it does not determine truth, entailment, contradiction, or whether a paper supports a hypothesis. Full-text retrieval, raw GEO matrix downloads, other dataset repositories, citation-network exploration, and calibrated evidence evaluation are not yet included. Gemini can now propose quote-grounded support/refute/contextual evidence-review candidates through --review-evidence, but every suggestion remains pending human review and never changes evidence weights automatically. The opt-in Gemini suite covers planner, researcher, explorer, hypothesis generator, skeptic, and experiment designer; auditor and novelty assessment remain deterministic and conservative. Publisher copyright may apply to abstract text.

### Optional Gemini claim extraction

Set GEMINI_API_KEY in your shell (do not put the key in source files or commit it), then run:

    export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    python -m oracle --literature "embryonic development cell fate signaling" --provider both --limit 10 --extract-claims --review-evidence
    python -m oracle --literature "Arabidopsis heat stress" --provider geo --limit 10 --extract-claims --gemini-model gemini-2.5-flash --json

Gemini output is accepted only when its evidence_quote is an exact substring of the retrieved abstract or GEO summary. Each candidate stores that quote, model name, source/evidence link, and an unreviewed status. Its evidence link remains CONTEXTUAL with zero weight. The feature is opt-in; normal offline runs never call Gemini.

### Cross-paper evidence comparison

Add --compare-papers together with --extract-claims to compare candidate statements across distinct papers:

    python -m oracle --literature "embryonic development cell fate signaling" --provider both --limit 10 --extract-claims --compare-papers
    python -m oracle --literature "Arabidopsis heat stress" --provider all --limit 12 --extract-claims --compare-papers --json

Gemini can propose one of four cross-paper relations: corroborates, contrasts, contextual, or not_comparable. Separately, --review-evidence asks Gemini to propose supports, refutes, or contextual for a candidate claim against an independent source passage. Both workflows require exact source quotations and preserve pending human review; model suggestions never change evidence stance or weight automatically. Every saved comparison must include exact quotations found in BOTH source abstracts/summaries. Comparisons retain both source and evidence IDs, model, rationale, and pending_review status. These are review candidates, not verified contradictions or proof of agreement. ORACLE does not change claim status, evidence stance, or uncertainty scores based on these model suggestions. At most 30 claim pairs are sent per run by default.

## Current limitations

The Gemini adapter currently extracts quote-grounded candidate claims and proposes cross-paper relationships; it does not perform complete entailment verification or update scientific truth status. The autonomous cycle defaults to deterministic baseline agents; the optional Gemini agent suite can be selected explicitly. The decision engine's progress signal measures newly persisted unique records, not scientific quality. A stopped run can be explicitly resumed; repeated no-progress cycles will stop it again unless a provider or new input produces new information.
