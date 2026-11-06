"""Transparent citation-graph traversal and ranking for a saved research run."""
from __future__ import annotations

from collections import defaultdict

from .models import ResearchRun


def rank_citation_graph(run: ResearchRun, iterations: int = 20,
                        damping: float = 0.85, limit: int = 100) -> dict:
    """Rank only edges whose two endpoint papers are present in this run.

    DOI-only references to papers outside the run remain visible as unresolved
    metadata and are not fabricated into graph nodes.
    """
    if not 1 <= iterations <= 100:
        raise ValueError("iterations must be between 1 and 100.")
    if not 0.0 < damping < 1.0:
        raise ValueError("damping must be strictly between 0 and 1.")
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500.")
    sources = {item.source_id: item for item in run.sources}
    doi_to_source = {
        item.doi.casefold().strip(): item.source_id
        for item in run.sources if item.doi.strip()
    }
    outgoing: dict[str, set[str]] = defaultdict(set)
    unresolved = 0
    for link in run.citation_links:
        if link.source_id not in sources or not link.target_doi:
            unresolved += 1
            continue
        target_id = doi_to_source.get(link.target_doi.casefold().strip())
        if target_id is None:
            unresolved += 1
            continue
        if link.relation == "cited_by":
            # link.source_id is the cited work; target DOI is the citing work.
            source_id, destination_id = target_id, link.source_id
        else:
            # Crossref references: link.source_id cites the target DOI.
            source_id, destination_id = link.source_id, target_id
        if source_id != destination_id:
            outgoing[source_id].add(destination_id)

    node_ids = sorted(sources)
    count = len(node_ids)
    if count:
        scores = {node: 1.0 / count for node in node_ids}
        for _ in range(iterations):
            updated = {node: (1.0 - damping) / count for node in node_ids}
            dangling = sum(scores[node] for node in node_ids if not outgoing[node])
            share = damping * dangling / count
            for node in node_ids:
                updated[node] += share
                neighbors = outgoing[node]
                if neighbors:
                    contribution = damping * scores[node] / len(neighbors)
                    for target in neighbors:
                        updated[target] += contribution
            scores = updated
    else:
        scores = {}

    incoming_counts = {node: 0 for node in node_ids}
    outgoing_counts = {node: len(outgoing[node]) for node in node_ids}
    for neighbors in outgoing.values():
        for target in neighbors:
            incoming_counts[target] += 1
    ranked = []
    for node in node_ids:
        source = sources[node]
        ranked.append({
            "source_id": node,
            "title": source.title,
            "doi": source.doi,
            "incoming_edges": incoming_counts[node],
            "outgoing_edges": outgoing_counts[node],
            "pagerank": round(scores[node], 10),
        })
    ranked.sort(key=lambda item: (item["pagerank"], item["incoming_edges"],
                                  item["outgoing_edges"]), reverse=True)
    return {
        "run_id": run.run_id,
        "nodes": count,
        "resolved_edges": sum(len(value) for value in outgoing.values()),
        "unresolved_citation_records": unresolved,
        "iterations": iterations,
        "damping": damping,
        "ranked_sources": ranked[:limit],
        "limitations": (
            "Graph contains only DOI-resolved edges between source records already present in this run. "
            "Unresolved cited/citing works are counted but not added as nodes. Citation counts and PageRank "
            "measure graph connectivity, not evidence quality, truth, importance, or causal support."
        ),
    }
