"""Conservative provenance-aware quality audit for ORACLE research-run JSON."""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from pathlib import Path
from typing import Any

def _items(value: Any) -> list[dict[str, Any]]:
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []

def _s(value: Any) -> str:
    return str(value or "").strip()

def _group(source: dict[str, Any]) -> str:
    accession = _s(source.get("dataset_accession")).upper()
    if accession: return "dataset:" + accession
    if _s(source.get("doi")): return "paper:" + _s(source["doi"]).casefold()
    if _s(source.get("pmid")): return "paper:" + _s(source["pmid"])
    return "source:" + (_s(source.get("source_id")) or _s(source.get("title")))

def audit_run(payload: dict[str, Any], *, fdr_threshold: float = 0.05) -> dict[str, Any]:
    if not 0 < fdr_threshold < 1: raise ValueError("fdr_threshold must be strictly between 0 and 1")
    run = payload.get("run", payload)
    if not isinstance(run, dict): raise ValueError("Input must contain a run object")
    sources, evidence = _items(run.get("sources")), _items(run.get("evidence"))
    hypotheses, claims = _items(run.get("hypotheses")), _items(run.get("claims"))
    contradictions = _items(run.get("contradiction_candidates"))
    de_analyses, dataset_analyses = _items(run.get("differential_expression_analyses")), _items(run.get("dataset_analyses"))
    by_id = {_s(x.get("source_id")): x for x in sources if _s(x.get("source_id"))}
    human = [x for x in sources if any(term in (_s(x.get("organism"))+" "+_s(x.get("dataset_summary"))+" "+_s(x.get("title"))).casefold() for term in ("human","homo sapiens"))]
    evidence_groups = set()
    for item in evidence:
        src = by_id.get(_s(item.get("source_id")), {})
        key = _s(item.get("dependence_group")) or (_group(src) if src else "")
        if key: evidence_groups.add(key)
    feature_map = defaultdict(dict)
    for analysis in de_analyses:
        accession = _s(analysis.get("dataset_accession")).upper()
        if not accession: continue
        for result in _items(analysis.get("results")):
            feature = _s(result.get("feature"))
            try: fc, padj = float(result["log2_fold_change"]), float(result["p_value_adjusted_bh"])
            except (KeyError, TypeError, ValueError): continue
            if not feature or not 0 <= padj <= 1: continue
            feature_map[feature][accession] = {"direction":"positive" if fc>0 else "negative" if fc<0 else "zero","significant":padj<=fdr_threshold,"adjusted_p_value":padj}
    replication=[]
    for feature, datasets in sorted(feature_map.items()):
        sig=[(acc,row) for acc,row in datasets.items() if row["significant"] and row["direction"]!="zero"]
        if len(sig)>=2:
            replication.append({"feature":feature,"independent_dataset_count":len(sig),"datasets":sorted(a for a,_ in sig),
              "classification":"directionally_concordant_screen" if len({r["direction"] for _,r in sig})==1 else "directional_conflict"})
    gates={
      "literature_prior_art":{"status":"not_established","sources_with_identifiers":sum(bool(_s(x.get("doi")) or _s(x.get("pmid")) or _s(x.get("pmcid"))) for x in sources),"reason":"Retrieved papers/citation metadata are not an exhaustive claim-level prior-art search; novelty remains unproven."},
      "human_relevance":{"status":"human_sources_found" if human else "not_demonstrated","human_source_count":len(human),"reason":"Check cohort, tissue, age definition, phenotype, and sample provenance before interpretation."},
      "independent_evidence":{"status":"multiple_source_groups" if len(evidence_groups)>=2 else "insufficient_independence","independent_evidence_groups":len(evidence_groups),"evidence_records":len(evidence),"reason":"Provenance groups are proxies, not proof that cohorts or participants are independent."},
      "statistical_support":{"status":"DE_results_present" if de_analyses else "not_run","DE_analysis_count":len(de_analyses),"FDR_threshold":fdr_threshold,"replicated_feature_screens":replication,"reason":"Check design, covariates, sample overlap, effect sizes, and multiple-testing universe."},
      "biological_replication":{"status":"potential_replication_screen" if replication else "not_demonstrated","replicated_feature_count":len(replication),"reason":"Distinct accession IDs do not prove independent cohorts or comparable phenotypes."},
      "contradiction_review":{"status":"candidates_present" if contradictions else "none_recorded","candidate_count":len(contradictions),"unresolved_count":sum(_s(x.get("status")).casefold() not in {"resolved","rejected","closed"} for x in contradictions)},
      "dataset_interpretation":{"status":"descriptive_only" if dataset_analyses else "no_dataset_analysis","analysis_count":len(dataset_analyses),"reason":"Descriptive parsing is not differential expression, causal inference, or validated biological evidence."},
      "human_expert_review":{"status":"required","reason":"Automated checks cannot replace blinded independent domain-expert review."}}
    return {"audit_version":"1.0","run_id":_s(run.get("run_id")),"question":_s(run.get("question")),"run_status":_s(run.get("status")),
      "counts":{"sources":len(sources),"evidence":len(evidence),"claims":len(claims),"hypotheses":len(hypotheses),"human_sources":len(human),"DE_analyses":len(de_analyses),"dataset_analyses":len(dataset_analyses)},
      "gates":gates,"hypothesis_reviews":[{"hypothesis_id":_s(h.get("hypothesis_id")),"statement":_s(h.get("statement")),"supporting_evidence_count":len(h.get("supporting_evidence_ids") or []),"opposing_evidence_count":len(h.get("opposing_evidence_ids") or []),"status":"unverified_candidate","warning":"Inspect linked evidence and alternatives; audit does not upgrade hypothesis status."} for h in hypotheses],
      "overall_assessment":"screening_only_no_validated_discovery",
      "limitations":["Deterministic screening only; not exhaustive literature review or peer review.","Absence of evidence in this run does not prove a mechanism false.","Novelty, causality, and clinical relevance are not established by association or generated hypotheses.","A discovery requires independent, well-designed replication and expert review."]}

def render_markdown(report: dict[str, Any]) -> str:
    lines=["# ORACLE research quality audit","",f"- Run: {report.get('run_id') or 'unknown'}",f"- Question: {report.get('question') or 'not recorded'}",f"- Overall: **{report.get('overall_assessment')}**","","## Quality gates","","| Gate | Status | Detail |","|---|---|---|"]
    for name,gate in report.get("gates",{}).items(): lines.append(f"| {name.replace('_',' ')} | {gate.get('status')} | {gate.get('reason',gate.get('candidate_count',''))} |")
    lines += ["","## Hypotheses",""]
    for h in report.get("hypothesis_reviews",[]): lines.append(f"- **{h.get('statement')}** — {h.get('status')}; supporting: {h.get('supporting_evidence_count')}, opposing: {h.get('opposing_evidence_count')}.")
    lines += ["","This is a screening audit only; it does not validate a discovery, establish novelty, or prove causality.","","## Limitations",""]
    lines += ["- "+x for x in report.get("limitations",[])]
    return "\n".join(lines)+"\n"

def main(argv=None):
    p=argparse.ArgumentParser(description="Audit ORACLE research-run evidence quality.")
    p.add_argument("input"); p.add_argument("--json-output",default="artifacts/oracle_quality_audit.json")
    p.add_argument("--markdown-output",default="artifacts/oracle_quality_audit.md"); p.add_argument("--fdr",type=float,default=.05)
    a=p.parse_args(argv); report=audit_run(json.loads(Path(a.input).read_text(encoding="utf-8")),fdr_threshold=a.fdr)
    jp,mp=Path(a.json_output),Path(a.markdown_output); jp.parent.mkdir(parents=True,exist_ok=True); mp.parent.mkdir(parents=True,exist_ok=True)
    jp.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); mp.write_text(render_markdown(report),encoding="utf-8")
    print(json.dumps({"audit":str(jp),"markdown":str(mp),"overall_assessment":report["overall_assessment"],"gates":{k:v["status"] for k,v in report["gates"].items()}},indent=2))
if __name__=="__main__": main()
