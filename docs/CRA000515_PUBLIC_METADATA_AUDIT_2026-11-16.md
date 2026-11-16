# CRA000515 public metadata audit — 2026-11-16

## Frozen acquisition

- Workflow run: [43874634708](https://github.com/Sachhin/ORACLE/actions/runs/43874634708)
- Artifact ID: `14228789805`
- Artifact name: `cra000515-source-metadata-audit`
- Artifact ZIP SHA-256: `81810c8f023d5d100500397d01f70101a6508a122d40e511a7717acf52262162`
- Retrieved: 2026-11-16 13:25:18 UTC
- No BAM/FASTQ files were downloaded.

## What the alternate acquisition established

The public GSA run CSV and per-BioSample CNCB API/page fallback produced a 171-row manifest:

| Field | Verified count |
|---|---:|
| Unique run accessions (CRR) | 171 |
| Unique BioSample accessions (SAMC) | 171 |
| Unique experiment accessions (CRX) | 171 |
| Unique CHHA sample aliases | 171 |
| Alias-to-BioSample cross-references | 171 |
| Samples with tissue metadata | 171 |
| Samples with raw sex code | 171 |
| Samples with age value | **0** |
| Samples with explicit cohort/group label | **0** |
| GSA Sample worksheet rows | **0** |
| GSA Experiment worksheet rows | **0** |
| GSA Run worksheet rows | **0** |
| Exact run-to-sample joins via GSA workbook | **0** |

Every retrieved BioSample record identifies peripheral blood. The raw sex attribute has two values: code `1` for 70 records and code `2` for 101 records. The source metadata does not include a codebook in this package, so these values are retained as raw codes and are **not** converted to male/female.

The GSA workbook download is non-empty as an XLSX container but its Sample, Experiment and Run sheets contain headers only. The fallback therefore enriches the 171 CRR-to-SAMC records with 171 unique CHHA aliases, submitter, project, tissue and raw sex code, but cannot perform the intended sample-sheet join.

## Source checksums

- `CRA000515.run_metadata.csv`: `a89387a1a9979589647a0648b2540aa98ce3a929062d5d49fe13c71745e8b444`
- `CRA000515.project_metadata.xlsx`: `9d0397d7f1e5b8aaf9b8baf451b3cd93c1e9583bab994b4e13ce66a417057ba7`
- `CRA000515.run_biosample_manifest.csv`: `dad14aede2826ede71ddf438d711c5bf9153e583db7e562ef372e1c4f16d7dff`
- The artifact also contains every individual BioSample API JSON and HTML page with per-source SHA-256 hashes, plus `SHA256SUMS.txt`.

## Scientific decision

The alternative public acquisition path is **complete for accession-level provenance**: 171 unique runs, 171 unique BioSamples and 171 unique aliases are cross-referenced, with raw source responses preserved.

It is **not complete for cohort validation**. No age values or centenarian/offspring/spouse labels were available; therefore the published 76/54/41 cohort counts cannot be assigned to individual aliases. Do not infer sex meanings from numeric codes, cohort membership from alias order, or age/group labels from aggregate counts.

The next required source is the sample-level annotation manifest and codebook from the study submitter. The 2026 article identifies Qing-Peng Kong as lead contact (`kongqp@mail.kiz.ac.cn`); the retrieved BioSample records identify Fu-Hui Xiao (`xiaofuhui@mail.kiz.ac.cn`) as submitter. The existing request in `docs/CRA000515_METADATA_ACQUISITION.md` should request the 171-row alias-to-age/cohort crosswalk and sex-code definitions.

**Status:** `metadata_acquired_needs_manual_provenance_review`. This is a reproducible acquisition result, not a biological validation or centenarian replication.
