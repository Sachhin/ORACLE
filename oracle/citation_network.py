"""Bounded first-degree reference discovery from Crossref work metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from urllib.parse import quote
from urllib.request import Request, urlopen
import json

from .models import CitationLink, ResearchRun


@dataclass
class CitationNetworkReport:
    sources_examined: int = 0
    links_created: int = 0
    references_without_doi: int = 0
    external_nodes_created: int = 0
    depth_reached: int = 0
    warnings: list[str] = field(default_factory=list)


class CrossrefCitationClient:
    """Retrieve reference lists for a bounded number of DOI-backed source records."""

    def __init__(self, timeout: float = 20.0, mailto: str = "",
                 max_sources: int = 10, max_references_per_source: int = 50,
                 max_depth: int = 1, max_nodes: int = 100):
        if timeout <= 0:
            raise ValueError("timeout must be positive.")
        if not 1 <= max_sources <= 25 or not 1 <= max_references_per_source <= 100:
            raise ValueError("Citation discovery limits are outside supported bounds.")
        self.timeout = timeout
        self.mailto = mailto.strip()
        self.max_sources = max_sources
        if not 1 <= max_depth <= 5 or not 1 <= max_nodes <= 250:
            raise ValueError('Citation depth must be 1-5 and node cap 1-250.')
        self.max_references_per_source = max_references_per_source
        self.max_depth = max_depth
        self.max_nodes = max_nodes

    def _get_json(self, doi: str) -> dict:
        normalized_doi = str(doi).strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
        url = "https://api.crossref.org/works/" + quote(normalized_doi, safe="")
        request = Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "ORACLE-Citation-Network/2.0 (mailto: " + (self.mailto or "not-provided") + ")",
        })
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read(8_000_000).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Crossref response was not a JSON object.")
        return payload

    @staticmethod
    def _clean(value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()


    def discover(self, run: ResearchRun) -> CitationNetworkReport:
        """Expand references breadth-first using Crossref, bounded by depth and nodes."""
        report = CitationNetworkReport()
        existing = {
            (item.source_id, item.target_doi.casefold() if item.target_doi else "",
             "" if item.target_doi else self._clean(item.target_title).casefold())
            for item in run.citation_links
        }
        known = {
            item.doi.strip().casefold().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
            for item in run.sources if item.doi
        }
        initial_count = len(run.sources)
        frontier = [item for item in run.sources if item.doi and item.source_type != "external_citation"][:self.max_sources]
        examined: set[str] = set()
        from .models import SourceRecord
        for depth in range(1, self.max_depth + 1):
            if not frontier or len(run.sources) - initial_count >= self.max_nodes:
                break
            next_frontier = []
            for source in frontier:
                if source.source_id in examined:
                    continue
                examined.add(source.source_id)
                report.sources_examined += 1
                try:
                    payload = self._get_json(source.doi)
                    references = payload.get("message", {}).get("reference", [])
                    if not isinstance(references, list):
                        report.warnings.append(f"{source.doi}: Crossref returned no reference list.")
                        continue
                    for reference in references[:self.max_references_per_source]:
                        if not isinstance(reference, dict):
                            continue
                        doi = self._clean(reference.get("DOI") or reference.get("doi"))
                        title = self._clean(reference.get("article-title") or reference.get("unstructured"))
                        author = self._clean(reference.get("author"))
                        year = self._clean(reference.get("year"))
                        if not doi:
                            report.references_without_doi += 1
                        if not doi and not title:
                            continue
                        key = (source.source_id, doi.casefold() if doi else "",
                               "" if doi else title.casefold())
                        if key not in existing:
                            run.citation_links.append(CitationLink(
                                source_id=source.source_id, target_doi=doi,
                                target_title=title, target_author=author,
                                target_year=year, provider="Crossref", relation="references"))
                            existing.add(key)
                            report.links_created += 1
                        normalized = doi.casefold().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
                        if normalized and normalized not in known and len(run.sources) - initial_count < self.max_nodes:
                            external = SourceRecord(
                                title=title or doi, doi=doi, authors=author, published_at=year,
                                provider="Crossref", source_type="external_citation", url="https://doi.org/"+doi,
                                reliability_rationale="Metadata-only node discovered through a reference relation; no evidence or quality assessment inferred.")
                            run.sources.append(external)
                            known.add(normalized)
                            next_frontier.append(external)
                            report.external_nodes_created += 1
                except Exception as exc:
                    report.warnings.append(f"{source.doi}: {exc}")
            if next_frontier:
                report.depth_reached = depth
            frontier = next_frontier
        run.findings.append(
            f"Citation network: {report.links_created} reference links and "
            f"{report.external_nodes_created} metadata-only external nodes discovered "
            f"through depth {report.depth_reached}; {report.references_without_doi} "
            "references lacked DOI metadata.")
        return report
