"""Live scholarly search via public Europe PMC and Crossref APIs."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
import json, re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .knowledge import KnowledgeBase
from .models import Evidence, EvidenceKind, EvidenceStance, ResearchRun, SourceRecord

class LiteratureSearchError(RuntimeError):
    pass

@dataclass
class LiteratureSearchReport:
    query: str
    providers: list[str]
    retrieved: int = 0
    ingested_sources: int = 0
    evidence_records: int = 0
    candidate_statements: int = 0
    warnings: list[str] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)

class LiteratureClient:
    PROVIDERS = ("europepmc", "crossref", "geo")
    def __init__(self, timeout: float = 20.0, mailto: str = ""):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.timeout, self.mailto = timeout, mailto.strip()

    def _get_json(self, url: str) -> dict[str, Any]:
        req = Request(url, headers={"Accept":"application/json",
            "User-Agent":"ORACLE-Scientific-Literature/2.0 (mailto: "+(self.mailto or "not-provided")+")"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read(8_000_000).decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise LiteratureSearchError(f"Request failed for {url.split('?')[0]}: {exc}") from exc

    @staticmethod
    def _clean(value: str) -> str:
        value = re.sub(r"(?i)<\s*\/?\s*(jats:)?(p|italic|bold|sup|sub|i|b|em|strong)[^>]*>", " ", value or "")
        return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()

    @staticmethod
    def _date(value: Any) -> str:
        if isinstance(value, dict):
            parts = value.get("date-parts", [[]])
            value = parts[0] if parts else []
        if isinstance(value, list):
            return "-".join(str(v).zfill(2) if i else str(v) for i,v in enumerate(value))
        return str(value or "")

    @classmethod
    def _epmc_record(cls, x: dict[str, Any]) -> dict[str, Any]:
        doi=(x.get("doi") or "").lower().strip(); pmid=str(x.get("pmid") or "")
        url="https://doi.org/"+doi if doi else ("https://europepmc.org/article/MED/"+pmid if pmid else "")
        return {"provider":"Europe PMC","provider_id":str(x.get("id") or ""),
            "doi":doi,"pmid":pmid,"title":cls._clean(x.get("title") or "Untitled record"),
            "authors":x.get("authorString") or "","journal":x.get("journalTitle") or "",
            "year":str(x.get("firstPublicationDate") or x.get("pubYear") or "")[:10],
            "url":url,"abstract":cls._clean(x.get("abstractText") or ""),
            "publication_type":", ".join(p.get("type","") for p in x.get("pubTypeList",{}).get("pubType",[]) if p.get("type")),
            "open_access":str(x.get("isOpenAccess") or "N").upper()=="Y",
            "license":", ".join(p.get("license","") for p in x.get("licenseList",{}).get("license",[]) if p.get("license")),
            "citation_count":x.get("citedByCount")}

    @classmethod
    def _crossref_record(cls, x: dict[str, Any]) -> dict[str, Any]:
        doi=(x.get("DOI") or "").lower().strip()
        authors="; ".join(" ".join(filter(None,(a.get("given"),a.get("family")))) for a in x.get("author",[])[:30])
        return {"provider":"Crossref","provider_id":doi,"doi":doi,"pmid":"",
            "title":cls._clean((x.get("title") or ["Untitled record"])[0]),"authors":authors,
            "journal":(x.get("container-title") or [""])[0],
            "year":cls._date(x.get("published") or x.get("created")),
            "url":x.get("URL") or ("https://doi.org/"+doi if doi else ""),
            "abstract":cls._clean(x.get("abstract") or ""),"publication_type":x.get("type") or "",
            "open_access":False,"license":", ".join(p.get("URL","") for p in x.get("license",[])),
            "citation_count":x.get("is-referenced-by-count")}

    def _search_europepmc(self, query: str, limit: int):
        url="https://www.ebi.ac.uk/europepmc/webservices/rest/search?"+urlencode({
            "query":query,"format":"json","resultType":"core","pageSize":limit})
        data=self._get_json(url)
        return [self._epmc_record(x) for x in data.get("resultList",{}).get("result",[])]

    def _search_crossref(self, query: str, limit: int):
        params={"query.bibliographic":query,"rows":limit,
            "select":"DOI,title,author,published,created,container-title,URL,abstract,type,link,license,is-referenced-by-count"}
        if self.mailto: params["mailto"]=self.mailto
        data=self._get_json("https://api.crossref.org/works?"+urlencode(params))
        return [self._crossref_record(x) for x in data.get("message",{}).get("items",[])]

    def search(self, query: str, limit: int=10, providers=("europepmc","crossref")) -> LiteratureSearchReport:
        query=query.strip()
        if not query: raise ValueError("Literature query cannot be empty.")
        if not 1 <= limit <= 50: raise ValueError("limit must be between 1 and 50.")
        selected=tuple(dict.fromkeys(providers))
        if not selected or any(p not in self.PROVIDERS for p in selected):
            raise ValueError("providers must be europepmc, crossref, and/or geo.")
        report=LiteratureSearchReport(query, list(selected))
        jobs={}
        with ThreadPoolExecutor(max_workers=len(selected)) as pool:
            for provider in selected:
                fn={"europepmc":self._search_europepmc,"crossref":self._search_crossref,"geo":self._search_geo}[provider]
                jobs[pool.submit(fn,query,limit)]=provider
            for future in as_completed(jobs):
                try: report.records.extend(future.result())
                except Exception as exc: report.warnings.append(f"{jobs[future]} failed: {exc}")
        if not report.records and report.warnings:
            raise LiteratureSearchError("All literature providers failed. "+" | ".join(report.warnings))
        merged={}
        for item in report.records:
            key=("doi:"+item["doi"] if item["doi"] else "pmid:"+item["pmid"] if item["pmid"]
                 else "title:"+re.sub(r"\W+","",item["title"].lower()))
            if key not in merged: merged[key]=item
            else:
                current=merged[key]
                for k,v in item.items():
                    if v not in (None,"",[],False) and current.get(k) in (None,"",[],False): current[k]=v
        report.records=list(merged.values())[:limit]; report.retrieved=len(report.records)
        return report

    @staticmethod
    def candidate_sentences(abstract: str, maximum: int=8) -> list[str]:
        sentences=re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])",abstract)
        output=[]; seen=set()
        for sentence in sentences:
            sentence=sentence.strip(); key=re.sub(r"\W+","",sentence.lower())
            if len(sentence)<45 or len(sentence.split())<7 or key in seen: continue
            seen.add(key); output.append(sentence[:1200])
            if len(output)>=maximum: break
        return output

    def ingest(self, run: ResearchRun, report: LiteratureSearchReport) -> LiteratureSearchReport:
        kb=KnowledgeBase(); now=datetime.now(timezone.utc).isoformat()
        for item in report.records:
            title=item.get("title") or "Untitled record"; doi=item.get("doi",""); pmid=item.get("pmid","")
            identity=doi or ("pmid:"+pmid if pmid else item.get("url") or title)
            sid="lit_"+re.sub(r"[^a-zA-Z0-9]+","_",identity).strip("_")[:48].lower()
            source=SourceRecord(title=title,url=item.get("url",""),publisher=item.get("journal",""),
                source_type=item.get("publication_type") or "scholarly_record",published_at=item.get("year",""),
                accessed_at=now,reliability_score=0.5,
                reliability_rationale="Unassessed metadata; peer review and study quality not independently evaluated.",
                source_id=sid,doi=doi,pmid=pmid,authors=item.get("authors",""),journal=item.get("journal",""),
                abstract=item.get("abstract",""),provider=item.get("provider",""),
                open_access=bool(item.get("open_access")),license=item.get("license",""),
                dataset_accession=item.get("dataset_accession",""),organism=item.get("organism",""),
                sample_count=str(item.get("sample_count") or ""),platform=str(item.get("platform") or ""),
                dataset_summary=item.get("abstract",""))
            source=kb.add_source(run,source); report.ingested_sources+=1
            abstract=item.get("abstract","").strip()
            if not abstract:
                report.warnings.append("No abstract supplied: "+title); continue
            evidence=next((e for e in run.evidence if e.source_id==source.source_id and e.locator=="Abstract"),None)
            if evidence is None:
                evidence=Evidence(claim=abstract[:12000],source=title,kind=(EvidenceKind.DATASET if item.get("dataset") else EvidenceKind.SOURCE),
                    method=("GEO dataset summary retrieved from NCBI E-utilities" if item.get("dataset") else "Abstract retrieved from "+item.get("provider","scholarly metadata API")),
                    limitations="Abstract only; full text and methods may not have been accessed.",
                    confidence="unassessed",source_id=source.source_id,locator=("GEO dataset summary" if item.get("dataset") else "Abstract"),reliability=0.5,
                    dependence_group=("doi:"+doi if doi else "pmid:"+pmid if pmid else ""))
                run.evidence.append(evidence); report.evidence_records+=1
            for sentence in self.candidate_sentences(abstract):
                claim=kb.add_claim(run,sentence,claim_type="literature_statement_candidate")
                if claim.status=="unassessed": claim.status="unreviewed_candidate"
                kb.link_evidence(run,claim.claim_id,evidence.evidence_id,EvidenceStance.CONTEXTUAL,
                    strength=0.0,rationale="Abstract sentence captured for review only; no support/refutation judgement.")
                report.candidate_statements+=1
        run.findings.append(f"Literature retrieval: {report.retrieved} records; {report.ingested_sources} sources; {report.evidence_records} abstracts; {report.candidate_statements} unreviewed sentence candidates.")
        return report
