# Universal scientific resource manager

ORACLE has a single auditable resource registry across biology/medicine,
physics/astronomy, computer science/AI, chemistry/materials, earth/environment,
mathematics/statistics, social/behavioral science, and general science.

The arXiv adapter is executable through the same literature pipeline, including Atom parsing, normalized metadata, and abstract ingestion. It does not claim peer review or validate preprint conclusions.

PubChem is also an executable compound-property adapter using the PUG REST API. It returns structured compound metadata (CID, formula, molecular weight, IUPAC name, and SMILES); ORACLE labels it as chemical metadata, not peer-reviewed evidence for a biological mechanism.

Use it from Python:

```python
from oracle.resource_manager import ResourceManager

manager = ResourceManager()
for resource in manager.list_resources("biology_medicine"):
    print(resource["key"], resource["status"], resource["api_url"])
report = manager.search("human longevity mechanisms", resources=("europepmc", "crossref", "ncbi_geo"))
preprints = manager.search("black hole information", resources=("arxiv",))
compounds = manager.search("aspirin", resources=("pubchem",))
```

The registry deliberately distinguishes `implemented` from `catalog_only`.
Executable dispatch currently uses Europe PMC, Crossref, NCBI GEO, arXiv,
and PubChem adapters. OpenAlex, Materials Project, NOAA, GBIF, World Bank,
and NASA technical reports remain catalog-only; they are not yet executable
connectors. A catalog entry must never be reported as a working
connector. New adapters require retrieval, parsing, pagination/rate-limit,
provenance, error-path, and fixture-backed tests before their status changes.

## Initial resource coverage

- Universal scholarly metadata: Crossref, OpenAlex
- Biology/medicine: Europe PMC, NCBI GEO
- Physics/astronomy and computing: arXiv
- Chemistry/materials: PubChem (implemented compound metadata search), Materials Project
- Earth/environment: NOAA NCEI, GBIF
- Social/economic science: World Bank Open Data

API keys are not embedded in the registry. Keyed providers must read secrets
from runtime configuration/environment and document quotas before activation.
