# ORACLE Literature Intelligence Engine

## Providers
The opt-in client queries Europe PMC Articles REST API (core results), Crossref REST API (/works), and NCBI GEO DataSets through E-utilities (ESearch followed by ESummary). All are public APIs and need no API key. Crossref's polite pool can be requested with --mailto. Calls have timeouts and bounded result limits. If one provider fails, results from the other are retained; if all fail, an explicit error is raised.

Use --provider both for paper databases, --provider geo for GEO experimental datasets, or --provider all for all three providers. GEO records retain accession (for example GSE...), organism, sample count, platform, dataset type, NCBI landing page, and summary. GEO summaries are stored as EvidenceKind.DATASET with locator='GEO dataset summary'. This is metadata discovery only: raw expression matrices, supplementary files, and sample-level data are not downloaded.

## Exact provenance
Records preserve provider, DOI, PMID, authors, journal, publication date, landing URL, publication type, open-access flag, license metadata, and abstract text. Abstracts are stored as evidence with locator="Abstract" and a stable source ID based on DOI/PMID. Reliability begins at neutral, explicitly unassessed 0.5.

## Candidate statements vs. claims
The extractor splits abstract text into sentence-sized review candidates. It does not resolve pronouns, extract causal relations, or judge entailment. Candidates have claim_type="literature_statement_candidate" and status="unreviewed_candidate". Links are CONTEXTUAL with zero weight. No candidate is treated as support/refutation until a later review stage explicitly judges it.

## Optional Gemini claim extraction

Set the GEMINI_API_KEY environment variable, then add --extract-claims to a literature search. The API key is sent in the x-goog-api-key request header and is never written to the SQLite database or source files. The feature is opt-in and uses the standard library only.

    export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    python -m oracle --literature "embryonic development cell fate signaling" --provider both --limit 10 --extract-claims
    python -m oracle --literature "Arabidopsis heat stress" --provider geo --limit 10 --extract-claims --gemini-model gemini-2.5-flash

The extractor asks Gemini for atomic statements plus exact verbatim source quotes. The application rejects a candidate unless its quote is an exact substring of the source abstract/summary. Candidate records retain the quote, model name, extraction method, and normal source/evidence relationship. Their status is unreviewed_candidate and their evidence links remain CONTEXTUAL with strength zero. This is provenance validation, not scientific fact verification: the model may still misinterpret a quote, and no entailment, support/refutation, or contradiction judgement is made. Human/model review is a separate future stage.

## Cross-paper evidence comparison

Run the comparison stage after quote-grounded extraction:

    python -m oracle --literature "embryonic development cell fate signaling" --provider both --limit 10 --extract-claims --compare-papers

The comparator forms a bounded set of pairs from unreviewed candidate claims linked to different source records. Gemini classifies each pair as corroborates, contrasts, contextual, or not_comparable. A comparison is saved only when it supplies two exact quotations, each found verbatim in its corresponding source abstract or GEO summary. The record stores both claim IDs, evidence IDs, source IDs, quotations, rationale, model, and pending_review status. The default cap is 30 pairs per run.

These labels are model-proposed review leads, not verified scientific conclusions. A contrast is not automatically a contradiction; differences in organism, tissue, condition, method, and endpoint matter. No evidence stance, claim status, hypothesis status, or uncertainty score is changed by this stage. Review by a scientist is required before using a comparison as scientific evidence.

## Run
    python -m oracle --literature "embryonic development cell fate signaling" --limit 10
    python -m oracle --literature "plant nonsense-mediated mRNA decay" --provider europepmc --limit 15 --json

Network calls occur only when --literature is provided. The normal offline workflow remains unchanged.

## Limits
No full-text downloading, raw dataset downloads, additional repository connectors, citation graph crawling, semantic support/refutation review, or autonomous LLM research loop is included yet. Abstracts are not substitutes for full methods/results. Open-access metadata is not a blanket licence to redistribute text.
