# CRA000515 2018 cohort supplementary metadata probe

The 2018 Genome Research article (PMCID PMC6211641; DOI 10.1101/gr.220780.117) identifies the 171-person Hainan cohort and links Supplemental Table S1 for sequencing/sample details and Supplemental File S1 for the DESeq2 analysis inputs. The main article reports cohort-level counts and sex totals, but the individual alias-to-cohort mapping is not present in the public GSA BioSample metadata.

This workflow probes the PMC Open Access service for the article's downloadable package, preserves the OA XML response and archive checksum, and inventories extracted supplement files. It is intended to determine whether Supplemental Table S1 or Supplemental File S1 includes sample identifiers that can be joined to the 171 CRA000515 CHHA aliases.

Workflow: .github/workflows/cra000515-pmc-supplement-probe.yml  
Script: scripts/probe_cra000515_pmc_supplements.py  
Artifact: oracle-cra000515-pmc-supplement-probe

No cohort labels will be assigned unless the supplement contains an explicit, source-authenticated identifier crosswalk. If the package is not available through PMC OA, the result will record that limitation and the author request remains necessary.
