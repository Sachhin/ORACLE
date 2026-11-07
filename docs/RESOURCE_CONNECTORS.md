# ORACLE scientific resource connectors

This registry separates **working adapters** from **catalogued resources**. A listed resource is not automatically queried: only entries marked `implemented` have an executable adapter in `LiteratureClient`.

## Executable adapters

| Adapter | Coverage | Authentication | Output / scope |
|---|---|---|---|
| Europe PMC | Biology and medicine | None | Papers, abstracts and eligible open-access full text |
| INSPIRE-HEP | High-energy physics literature | None | Literature, DOI, arXiv and citation metadata |
| Ensembl | Human gene annotation | None | Human gene-symbol cross-reference lookup (not free-text gene discovery) |
| PubMed | Biomedical literature | None | NCBI E-utilities search and citation metadata |
| Crossref | All scholarly fields | None | DOI, publication and reference metadata |
| OpenAlex | All scholarly disciplines | Optional mailto | Works, authors, venues, OA status and citation metadata |
| NCBI GEO | Functional genomics | None | GEO Series and supplementary-file metadata |
| NCBI GenBank | Nucleotide sequence records | None | Sequence-record metadata |
| NCBI SRA | Sequencing studies | None | Study/run metadata; raw reads require separate download tooling |
| arXiv | Physics, astronomy, CS/AI, mathematics and engineering | None | Preprints and abstracts |
| PubChem | Chemistry and molecular biology | None | Compound properties, not mechanistic evidence |
| RCSB PDB | Protein and nucleic-acid structures | None | Structure search and entry metadata |
| PRIDE Archive | Proteomics | None for public projects | Proteomics project metadata and accessions |
| ClinicalTrials.gov | Clinical and observational studies | None | Study registry records and summaries |
| OpenAlex / Crossref | Cross-disciplinary scholarly discovery | None | Metadata discovery; source full text retains its own rights |
| GBIF | Biodiversity and organism occurrence records | None | Occurrence records and dataset identifiers |
| World Bank | Economics, development and social indicators | None | Indicator catalogue metadata, not country/time-series observations |
| NOAA NCEI | Climate and environmental datasets | None for catalogue search | Dataset search metadata |
| NASA Earthdata | Earth observation | Login requirements vary by collection | Collection search metadata; collection access can vary |
| USGS ScienceBase | Earth and environmental science | None | ScienceBase item and dataset metadata |
| Zenodo | Cross-disciplinary research outputs | None for public records | Records, DOI, licence and file metadata |
| Harvard Dataverse | Research datasets | None for public records | Dataset search metadata; file download is a separate step |
| Figshare | Research datasets and outputs | None for public records | Dataset metadata, DOI and file metadata |
| Hugging Face Datasets | ML and research datasets | None for public records; gated datasets require access | Dataset metadata, card description, licence and gated flag |
| OpenML | ML benchmark datasets | None for public metadata | Dataset metadata and accession |
| Internet Archive | Digitized books and primary sources | None for public metadata | Item search and metadata; item rights and lending restrictions apply |
| Library of Congress | Historical and cultural primary sources | None | Item search and metadata |

OpenAlex is the cross-disciplinary scholarly discovery fallback for domains without a more specific adapter. Crossref remains the DOI metadata fallback. Metadata adapters do not guarantee that linked files are downloadable or openly licensed. Retrieved metadata, chemical properties and dataset descriptions must not be interpreted as peer-reviewed causal claims.

## Catalogued, not yet executable in ORACLE

- **Astronomy:** NASA Astrophysics Data System (NASA ADS; API token required), INSPIRE-HEP, NASA Technical Reports Server.
- **Biology/medicine:** Ensembl (catalogued, but no executable adapter in this release).
- **Materials/chemistry:** Materials Project (API key required), NOMAD, Crystallography Open Database.
- **Engineering and software:** GitHub repositories, Papers with Code.
- **Mathematics:** zbMATH Open.
- **History/archaeology and arts:** Open Context, Europeana (API key), Smithsonian Open Access (API key).
- **Philosophy:** PhilPapers.
- **Social/behavioural science:** OSF, ICPSR, UN Data.
- **Education:** ERIC.
- **Earth/environment:** PANGAEA, OpenStreetMap.
- **General/interdisciplinary:** sources are routed through OpenAlex and Crossref where available.

Catalog-only entries are deliberately rejected by `ResourceManager.search()`; they are not silently treated as live connectors. Some sources require credentials, registration, domain-specific ingestion, or dataset-specific access and licence review.

## Routing

`resolve_literature_providers(question, "auto")` chooses working adapters based on the domain router. OpenAlex + Crossref are included for all domains; specialist adapters are added where available (Europe PMC/PubMed/GEO/GenBank/SRA/PRIDE, PubChem/PDB, arXiv, GBIF, World Bank, NOAA NCEI, NASA Earthdata, USGS, ClinicalTrials.gov, Zenodo, Harvard Dataverse, Figshare, Hugging Face, OpenML, Internet Archive and Library of Congress). This remains deterministic keyword routing, not semantic certainty.

## Validation and limitations

Unit tests mock external HTTP responses and validate normalization/dispatch. They do not prove that every provider endpoint is currently reachable, that every dataset is downloadable, or that retrieved content supports a scientific claim. Live API smoke tests, rate-limit handling, licensing review, and specialist adapters remain separate validation work. ORACLE records provenance and should retain provider identifiers and dataset licences when interpreting results.


## Downloading retrieved dataset files

ORACLE can download a single HTTPS file from approved public repository hosts
without unpacking or executing it. The downloader enforces an explicit byte
limit, checks redirects against the host allowlist, removes partial files after
errors, and returns a SHA-256 digest for provenance.

```bash
oracle --download-dataset-file "https://zenodo.org/records/RECORD/files/data.csv" \
  --dataset-output data/raw/data.csv --dataset-max-mb 500
```

The user must select a specific file URL from the source record and confirm
its access and licence conditions. Search metadata is not a guarantee that
all linked files are openly downloadable. This is a generic single-file
download step; it does not yet automatically crawl every dataset's file list,
unpack archives, parse every scientific format, or ingest data into a validated
analysis. SHA-256 and source URL should be retained with any downstream result.
