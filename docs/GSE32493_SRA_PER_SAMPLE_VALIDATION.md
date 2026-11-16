# GSE32493 per-sample raw SRA validation

Date: 2026-11-16  
Implementation branch: `reproduce-gse32493-from-sra-reads`

## Why this workflow exists

The GEO supplementary files contain one aggregate count column per group, not three individual sample columns. Those group-level tables support descriptive fold changes but not replicate-level inference. GEO separately identifies six biological samples and links the series to SRA study SRP008552. The SRA run records expose six individual single-end runs, so a new per-sample analysis can be performed from the deposited raw reads instead of treating group aggregates as replicates.

## Source-authenticated sample map

| GEO sample | SRA experiment | SRA run | Group | SRA-reported spots | Approx. FASTQ download |
|---|---|---|---|---:|---:|
| GSM804340 | SRX099372 | SRR350239 | Control 1 | 5,001,231 | 121.0 MB |
| GSM804341 | SRX099373 | SRR350240 | Control 2 | 3,397,339 | 114.5 MB |
| GSM804342 | SRX099374 | SRR350241 | Control 3 | 5,507,871 | 129.3 MB |
| GSM804343 | SRX099375 | SRR350242 | Centenarian 1 | 3,416,386 | 112.3 MB |
| GSM804344 | SRX099376 | SRR350243 | Centenarian 2 | 5,221,462 | 160.5 MB |
| GSM804345 | SRX099377 | SRR350244 | Centenarian 3 | 4,390,079 | 126.9 MB |

GEO sample records explicitly distinguish the three controls and three centenarians. The SRA study record confirms six public single-end Illumina runs and the run accessions above. No sample labels are inferred from filenames or sample order.

Sources:
- GEO series: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE32493
- SRA study: https://www.ncbi.nlm.nih.gov/sra?term=SRP008552
- Example individual run record: https://www.ncbi.nlm.nih.gov/sra/SRX099377

## Analysis implementation

1. Download the six source-authenticated SRA run accessions with NCBI SRA Toolkit (prefetch and fasterq-dump), then gzip the resulting single-end FASTQ files.
2. Run fastp single-end automatic adapter detection and retain 18–30 nt reads.
3. Download the miRBase 23.1 current mature reference and extract human (`hsa-`) entries.
4. Align with Bowtie 1, allowing up to one mismatch and retaining all best-stratum alignments.
5. Count a read only when it has exactly one distinct best human mature-miRNA target; exclude multi-mapping reads rather than assigning them arbitrarily.
6. Run edgeR's negative-binomial exact test for control versus centenarian with three biological samples per group.
7. Preserve SRA run accessions, trimmed FASTQ checksums, the complete miRBase 23.1 mature FASTA checksum and the verified 74,463-record count, fastp QC, SAM checksums, count matrix, edgeR results, and R session information in the workflow artifact.

## Interpretation constraints

- This is a new, reproducible per-sample reanalysis, not an exact reproduction of the 2012 authors' pipeline. The GEO record does not fully specify the original miRBase release or all adapter-trimming settings.
- The cohort is only three centenarians and three controls, from Ashkenazi Jewish EBV-transformed B-cell lines. It is not a direct replication of the Chinese nonagenarian/centenarian whole-blood mRPG signature.
- miRBase 23.1 is a modern reference, so annotation may differ from the original 2012 analysis.
- Bowtie multi-mappers are excluded; this conservative choice can reduce assigned read counts.
- Any edgeR result is exploratory, low-powered and tissue/model-specific. It cannot establish organismal longevity causality.
- This analysis does not solve CRA000515 sample-level age/cohort metadata or Mendeley access for the 2026 Chinese cohort.

## Release status

The pipeline and offline SAM parser tests are included in PR. The live raw-read run must pass before reporting numerical outcomes. The result artifact must be inspected for per-sample read counts, mapping rates, adapter trimming, sample mapping, count matrix, edgeR FDR and reference checksum.


## Raw FASTQ diagnostic and adapter correction (2026-11-16)

The first SRA attempt exposed a real preprocessing mismatch: the first ten raw reads are 35 nt and their quality characters correspond to Phred Q0–Q10, so fastp's default Q15 filter rejected all reads. The reads also contain the Illumina SRA 3′ adapter motif `TCGTATGCCGTCTTCTGCTTG`; fastp's automatic adapter detector did not identify it.

The corrected pipeline now supplies the explicit Illumina v1.0 small-RNA 3′ adapter sequence and disables quality filtering (but retains the original quality strings and reports their distribution). It keeps only adapter-trimmed inserts 18–30 nt long. This avoids treating low/archived quality values as a reliable filtering signal, but it is an explicit limitation and must be considered when interpreting counts.

Evidence:
- GEO sample GSM804340 records Illumina Small RNA Prep Kit FC-930-1004: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM804340
- Illumina's FC-930-1004 guide identifies the SRA 3′ adapter and the 18–30 nt size-selection range: https://sapac.illumina.com/content/dam/illumina-support/documents/documentation/chemistry_documentation/samplepreps_legacy/SmallRNA_SamplePrep_Guide_1004239_D.pdf
- A public GEO record documents the exact Illumina v1.0 small-RNA 3′ adapter sequence `TCGTATGCCGTCTTCTGCTTG`: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM803573

The new workflow preserves the raw-read preview artifact even if trimming or mapping fails. No differential-expression result is considered valid until all six samples have non-zero post-trim reads, per-sample mapping QC is inspected, and the edgeR output is independently checked.


## Verified raw-read result (GitHub Actions run 43900103792)

The six-run workflow completed successfully. The source-authenticated mapping is three controls (GSM804340–GSM804342 / SRR350239–SRR350241) and three centenarians (GSM804343–GSM804345 / SRR350242–SRR350244).

| QC metric | Total across 6 runs |
|---|---:|
| Raw reads | 26,934,368 |
| Reads retained after adapter/length processing | 21,629,996 |
| Reads with adapter trimmed | 25,129,847 |
| Reads with at least one best-stratum miRNA alignment | 12,973,535 |
| Uniquely mapped reads counted | 11,637,986 |
| Multi-mapped reads excluded | 1,335,549 |
| Features in count matrix | 1,105 |
| Features retained/tested by edgeR | 302 |
| Features with FDR < 0.05 | 0 |

The six sample-level counts, raw/trimmed FASTQ checksums, SAM checksums, fastp JSON/HTML QC and edgeR results are frozen in the workflow artifact `oracle-gse32493-sra-per-sample-validation`.

**Statistical result:** with only three biological samples per group, edgeR identified no miRNA with BH FDR below 0.05. Several nominal p-values were below 0.05, but their FDR values were 1.0 after correction. ORACLE therefore reports no statistically significant differential miRNA from this reanalysis.

**Interpretation limits:**
- GSE32493 is a small study of EBV-transformed B-cell lines, not a whole-blood or tissue-level human longevity cohort.
- It measures mature miRNAs, not the 8 mitochondrial ribosomal protein mRNAs; it is not a direct replication of the 2026 mRPG signature.
- The three-versus-three design is underpowered and exploratory.
- The archive's FASTQ quality strings were Q0–Q10 in the inspected records; quality filtering was disabled to avoid discarding all reads. This makes count uncertainty higher and must be reported.
- The analysis uses the current miRBase 23.1 human mature reference, not necessarily the exact historical annotation used by the 2012 study. It is a reproducible reanalysis, not a bit-for-bit reproduction of the original pipeline.
- No causal or organism-level longevity mechanism is established.

This closes the live raw-read execution blocker for GSE32493, but does not create a new validated longevity mechanism.
