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


## Additional 2026 cohort cross-reference

The 2026 Cell Reports Medicine study *Preserved mitochondrial ribosomal protein
gene expression marks a youthful transcriptional state in Chinese
nonagenarians and centenarians* (DOI
`10.1016/j.xcrm.2026.102767`) identifies 171 RNA-seq samples from
CRA000515 and 271 from HRA000656 as previously reported samples, and lists
1,310 newly included samples under HRA000721, HRA015371, and HRA015372. It
states that a 1,751-sample expression matrix is deposited at Mendeley Data
(DOI `10.17632/fpf4y72kfz.1`). This is a useful independent cross-reference
for the project, but it does not by itself provide the 171-row
alias-to-age/cohort crosswalk required by this audit.

The paper's lead contact is Qing-Peng Kong (`kongqp@mail.kiz.ac.cn`). If the
public sample records remain incomplete, request the sample annotation
manifest, its field definitions, and the mapping between CRA000515 aliases
and the 2026 integrated expression matrix before treating the groups as
validated.


## Public BioSample fallback and current metadata limitation

The fallback acquisition path queries the CNCB public BioSample API and
human-readable BioSample record for each BioSample accession in the GSA run
manifest. It preserves each raw response and SHA-256, and records source
fields independently. This is a second metadata route in addition to the
GSA project workbook and run CSV.

Publicly indexed BioSample records for this project show the CHHA alias,
BioSample accession, sex, tissue, submitter and project accession, but the
age field is blank in representative records (for example SAMC016716 /
CHHA3 and SAMC016887 / CHHA171). The public BioProject PRJCA000568 lists 171
BioSamples and their CHHA aliases. This is useful for authenticating the
alias-to-BioSample cross-reference and available sex/tissue fields, but it
does not provide the missing age/cohort labels needed to reproduce the
published centenarian/offspring/spouse groups.

Accordingly, the fallback must not promote a retrieved BioSample record to
a validated cohort label. The acquisition status remains
`metadata_acquired_needs_manual_provenance_review` until the complete
sample-level age and cohort annotation is authenticated from the submitter
or original study records. The integrated Mendeley expression matrix is a
potential numerical source, but the public dataset landing page alone does
not expose a verifiable alias-to-phenotype manifest.

References:
- CNCB BioProject PRJCA000568: https://ngdc.cncb.ac.cn/bioproject/browse/PRJCA000568
- Example BioSample record CHHA3 / SAMC016716: https://ngdc.cncb.ac.cn/biosample/browse/SAMC016716
- Example BioSample record CHHA171 / SAMC016887: https://ngdc.cncb.ac.cn/biosample/browse/SAMC016887
- Mendeley expression-matrix dataset: https://data.mendeley.com/datasets/fpf4y72kfz/1


## Pull-request audit artifacts

The metadata-only acquisition runs on pull requests as a reproducibility check.
Its output artifact is now uploaded for pull_request, push, and manual
workflow_dispatch events alike, so the raw response hashes, extracted workbook
sheets, 171-row run/BioSample manifest and cohort audit can be inspected
before merge. The acquisition job is not considered cohort validation merely
because it exits successfully; missing group/age annotations remain a
manual-provenance blocker.
