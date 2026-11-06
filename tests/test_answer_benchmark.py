"""Human-scored answer benchmark validation and persistence tests."""
import tempfile
import unittest
from pathlib import Path

from oracle.answer_benchmark import DIMENSIONS, summarize_answer_reviews, validate_answer_review
from oracle.models import ResearchRun, SourceRecord
from oracle.storage import ResearchStore


class AnswerBenchmarkTests(unittest.TestCase):
    def test_rubric_requires_all_five_bounded_integer_scores(self):
        scores = {name: 4 for name in DIMENSIONS}
        self.assertEqual(validate_answer_review(scores), scores)
        with self.assertRaises(ValueError):
            validate_answer_review({"factual_accuracy": 5})
        invalid = dict(scores, reasoning_quality=6)
        with self.assertRaises(ValueError):
            validate_answer_review(invalid)

    def test_human_reviews_persist_with_validated_source_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(Path(tmp) / "oracle.sqlite3")
            run = ResearchRun("Answer quality review")
            run.sources.append(SourceRecord("Primary paper", source_id="src-primary"))
            store.save_run(run)
            review = store.record_answer_quality_review(
                run.run_id, "A carefully qualified scientific answer.",
                "Reviewer A", {name: 4 for name in DIMENSIONS},
                "Checked key statements against the primary source.",
                ["src-primary"],
            )
            loaded = store.list_answer_quality_reviews(run.run_id)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["review_id"], review["review_id"])
            self.assertEqual(loaded[0]["source_ids"], ["src-primary"])
            with self.assertRaisesRegex(ValueError, "source ID absent"):
                store.record_answer_quality_review(
                    run.run_id, "Answer", "Reviewer B",
                    {name: 3 for name in DIMENSIONS}, "Review note", ["src-fake"],
                )

    def test_review_summary_averages_human_scores_and_states_limits(self):
        reviews = [
            {"scores": {name: 4 for name in DIMENSIONS}},
            {"scores": {name: 2 for name in DIMENSIONS}},
        ]
        summary = summarize_answer_reviews(reviews)
        self.assertEqual(summary["review_count"], 2)
        self.assertEqual(summary["overall_mean"], 3.0)
        self.assertIn("subjective reviewer judgments", summary["limitations"])


if __name__ == "__main__":
    unittest.main()
