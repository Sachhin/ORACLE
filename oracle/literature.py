"""Live scholarly search via public Europe PMC and Crossref APIs."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
import json, re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
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
    PROVIDERS = ("europepmc", "crossref", "geo", "arxiv", "pubchem")
    def __init__(self, timeout: float = 20.0, mailto: str = "",
                 max_abstract_enrichments: int = 10):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if not 0 <= max_abstract_enrichments <= 20:
            raise ValueError("max_abstract_enrichments must be between 0 and 20")
        self.timeout, self.mailto = timeout, mailto.strip()
        self.max_abstract_enrichments = max_abstract_enrichments

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
            "doi":doi,"pmid":pmid,"pmcid":str(x.get("pmcid") or ""),"title":cls._clean(x.get("title") or "Untitled record"),
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
        return {"provider":"Crossref","provider_id":doi,"doi":doi,"pmid":"","pmcid":"",
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

    @classmethod
    def _arxiv_record(cls, item: dict[str, Any]) -> dict[str, Any]:
        """Normalize one Atom arXiv entry into ORACLE's literature schema."""
        arxiv_id = str(item.get("id") or "").strip()
        authors = "; ".join(str(name).strip() for name in item.get("authors", []) if str(name).strip())
        categories = item.get("categories", [])
        return {
            "provider": "arXiv", "provider_id": arxiv_id,
            "doi": str(item.get("doi") or "").strip().lower(),
            "pmid": "", "pmcid": "",
            "title": cls._clean(str(item.get("title") or "Untitled preprint")),
            "authors": authors, "journal": str(item.get("journal_ref") or "arXiv preprint"),
            "year": str(item.get("published") or "")[:10],
            "url": arxiv_id, "abstract": cls._clean(str(item.get("summary") or "")),
            "publication_type": "preprint", "open_access": True,
            "license": str(item.get("license") or "See arXiv record for version-specific licence"),
            "citation_count": None, "categories": categories,
        }

    def _search_arxiv(self, query: str, limit: int):
        params = {"search_query": "all:" + query, "start": 0,
                  "max_results": limit, "sortBy": "relevance", "sortOrder": "descending"}
        url = "https://export.arxiv.org/api/query?" + urlencode(params)
        req = Request(url, headers={"Accept": "application/atom+xml",
            "User-Agent": "ORACLE-Scientific-Literature/2.0"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                payload = response.read(8_000_000)
            root = ET.fromstring(payload)
        except (HTTPError, URLError, TimeoutError, ET.ParseError, OSError) as exc:
            raise LiteratureSearchError(f"arXiv request failed: {exc}") from exc
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        records = []
        for entry in root.findall("atom:entry", ns):
            def value(tag: str) -> str:
                node = entry.find("atom:" + tag, ns)
                return (node.text or "").strip() if node is not None else ""
            authors = [(node.findtext("atom:name", default="", namespaces=ns) or "").strip()
                       for node in entry.findall("atom:author", ns)]
            categories = [node.attrib.get("term", "") for node in entry.findall("atom:category", ns)]
            doi = entry.findtext("arxiv:doi", default="", namespaces=ns) or ""
            journal = entry.findtext("arxiv:journal_ref", default="", namespaces=ns) or ""
            records.append(self._arxiv_record({
                "id": value("id"), "title": value("title"), "summary": value("summary"),
                "published": value("published"), "authors": authors, "categories": categories,
                "doi": doi, "journal_ref": journal,
            }))
        return records

    @classmethod
    def _pubchem_record(cls, item: dict[str, Any]) -> dict[str, Any]:
        """Normalize PubChem compound properties; these are not literature claims."""
        cid = str(item.get("CID") or "")
        name = cls._clean(str(item.get("IUPACName") or item.get("Title") or f"PubChem CID {cid}"))
        formula = str(item.get("MolecularFormula") or "")
        weight = str(item.get("MolecularWeight") or "")
        smiles = str(item.get("ConnectivitySMILES") or item.get("CanonicalSMILES") or "")
        details = [
            f"PubChem compound record CID {cid}.",
            f"IUPAC name: {name}." if name else "",
            f"Molecular formula: {formula}." if formula else "",
            f"Molecular weight: {weight} g/mol." if weight else "",
            f"Canonical/connectivity SMILES: {smiles}." if smiles else "",
        ]
        return {
            "provider": "PubChem", "provider_id": cid, "doi": "", "pmid": "", "pmcid": "",
            "title": name or f"PubChem CID {cid}", "authors": "", "journal": "PubChem",
            "year": "", "url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else "",
            "abstract": " ".join(part for part in details if part),
            "publication_type": "chemical compound record", "open_access": True,
            "license": "See PubChem data-use and linked-source terms",
            "citation_count": None, "dataset": False, "compound_cid": cid,
            "molecular_formula": formula, "molecular_weight": weight, "smiles": smiles,
        }

    def _search_pubchem(self, query: str, limit: int):
        encoded = quote(query.strip(), safe="")
        properties = "MolecularFormula,MolecularWeight,IUPACName,CanonicalSMILES"
        url = (f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}"
               f"/property/{properties}/JSON?MaxRecords={limit}")
        data = self._get_json(url)
        rows = data.get("PropertyTable", {}).get("Properties", [])
        return [self._pubchem_record(item) for item in rows]

    def _search_geo(self, query: str, limit: int):
        base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        search = self._get_json(base+"esearch.fcgi?"+urlencode({
            "db":"gds","term":query,"retmax":limit,"retmode":"json"}))
        ids = search.get("esearchresult",{}).get("idlist",[])
        if not ids:
            return []
        summary = self._get_json(base+"esummary.fcgi?"+urlencode({
            "db":"gds","id":",".join(ids),"retmode":"json"}))
        result = summary.get("result",{})
        records = []
        for uid in ids:
            item = result.get(str(uid),{})
            accession = item.get("accession") or ""
            if not accession:
                continue
            records.append({
                "provider":"NCBI GEO","provider_id":str(uid),"doi":"","pmid":"","pmcid":"",
                "title":item.get("title") or accession,"authors":"","journal":"",
                "year":str(item.get("pdat") or ""),
                "url":"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc="+accession,
                "abstract":self._clean(item.get("summary") or ""),
                "publication_type":"gene expression dataset","open_access":False,"license":"",
                "citation_count":None,"dataset":True,"dataset_accession":accession,
                "organism":item.get("taxon") or "","sample_count":item.get("n_samples"),
                "platform":item.get("gpl") or "",
                "dataset_type":item.get("gdsType") or item.get("entryType") or "",
                "pubmed_ids":item.get("pubmedids") or [],
            })
        return records

    def _enrich_missing_abstracts(self, records: list[dict[str, Any]]) -> None:
        """Recover abstracts omitted by one index using exact PMID/DOI lookups."""
        remaining = self.max_abstract_enrichments
        for record in records:
            if remaining <= 0:
                break
            if record.get("abstract") or not (record.get("pmid") or record.get("doi")):
                continue
            identifier = ("EXT_ID:" + str(record["pmid"]) if record.get("pmid")
                          else "DOI:" + str(record["doi"]))
            url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urlencode({
                "query": identifier, "format": "json", "resultType": "core", "pageSize": 1,
            })
            remaining -= 1
            try:
                data = self._get_json(url)
                hits = data.get("resultList", {}).get("result", [])
                if not hits:
                    continue
                match = self._epmc_record(hits[0])
                same_pmid = bool(record.get("pmid") and match.get("pmid") == str(record["pmid"]))
                same_doi = bool(record.get("doi") and match.get("doi", "").casefold()
                                == str(record["doi"]).casefold())
                if not (same_pmid or same_doi):
                    continue
                for key in ("abstract", "pmcid", "license", "open_access", "pmid", "doi"):
                    if match.get(key) not in (None, "") and (
                        key in {"abstract", "pmcid", "license"} or not record.get(key)
                    ):
                        record[key] = match[key]
            except Exception:
                continue

    @staticmethod
    def _relevance_score(query: str, record: dict[str, Any]) -> int:
        """Prefer records whose title/abstract actually discuss the requested topic."""
        stop = {"the", "and", "for", "with", "from", "that", "this", "into",
                "can", "does", "how", "what", "are", "was", "were", "in", "of",
                "to", "a", "an", "is", "on", "by", "their", "human"}
        terms = {token for token in re.findall(r"[a-z0-9]+", query.casefold())
                 if len(token) >= 3 and token not in stop}
        if not terms:
            return 0
        title = set(re.findall(r"[a-z0-9]+", str(record.get("title", "")).casefold()))
        abstract = set(re.findall(r"[a-z0-9]+", str(record.get("abstract", "")).casefold()))
        return 4 * len(terms & title) + len(terms & abstract)

    def search(self, query: str, limit: int=10, providers=("europepmc","crossref")) -> LiteratureSearchReport:
        query=query.strip()
        if not query: raise ValueError("Literature query cannot be empty.")
        if not 1 <= limit <= 50: raise ValueError("limit must be between 1 and 50.")
        selected=tuple(dict.fromkeys(providers))
        if not selected or any(p not in self.PROVIDERS for p in selected):
            raise ValueError("providers must be europepmc, crossref, geo, arxiv, and/or pubchem.")
        report=LiteratureSearchReport(query, list(selected))
        jobs={}
        with ThreadPoolExecutor(max_workers=len(selected)) as pool:
            for provider in selected:
                fn={"europepmc":self._search_europepmc,"crossref":self._search_crossref,"geo":self._search_geo,"arxiv":self._search_arxiv,"pubchem":self._search_pubchem}[provider]
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
        records = list(merged.values())
        self._enrich_missing_abstracts(records)
        # Provider completion order is nondeterministic; rank by topical overlap.
        records.sort(key=lambda item: self._relevance_score(query, item), reverse=True)
        report.records = records[:limit]
        report.retrieved = len(report.records)
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
                source_id=sid,doi=doi,pmid=pmid,pmcid=item.get("pmcid",""),
                authors=item.get("authors",""),journal=item.get("journal",""),
                abstract=item.get("abstract",""),provider=item.get("provider",""),
                open_access=bool(item.get("open_access")),license=item.get("license",""),
                dataset_accession=item.get("dataset_accession",""),organism=item.get("organism",""),
                sample_count=str(item.get("sample_count") or ""),platform=str(item.get("platform") or ""),
                dataset_summary=item.get("abstract",""))
            source=kb.add_source(run,source); report.ingested_sources+=1
            abstract=item.get("abstract","").strip()
            if not abstract:
                report.warnings.append("No abstract supplied: "+title); continue
            target_locator = ("GEO dataset summary" if item.get("dataset") else
                              "Compound properties" if item.get("provider") == "PubChem" else "Abstract")
            evidence=next((e for e in run.evidence if e.source_id==source.source_id and e.locator==target_locator),None)
            if evidence is None:
                evidence=Evidence(claim=abstract[:12000],source=title,kind=(EvidenceKind.DATASET if item.get("dataset") else EvidenceKind.SOURCE),
                    method=("GEO dataset summary retrieved from NCBI E-utilities" if item.get("dataset") else
                            "Structured compound properties retrieved from PubChem PUG REST" if item.get("provider") == "PubChem" else
                            "Abstract retrieved from "+item.get("provider","scholarly metadata API")),
                    limitations=("Structured chemical metadata, not a peer-reviewed mechanistic claim." if item.get("provider") == "PubChem" else "Abstract only; full text and methods may not have been accessed."),
                    confidence="unassessed",source_id=source.source_id,locator=target_locator,reliability=0.5,
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
