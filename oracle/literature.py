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
    abstract_enrichment_attempted: int = 0
    abstract_enrichment_recovered: int = 0
    abstract_enrichment_no_match: int = 0
    abstract_enrichment_failed: int = 0
    abstract_enrichment_skipped_no_identifier: int = 0

class LiteratureClient:
    PROVIDERS = ("europepmc", "crossref", "geo", "arxiv", "pubchem", "openalex", "gbif", "world_bank", "noaa_ncei", "clinical_trials", "zenodo", "harvard_dataverse", "sra", "pdb", "pride", "huggingface_datasets", "openml", "nasa_earthdata", "usgs", "figshare", "internet_archive", "loc")
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

    @staticmethod
    def _epmc_values(container: Any, key: str) -> list[Any]:
        """Normalize Europe PMC's occasionally scalar or object-wrapped list fields."""
        if isinstance(container, dict):
            values = container.get(key, [])
        else:
            values = container
        if values is None:
            return []
        return values if isinstance(values, list) else [values]

    @classmethod
    def _epmc_record(cls, x: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(x, dict):
            raise ValueError(f"Europe PMC result must be an object, got {type(x).__name__}")
        doi=str(x.get("doi") or "").lower().strip(); pmid=str(x.get("pmid") or "")
        url="https://doi.org/"+doi if doi else ("https://europepmc.org/article/MED/"+pmid if pmid else "")
        pub_types = cls._epmc_values(x.get("pubTypeList", {}), "pubType")
        licenses = cls._epmc_values(x.get("licenseList", {}), "license")
        publication_types = []
        for value in pub_types:
            label = value.get("type", "") if isinstance(value, dict) else str(value or "")
            if label:
                publication_types.append(label)
        license_values = []
        for value in licenses:
            label = value.get("license", "") if isinstance(value, dict) else str(value or "")
            if label:
                license_values.append(label)
        return {"provider":"Europe PMC","provider_id":str(x.get("id") or ""),
            "doi":doi,"pmid":pmid,"pmcid":str(x.get("pmcid") or ""),"title":cls._clean(x.get("title") or "Untitled record"),
            "authors":x.get("authorString") or "","journal":x.get("journalTitle") or "",
            "year":str(x.get("firstPublicationDate") or x.get("pubYear") or "")[:10],
            "url":url,"abstract":cls._clean(x.get("abstractText") or ""),
            "publication_type":", ".join(publication_types),
            "open_access":str(x.get("isOpenAccess") or "N").upper()=="Y",
            "license":", ".join(license_values),
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
        if not isinstance(data, dict):
            raise LiteratureSearchError("Europe PMC returned a non-object JSON response")
        result_list = data.get("resultList", {})
        if not isinstance(result_list, dict):
            raise LiteratureSearchError("Europe PMC response has an invalid resultList")
        rows = result_list.get("result", [])
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise LiteratureSearchError("Europe PMC response has an invalid result collection")
        records = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            records.append(self._epmc_record(row))
        return records

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


    def _search_openalex(self, query: str, limit: int):
        params = {"search": query, "per-page": limit,
                  "select": "id,doi,title,authorships,publication_year,primary_location,open_access,cited_by_count,type,abstract_inverted_index"}
        if self.mailto:
            params["mailto"] = self.mailto
        data = self._get_json("https://api.openalex.org/works?" + urlencode(params))
        records = []
        for item in data.get("results", []):
            inverted = item.get("abstract_inverted_index") or {}
            words = sorted(((position, word) for word, positions in inverted.items()
                            for position in positions), key=lambda pair: pair[0])
            abstract = " ".join(word for _, word in words)
            authors = "; ".join(
                (entry.get("author") or {}).get("display_name", "")
                for entry in item.get("authorships", [])[:30]
                if (entry.get("author") or {}).get("display_name"))
            location = item.get("primary_location") or {}
            source = location.get("source") or {}
            doi = str(item.get("doi") or "").replace("https://doi.org/", "").lower()
            records.append({
                "provider": "OpenAlex", "provider_id": item.get("id", ""),
                "doi": doi, "pmid": "", "pmcid": "",
                "title": self._clean(item.get("title") or "Untitled work"),
                "authors": authors, "journal": source.get("display_name", ""),
                "year": str(item.get("publication_year") or ""),
                "url": item.get("doi") or item.get("id") or "",
                "abstract": self._clean(abstract),
                "publication_type": item.get("type") or "scholarly_work",
                "open_access": bool((item.get("open_access") or {}).get("is_oa")),
                "license": str((item.get("open_access") or {}).get("oa_status") or ""),
                "citation_count": item.get("cited_by_count"),
            })
        return records

    def _search_gbif(self, query: str, limit: int):
        data = self._get_json("https://api.gbif.org/v1/occurrence/search?" +
                              urlencode({"q": query, "limit": limit}))
        records = []
        for item in data.get("results", []):
            key = item.get("key")
            title = " ".join(filter(None, (
                item.get("scientificName"), item.get("vernacularName"),
                item.get("country"), str(item.get("year") or ""))))
            records.append({
                "provider": "GBIF", "provider_id": str(key or ""),
                "doi": "", "pmid": "", "pmcid": "",
                "title": title or f"GBIF occurrence {key}",
                "authors": item.get("recordedBy", ""), "journal": "GBIF occurrence data",
                "year": str(item.get("year") or ""),
                "url": f"https://www.gbif.org/occurrence/{key}" if key else "https://www.gbif.org/",
                "abstract": self._clean("; ".join(
                    f"{k}: {item.get(k)}" for k in ("scientificName", "country",
                    "stateProvince", "eventDate", "basisOfRecord", "datasetKey")
                    if item.get(k) is not None)),
                "publication_type": "biodiversity occurrence record",
                "open_access": True, "license": item.get("license") or "",
                "citation_count": None, "dataset": True,
            })
        return records

    def _search_world_bank(self, query: str, limit: int):
        data = self._get_json("https://api.worldbank.org/v2/indicator?" +
                              urlencode({"format": "json", "per_page": 100, "source": 2}))
        rows = data[1] if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list) else []
        terms = {term for term in re.findall(r"[a-z0-9]+", query.casefold()) if len(term) > 2}
        ranked = []
        for item in rows:
            haystack = (str(item.get("name") or "") + " " + str(item.get("sourceNote") or "")).casefold()
            score = sum(1 for term in terms if term in haystack)
            if score:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: (-pair[0], str(pair[1].get("id", ""))))
        records = []
        for _, item in ranked[:limit]:
            code = str(item.get("id") or "")
            records.append({
                "provider": "World Bank", "provider_id": code,
                "doi": "", "pmid": "", "pmcid": "",
                "title": self._clean(str(item.get("name") or code)),
                "authors": "World Bank", "journal": "World Development Indicators",
                "year": "", "url": f"https://api.worldbank.org/v2/indicator/{quote(code)}?format=json",
                "abstract": self._clean(str(item.get("sourceNote") or item.get("sourceOrganization") or "")),
                "publication_type": "development indicator metadata",
                "open_access": True, "license": "See World Bank data terms",
                "citation_count": None, "dataset": True, "dataset_accession": code,
            })
        return records

    def _search_noaa_ncei(self, query: str, limit: int):
        url = "https://www.ncei.noaa.gov/access/services/search/v1/datasets?" + urlencode({"text": query, "limit": limit})
        data = self._get_json(url)
        rows = data if isinstance(data, list) else data.get("results", data.get("datasets", []))
        records = []
        for item in rows[:limit] if isinstance(rows, list) else []:
            dataset_id = str(item.get("id") or item.get("dataset") or "")
            title = str(item.get("name") or item.get("title") or dataset_id or "NOAA dataset")
            records.append({
                "provider": "NOAA NCEI", "provider_id": dataset_id,
                "doi": "", "pmid": "", "pmcid": "", "title": self._clean(title),
                "authors": "NOAA National Centers for Environmental Information",
                "journal": "NOAA NCEI", "year": str(item.get("date_start") or "")[:4],
                "url": item.get("url") or "https://www.ncei.noaa.gov/",
                "abstract": self._clean(str(item.get("description") or item.get("summary") or "")),
                "publication_type": "climate and environmental dataset",
                "open_access": True, "license": "Check dataset-specific terms",
                "citation_count": None, "dataset": True, "dataset_accession": dataset_id,
            })
        return records



    def _search_pdb(self, query: str, limit: int):
        search_query = {
            "query": {"type": "terminal", "service": "full_text",
                      "parameters": {"value": query}},
            "return_type": "entry",
            "request_options": {"paginate": {"start": 0, "rows": limit}},
        }
        payload = self._get_json("https://search.rcsb.org/rcsbsearch/v2/query?" + urlencode({
            "json": json.dumps(search_query, separators=(",", ":"))
        }))
        identifiers = [str(x.get("identifier") or "") for x in payload.get("result_set", [])]
        records = []
        for pdb_id in identifiers[:limit]:
            if not re.fullmatch(r"[0-9][A-Za-z0-9]{3}", pdb_id):
                continue
            item = self._get_json("https://data.rcsb.org/rest/v1/core/entry/" + quote(pdb_id))
            title = (item.get("struct") or {}).get("title") or pdb_id
            method = "; ".join(x.get("method", "") for x in item.get("exptl", []) if x.get("method"))
            records.append({
                "provider": "RCSB PDB", "provider_id": pdb_id, "doi": "", "pmid": "", "pmcid": "",
                "title": self._clean(title), "authors": "", "journal": "Worldwide Protein Data Bank",
                "year": str((item.get("rcsb_accession_info") or {}).get("initial_release_date") or "")[:4],
                "url": "https://www.rcsb.org/structure/" + pdb_id,
                "abstract": self._clean("Experimental structure. " + method),
                "publication_type": "protein or nucleic-acid structure", "open_access": True,
                "license": "PDB data use and attribution terms apply", "citation_count": None,
                "dataset": True, "dataset_accession": pdb_id,
            })
        return records

    def _search_pride(self, query: str, limit: int):
        data = self._get_json("https://www.ebi.ac.uk/pride/ws/archive/v2/projects?" + urlencode({
            "keyword": query, "page": 0, "size": limit
        }))
        if isinstance(data, list):
            rows = data
        else:
            rows = data.get("content") or data.get("projects") or (data.get("_embedded") or {}).get("projects") or []
        records = []
        for item in rows[:limit]:
            accession = str(item.get("accession") or item.get("projectAccession") or "")
            title = item.get("title") or item.get("projectTitle") or accession or "PRIDE project"
            records.append({
                "provider": "PRIDE Archive", "provider_id": accession, "doi": str(item.get("doi") or ""),
                "pmid": "", "pmcid": "", "title": self._clean(str(title)),
                "authors": str(item.get("submitter") or ""), "journal": "PRIDE Archive",
                "year": str(item.get("publicationDate") or item.get("submissionDate") or "")[:4],
                "url": "https://www.ebi.ac.uk/pride/archive/projects/" + accession if accession else "https://www.ebi.ac.uk/pride/archive/",
                "abstract": self._clean(str(item.get("projectDescription") or item.get("description") or "")),
                "publication_type": "proteomics dataset", "open_access": True,
                "license": "Project and file-level access/licence conditions apply",
                "citation_count": None, "dataset": True, "dataset_accession": accession,
            })
        return records

    def _search_huggingface_datasets(self, query: str, limit: int):
        rows = self._get_json("https://huggingface.co/api/datasets?" + urlencode({
            "search": query, "limit": limit, "full": "true"
        }))
        records = []
        for item in rows[:limit] if isinstance(rows, list) else []:
            repo_id = str(item.get("id") or item.get("name") or "")
            card = item.get("cardData") or {}
            records.append({
                "provider": "Hugging Face Datasets", "provider_id": repo_id, "doi": "", "pmid": "", "pmcid": "",
                "title": self._clean(repo_id), "authors": str(item.get("author") or ""),
                "journal": "Hugging Face Hub", "year": "",
                "url": "https://huggingface.co/datasets/" + repo_id if repo_id else "https://huggingface.co/datasets",
                "abstract": self._clean(str(card.get("description") or card.get("task_categories") or "")),
                "publication_type": "machine-learning dataset", "open_access": not bool(item.get("gated")),
                "license": str(card.get("license") or "Check dataset card and access conditions"),
                "citation_count": None, "dataset": True, "dataset_accession": repo_id,
                "downloads": item.get("downloads"), "last_modified": item.get("lastModified"),
            })
        return records

    def _search_openml(self, query: str, limit: int):
        url = "https://www.openml.org/api/v1/json/data/list/data_name/" + quote(query, safe="") + "/limit/" + str(limit)
        data = self._get_json(url)
        container = data.get("data") or {}
        rows = container.get("dataset") or []
        if isinstance(rows, dict):
            rows = [rows]
        records = []
        for item in rows[:limit]:
            dataset_id = str(item.get("did") or item.get("id") or "")
            name = item.get("name") or ("OpenML dataset " + dataset_id)
            records.append({
                "provider": "OpenML", "provider_id": dataset_id, "doi": "", "pmid": "", "pmcid": "",
                "title": self._clean(str(name)), "authors": str(item.get("creator") or ""),
                "journal": "OpenML", "year": str(item.get("upload_date") or "")[:4],
                "url": "https://www.openml.org/d/" + dataset_id if dataset_id else "https://www.openml.org/",
                "abstract": self._clean(str(item.get("description") or "")),
                "publication_type": "machine-learning dataset", "open_access": True,
                "license": str(item.get("licence") or item.get("license") or "Check dataset-level licence"),
                "citation_count": None, "dataset": True, "dataset_accession": dataset_id,
            })
        return records


    def _search_nasa_earthdata(self, query: str, limit: int):
        data = self._get_json("https://cmr.earthdata.nasa.gov/search/collections.json?" + urlencode({
            "keyword": query, "page_size": limit
        }))
        rows = (data.get("feed") or {}).get("entry") or []
        records = []
        for item in rows[:limit]:
            concept = str(item.get("id") or "")
            title = item.get("title") or concept or "NASA Earthdata collection"
            links = item.get("links") or []
            url = next((x.get("href") for x in links if x.get("rel", "").endswith("/metadata")), "")
            records.append({
                "provider": "NASA Earthdata", "provider_id": concept, "doi": "", "pmid": "", "pmcid": "",
                "title": self._clean(str(title)), "authors": str(item.get("机构") or "NASA"),
                "journal": "NASA Earthdata CMR", "year": str(item.get("updated") or "")[:4],
                "url": url or ("https://search.earthdata.nasa.gov/search?q=" + quote(query)),
                "abstract": self._clean(str(item.get("summary") or "")),
                "publication_type": "Earth observation data collection", "open_access": True,
                "license": "Collection and granule access requirements vary; Earthdata Login may be required",
                "citation_count": None, "dataset": True, "dataset_accession": concept,
            })
        return records

    def _search_usgs(self, query: str, limit: int):
        data = self._get_json("https://www.sciencebase.gov/catalog/items?" + urlencode({
            "q": query, "format": "json", "max": limit
        }))
        rows = data.get("items") or []
        records = []
        for item in rows[:limit]:
            identifier = str(item.get("id") or "")
            title = item.get("title") or identifier or "USGS ScienceBase item"
            records.append({
                "provider": "USGS ScienceBase", "provider_id": identifier, "doi": "", "pmid": "", "pmcid": "",
                "title": self._clean(str(title)), "authors": str(item.get("provenance") or {}).strip(),
                "journal": "USGS ScienceBase", "year": str(item.get("dateCreated") or "")[:4],
                "url": item.get("link") or ("https://www.sciencebase.gov/catalog/item/" + identifier),
                "abstract": self._clean(str(item.get("summary") or "")),
                "publication_type": "earth science data record", "open_access": True,
                "license": "Item-specific access and reuse terms apply", "citation_count": None,
                "dataset": True, "dataset_accession": identifier,
            })
        return records

    def _search_figshare(self, query: str, limit: int):
        data = self._get_json("https://api.figshare.com/v2/articles?" + urlencode({
            "search": query, "limit": limit
        }))
        rows = data if isinstance(data, list) else data.get("items", [])
        records = []
        for item in rows[:limit]:
            identifier = str(item.get("id") or "")
            records.append({
                "provider": "Figshare", "provider_id": identifier, "doi": str(item.get("doi") or ""),
                "pmid": "", "pmcid": "", "title": self._clean(str(item.get("title") or identifier)),
                "authors": "; ".join(str(x.get("full_name") or "") for x in item.get("authors", [])[:20]),
                "journal": "Figshare", "year": str(item.get("published_date") or item.get("created_date") or "")[:4],
                "url": item.get("url_public_html") or item.get("url") or "",
                "abstract": self._clean(str(item.get("description") or "")),
                "publication_type": str(item.get("defined_type_name") or "research output"),
                "open_access": True, "license": str(item.get("license") or "Check item-level licence"),
                "citation_count": None, "dataset": True, "dataset_accession": identifier,
                "download_url": item.get("download_url") or "",
            })
        return records

    def _search_internet_archive(self, query: str, limit: int):
        data = self._get_json("https://archive.org/advancedsearch.php?" + urlencode({
            "q": query, "fl[]": ["identifier", "title", "description", "creator", "date"],
            "rows": limit, "output": "json"
        }, doseq=True))
        rows = (data.get("response") or {}).get("docs") or []
        records = []
        for item in rows[:limit]:
            identifier = str(item.get("identifier") or "")
            records.append({
                "provider": "Internet Archive", "provider_id": identifier, "doi": "", "pmid": "", "pmcid": "",
                "title": self._clean(str(item.get("title") or identifier)),
                "authors": str(item.get("creator") or ""), "journal": "Internet Archive",
                "year": str(item.get("date") or "")[:4],
                "url": "https://archive.org/details/" + identifier if identifier else "https://archive.org/",
                "abstract": self._clean(str(item.get("description") or "")),
                "publication_type": "digitized primary source or archived item",
                "open_access": True, "license": "Item-specific copyright, lending and reuse restrictions apply",
                "citation_count": None, "dataset": False, "dataset_accession": identifier,
            })
        return records

    def _search_loc(self, query: str, limit: int):
        data = self._get_json("https://www.loc.gov/search/?" + urlencode({
            "q": query, "fo": "json", "c": limit
        }))
        rows = data.get("results") or []
        records = []
        for item in rows[:limit]:
            identifier = str(item.get("id") or item.get("url") or "")
            title = item.get("title") or identifier or "Library of Congress item"
            records.append({
                "provider": "Library of Congress", "provider_id": identifier, "doi": "", "pmid": "", "pmcid": "",
                "title": self._clean(str(title)), "authors": str(item.get("contributor") or ""),
                "journal": "Library of Congress", "year": str(item.get("date") or "")[:4],
                "url": item.get("url") or identifier, "abstract": self._clean(str(item.get("description") or "")),
                "publication_type": "digital collection or primary source", "open_access": True,
                "license": "Item-level rights statements apply", "citation_count": None,
                "dataset": False, "dataset_accession": identifier,
            })
        return records

    def _search_clinical_trials(self, query: str, limit: int):
        data = self._get_json("https://clinicaltrials.gov/api/v2/studies?" + urlencode({
            "query.term": query, "pageSize": limit, "format": "json",
            "fields": "NCTId,BriefTitle,OfficialTitle,BriefSummary,StudyType,OverallStatus,StartDate,CompletionDate,LeadSponsorName"
        }))
        records = []
        for item in data.get("studies", []):
            protocol = item.get("protocolSection") or {}
            ident = protocol.get("identificationModule") or {}
            design = protocol.get("designModule") or {}
            status = protocol.get("statusModule") or {}
            desc = protocol.get("descriptionModule") or {}
            sponsor = protocol.get("sponsorCollaboratorsModule") or {}
            nct = (ident.get("nctId") or "").strip()
            title = ident.get("briefTitle") or ident.get("officialTitle") or nct
            summary = desc.get("briefSummary") or ""
            records.append({
                "provider": "ClinicalTrials.gov", "provider_id": nct,
                "doi": "", "pmid": "", "pmcid": "", "title": self._clean(title),
                "authors": (sponsor.get("leadSponsor") or {}).get("name", ""),
                "journal": "ClinicalTrials.gov", "year": str((status.get("studyFirstPostDateStruct") or {}).get("date") or "")[:4],
                "url": "https://clinicaltrials.gov/study/" + nct if nct else "https://clinicaltrials.gov/",
                "abstract": self._clean(summary), "publication_type": design.get("studyType") or "clinical study",
                "open_access": True, "license": "Study registry record; linked documents have separate rights",
                "citation_count": None, "dataset": True, "dataset_accession": nct,
                "study_status": (status.get("overallStatus") or ""),
            })
        return records

    def _search_zenodo(self, query: str, limit: int):
        data = self._get_json("https://zenodo.org/api/records?" + urlencode({
            "q": query, "size": limit, "sort": "mostrecent"
        }))
        records = []
        for item in data.get("hits", {}).get("hits", []):
            metadata = item.get("metadata") or {}
            doi = str(metadata.get("doi") or item.get("doi") or "").lower()
            identifier = str(item.get("id") or "")
            creators = metadata.get("creators") or []
            records.append({
                "provider": "Zenodo", "provider_id": identifier, "doi": doi,
                "pmid": "", "pmcid": "",
                "title": self._clean(metadata.get("title") or f"Zenodo record {identifier}"),
                "authors": "; ".join(str(x.get("name") or "") for x in creators[:30]),
                "journal": "Zenodo repository", "year": str((metadata.get("publication_date") or "")[:4]),
                "url": item.get("links", {}).get("self_html") or item.get("links", {}).get("html") or "",
                "abstract": self._clean(metadata.get("description") or ""),
                "publication_type": metadata.get("resource_type", {}).get("type") or "research output",
                "open_access": True, "license": (metadata.get("license") or {}).get("id", ""),
                "citation_count": None, "dataset": True, "dataset_accession": identifier,
                "files": item.get("files") or [],
            })
        return records

    def _search_dataverse(self, query: str, limit: int):
        data = self._get_json("https://dataverse.harvard.edu/api/search?" + urlencode({
            "q": query, "type": "dataset", "per_page": limit, "start": 0
        }))
        response = data.get("data") or {}
        records = []
        for item in response.get("items", []):
            pid = str(item.get("global_id") or item.get("entity_id") or "")
            name = item.get("name") or item.get("title") or pid
            description = item.get("description") or ""
            records.append({
                "provider": "Harvard Dataverse", "provider_id": pid,
                "doi": pid.replace("doi:", "") if pid.startswith("doi:") else "",
                "pmid": "", "pmcid": "", "title": self._clean(name),
                "authors": "", "journal": item.get("type", "Dataverse dataset"),
                "year": str(item.get("published_at") or "")[:4],
                "url": item.get("url") or ("https://dataverse.harvard.edu/dataset.xhtml?persistentId=" + quote(pid, safe="") if pid else ""),
                "abstract": self._clean(description), "publication_type": "research dataset",
                "open_access": True, "license": "Check dataset-level licence and access conditions",
                "citation_count": None, "dataset": True, "dataset_accession": pid,
            })
        return records

    def _search_sra(self, query: str, limit: int):
        base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        search = self._get_json(base + "esearch.fcgi?" + urlencode({
            "db": "sra", "term": query, "retmax": limit, "retmode": "json"
        }))
        ids = (search.get("esearchresult") or {}).get("idlist") or []
        if not ids:
            return []
        summary = self._get_json(base + "esummary.fcgi?" + urlencode({
            "db": "sra", "id": ",".join(ids), "retmode": "json"
        }))
        result = summary.get("result") or {}
        records = []
        for uid in ids:
            item = result.get(str(uid)) or {}
            exp = item.get("expXml") or item.get("expxml") or ""
            title = item.get("title") or item.get("caption") or f"SRA record {uid}"
            accession_match = re.search(r"(SR[APRXZ]\d+)", str(exp) + " " + str(item.get("accession") or ""))
            accession = accession_match.group(1) if accession_match else str(item.get("accession") or uid)
            records.append({
                "provider": "NCBI SRA", "provider_id": str(uid),
                "doi": "", "pmid": "", "pmcid": "", "title": self._clean(str(title)),
                "authors": "", "journal": "NCBI Sequence Read Archive",
                "year": str(item.get("published") or "")[:4],
                "url": "https://www.ncbi.nlm.nih.gov/sra/" + accession,
                "abstract": self._clean(str(item.get("summary") or item.get("description") or title)),
                "publication_type": "sequencing dataset", "open_access": True,
                "license": "Study-level access and reuse terms apply", "citation_count": None,
                "dataset": True, "dataset_accession": accession,
            })
        return records

    def _enrich_missing_abstracts(self, records: list[dict[str, Any]]) -> dict[str, int]:
        """Recover missing abstracts by exact identifiers and report every outcome."""
        stats = {"attempted": 0, "recovered": 0, "no_match": 0, "failed": 0, "skipped_no_identifier": 0}
        remaining = self.max_abstract_enrichments
        for record in records:
            if record.get("abstract"):
                continue
            if not (record.get("pmid") or record.get("doi")):
                stats["skipped_no_identifier"] += 1
                continue
            if remaining <= 0:
                continue
            identifier = ("EXT_ID:" + str(record["pmid"]) if record.get("pmid") else "DOI:" + str(record["doi"]))
            url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urlencode({
                "query": identifier, "format": "json", "resultType": "core", "pageSize": 1,
            })
            remaining -= 1
            stats["attempted"] += 1
            try:
                data = self._get_json(url)
                if not isinstance(data, dict):
                    stats["failed"] += 1
                    continue
                result_list = data.get("resultList", {})
                if not isinstance(result_list, dict):
                    stats["failed"] += 1
                    continue
                hits = result_list.get("result", [])
                if isinstance(hits, dict):
                    hits = [hits]
                if not isinstance(hits, list):
                    stats["failed"] += 1
                    continue
                hit = next((item for item in hits if isinstance(item, dict)), None)
                if hit is None:
                    stats["no_match"] += 1
                    continue
                match = self._epmc_record(hit)
                same_pmid = bool(record.get("pmid") and match.get("pmid") == str(record["pmid"]))
                same_doi = bool(record.get("doi") and match.get("doi", "").casefold() == str(record["doi"]).casefold())
                if not (same_pmid or same_doi):
                    stats["no_match"] += 1
                    continue
                recovered_abstract = bool(match.get("abstract"))
                for key in ("abstract", "pmcid", "license", "open_access", "pmid", "doi"):
                    if match.get(key) not in (None, "") and (key in {"abstract", "pmcid", "license"} or not record.get(key)):
                        record[key] = match[key]
                if recovered_abstract:
                    stats["recovered"] += 1
                else:
                    stats["no_match"] += 1
            except Exception:
                # Keep the retrieval run alive, but never hide failed enrichment attempts.
                stats["failed"] += 1
        return stats

    @staticmethod
    def _topic_profile(query: str) -> str:
        """Recognize longevity and age-comparison wording, including plain-language questions."""
        text = re.sub(r"[^a-z0-9]+", " ", query.casefold()).strip()
        terms = set(text.split())
        explicit_aging = any(term in text for term in (
            "longevity", "lifespan", "life span", "healthspan", "centenarian",
            "aging", "ageing", "senescence", "geroscience", "age related",
            "age associated", "age dependent", "old age", "older adult",
            "older adults", "elderly",
        ))
        young_old_comparison = (
            {"young", "old"}.issubset(terms)
            or {"younger", "older"}.issubset(terms)
            or ({"young", "older"}.issubset(terms))
            or ({"younger", "old"}.issubset(terms))
        )
        age_expression = (
            "gene expression" in text
            and bool(terms & {"age", "aged", "adult", "adults", "young", "older", "old"})
        )
        if explicit_aging or young_old_comparison or age_expression:
            return "human_longevity"
        return ""

    @classmethod
    def _relevance_score(cls, query: str, record: dict[str, Any]) -> int:
        """Score topical evidence, giving title matches more weight than abstract matches."""
        stop = {"the", "and", "for", "with", "from", "that", "this", "into",
                "can", "does", "how", "what", "are", "was", "were", "in", "of",
                "to", "a", "an", "is", "on", "by", "their", "human", "previously",
                "unknown", "identify", "identified", "involved"}
        terms = {token for token in re.findall(r"[a-z0-9]+", query.casefold())
                 if len(token) >= 3 and token not in stop}
        title = set(re.findall(r"[a-z0-9]+", str(record.get("title", "")).casefold()))
        abstract = set(re.findall(r"[a-z0-9]+", str(record.get("abstract", "")).casefold()))
        score = 5 * len(terms & title) + len(terms & abstract)
        if cls._topic_profile(query) == "human_longevity":
            anchors = {"longevity", "lifespan", "healthspan", "centenarian", "centenarians",
                       "aging", "ageing", "senescence", "geroscience", "geroprotector",
                       "geroprotective"}
            mechanisms = {"mechanism", "mechanisms", "genetic", "genetics", "genomic",
                          "molecular", "cellular", "pathway", "pathways", "mitochondrial",
                          "telomere", "telomeres", "proteostasis", "epigenetic", "epigenetics",
                          "autophagy", "inflammation", "metabolism", "immune", "immunity",
                          "repair", "stem", "senescent"}
            score += 12 * len(anchors & title) + 4 * len(anchors & abstract)
            score += 2 * len(mechanisms & title) + len(mechanisms & abstract)
        return score

    @classmethod
    def _passes_topic_gate(cls, query: str, record: dict[str, Any]) -> bool:
        """Reject obvious off-topic hits for longevity missions; retain sparse metadata hits only
        when their title itself clearly identifies longevity/aging.
        """
        if cls._topic_profile(query) != "human_longevity":
            return True
        # GEO datasets are selected by a dedicated, human-organism-constrained
        # NCBI query. Their accession/title may not repeat the search term, so do
        # not discard them using the publication-title relevance gate.
        if record.get("dataset") and str(record.get("dataset_accession", "")).upper().startswith("GSE"):
            return True
        title = str(record.get("title", "")).casefold()
        abstract = str(record.get("abstract", "")).casefold()
        # Search APIs sometimes return figure/table captions as if they were papers.
        if re.match(r"^\s*(figure|fig\.?|table|supplement(?:ary|al)?)\s*(?:\d|[:.\-])", title):
            return False
        anchors = ("longevity", "lifespan", "life span", "healthspan", "centenarian",
                   "aging", "ageing", "senescence", "geroscience", "geroprotector",
                   "age-related", "age related", "age-associated", "age associated",
                   "age-dependent", "age dependent", "older adult", "older adults",
                   "old age", "elderly")
        return any(term in title or term in abstract for term in anchors)

    @classmethod
    def geo_dataset_queries(cls, query: str) -> list[str]:
        """Return bounded, human-specific GEO searches for a longevity mission."""
        if cls._topic_profile(query) == "human_longevity":
            return [
                '("longevity"[All Fields] OR "life span"[All Fields] OR "lifespan"[All Fields] OR "healthspan"[All Fields] OR "centenarian"[All Fields]) AND "Homo sapiens"[Organism]',
                '("aging"[All Fields] OR "ageing"[All Fields] OR "senescence"[All Fields]) AND "Homo sapiens"[Organism]',
                '("aging"[All Fields] OR "ageing"[All Fields]) AND ("mitochondria"[All Fields] OR "autophagy"[All Fields] OR "DNA repair"[All Fields] OR "proteostasis"[All Fields] OR "epigenetic"[All Fields]) AND "Homo sapiens"[Organism]',
            ]
        return [f'({query.strip()}) AND "Homo sapiens"[Organism]']

    def search_geo_datasets(self, query: str, limit: int = 20) -> LiteratureSearchReport:
        """Search NCBI GEO independently of the paper search and deduplicate GSE accessions."""
        if not query.strip():
            raise ValueError("GEO dataset search query cannot be empty.")
        if not 1 <= limit <= 50:
            raise ValueError("GEO dataset limit must be between 1 and 50.")
        queries = self.geo_dataset_queries(query)
        report = LiteratureSearchReport(
            query="; ".join(queries), providers=["geo"]
        )
        by_accession: dict[str, dict[str, Any]] = {}
        per_query_limit = min(20, limit)
        for geo_query in queries:
            try:
                for item in self._search_geo(geo_query, per_query_limit):
                    accession = str(item.get("dataset_accession") or "").upper()
                    if not re.fullmatch(r"GSE\d+", accession):
                        report.warnings.append(
                            f"Skipped GEO result without a valid GSE accession: {item.get('title', 'untitled')}"
                        )
                        continue
                    by_accession.setdefault(accession, item)
            except Exception as exc:
                report.warnings.append(f"NCBI GEO query failed ({geo_query[:90]}): {exc}")
        report.records = list(by_accession.values())[:limit]
        report.retrieved = len(report.records)
        if not report.records and not report.warnings:
            report.warnings.append("NCBI GEO returned no human GEO Series for the targeted searches.")
        return report

    def search(self, query: str, limit: int=10, providers=("europepmc","crossref")) -> LiteratureSearchReport:
        query=query.strip()
        if not query: raise ValueError("Literature query cannot be empty.")
        if not 1 <= limit <= 50: raise ValueError("limit must be between 1 and 50.")
        selected=tuple(dict.fromkeys(providers))
        if not selected or any(p not in self.PROVIDERS for p in selected):
            raise ValueError("Unsupported literature/data provider selected.")
        report=LiteratureSearchReport(query, list(selected))
        jobs={}
        with ThreadPoolExecutor(max_workers=len(selected)) as pool:
            for provider in selected:
                fn={"europepmc":self._search_europepmc,"crossref":self._search_crossref,
                    "geo":self._search_geo,"arxiv":self._search_arxiv,
                    "pubchem":self._search_pubchem,"openalex":self._search_openalex,
                    "gbif":self._search_gbif,"world_bank":self._search_world_bank,"noaa_ncei":self._search_noaa_ncei,
                    "clinical_trials":self._search_clinical_trials,"zenodo":self._search_zenodo,
                    "harvard_dataverse":self._search_dataverse,"sra":self._search_sra,
                    "pdb":self._search_pdb,"pride":self._search_pride,
                    "huggingface_datasets":self._search_huggingface_datasets,"openml":self._search_openml,\n                    "nasa_earthdata":self._search_nasa_earthdata,"usgs":self._search_usgs,\n                    "figshare":self._search_figshare,"internet_archive":self._search_internet_archive,"loc":self._search_loc}[provider]
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
        enrichment = self._enrich_missing_abstracts(records)
        report.abstract_enrichment_attempted = enrichment["attempted"]
        report.abstract_enrichment_recovered = enrichment["recovered"]
        report.abstract_enrichment_no_match = enrichment["no_match"]
        report.abstract_enrichment_failed = enrichment["failed"]
        report.abstract_enrichment_skipped_no_identifier = enrichment["skipped_no_identifier"]
        if enrichment["attempted"] or enrichment["skipped_no_identifier"]:
            report.warnings.append(
                "Abstract recovery: "
                f'{enrichment["recovered"]}/{enrichment["attempted"]} recovered; '
                f'{enrichment["no_match"]} exact lookups had no abstract match; '
                f'{enrichment["failed"]} lookup failures; '
                f'{enrichment["skipped_no_identifier"]} missing-abstract records lacked PMID/DOI.'
            )
        # Provider completion order is nondeterministic; rank by topical overlap.
        # Longevity missions use a conservative topical gate so generic "unknown"
        # results (viruses, yeast replication, ancestry, etc.) do not become evidence.
        if self._topic_profile(query) == "human_longevity":
            before = len(records)
            records = [item for item in records if self._passes_topic_gate(query, item)]
            rejected = before - len(records)
            if rejected:
                report.warnings.append(
                    f"Relevance filter excluded {rejected} records without an explicit longevity/aging signal in title or abstract."
                )
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
            is_dataset = bool(item.get("dataset"))
            target_locator = ("GEO dataset summary" if item.get("provider") == "NCBI GEO" else
                              "Dataset record" if is_dataset else
                              "Compound properties" if item.get("provider") == "PubChem" else "Abstract")
            evidence=next((e for e in run.evidence if e.source_id==source.source_id and e.locator==target_locator),None)
            if evidence is None:
                evidence=Evidence(claim=abstract[:12000],source=title,kind=(EvidenceKind.DATASET if is_dataset else EvidenceKind.SOURCE),
                    method=("GEO dataset summary retrieved from NCBI E-utilities" if item.get("provider") == "NCBI GEO" else
                            "Dataset metadata retrieved from "+item.get("provider","data provider") if is_dataset else
                            "Structured compound properties retrieved from PubChem PUG REST" if item.get("provider") == "PubChem" else
                            "Abstract retrieved from "+item.get("provider","scholarly metadata API")),
                    limitations=("Dataset/indicator/occurrence metadata only; inspect the linked data and its study design before scientific interpretation." if is_dataset else
                                 "Structured chemical metadata, not a peer-reviewed mechanistic claim." if item.get("provider") == "PubChem" else
                                 "Abstract only; full text and methods may not have been accessed."),
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
