# Hybrid domain-specialist research

ORACLE keeps one shared research lifecycle and selects a specialist research
profile for each question. The router is deterministic and explainable; it does
not imply that external tools, experiments, or domain-specific analyses ran.

## Domains

- `biology_medicine`: PubMed/Europe PMC, GEO/SRA, PRIDE/ProteomeXchange,
  clinical study design, omics QC and independent-cohort replication.
- `physics_astronomy`: arXiv, NASA/ESA, ADS and INSPIRE-HEP; dimensional
  analysis, derivations, simulations and observational constraints.
- `chemistry_materials`: PubChem, ChEBI, Materials Project and NIST;
  stoichiometry, structure-property analysis and molecular simulation.
- `computer_science_ai`: arXiv, ACM/IEEE and benchmark repositories; formal
  specifications, baselines, ablations, leakage checks and reproducibility.
- `earth_environment`: NASA Earthdata, NOAA, USGS, Copernicus and GBIF;
  spatiotemporal analysis and independent geographic/temporal validation.
- `mathematics_statistics`: arXiv, zbMATH and MathSciNet; proof obligations,
  counterexample search and symbolic/numerical checks.
- `social_behavioral`: PsycINFO, SocArXiv, ICPSR and World Bank data;
  measurement validity, sampling, causal identification and replication.
- `engineering`: IEEE/ASME, NASA technical reports and NIST; modelling,
  verification, safety factors and prototype validation.
- `general_science`: conservative cross-disciplinary fallback.
- `history_archaeology`: primary-source criticism, archival provenance, chronology,
  archaeology and triangulation across historical evidence.
- `law_policy`: jurisdiction-aware primary legal authorities, case/statute comparison
  and policy evaluation; legal information is not legal advice.
- `economics_business`: official economic statistics, econometrics, market structure,
  business mechanisms and robustness checks.
- `finance`: filings, central-bank/market data, valuation and risk analysis with
  look-ahead/survivorship-bias controls.
- `philosophy_ethics`: conceptual analysis, argument reconstruction, logic,
  counterexamples and normative-framework comparison.
- `linguistics_literature`: corpora, language structure/change, textual criticism,
  discourse and translation uncertainty.
- `education`: learning outcomes, education studies, implementation, sampling,
  attrition and subgroup effects.
- `geography_urban`: GIS, census/geospatial data, spatial statistics and scale sensitivity.
- `politics_governance`: institutions, election/government records, comparative
  analysis and measurement/sampling checks.
- `arts_culture`: primary works, catalogues, provenance, historical context and
  interpretation-versus-fact distinctions.
- `religion_theology`: primary texts, textual variants, historical context and
  comparative interpretation across traditions.

## Usage

Automatic routing is the default and preserves existing command lines:

```bash
python -m oracle "Can we identify previously unknown biological mechanisms involved in human longevity?" \
  --domain auto --mode both --cycles 3 --agent-provider gemini \
  --research-literature --provider all --extract-claims --compare-papers \
  --review-evidence --full-text --discover-geo-files --json
```

To override routing, use any profile key listed above, or `--domain auto`.
The dashboard exposes the same choices. The router also records secondary-domain
signals for interdisciplinary questions and classifies research intent separately
from subject area. This remains heuristic routing; inspect the report diagnostics
when a question is ambiguous or uses unfamiliar terminology.

The selected profile and routing diagnostics are included in the run event log
and passed to model agents as bounded research guidance. The deterministic planner adds up to four
domain-specific tasks. Existing evidence, source, claim, hypothesis, experiment
and review models remain unchanged.

## Scientific integrity limits

A profile lists suggested repositories and methods; it does not automatically
download datasets from every listed source or execute specialist software.
ORACLE must report a tool as run only when it actually ran. A hypothesis is
not a discovery, simulation is not an experiment, and a literature search is
not proof of novelty. Use field-appropriate external references, independent
datasets, uncertainty estimates and qualified human review before promoting
scientific conclusions.
