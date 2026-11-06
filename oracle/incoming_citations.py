"""Bounded incoming-citation discovery using the public OpenAlex works API."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .models import CitationLink, ResearchRun


@dataclass
class IncomingCitationReport:
    sources_examined: int = 0
    citing_works_examined: int = 0
    links_created: int = 0
    works_without_doi: int = 0
    external_nodes_created: int = 0
    depth_reached: int = 0
    requests_made: int = 0
    warnings: list[str] = field(default_factory=list)


class OpenAlexIncomingCitationClient:
    """Find a bounded set of works that cite each DOI-backed source."""

    def __init__(self, timeout: float = 20.0, mailto: str = "",
                 max_sources: int = 10, max_citing_works: int = 50,
                 max_depth: int = 1, max_nodes: int = 100):
        if timeout <= 0:
            raise ValueError("timeout must be positive.")
        if not 1 <= max_sources <= 25 or not 1 <= max_citing_works <= 100:
            raise ValueError("Incoming citation limits are outside supported bounds.")
        self.timeout = timeout
        self.mailto = mailto.strip()
        self.max_sources = max_sources
        if not 1 <= max_depth <= 5 or not 1 <= max_nodes <= 250:
            raise ValueError('Multi-hop depth must be 1-5 and node cap 1-250.')
        self.max_citing_works = max_citing_works
        self.max_depth = max_depth
        self.max_nodes = max_nodes

    def _get_json(self, url: str) -> dict:
        request = Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "ORACLE-Incoming-Citations/2.0" +
                          (f" (mailto: {self.mailto})" if self.mailto else ""),
        })
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read(8_000_000).decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read(1500).decode("utf-8", "replace")
            raise RuntimeError(f"OpenAlex HTTP {exc.code}: {detail[:700]}") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"OpenAlex request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("OpenAlex response was not a JSON object.")
        return payload


    def discover(self, run: ResearchRun) -> IncomingCitationReport:
        """Expand incoming citation links breadth-first, adding metadata-only nodes."""
        report = IncomingCitationReport()
        existing_keys = {
            (item.source_id, item.provider,
             item.target_doi.casefold() if item.target_doi else item.target_title.casefold(),
             item.relation)
            for item in run.citation_links
        }
        known_dois = {
            source.doi.strip().casefold().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
            for source in run.sources if source.doi.strip()
        }
        frontier = [item for item in run.sources if item.doi and item.source_type != 'external_citation'][:self.max_sources]
        examined_ids: set[str] = set()
        initial_count = len(run.sources)
        from .models import SourceRecord

        for depth in range(1, self.max_depth + 1):
            if not frontier or len(run.sources) - initial_count >= self.max_nodes:
                break
            next_frontier = []
            for source in frontier:
                if source.source_id in examined_ids:
                    continue
                examined_ids.add(source.source_id)
                report.sources_examined += 1
                try:
                    doi = source.doi.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
                    encoded_doi = quote(doi, safe="/.")
                    work_url = f"https://api.openalex.org/works/https://doi.org/{encoded_doi}"
                    if self.mailto:
                        work_url += "?" + urlencode({"mailto": self.mailto})
                    work = self._get_json(work_url)
                    report.requests_made += 1
                    work_id = str(work.get("id", "")).rsplit("/", 1)[-1]
                    if not work_id.startswith("W"):
                        report.warnings.append(f"{source.doi}: OpenAlex did not resolve a work ID.")
                        continue
                    params = {"filter": f"cites:{work_id}", "per-page": str(self.max_citing_works),
                              "sort": "publication_date:desc",
                              "select": "id,doi,title,publication_year,authorships"}
                    if self.mailto:
                        params["mailto"] = self.mailto
                    response = self._get_json("https://api.openalex.org/works?" + urlencode(params))
                    report.requests_made += 1
                    results = response.get("results", [])
                    if not isinstance(results, list):
                        report.warnings.append(f"{source.doi}: OpenAlex returned an invalid citing-works list.")
                        continue
                    for item in results[:self.max_citing_works]:
                        if not isinstance(item, dict):
                            continue
                        report.citing_works_examined += 1
                        doi_value = str(item.get("doi") or "").strip()
                        normalized_doi = doi_value.casefold().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
                        title = str(item.get("title") or "").strip()
                        if not doi_value:
                            report.works_without_doi += 1
                        if not doi_value and not title:
                            continue
                        authorships = item.get("authorships") or []
                        author = ""
                        if authorships and isinstance(authorships[0], dict):
                            author = str((authorships[0].get("author") or {}).get("display_name") or "")
                        year = str(item.get("publication_year") or "")
                        key = (source.source_id, "OpenAlex",
                               doi_value.casefold() if doi_value else title.casefold(), "cited_by")
                        if key not in existing_keys:
                            run.citation_links.append(CitationLink(
                                source_id=source.source_id, target_doi=doi_value,
                                target_title=title, target_author=author,
                                target_year=year, provider="OpenAlex", relation="cited_by"))
                            existing_keys.add(key)
                            report.links_created += 1
                        if normalized_doi and normalized_doi not in known_dois:
                            if len(run.sources) - initial_count >= self.max_nodes:
                                continue
                            external = SourceRecord(
                                title=title or doi_value, doi=doi_value, authors=author,
                                published_at=year, provider="OpenAlex",
                                source_type="external_citation", url=doi_value,
                                reliability_rationale="Metadata-only citation node; no evidence or quality assessment inferred.")
                            run.sources.append(external)
                            known_dois.add(normalized_doi)
                            next_frontier.append(external)
                            report.external_nodes_created += 1
                except Exception as exc:
                    report.warnings.append(f"{source.doi}: {exc}")
            if next_frontier:
                report.depth_reached = depth
            frontier = next_frontier

        run.findings.append(
            f"Incoming citations: {report.links_created} links and {report.external_nodes_created} "
            f"metadata-only nodes discovered through depth {report.depth_reached}; "
            f"{report.works_without_doi} citing works lacked DOI metadata.")
        return report
