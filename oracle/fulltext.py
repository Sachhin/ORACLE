"""Licence-gated retrieval of Europe PMC open-access full text."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .models import Evidence, EvidenceKind, ResearchRun


@dataclass
class FullTextReport:
    examined_sources: int = 0
    full_text_records: int = 0
    skipped_no_pmcid: int = 0
    skipped_license: int = 0
    warnings: list[str] = field(default_factory=list)


class OpenAccessFullTextClient:
    """Retrieve only PMC articles with a recognized reuse-friendly CC licence."""

    ALLOWED_LICENSE_PATTERNS = (
        re.compile(r"\bcc\s*by\b", re.I),
        re.compile(r"\bcc\s*by\s*sa\b", re.I),
        re.compile(r"\bcc0\b", re.I),
        re.compile(r"creative commons attribution", re.I),
    )

    def __init__(self, timeout: float = 30.0, max_bytes: int = 10_000_000,
                 max_chars: int = 100_000):
        if timeout <= 0 or max_bytes < 1024 or max_chars < 1000:
            raise ValueError("Invalid full-text retrieval limits.")
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_chars = max_chars

    @classmethod
    def license_allowed(cls, license_text: str) -> bool:
        value = (license_text or "").strip()
        if not value or re.search(r"\bNC\b|non.?commercial|\bND\b|no.?derivatives", value, re.I):
            return False
        return any(pattern.search(value) for pattern in cls.ALLOWED_LICENSE_PATTERNS)

    def _fetch_xml(self, pmcid: str) -> bytes:
        if not re.fullmatch(r"PMC\d+", pmcid):
            raise ValueError("Invalid PMCID.")
        url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
        request = Request(url, headers={
            "Accept": "application/xml",
            "User-Agent": "ORACLE-OpenAccess-FullText/2.0",
        })
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = response.read(self.max_bytes + 1)
        except HTTPError as exc:
            raise RuntimeError(f"Europe PMC full-text HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"Europe PMC full-text request failed: {exc}") from exc
        if len(payload) > self.max_bytes:
            raise RuntimeError(f"Full text exceeded the {self.max_bytes}-byte safety limit.")
        return payload

    @staticmethod
    def _extract_body(xml_payload: bytes) -> str:
        try:
            root = ElementTree.fromstring(xml_payload)
        except ElementTree.ParseError as exc:
            raise RuntimeError("Europe PMC returned malformed full-text XML.") from exc
        body = root.find(".//body")
        if body is None:
            raise RuntimeError("Full-text XML did not contain an article body.")
        # References are not part of the article's reported findings and can dominate length.
        chunks = []
        for child in body.iter():
            if child.tag.split("}")[-1] == "ref-list":
                continue
            if child.text and child.text.strip():
                chunks.append(child.text.strip())
            if child.tail and child.tail.strip():
                chunks.append(child.tail.strip())
        return " ".join(" ".join(chunks).split())

    def ingest(self, run: ResearchRun) -> FullTextReport:
        report = FullTextReport()
        for source in list(run.sources):
            if not source.open_access:
                continue
            report.examined_sources += 1
            if not source.pmcid:
                report.skipped_no_pmcid += 1
                continue
            if not self.license_allowed(source.license):
                report.skipped_license += 1
                report.warnings.append(
                    f"Skipped {source.pmcid}: licence is missing or not in the allowed reuse set ({source.license or 'unknown'})."
                )
                continue
            if any(
                item.source_id == source.source_id and item.locator == f"Full text ({source.pmcid})"
                for item in run.evidence
            ):
                continue
            try:
                xml_payload = self._fetch_xml(source.pmcid)
                text = self._extract_body(xml_payload)
            except Exception as exc:
                report.warnings.append(f"{source.pmcid}: {exc}")
                continue
            if not text:
                report.warnings.append(f"{source.pmcid}: article body was empty.")
                continue
            truncated = len(text) > self.max_chars
            stored_text = text[:self.max_chars]
            limitations = (
                f"Retrieved from Europe PMC under reported licence {source.license}. "
                "Full-text extraction preserves article body text only; source methods and study quality "
                "have not been independently assessed."
            )
            if truncated:
                limitations += f" Text truncated at {self.max_chars} characters."
            run.evidence.append(Evidence(
                claim=stored_text,
                source=source.title,
                kind=EvidenceKind.SOURCE,
                method="Europe PMC open-access fullTextXML retrieval",
                limitations=limitations,
                confidence="unassessed",
                source_id=source.source_id,
                locator=f"Full text ({source.pmcid})",
                reliability=source.reliability_score,
                dependence_group=("doi:" + source.doi if source.doi else
                                   "pmid:" + source.pmid if source.pmid else source.source_id),
            ))
            report.full_text_records += 1
        run.findings.append(
            f"Open-access full text: {report.full_text_records} article bodies retrieved; "
            f"{report.skipped_no_pmcid} lacked PMCID; {report.skipped_license} skipped by licence."
        )
        return report
