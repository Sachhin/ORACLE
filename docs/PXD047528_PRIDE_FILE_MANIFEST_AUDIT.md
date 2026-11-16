# PXD047528 PRIDE file-manifest audit

This workflow queries the public PRIDE Archive v3 project endpoint and project-file endpoint for PXD047528. It saves the complete returned metadata and a normalized TSV manifest, including filenames, file categories, sizes, sample accession fields and public file locations.

The audit is deliberately metadata-only. It does not download raw spectra and does not infer clinical phenotype or participant identity from file order, file naming, or the number of acquisitions.

Workflow:
- `.github/workflows/pxd047528-pride-manifest.yml`
- Script: `scripts/audit_pxd047528_pride_manifest.py`
- Artifact: `oracle-pxd047528-pride-metadata`

A successful API response establishes the technical file inventory, not the missing clinical crosswalk. A 15-alias-to-13-person map still requires the submitter's source-authenticated manifest.
