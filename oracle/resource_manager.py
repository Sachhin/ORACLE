"""Universal scientific resource registry and safe connector dispatch.

The catalog is metadata, not a claim that every listed API has an implemented
client. Search dispatch is enabled only for providers backed by a tested
ORACLE adapter (currently Europe PMC, Crossref, NCBI GEO, arXiv, and PubChem).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .literature import LiteratureClient, LiteratureSearchReport


@dataclass(frozen=True)
class ScientificResource:
    key: str
    name: str
    domains: tuple[str, ...]
    api_url: str
    access: str
    authentication: str
    license_note: str
    connector: str = ""
    capabilities: tuple[str, ...] = ()


# Keep this registry explicit and auditable. "catalog_only" resources are
# discoverable but are not represented as executable connectors.
_RESOURCES = (
    ScientificResource("europepmc", "Europe PMC", ("biology_medicine", "general_science"),
        "https://www.ebi.ac.uk/europepmc/webservices/rest", "public_api", "none",
        "Record-level reuse terms vary; check full-text licence", "europepmc",
        ("literature_search", "metadata", "open_access_full_text")),
    ScientificResource("crossref", "Crossref", ("all",),
        "https://api.crossref.org", "public_api", "none",
        "Metadata is openly available; underlying works retain their own rights", "crossref",
        ("literature_search", "doi_metadata", "references")),
    ScientificResource("ncbi_geo", "NCBI GEO", ("biology_medicine",),
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils", "public_api", "none",
        "Dataset-specific terms apply; respect NCBI usage policies", "geo",
        ("dataset_search", "expression_metadata")),
    ScientificResource("openalex", "OpenAlex", ("all",),
        "https://api.openalex.org", "public_api", "optional",
        "Open bibliographic metadata; source records may have separate rights", "openalex",
        ("literature_search", "literature_metadata", "citation_metadata", "open_access_locations")),
    ScientificResource("arxiv", "arXiv", ("physics_astronomy", "computer_science_ai",
        "mathematics_statistics", "general_science"),
        "https://export.arxiv.org/api/query", "public_api", "none",
        "Article licences vary by submission", "arxiv", ("preprint_search", "literature_search")),
    ScientificResource("pubchem", "PubChem", ("chemistry_materials", "biology_medicine"),
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug", "public_api", "none",
        "PubChem data are generally public; linked records may carry separate terms", "pubchem",
        ("chemical_metadata", "compound_search")),
    ScientificResource("materials_project", "Materials Project", ("chemistry_materials",),
        "https://api.materialsproject.org", "public_api", "api_key",
        "Check Materials Project terms and attribution", capabilities=("materials_data",)),
    ScientificResource("noaa_ncei", "NOAA NCEI", ("earth_environment",),
        "https://www.ncei.noaa.gov/access/services", "public_api", "varies",
        "Dataset-specific terms and attribution apply", capabilities=("climate_data",)),
    ScientificResource("gbif", "GBIF", ("earth_environment", "biology_medicine"),
        "https://api.gbif.org/v1", "public_api", "none",
        "Occurrence records retain dataset licences; preserve dataset citations",
        "gbif", ("biodiversity_occurrences", "dataset_search")),
    ScientificResource("world_bank", "World Bank Open Data", ("social_behavioral", "economics_business", "general_science"),
        "https://api.worldbank.org/v2", "public_api", "none",
        "Check indicator and dataset-specific terms", "world_bank", ("economic_indicators", "dataset_search")),
    ScientificResource("nasa_technical_reports", "NASA Technical Reports Server", ("engineering", "physics_astronomy"),
        "https://ntrs.nasa.gov/api", "public_api", "none",
        "Report-level rights and distribution statements apply",
        capabilities=("technical_reports", "engineering_research")),
    ScientificResource("nasa_ads", "NASA Astrophysics Data System", ("physics_astronomy",),
        "https://api.adsabs.harvard.edu/v1", "public_api", "api_token",
        "ADS API token required; abstracts and metadata subject to provider terms",
        capabilities=("astronomy_literature", "citation_search")),
    ScientificResource("open_context", "Open Context", ("history_archaeology",),
        "https://opencontext.org", "public_catalog", "none",
        "Dataset-specific open licences apply", capabilities=("archaeology_datasets",)),
    ScientificResource("osf", "Open Science Framework", ("social_behavioral", "general_science"),
        "https://api.osf.io/v2", "public_api", "none",
        "Project and file licences vary", capabilities=("research_projects", "preprints")),
    ScientificResource("openstreetmap", "OpenStreetMap", ("geography_urban", "earth_environment"),
        "https://overpass-api.de/api/interpreter", "public_api", "none",
        "ODbL attribution and share-alike obligations apply", capabilities=("geospatial_data",)),
    ScientificResource("clinical_trials", "ClinicalTrials.gov", ("biology_medicine",),
        "https://clinicaltrials.gov/api/v2", "public_api", "none",
        "Study records are public; linked documents have separate rights", capabilities=("clinical_trials",)),
    ScientificResource("un_data", "UN Data", ("social_behavioral", "general_science"),
        "https://data.un.org", "public_catalog", "none",
        "Dataset-specific terms apply", capabilities=("international_statistics",)),
    ScientificResource("nasa_ads", "NASA Astrophysics Data System", ("physics_astronomy",),
        "https://api.adsabs.harvard.edu/v1", "public_api", "api_token",
        "ADS API token required; abstracts and metadata subject to provider terms",
        capabilities=("astronomy_literature", "citation_search")),
    ScientificResource("open_context", "Open Context", ("history_archaeology",),
        "https://opencontext.org", "public_catalog", "none",
        "Dataset-specific open licences apply", capabilities=("archaeology_datasets",)),
    ScientificResource("osf", "Open Science Framework", ("social_behavioral", "general_science"),
        "https://api.osf.io/v2", "public_api", "none",
        "Project and file licences vary", capabilities=("research_projects", "preprints")),
    ScientificResource("openstreetmap", "OpenStreetMap", ("geography_urban", "earth_environment"),
        "https://overpass-api.de/api/interpreter", "public_api", "none",
        "ODbL attribution and share-alike obligations apply", capabilities=("geospatial_data",)),
    ScientificResource("clinical_trials", "ClinicalTrials.gov", ("biology_medicine",),
        "https://clinicaltrials.gov/api/v2", "public_api", "none",
        "Study records are public; linked documents have separate rights", capabilities=("clinical_trials",)),
    ScientificResource("un_data", "UN Data", ("social_behavioral", "general_science"),
        "https://data.un.org", "public_catalog", "none",
        "Dataset-specific terms apply", capabilities=("international_statistics",)),
)


def resolve_literature_providers(question: str, requested_domain: str = "auto") -> tuple[str, ...]:
    """Choose only currently implemented scholarly adapters for the routed field.

    Crossref is the generic scholarly-metadata fallback. Catalog-only sources
    are deliberately not selected until an executable connector exists.
    """
    from .domain_router import resolve_domain

    profile, _ = resolve_domain(question, requested_domain)
    by_domain = {
        "biology_medicine": ("openalex", "europepmc", "crossref", "geo", "pubchem"),
        "physics_astronomy": ("openalex", "arxiv", "crossref"),
        "computer_science_ai": ("arxiv", "crossref"),
        "mathematics_statistics": ("arxiv", "crossref"),
        "chemistry_materials": ("openalex", "pubchem", "crossref"),
        "general_science": ("openalex", "europepmc", "crossref", "arxiv", "pubchem"),
        "earth_environment": ("openalex", "crossref", "gbif", "noaa_ncei"),
        "social_behavioral": ("openalex", "crossref", "world_bank"),
        "history_archaeology": ("openalex", "crossref"),
        "philosophy_ethics": ("openalex", "crossref"),
        "economics_business": ("openalex", "crossref", "world_bank"),
        "geography_urban": ("openalex", "crossref"),
        "engineering": ("openalex", "crossref", "arxiv"),
        "law_policy": ("openalex", "crossref"),
        "finance": ("openalex", "crossref", "world_bank"),
        "linguistics_literature": ("openalex", "crossref"),
        "education": ("openalex", "crossref"),
        "politics_governance": ("openalex", "crossref", "world_bank"),
        "arts_culture": ("openalex", "crossref"),
        "religion_theology": ("openalex", "crossref"),
    }
    return by_domain.get(profile.key, ("crossref",))


class ResourceManager:
    """Discover resource metadata and dispatch only implemented search adapters."""

    def __init__(self, literature_client: LiteratureClient | None = None):
        self.literature = literature_client or LiteratureClient()

    @staticmethod
    def list_resources(domain: str = "all") -> list[dict[str, Any]]:
        domain = (domain or "all").strip().casefold()
        if domain not in {"all", "auto"}:
            from .domain_router import _ALIASES
            domain = _ALIASES.get(domain, domain)
        if domain not in {"all", "auto"} and not any(
            domain in resource.domains for resource in _RESOURCES
        ):
            raise ValueError(f"Unknown resource domain: {domain}")
        return [
            {**asdict(resource),
             "domains": list(resource.domains),
             "capabilities": list(resource.capabilities),
             "status": "implemented" if resource.connector in {"europepmc", "crossref", "geo", "arxiv", "pubchem", "openalex", "gbif", "world_bank", "noaa_ncei"}
                       else "catalog_only"}
            for resource in _RESOURCES
            if domain in {"all", "auto"} or "all" in resource.domains
            or domain in resource.domains
        ]

    @staticmethod
    def get_resource(key: str) -> dict[str, Any]:
        # CLI/provider adapters use "geo"; the catalog's canonical key is
        # "ncbi_geo". Accept both names while keeping catalog metadata stable.
        aliases = {"geo": "ncbi_geo"}
        canonical_key = aliases.get(key, key)
        for item in ResourceManager.list_resources():
            if item["key"] == canonical_key:
                return item
        raise KeyError(f"Unknown scientific resource: {key}")

    def search(self, query: str, limit: int = 10,
               resources: tuple[str, ...] = ("europepmc", "crossref")) -> LiteratureSearchReport:
        """Search supported providers; fail clearly for catalog-only resources."""
        if not resources:
            raise ValueError("Select at least one resource.")
        providers: list[str] = []
        unsupported: list[str] = []
        for key in dict.fromkeys(resources):
            item = self.get_resource(key)
            if item["connector"] in {"europepmc", "crossref", "geo", "arxiv", "pubchem", "openalex", "gbif", "world_bank", "noaa_ncei"}:
                providers.append(item["connector"])
            else:
                unsupported.append(key)
        if unsupported:
            raise NotImplementedError(
                "No executable connector yet for: " + ", ".join(unsupported)
                + ". These entries are catalog metadata only."
            )
        return self.literature.search(query, limit=limit, providers=tuple(providers))
