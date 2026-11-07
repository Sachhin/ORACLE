"""Domain routing and specialist research profiles for hybrid ORACLE.

Routing is deterministic and transparent. It selects a research lens and tool
recommendations; it does not claim that a specialist model or domain dataset ran.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


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
        ("gene", "protein", "cell", "organism", "biology", "medicine", "disease",
         "cancer", "longevity", "aging", "genetic", "clinical", "drug", "brain",
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

_ALIASES = {
    "biology": "biology_medicine", "medicine": "biology_medicine",
    "biomedical": "biology_medicine", "life_science": "biology_medicine",
    "physics": "physics_astronomy", "astronomy": "physics_astronomy",
    "chemistry": "chemistry_materials", "materials": "chemistry_materials",
    "ai": "computer_science_ai", "computer_science": "computer_science_ai",
    "environment": "earth_environment", "earth_science": "earth_environment",
    "math": "mathematics_statistics", "statistics": "mathematics_statistics",
    "psychology": "social_behavioral", "social_science": "social_behavioral",
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

    text = " " + " ".join(question.casefold().replace("-", " ").split()) + " "
    scores = {}
    for key, profile in _PROFILES.items():
        score = sum(1 for term in profile.search_terms
                    if (" " + term + " ") in text or term in text)
        if score:
            scores[key] = score
    if not scores:
        return _PROFILES["general_science"], {
            "method": "keyword_fallback", "matched_terms": [], "confidence": 0.0}
    winner = max(scores, key=lambda key: (scores[key], key))
    profile = _PROFILES[winner]
    matched = [term for term in profile.search_terms
               if (" " + term + " ") in text or term in text]
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
