# Universal scientific resource manager

ORACLE has a single auditable resource registry across biology/medicine,
physics/astronomy, computer science/AI, chemistry/materials, earth/environment,
mathematics/statistics, social/behavioral science, and general science.

Use it from Python:

```python
from oracle.resource_manager import ResourceManager

manager = ResourceManager()
for resource in manager.list_resources("biology_medicine"):
    print(resource["key"], resource["status"], resource["api_url"])
report = manager.search("human longevity mechanisms", resources=("europepmc", "crossref", "ncbi_geo"))
```

The registry deliberately distinguishes `implemented` from `catalog_only`.
At this stage, executable dispatch reuses the existing Europe PMC, Crossref,
and NCBI GEO literature adapters. Other entries document authoritative API
endpoints, authentication expectations, and licence cautions, but do not yet
download or analyze data. A catalog entry must never be reported as a working
connector. New adapters require retrieval, parsing, pagination/rate-limit,
provenance, error-path, and fixture-backed tests before their status changes.

## Initial resource coverage

- Universal scholarly metadata: Crossref, OpenAlex
- Biology/medicine: Europe PMC, NCBI GEO
- Physics/astronomy and computing: arXiv
- Chemistry/materials: PubChem, Materials Project
- Earth/environment: NOAA NCEI, GBIF
- Social/economic science: World Bank Open Data

API keys are not embedded in the registry. Keyed providers must read secrets
from runtime configuration/environment and document quotas before activation.
