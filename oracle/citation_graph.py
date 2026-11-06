"""Transparent citation-graph traversal and ranking for a saved research run."""
from __future__ import annotations

from collections import defaultdict, deque

from .models import ResearchRun


def _doi_key(value: str) -> str:
    return value.strip().casefold().removeprefix("https://doi.org/").removeprefix("http://doi.org/")


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
        _doi_key(item.doi): item.source_id
        for item in run.sources if item.doi.strip()
    }
    outgoing: dict[str, set[str]] = defaultdict(set)
    unresolved = 0
    for link in run.citation_links:
        if link.source_id not in sources or not link.target_doi:
            unresolved += 1
            continue
        target_id = doi_to_source.get(_doi_key(link.target_doi))
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



def traverse_citation_graph(
    run: ResearchRun,
    start_source_id: str,
    direction: str = "both",
    max_depth: int = 3,
    limit: int = 100,
) -> dict:
    """Return shortest citation paths from one source through resolved run-local edges."""
    if direction not in {"outgoing", "incoming", "both"}:
        raise ValueError("direction must be outgoing, incoming, or both.")
    if not 1 <= max_depth <= 6:
        raise ValueError("max_depth must be between 1 and 6.")
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200.")

    sources = {item.source_id: item for item in run.sources}
    if start_source_id not in sources:
        raise ValueError(f"Start source not found in this run: {start_source_id}")
    doi_to_source = {
        _doi_key(item.doi): item.source_id
        for item in run.sources if item.doi.strip()
    }
    outgoing: dict[str, set[str]] = defaultdict(set)
    incoming: dict[str, set[str]] = defaultdict(set)
    unresolved = 0
    for link in run.citation_links:
        if link.source_id not in sources or not link.target_doi:
            unresolved += 1
            continue
        target_id = doi_to_source.get(_doi_key(link.target_doi))
        if target_id is None:
            unresolved += 1
            continue
        if link.relation == "cited_by":
            citing_id, cited_id = target_id, link.source_id
        else:
            citing_id, cited_id = link.source_id, target_id
        if citing_id != cited_id:
            outgoing[citing_id].add(cited_id)
            incoming[cited_id].add(citing_id)

    def neighbors(node: str) -> list[str]:
        values: set[str] = set()
        if direction in {"outgoing", "both"}:
            values.update(outgoing[node])
        if direction in {"incoming", "both"}:
            values.update(incoming[node])
        return sorted(values)

    queue = deque([(start_source_id, [start_source_id])])
    visited = {start_source_id}
    reached = []
    while queue and len(reached) < limit:
        current, path = queue.popleft()
        depth = len(path) - 1
        if depth >= max_depth:
            continue
        for neighbor in neighbors(current):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            next_path = [*path, neighbor]
            source = sources[neighbor]
            reached.append({
                "source_id": neighbor,
                "title": source.title,
                "doi": source.doi,
                "depth": depth + 1,
                "path_source_ids": next_path,
            })
            if len(reached) >= limit:
                break
            queue.append((neighbor, next_path))

    return {
        "run_id": run.run_id,
        "start_source_id": start_source_id,
        "start_title": sources[start_source_id].title,
        "direction": direction,
        "max_depth": max_depth,
        "nodes_reached": len(reached),
        "unresolved_citation_records": unresolved,
        "results": reached,
        "limitations": (
            "Traversal is limited to DOI-resolved edges whose endpoint source records "
            "already exist in this run. It does not fetch missing papers or prove that "
            "a citation supports the citing paper. Citation direction is a navigation "
            "relationship, not evidence stance or scientific agreement."
        ),
    }
