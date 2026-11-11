import unittest
from oracle.quality_audit import audit_run, render_markdown

class QualityAuditTests(unittest.TestCase):
    def test_empty_run_never_claims_novelty_or_discovery(self):
        r=audit_run({"run":{"run_id":"r1","question":"longevity"}})
        self.assertEqual(r["overall_assessment"],"screening_only_no_validated_discovery")
        self.assertEqual(r["gates"]["literature_prior_art"]["status"],"not_established")
        self.assertEqual(r["gates"]["human_expert_review"]["status"],"required")
    def test_human_evidence_and_concordant_dataset_screen(self):
        run={"sources":[{"source_id":"s1","title":"Human ageing","organism":"Homo sapiens","dataset_accession":"GSE1"},{"source_id":"s2","title":"Human longevity","organism":"human","dataset_accession":"GSE2"}],
        "evidence":[{"source_id":"s1"},{"source_id":"s2"}],
        "differential_expression_analyses":[{"dataset_accession":"GSE1","results":[{"feature":"GENE1","log2_fold_change":1.2,"p_value_adjusted_bh":.01}]},{"dataset_accession":"GSE2","results":[{"feature":"GENE1","log2_fold_change":.8,"p_value_adjusted_bh":.02}]}],
        "hypotheses":[{"hypothesis_id":"h1","statement":"candidate","supporting_evidence_ids":["e1"]}]}
        r=audit_run({"run":run})
        self.assertEqual(r["gates"]["human_relevance"]["human_source_count"],2)
        self.assertEqual(r["gates"]["independent_evidence"]["independent_evidence_groups"],2)
        self.assertEqual(r["gates"]["biological_replication"]["status"],"potential_replication_screen")
        self.assertEqual(r["hypothesis_reviews"][0]["status"],"unverified_candidate")
    def test_opposite_directions_flag_conflict(self):
        r=audit_run({"differential_expression_analyses":[{"dataset_accession":"GSE1","results":[{"feature":"X","log2_fold_change":1,"p_value_adjusted_bh":.01}]},{"dataset_accession":"GSE2","results":[{"feature":"X","log2_fold_change":-1,"p_value_adjusted_bh":.01}]}]})
        self.assertEqual(r["gates"]["statistical_support"]["replicated_feature_screens"][0]["classification"],"directional_conflict")
    def test_invalid_fdr_rejected(self):
        with self.assertRaises(ValueError): audit_run({},fdr_threshold=1)
    def test_markdown_scope(self):
        self.assertIn("does not validate a discovery",render_markdown(audit_run({"run":{"run_id":"r"}})))
if __name__=="__main__": unittest.main()
