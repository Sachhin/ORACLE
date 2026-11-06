"""Domain-specific protocol template tests."""
import unittest

from oracle.models import ExperimentStatus, Hypothesis, ResearchRun
from oracle.protocols import ExperimentProtocolBuilder


class ExperimentProtocolTests(unittest.TestCase):
    def test_each_domain_builds_a_proposed_reproducibility_protocol(self):
        builder = ExperimentProtocolBuilder()
        for domain in builder.domains():
            run = ResearchRun("Test a scientific mechanism")
            experiment = builder.build(run, domain)
            self.assertEqual(experiment.status, ExperimentStatus.PROPOSED)
            self.assertGreaterEqual(len(experiment.protocol), 8)
            self.assertIn("checksums", " ".join(experiment.protocol).lower())
            self.assertIn("Template only", experiment.limitations)
            self.assertEqual(run.experiments, [experiment])

    def test_protocol_uses_hypothesis_predictions_without_promoting_it(self):
        run = ResearchRun("Original question")
        hypothesis = Hypothesis(
            "A specific mechanism explains the phenotype.",
            "Provisional rationale.",
            predictions=["The primary readout changes after perturbation."],
        )
        run.hypotheses.append(hypothesis)
        experiment = ExperimentProtocolBuilder().build(
            run, "plant_biology", hypothesis.hypothesis_id,
        )
        self.assertIn(hypothesis.statement, experiment.question)
        self.assertEqual(experiment.predictions, hypothesis.predictions)
        self.assertEqual(hypothesis.status.value, "proposed")
        self.assertEqual(experiment.status, ExperimentStatus.PROPOSED)

    def test_unknown_domain_or_hypothesis_is_rejected(self):
        run = ResearchRun("Test")
        builder = ExperimentProtocolBuilder()
        with self.assertRaises(ValueError):
            builder.build(run, "unknown_domain")
        with self.assertRaises(ValueError):
            builder.build(run, "cell_biology", "missing-hypothesis")


if __name__ == "__main__":
    unittest.main()
