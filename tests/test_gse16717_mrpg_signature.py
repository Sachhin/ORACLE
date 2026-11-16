import unittest

import numpy as np

from scripts.analyze_gse16717_mrpg_signature import (
    C_RPG,
    M_RPG,
    build_complete_panel_scores,
)


class GSE16717PanelScoreTests(unittest.TestCase):
    def test_complete_mrpg_panel_is_scored(self):
        values = {gene: np.array([1.0, 2.0, 3.0]) for gene in M_RPG}
        scores, status = build_complete_panel_scores(values)
        self.assertIn("mRPG_8", scores)
        self.assertEqual(status["mRPG_8"]["status"], "COMPLETE")
        self.assertEqual(status["mRPG_8"]["present_genes"], 8)

    def test_incomplete_crpg_panel_is_not_scored(self):
        values = {gene: np.array([1.0, 2.0, 3.0]) for gene in C_RPG if gene != "RPS6"}
        scores, status = build_complete_panel_scores(values)
        self.assertNotIn("cRPG_7", scores)
        self.assertEqual(status["cRPG_7"]["status"], "INCOMPLETE_NO_COMPOSITE_SCORE")
        self.assertEqual(status["cRPG_7"]["missing_genes"], ["RPS6"])


if __name__ == "__main__":
    unittest.main()
