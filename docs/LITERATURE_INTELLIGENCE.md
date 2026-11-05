# ORACLE Literature Intelligence Engine

## Providers
The opt-in client queries Europe PMC Articles REST API (core results) and Crossref REST API (/works). Both are public APIs and need no API key. Crossref's polite pool can be requested with --mailto. Calls have timeouts and bounded result limits. If one provider fails, results from the other are retained; if all fail, an explicit error is raised.

## Exact provenance
Records preserve provider, DOI, PMID, authors, journal, publication date, landing URL, publication type, open-access flag, license metadata, and abstract text. Abstracts are stored as evidence with locator="Abstract" and a stable source ID based on DOI/PMID. Reliability begins at neutral, explicitly unassessed 0.5.

## Candidate statements vs. claims
The extractor splits abstract text into sentence-sized review candidates. It does not resolve pronouns, extract causal relations, or judge entailment. Candidates have claim_type="literature_statement_candidate" and status="unreviewed_candidate". Links are CONTEXTUAL with zero weight. No candidate is treated as support/refutation until a later review stage explicitly judges it.

## Run
    python -m oracle --literature "embryonic development cell fate signaling" --limit 10
    python -m oracle --literature "plant nonsense-mediated mRNA decay" --provider europepmc --limit 15 --json

Network calls occur only when --literature is provided. The normal offline workflow remains unchanged.

## Limits
No full-text downloading, dataset repository connectors, citation graph crawling, semantic claim extraction, contradiction detection across article findings, or LLM provider is included yet. Abstracts are not substitutes for full methods/results. Open-access metadata is not a blanket licence to redistribute text.
