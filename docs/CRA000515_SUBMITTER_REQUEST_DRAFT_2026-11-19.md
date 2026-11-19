# CRA000515 source-authenticated manifest request (draft; not sent)

**Recipient:** Qing-Peng Kong, lead contact listed in the 2026 longevity study  
**Address:** kongqp@mail.kiz.ac.cn  
**Status:** Follow-up template only. The repository's 2026-11-17 outreach log records that the initial de-identified manifest request was sent to the published lead-author contact; no authenticated response/file has been recorded as of 2026-11-19. Do not resend without checking the user's email thread first.

## Subject
Request for CRA000515 sample-level age/cohort manifest and linked expression data

Dear Dr. Kong,

I am independently auditing the publicly deposited CRA000515 cohort data cited in your study, “Preserved mitochondrial ribosomal protein gene expression marks a youthful transcriptional state in Chinese nonagenarians and centenarians.”

The public archive exposes 171 runs/BioSamples and sex metadata, but the individual age and CEN/F1/F1SP cohort labels needed to reproduce the analysis are not present in the public BioSample records. The article's supplement references a sample-information file, but the corresponding row-level file was not available in the public supplement archive inspected.

Would you be willing to provide, or point me to, the source-authenticated sample manifest for the 171 CRA000515 samples? Ideally, each row would include:

- CHHA sample alias and CRR run accession
- SAMC BioSample and CRX experiment accession
- chronological age at sampling (or an explicit age field with units)
- original cohort/group label (CEN, F1, F1SP) and the study's definition of each group
- sex, region/province, library type, read type, and sequencing/batch metadata
- any exclusions, missing-age records, relabelling, or duplicate/related-sample notes
- the exact source filename/version and a checksum or repository URL, if available

If sharing individual-level metadata is restricted, an approved de-identified mapping with the age and group fields retained would still be useful. I will preserve the provenance, cite the source, and use the data only within its stated permissions. I will not infer missing ages or cohort labels from aggregate counts, sex, expression profiles, or sample order.

Could you also clarify whether the sample-level expression matrix referenced by the article is available through an authenticated Mendeley download or another repository route, and how the CRA000515 samples map to the integrated 2026 analysis?

Thank you for your time and for any guidance you can provide.

Best regards,
ORACLE independent reproducibility audit

## Required handling if a response is received
1. Preserve the original response and attachment unchanged.
2. Record sender identity/role, date, and permission/terms.
3. Hash every received file with SHA-256.
4. Validate all 171 aliases and accession joins; report missing, duplicate, and conflicting rows.
5. Compare supplied aggregate group counts with the published 76 CEN, 54 F1, and 41 F1SP counts without forcing a match.
6. Keep the one previously published sample with missing age explicitly identified; do not assume it belongs to CRA000515.
7. Only then update the CRA audit and rerun the release gate.

## Current blocker
The request is a draft only. No author contact has been made, no manifest has been received, and the CRA000515 individual age/cohort blocker remains open.
