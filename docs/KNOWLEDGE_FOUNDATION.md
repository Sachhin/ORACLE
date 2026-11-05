# Scientific knowledge foundation

ORACLE stores claims separately from evidence and records explicit evidence-to-claim links. A link has a stance (supports, refutes, contextual), a 0..1 strength and a rationale. Every reference is validated against an existing claim and evidence record.

## Competing hypotheses

Hypotheses can be grouped under the same research question. Alternatives remain side by side; adding one does not overwrite or silently reject another.

## Contradictions and uncertainty

Contradictions are surfaced from explicit claim-to-claim links and a deliberately narrow direct-negation heuristic. This is not semantic contradiction detection; ambiguous natural language must be reviewed rather than guessed.

Claim uncertainty reports evidence counts, weighted supporting and opposing evidence, and unresolved contradictions. Its optional evidence-balance value is explicitly **not a calibrated probability**. Contextual links do not count as support or refutation. No evidence means no estimate.

## Recovery

Every completed cycle persists a full run snapshot and an append-only event. `resume(run_id, additional_cycles)` restores the typed run, retains history and continues from the next cycle. The CLI accepts `--resume RUN_ID`. Cycle snapshots are atomic: interrupted partial cycles are retried from the last completed checkpoint.

## Integrity boundary

The baseline agents remain deterministic scaffolds. They do not retrieve papers, establish scientific truth, prove novelty, or perform experiments. Inference records are labelled as such. The knowledge layer is infrastructure for future providers, not a substitute for evidence.
