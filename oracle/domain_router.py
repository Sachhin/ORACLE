"""Domain routing and specialist research profiles for hybrid ORACLE.

Routing is deterministic and transparent. It selects a research lens and tool
recommendations; it does not claim that a specialist model or domain dataset ran.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re


@dataclass(frozen=True)
class DomainProfile:
    key: str
    label: str
    description: str
    search_terms: tuple[str, ...]
    preferred_sources: tuple[str, ...]
    analysis_methods: tuple[str, ...]
    validation_checks: tuple[str, ...]
    task_templates: tuple[str, ...]


_PROFILES = {
    "biology_medicine": DomainProfile(
        "biology_medicine", "Biology & Medicine",
        "Molecular, cellular, organismal, clinical and population biology.",
        ("gene", "protein", "cell", "organism", "biology", "biological", "mechanism",
         "mechanisms", "medicine", "medical", "disease", "cancer", "longevity",
         "aging", "ageing", "genetic", "clinical", "drug", "brain",
         "neuroscience", "microbiome", "immune", "patient"),
        ("PubMed/Europe PMC", "NCBI GEO/SRA", "PRIDE/ProteomeXchange",
         "ClinicalTrials.gov", "UniProt", "Ensembl"),
        ("study-design and cohort audit", "omics quality control",
         "appropriate count/continuous-data statistics", "effect sizes and multiple-testing correction",
         "independent-cohort replication"),
        ("organism and tissue match", "sample size and biological replicates",
         "batch/confounder assessment", "ethics and biosafety review",
         "independent replication before causal claims"),
        ("Identify organism, tissue, phenotype and assay context",
         "Find primary studies and public biological datasets",
         "Audit cohort design, controls, confounders and measurement quality",
         "Compare candidate mechanisms across independent cohorts"),
    ),
    "physics_astronomy": DomainProfile(
        "physics_astronomy", "Physics & Astronomy",
        "Physical systems, fundamental theory, astrophysics and cosmology.",
        ("physics", "quantum", "particle", "cosmology", "astronomy", "galaxy",
         "black hole", "dark matter", "relativity", "thermodynamics", "optics"),
        ("NASA/ESA archives", "arXiv", "INSPIRE-HEP", "ADS", "NIST"),
        ("dimensional analysis", "analytical derivation", "numerical simulation",
         "uncertainty propagation", "comparison with observational constraints"),
        ("units and dimensional consistency", "boundary conditions",
         "numerical convergence", "independent derivation or measurement",
         "agreement with established constraints"),
        ("Define physical regime, scales, units and assumptions",
         "Locate observational data and theoretical prior work",
         "Derive competing models and quantitative predictions",
         "Test predictions against independent observations or simulations"),
    ),
    "chemistry_materials": DomainProfile(
        "chemistry_materials", "Chemistry & Materials Science",
        "Molecular structure, reactions, materials, catalysis and properties.",
        ("chemistry", "molecule", "reaction", "catalyst", "polymer", "material",
         "battery", "nanomaterial", "crystal", "electrochemistry", "chemical"),
        ("PubChem", "ChEBI", "Materials Project", "Crystallography Open Database",
         "NIST Chemistry WebBook"),
        ("stoichiometric and thermodynamic checks", "structure-property analysis",
         "molecular simulation", "spectral interpretation", "materials benchmarking"),
        ("chemical identity and units", "mass/charge balance",
         "simulation method and parameter provenance", "reproducibility",
         "toxicity and laboratory safety review"),
        ("Define compounds, structures, phases and target properties",
         "Retrieve curated molecular/material records and experimental studies",
         "Compare mechanistic and structure-property explanations",
         "Specify computational or laboratory validation with safety constraints"),
    ),
    "computer_science_ai": DomainProfile(
        "computer_science_ai", "Computer Science & AI",
        "Algorithms, software, machine learning, robotics and computational systems.",
        ("computer", "algorithm", "software", "artificial intelligence", "machine learning",
         "neural network", "robot", "robotics", "agi", "programming", "cyber"),
        ("arXiv", "ACM Digital Library", "IEEE Xplore", "Papers with Code",
         "Open-source benchmark repositories"),
        ("formal specification", "complexity analysis", "ablation studies",
         "benchmark evaluation", "reproducible implementation"),
        ("data leakage and benchmark contamination", "baseline selection",
         "statistical uncertainty across seeds", "compute and version provenance",
         "security and misuse review"),
        ("Formalize the problem, input/output contract and success criteria",
         "Find prior algorithms, implementations and benchmark datasets",
         "Compare against strong baselines with ablations",
         "Verify complexity, reproducibility, robustness and failure modes"),
    ),
    "earth_environment": DomainProfile(
        "earth_environment", "Earth & Environmental Science",
        "Climate, geoscience, oceans, ecology and environmental systems.",
        ("climate", "earth", "environment", "ocean", "ecosystem", "ecology",
         "geology", "weather", "biodiversity", "pollution", "soil", "hydrology"),
        ("NASA Earthdata", "NOAA", "USGS", "Copernicus", "GBIF"),
        ("spatiotemporal analysis", "remote-sensing validation",
         "geospatial uncertainty", "time-series analysis", "sensitivity analysis"),
        ("spatial/temporal resolution", "sensor calibration",
         "missingness and coverage", "confounding and autocorrelation",
         "independent geographic or temporal validation"),
        ("Define spatial and temporal scale and target system",
         "Locate open observational and remote-sensing datasets",
         "Audit sensor, sampling and coverage limitations",
         "Test spatial/temporal generalization and alternative drivers"),
    ),
    "mathematics_statistics": DomainProfile(
        "mathematics_statistics", "Mathematics & Statistics",
        "Pure/applied mathematics, inference, optimization and statistical theory.",
        ("mathematics", "theorem", "proof", "number theory", "topology",
         "statistics", "probability", "optimization", "equation", "conjecture"),
        ("arXiv", "zbMATH", "MathSciNet", "Crossref", "OpenAlex"),
        ("proof decomposition", "symbolic computation", "counterexample search",
         "simulation for conjecture exploration", "sensitivity and identifiability analysis"),
        ("proof obligations and assumptions", "edge cases and counterexamples",
         "independent proof checking", "numerical precision",
         "distinguish empirical evidence from proof"),
        ("State definitions, assumptions and quantifiers precisely",
         "Map known theorems and related conjectures",
         "Search for proof strategies and counterexamples",
         "Verify each derivation and separate proof from numerical evidence"),
    ),
    "social_behavioral": DomainProfile(
        "social_behavioral", "Social & Behavioral Sciences",
        "Psychology, sociology, economics, education and human behavior.",
        ("psychology", "behavior", "society", "sociology", "economics",
         "education", "political", "cognition", "survey", "human behavior"),
        ("PsycINFO", "SocArXiv", "SSRN", "ICPSR", "World Bank Open Data"),
        ("causal-inference design audit", "measurement validity",
         "multilevel analysis", "survey weighting", "meta-analysis"),
        ("sampling and representativeness", "measurement invariance",
         "confounding and reverse causality", "privacy and consent",
         "cross-cultural replication"),
        ("Operationalize constructs and population",
         "Find primary studies, surveys and administrative datasets",
         "Audit sampling, measurement and causal identification",
         "Compare replications and population-specific limitations"),
    ),
    "engineering": DomainProfile(
        "engineering", "Engineering & Applied Science",
        "Design, control, energy, electronics, manufacturing and systems.",
        ("engineering", "electrical", "mechanical", "civil", "aerospace",
         "control system", "semiconductor", "manufacturing", "power system"),
        ("IEEE Xplore", "ASME Digital Collection", "NASA Technical Reports",
         "NIST", "open hardware repositories"),
        ("system modelling", "finite-element or numerical simulation",
         "control/stability analysis", "design-of-experiments", "reliability analysis"),
        ("units and boundary conditions", "model verification and validation",
         "safety factors", "component tolerances", "physical prototype testing"),
        ("Define operating envelope and measurable performance targets",
         "Locate standards, prior designs and reference datasets",
         "Compare analytical and simulation models",
         "Specify verification, safety and prototype validation"),
    ),
    "general_science": DomainProfile(
        "general_science", "General / Interdisciplinary Science",
        "Cross-disciplinary or not-yet-classified scientific questions.",
        (), ("Crossref", "OpenAlex", "Europe PMC", "arXiv"),
        ("systematic question decomposition", "comparative evidence synthesis",
         "quantitative analysis where suitable", "uncertainty and sensitivity analysis"),
        ("define terms and scope", "check source provenance",
         "seek disconfirming evidence", "replicate with independent data",
         "state limits and abstain when evidence is insufficient"),
        ("Define the question, key terms and measurable outcomes",
         "Map relevant disciplines and competing explanations",
         "Identify evidence gaps and suitable data sources",
         "Select field-specific validation after domain classification"),
    ),
}


# Extensible non-STEM and humanities/social research profiles. These profiles
# describe suitable research practice and source discovery; they do not imply
# that ORACLE has a dedicated connector for every listed source.
_PROFILES.update({
    "history_archaeology": DomainProfile(
        "history_archaeology", "History & Archaeology",
        "Historical periods, archival research, archaeology and material culture.",
        ("history", "historical", "archaeology", "archaeological", "ancient", "medieval",
         "empire", "civilization", "civilisation", "archive", "archival", "manuscript",
         "artifact", "artefact", "historian", "past societies"),
        ("JSTOR", "Internet Archive", "Europeana", "DPLA", "Open Context", "Zenodo"),
        ("source criticism", "chronology and provenance analysis", "comparative historiography",
         "archaeological context analysis", "triangulation across primary sources"),
        ("primary versus secondary source distinction", "dating and provenance uncertainty",
         "translation and transcription limits", "survival and sampling bias",
         "independent corroboration"),
        ("Define period, place, actors and historical claim",
         "Locate primary sources, archives and material evidence",
         "Compare competing interpretations and source provenance",
         "Triangulate evidence and document uncertainty"),
    ),
    "law_policy": DomainProfile(
        "law_policy", "Law & Public Policy",
        "Legal systems, statutes, case law, regulation and public-policy analysis.",
        ("law", "legal", "legislation", "statute", "regulation", "court", "judicial",
         "constitutional", "policy", "regulatory", "rights", "jurisprudence", "case law"),
        ("official legislation portals", "court and tribunal databases",
         "government policy repositories", "WorldLII", "Google Scholar"),
        ("jurisdiction and authority analysis", "doctrinal comparison",
         "policy impact evaluation", "statutory interpretation", "comparative legal analysis"),
        ("jurisdiction and effective date", "binding versus persuasive authority",
         "amendment and repeal status", "primary authority verification",
         "distinguish legal information from legal advice"),
        ("Identify jurisdiction, date and legal question",
         "Retrieve current primary legal authorities",
         "Compare holdings, statutory text and policy evidence",
         "Flag uncertainty and need for qualified legal review"),
    ),
    "economics_business": DomainProfile(
        "economics_business", "Economics & Business",
        "Markets, firms, trade, development, management and economic systems.",
        ("economics", "economic", "business", "market", "markets", "company", "firm",
         "trade", "inflation", "gdp", "employment", "productivity", "management",
         "entrepreneurship", "supply chain", "consumer", "pricing"),
        ("World Bank Open Data", "IMF Data", "OECD Data", "UNData",
         "national statistical agencies", "OpenAlex", "SSRN"),
        ("econometric identification", "time-series and panel analysis",
         "market structure analysis", "cost-benefit analysis", "forecast backtesting"),
        ("nominal versus real values", "selection and survivorship bias",
         "causal identification", "data vintage and revisions", "external validity"),
        ("Define market, geography, time horizon and outcome",
         "Find official statistics and primary empirical studies",
         "Compare mechanisms and alternative explanations",
         "Test robustness, incentives and external validity"),
    ),
    "finance": DomainProfile(
        "finance", "Finance & Investing Research",
        "Financial markets, corporate finance, risk, banking and investment analysis.",
        ("finance", "financial", "stock", "stocks", "bond", "bonds", "equity",
         "portfolio", "investment", "investing", "banking", "credit", "derivative",
         "valuation", "asset pricing", "risk premium"),
        ("central-bank databases", "SEC EDGAR", "FRED", "World Bank Data",
         "exchange filings and official market data"),
        ("cash-flow and valuation analysis", "risk and scenario analysis",
         "event studies", "time-series diagnostics", "portfolio risk decomposition"),
        ("adjusted versus unadjusted prices", "look-ahead and survivorship bias",
         "fees, taxes and liquidity", "out-of-sample validation",
         "risk disclosure; no guaranteed-return claims"),
        ("Define instrument, market, horizon and risk tolerance assumptions",
         "Retrieve filings and authoritative market/economic data",
         "Compare valuation, risk and competing scenarios",
         "Backtest without look-ahead bias and state uncertainty"),
    ),
    "philosophy_ethics": DomainProfile(
        "philosophy_ethics", "Philosophy & Ethics",
        "Conceptual analysis, logic, epistemology, metaphysics and normative ethics.",
        ("philosophy", "philosophical", "ethics", "ethical", "morality", "moral",
         "epistemology", "metaphysics", "consciousness", "free will", "logic",
         "normative", "utilitarian", "deontology", "ontology"),
        ("PhilPapers", "Stanford Encyclopedia of Philosophy", "Internet Encyclopedia of Philosophy",
         "JSTOR", "OpenAlex"),
        ("conceptual distinction analysis", "argument reconstruction",
         "formal logic", "counterexample testing", "normative framework comparison"),
        ("define contested terms", "separate descriptive and normative premises",
         "represent opposing arguments fairly", "check validity versus soundness",
         "avoid presenting unresolved value judgments as facts"),
        ("Clarify concepts and the exact philosophical question",
         "Map major arguments and primary texts",
         "Reconstruct premises, inferences and counterexamples",
         "Compare frameworks and identify unresolved assumptions"),
    ),
    "linguistics_literature": DomainProfile(
        "linguistics_literature", "Linguistics & Literature",
        "Language structure, language change, texts, translation and literary studies.",
        ("linguistics", "language", "linguistic", "grammar", "syntax", "semantics",
         "phonetics", "phonology", "pragmatics", "literature", "literary", "novel",
         "poetry", "translation", "corpus", "dialect"),
        ("ACL Anthology", "Linguistics Open Access", "DOAJ", "JSTOR",
         "Wikimedia language resources", "OpenAlex"),
        ("corpus analysis", "phonetic/statistical analysis", "discourse analysis",
         "textual criticism", "comparative and historical linguistics"),
        ("corpus representativeness", "annotation agreement", "translation ambiguity",
         "genre and period context", "distinguish interpretation from measurable claims"),
        ("Specify language, variety, period and text population",
         "Find corpora, primary texts and peer-reviewed analyses",
         "Compare structural or interpretive explanations",
         "Check sampling, annotation and translation uncertainty"),
    ),
    "education": DomainProfile(
        "education", "Education & Learning Sciences",
        "Teaching, learning, assessment, educational systems and pedagogy.",
        ("education", "educational", "teaching", "learning", "student", "school",
         "university", "pedagogy", "curriculum", "literacy", "assessment", "classroom"),
        ("ERIC", "UNESCO Institute for Statistics", "OECD Education", "IES",
         "government education statistics"),
        ("quasi-experimental evaluation", "multilevel modelling",
         "learning-outcome measurement", "systematic review", "implementation analysis"),
        ("baseline equivalence", "attrition and selection effects",
         "validated outcome measures", "school/context clustering",
         "equity and subgroup effects"),
        ("Define learner population, setting and learning outcome",
         "Retrieve education studies and official statistics",
         "Audit intervention design, measures and confounders",
         "Compare replication, implementation and subgroup outcomes"),
    ),
    "geography_urban": DomainProfile(
        "geography_urban", "Geography & Urban Studies",
        "Human and physical geography, cities, transport and spatial systems.",
        ("geography", "geographic", "geospatial", "urban", "city", "cities",
         "transport", "migration", "land use", "mapping", "spatial", "regional planning"),
        ("OpenStreetMap", "WorldPop", "Natural Earth", "UNData",
         "national census and geospatial portals"),
        ("GIS and spatial statistics", "network analysis", "accessibility modelling",
         "spatiotemporal analysis", "remote-sensing comparison"),
        ("coordinate reference systems", "ecological fallacy",
         "spatial autocorrelation", "boundary and resolution sensitivity",
         "data coverage and temporal alignment"),
        ("Define location, spatial scale and population",
         "Find authoritative geospatial and census data",
         "Compare spatial patterns and plausible drivers",
         "Test sensitivity to boundaries, scale and time"),
    ),
    "politics_governance": DomainProfile(
        "politics_governance", "Politics & Governance",
        "Political institutions, public administration, elections and international relations.",
        ("politics", "political", "governance", "government", "election", "democracy",
         "parliament", "diplomacy", "international relations", "geopolitics",
         "public administration", "political party"),
        ("official election commissions", "parliamentary records",
         "V-Dem", "International IDEA", "World Bank Governance"),
        ("comparative institutional analysis", "survey analysis",
         "process tracing", "causal inference", "policy evaluation"),
        ("source and sponsor transparency", "representative sampling",
         "measurement comparability", "temporal and jurisdiction context",
         "separate descriptive evidence from normative judgment"),
        ("Define institutions, jurisdiction, period and outcomes",
         "Locate primary government records and transparent datasets",
         "Compare institutional and causal explanations",
         "Audit measurement, selection and competing interpretations"),
    ),
    "arts_culture": DomainProfile(
        "arts_culture", "Arts & Culture",
        "Visual arts, music, media, cultural heritage and creative practice research.",
        ("art", "arts", "culture", "cultural", "music", "film", "cinema",
         "architecture", "design", "museum", "heritage", "media studies"),
        ("Europeana", "Smithsonian Open Access", "DPLA", "UNESCO",
         "museum and archive catalogues", "OpenAlex"),
        ("formal and stylistic analysis", "historical contextualization",
         "comparative interpretation", "provenance research", "audience-study analysis"),
        ("work attribution and provenance", "date and cultural context",
         "copyright and reproduction rights", "distinguish interpretation from fact",
         "catalogue completeness and preservation bias"),
        ("Define medium, period, region and cultural context",
         "Locate primary works, catalogues and scholarly interpretations",
         "Compare stylistic and historical explanations",
         "Verify provenance and distinguish evidence from interpretation"),
    ),
    "religion_theology": DomainProfile(
        "religion_theology", "Religion & Theology",
        "Religious traditions, texts, institutions, history and theological arguments.",
        ("religion", "religious", "theology", "theological", "scripture", "bible",
         "quran", "torah", "hinduism", "buddhism", "islam", "christianity",
         "judaism", "religious history", "ritual"),
        ("primary religious text collections", "JSTOR", "ATLA Religion Database",
         "Internet Archive", "OpenAlex"),
        ("textual and historical criticism", "comparative theology",
         "hermeneutic analysis", "historical contextualization", "argument comparison"),
        ("tradition and denomination context", "translation and textual variants",
         "primary versus later interpretation", "represent traditions respectfully",
         "separate historical claims from faith commitments"),
        ("Specify tradition, period, text and interpretive perspective",
         "Locate primary texts and reputable scholarship",
         "Compare interpretations and historical context",
         "State where empirical and theological claims differ"),
    ),
})

_ALIASES = {
    "biology": "biology_medicine", "medicine": "biology_medicine",
    "biomedical": "biology_medicine", "life_science": "biology_medicine",
    "physics": "physics_astronomy", "astronomy": "physics_astronomy",
    "chemistry": "chemistry_materials", "materials": "chemistry_materials",
    "ai": "computer_science_ai", "computer_science": "computer_science_ai",
    "environment": "earth_environment", "earth_science": "earth_environment",
    "math": "mathematics_statistics", "statistics": "mathematics_statistics",
    "psychology": "social_behavioral", "social_science": "social_behavioral",
    "history": "history_archaeology", "archaeology": "history_archaeology",
    "law": "law_policy", "policy": "law_policy",
    "business": "economics_business", "economics": "economics_business",
    "investing": "finance", "financial": "finance",
    "philosophy": "philosophy_ethics", "ethics": "philosophy_ethics",
    "linguistics": "linguistics_literature", "literature": "linguistics_literature",
    "education": "education", "geography": "geography_urban",
    "urban": "geography_urban", "politics": "politics_governance",
    "governance": "politics_governance", "arts": "arts_culture",
    "culture": "arts_culture", "religion": "religion_theology",
}


def list_domains() -> list[dict]:
    return [{"key": key, "label": profile.label, "description": profile.description}
            for key, profile in _PROFILES.items()]


def resolve_domain(question: str, requested: str = "auto") -> tuple[DomainProfile, dict]:
    """Return profile and transparent keyword-routing diagnostics."""
    requested = (requested or "auto").strip().casefold()
    requested = _ALIASES.get(requested, requested)
    if requested != "auto":
        if requested not in _PROFILES:
            raise ValueError(f"Unknown research domain: {requested}")
        profile = _PROFILES[requested]
        return profile, {"method": "user_selected", "matched_terms": [], "confidence": 1.0}

    text = re.sub(r"[^\w\s]", " ", question.casefold().replace("-", " "))
    text = " ".join(text.split())
    words = set(text.split())
    def matches(term: str) -> bool:
        return term in words if " " not in term else term in text

    scores = {}
    for key, profile in _PROFILES.items():
        score = sum(1 for term in profile.search_terms if matches(term))
        if score:
            scores[key] = score
    if not scores:
        return _PROFILES["general_science"], {
            "method": "keyword_fallback", "matched_terms": [], "confidence": 0.0}
    winner = max(scores, key=lambda key: (scores[key], key))
    profile = _PROFILES[winner]
    matched = [term for term in profile.search_terms if matches(term)]
    ranked = sorted(scores.values(), reverse=True)
    confidence = round(ranked[0] / max(1, sum(ranked)), 3)
    return profile, {"method": "keyword_router", "matched_terms": matched,
                     "confidence": confidence, "scores": scores}


def profile_dict(profile: DomainProfile) -> dict:
    value = asdict(profile)
    for key in ("search_terms", "preferred_sources", "analysis_methods",
                "validation_checks", "task_templates"):
        value[key] = list(value[key])
    return value
