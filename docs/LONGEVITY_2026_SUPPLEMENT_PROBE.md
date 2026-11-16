# 2026 human-longevity article supplementary-data probe

The 2026 Cell Reports Medicine paper on the 8-mRPG signature is available as PMCID PMC13198318. Its exact eight-gene signature, supplementary tables, and cohort annotations are needed for an independent numerical replication.

This workflow retrieves the Europe PMC full-text XML and supplementaryFiles archive, inventories the extracted files, and preserves SHA-256 checksums. It is a public-data-only workflow and does not use any AI model or infer missing sample annotations.

Workflow: .github/workflows/longevity-2026-supplement-probe.yml  
Script: scripts/probe_longevity_2026_supplements.py  
Artifact: oracle-longevity-2026-supplementary-data

The first inspection target is any supplementary table containing the exact 8-mRPG and 7-cRPG gene lists, sample-level expression matrix, cohort/sample metadata, or validation cohort mapping. If the supplements do not contain these data, the Mendeley dataset files and author-provided annotations remain necessary.
