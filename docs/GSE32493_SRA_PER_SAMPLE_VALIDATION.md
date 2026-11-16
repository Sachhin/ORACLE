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

1. Query the ENA run-file report for each SRA run, download its single-end FASTQ, and verify the archive-provided MD5 and byte count before analysis.
2. Run fastp single-end automatic adapter detection and retain 18–30 nt reads.
3. Download the miRBase 23.1 current mature reference and extract human (`hsa-`) entries.
4. Align with Bowtie 1, allowing up to one mismatch and retaining all best-stratum alignments.
5. Count a read only when it has exactly one distinct best human mature-miRNA target; exclude multi-mapping reads rather than assigning them arbitrarily.
6. Run edgeR's negative-binomial exact test for control versus centenarian with three biological samples per group.
7. Preserve ENA source URLs and MD5/SHA-256 checksums, raw FASTQ byte counts, trimmed FASTQ checksums, reference archive checksum, fastp QC, SAM checksums, count matrix, edgeR results, and R session information in the workflow artifact.

## Interpretation constraints

- This is a new, reproducible per-sample reanalysis, not an exact reproduction of the 2012 authors' pipeline. The GEO record does not fully specify the original miRBase release or all adapter-trimming settings.
- The cohort is only three centenarians and three controls, from Ashkenazi Jewish EBV-transformed B-cell lines. It is not a direct replication of the Chinese nonagenarian/centenarian whole-blood mRPG signature.
- miRBase 23.1 is a modern reference, so annotation may differ from the original 2012 analysis.
- Bowtie multi-mappers are excluded; this conservative choice can reduce assigned read counts.
- Any edgeR result is exploratory, low-powered and tissue/model-specific. It cannot establish organismal longevity causality.
- This analysis does not solve CRA000515 sample-level age/cohort metadata or Mendeley access for the 2026 Chinese cohort.

## Release status

The pipeline and offline SAM parser tests are included in PR. The live raw-read run must pass before reporting numerical outcomes. The result artifact must be inspected for per-sample read counts, mapping rates, adapter trimming, sample mapping, count matrix, edgeR FDR and reference checksum.
