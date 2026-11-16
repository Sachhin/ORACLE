# Legacy Qwen PR GEO-fix extraction audit

Audit date: 2026-11-16

This review covers the GEO-related changes in legacy PRs #88, #90 and #94. Those PRs are closed and unmerged. ORACLE remains model-free: no Qwen3 workflow, model download, local inference runtime, provider configuration or model-based scientific reasoning is restored by this extraction.

## Reusable GEO workflow fixes already present on main

- Run the GEO analysis on pull requests touching the workflow, analysis script or validation blocker documentation.
- Install the required system libraries for GEOquery/Bioconductor compilation and retrieval.
- Install only GEOquery and limma as analysis dependencies; the optional `lumiHumanIDMapping` package is not required.
- Create the artifact directory before writing the report.
- Use the current report field `samples_analyzed` in the GitHub step summary.
- Keep the GEO analysis artifact and report generation independent of any language model.

These are present in `.github/workflows/human-aging-geo-analysis.yml` on main.

## Remaining parser fixes extracted in PR #163

- Reject implausible human ages outside 0–120, both for direct age columns and age-labelled characteristic fields.
- Prefer explicit participant labels such as “young control” over broad cohort descriptors such as “nonagenarian cohort”.
- Add regression guards for both cases.

The current main parser already uses a stricter explicit-field extraction strategy than the broad substring parser in the old PR patches. The extraction therefore applies the edge-case protections to the current parser rather than restoring the older broad parser.

## Deliberately excluded

- Qwen3 model download/configuration and local inference workflow changes.
- SciFact prompt/retry/model-output handling changes.
- Any change that reinstates `oracle.language_model`, Qwen3 or a provider API dependency.

## Decision

Only GEO data-retrieval, dependency, reporting and metadata-parsing improvements are retained. No Qwen3/model capability is brought back. PR #163 is the isolated parser-fix change; its GEO workflow run must pass before merge.
