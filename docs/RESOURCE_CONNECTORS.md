# ORACLE scientific resource connectors

This registry separates **working adapters** from **catalogued resources**. A listed resource is not automatically queried: only entries marked `implemented` have an executable adapter in `LiteratureClient`.

## Executable adapters

| Adapter | Coverage | Authentication | Output |
|---|---|---|---|
| Europe PMC | Biology, medicine, biomedical literature | None | Papers, abstracts, OA metadata |
| Crossref | All scholarly fields | None | DOI and publication metadata |
| NCBI GEO | Functional genomics | None | GEO Series metadata |
| arXiv | Physics, astronomy, CS/AI, mathematics, engineering | None | Preprints and abstracts |
| PubChem | Chemistry and molecular biology | None | Compound properties (not mechanistic evidence) |
| OpenAlex | All scholarly disciplines | Optional mailto | Works, authors, venues, OA status, citation counts |
| GBIF | Biodiversity and organism occurrence records | None | Occurrence records and dataset identifiers |
| World Bank | Economics, development and social indicators | None | Indicator catalogue metadata |

OpenAlex is the cross-disciplinary scholarly discovery fallback for domains without a dedicated adapter. Crossref remains the DOI metadata fallback. Dataset records and chemical properties are stored as source records but must not be interpreted as peer-reviewed causal claims.

## Catalogued, not yet executable in ORACLE

- **Astronomy:** NASA ADS (token required), NASA Technical Reports Server.
- **Biology/medicine:** PDB, PRIDE, NCBI SRA, ClinicalTrials.gov.
- **Earth/environment:** NOAA NCEI, NASA Earthdata (collection/login requirements vary), USGS ScienceBase, PANGAEA, OpenStreetMap.
- **Materials/chemistry:** Materials Project (API key required), NOMAD, Crystallography Open Database.
- **Engineering:** NASA Technical Reports Server.
- **History/archaeology and arts:** Open Context, Internet Archive, Europeana (API key), Smithsonian Open Access (API key).
- **Philosophy:** PhilPapers.
- **Social/behavioural science:** OSF, ICPSR, Harvard Dataverse, UN Data, World Bank.
- **Education:** ERIC.

Catalog-only entries are deliberately rejected by `ResourceManager.search()`; they are not silently treated as live connectors. Some sources require credentials, registration, or dataset-specific access and licences.

## Routing

`resolve_literature_providers(question, "auto")` chooses working adapters based on the domain router. OpenAlex + Crossref are included for all domains; specialist adapters are added where available (Europe PMC/GEO/PubChem, arXiv, GBIF, World Bank). This remains deterministic keyword routing, not semantic certainty.

## Validation and limitations

Unit tests mock external HTTP responses and validate normalization/dispatch. They do not prove that every provider endpoint is currently reachable, that every dataset is downloadable, or that retrieved content supports a scientific claim. Live API smoke tests, rate-limit handling, licensing review, and specialist adapters remain separate validation work. ORACLE records provenance and should retain provider identifiers and dataset licences when interpreting results.
