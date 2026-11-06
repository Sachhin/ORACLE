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
    warnings: list[str] = field(default_factory=list)


class OpenAlexIncomingCitationClient:
    """Find a bounded set of works that cite each DOI-backed source."""

    def __init__(self, timeout: float = 20.0, mailto: str = "",
                 max_sources: int = 10, max_citing_works: int = 50):
        if timeout <= 0:
            raise ValueError("timeout must be positive.")
        if not 1 <= max_sources <= 25 or not 1 <= max_citing_works <= 100:
            raise ValueError("Incoming citation limits are outside supported bounds.")
        self.timeout = timeout
        self.mailto = mailto.strip()
        self.max_sources = max_sources
        self.max_citing_works = max_citing_works

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
        report = IncomingCitationReport()
        existing = {
            (item.source_id, item.provider, item.target_doi.casefold() if item.target_doi
             else item.target_title.casefold(), item.relation)
            for item in run.citation_links
        }
        for source in [item for item in run.sources if item.doi][:self.max_sources]:
            report.sources_examined += 1
            try:
                encoded_doi = quote(source.doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/"), safe="/.")
                work_url = f"https://api.openalex.org/works/https://doi.org/{encoded_doi}"
                if self.mailto:
                    work_url += "?" + urlencode({"mailto": self.mailto})
                work = self._get_json(work_url)
                work_id = str(work.get("id", "")).rsplit("/", 1)[-1]
                if not work_id.startswith("W"):
                    report.warnings.append(f"{source.doi}: OpenAlex did not resolve a work ID.")
                    continue
                params = {
                    "filter": f"cites:{work_id}",
                    "per-page": str(self.max_citing_works),
                    "sort": "publication_date:desc",
                    "select": "id,doi,title,publication_year,authorships",
                }
                if self.mailto:
                    params["mailto"] = self.mailto
                citing_url = "https://api.openalex.org/works?" + urlencode(params)
                response = self._get_json(citing_url)
                results = response.get("results", [])
                if not isinstance(results, list):
                    report.warnings.append(f"{source.doi}: OpenAlex returned an invalid citing-works list.")
                    continue
                for item in results[:self.max_citing_works]:
                    if not isinstance(item, dict):
                        continue
                    report.citing_works_examined += 1
                    doi = str(item.get("doi") or "").strip().lower()
                    title = str(item.get("title") or "").strip()
                    if not doi:
                        report.works_without_doi += 1
                    if not doi and not title:
                        continue
                    authorships = item.get("authorships") or []
                    author = ""
                    if authorships and isinstance(authorships[0], dict):
                        author = str((authorships[0].get("author") or {}).get("display_name") or "")
                    year = str(item.get("publication_year") or "")
                    key = (source.source_id, "OpenAlex",
                           doi.casefold() if doi else title.casefold(), "cited_by")
                    if key in existing:
                        continue
                    run.citation_links.append(CitationLink(
                        source_id=source.source_id, target_doi=doi,
                        target_title=title, target_author=author,
                        target_year=year, provider="OpenAlex", relation="cited_by",
                    ))
                    existing.add(key)
                    report.links_created += 1
            except Exception as exc:
                report.warnings.append(f"{source.doi}: {exc}")
        run.findings.append(
            f"Incoming citations: {report.links_created} citing works discovered "
            f"from {report.sources_examined} DOI-backed sources; bounded OpenAlex lookup, "
            f"{report.works_without_doi} citing works lacked DOI metadata."
        )
        return report
