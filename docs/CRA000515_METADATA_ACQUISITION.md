# CRA000515 reproducible metadata acquisition

## Scope and safety

Run the metadata-only workflow before any sequencing-file acquisition. The
workflow calls the public GSA `getRunInfoByCra` and `exportExcelFile`
interfaces, saves their raw responses, hashes them, exports workbook sheets,
and joins run records to sample records **only by BioSample accession**.

It does not download BAM/FASTQ files (individual BAMs can be multi-GB), infer
age/group from sample aliases, or run expression analysis.

## Execute

GitHub Actions → **ORACLE CRA000515 centenarian metadata acquisition and audit**
→ Run workflow → accession `CRA000515`.

Download the artifact `cra000515-source-metadata-audit`. It contains:
- original run metadata CSV and project metadata XLSX;
- extracted Sample/Experiment/Run sheets as CSV;
- run-to-BioSample manifest, retaining raw source row JSON;
- metadata audit JSON and SHA256SUMS.txt.

## Acceptance checks before any BAM download

1. GSA run CSV and workbook are both present and nonempty.
2. Every run ID is a unique CRR accession; every BioSample is a valid SAMC accession.
3. Every run-to-sample join is exact by BioSample accession; unmatched rows are
   reported and must be resolved, never joined by row order or alias.
4. Inspect group and age attributes. Compare explicit metadata with the
   published design (76 centenarians, 54 offspring, 41 offspring spouses),
   but never assign labels to force those aggregate counts to match.
5. Verify unique people versus technical replicates, library strategy/layout,
   tissue, sex, age, exclusions and covariates against source records.
6. Freeze the validated manifest and checksums before bulk BAM acquisition.

A successful metadata workflow means **metadata retrieved and structurally
audited**, not that sample identities are biologically validated or that the
centenarian study has been replicated. If the public workbook omits ages or
cohort labels, request the source-authenticated manifest from the submitter.
