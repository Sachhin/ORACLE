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
    warnings: list[str] = field(default_factory=list)


class CrossrefCitationClient:
    """Retrieve reference lists for a bounded number of DOI-backed source records."""

    def __init__(self, timeout: float = 20.0, mailto: str = "",
                 max_sources: int = 10, max_references_per_source: int = 50):
        if timeout <= 0:
            raise ValueError("timeout must be positive.")
        if not 1 <= max_sources <= 25 or not 1 <= max_references_per_source <= 100:
            raise ValueError("Citation discovery limits are outside supported bounds.")
        self.timeout = timeout
        self.mailto = mailto.strip()
        self.max_sources = max_sources
        self.max_references_per_source = max_references_per_source

    def _get_json(self, doi: str) -> dict:
        url = "https://api.crossref.org/works/" + quote(doi, safe="")
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
        report = CitationNetworkReport()
        existing = {(item.source_id, item.target_doi.casefold(),
                     self._clean(item.target_title).casefold())
                    for item in run.citation_links}
        sources = [item for item in run.sources if item.doi][:self.max_sources]
        for source in sources:
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
                    doi = self._clean(reference.get("DOI") or reference.get("doi")).lower()
                    title = self._clean(reference.get("article-title") or reference.get("unstructured"))
                    author = self._clean(reference.get("author"))
                    year = self._clean(reference.get("year"))
                    if not doi:
                        report.references_without_doi += 1
                    if not doi and not title:
                        continue
                    key = (source.source_id, doi.casefold(), title.casefold())
                    if key in existing:
                        continue
                    run.citation_links.append(CitationLink(
                        source_id=source.source_id,
                        target_doi=doi,
                        target_title=title,
                        target_author=author,
                        target_year=year,
                    ))
                    existing.add(key)
                    report.links_created += 1
            except Exception as exc:
                report.warnings.append(f"{source.doi}: {exc}")
        run.findings.append(
            f"Citation network: {report.links_created} first-degree reference links discovered "
            f"from {report.sources_examined} DOI-backed sources; "
            f"{report.references_without_doi} references lacked DOI metadata."
        )
        return report
