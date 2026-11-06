import json, tempfile, unittest
from pathlib import Path
from oracle.answer_benchmark import DIMENSIONS
from oracle.model_comparison import evaluate_paired_answers, run_paired_answer_benchmark

def scores(value):
    return {key:value for key in DIMENSIONS}

class PairedModelComparisonTests(unittest.TestCase):
    def case(self):
        return {"case_id":"Q1","source_packet_sha256":"a"*64,
                "prompt_version":"p1","model_version":"candidate-v1",
                "reviewer_ids":["reviewer-a","reviewer-b"],
                "baseline_scores":scores(3),"candidate_scores":scores(4)}
    def test_paired_delta_and_bootstrap_are_reproducible(self):
        report=evaluate_paired_answers([self.case()],bootstrap_samples=200,seed=9)
        self.assertEqual(report["dimensions"]["factual_accuracy"]["mean_paired_delta_candidate_minus_baseline"],1)
        self.assertEqual(report,evaluate_paired_answers([self.case()],bootstrap_samples=200,seed=9))
    def test_requires_two_reviewers(self):
        row=self.case(); row["reviewer_ids"]=["one"]
        with self.assertRaisesRegex(ValueError,"two distinct"):
            evaluate_paired_answers([row])
    def test_requires_same_source_packet_provenance(self):
        row=self.case(); row["source_packet_sha256"]="bad"
        with self.assertRaisesRegex(ValueError,"SHA-256"):
            evaluate_paired_answers([row])
    def test_file_runner_hashes_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"paired.json"
            path.write_text(json.dumps({"benchmark_id":"paired-v1","cases":[self.case()]}))
            report=run_paired_answer_benchmark(path,bootstrap_samples=200)
            self.assertEqual(len(report["benchmark_sha256"]),64)

if __name__ == "__main__": unittest.main()
