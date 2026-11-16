import importlib.util
import unittest


class GSE16717PanelScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec("numpy") is None:
            raise unittest.SkipTest("numpy is installed by the dedicated GSE16717 workflow")
        import numpy as np
        from scripts.analyze_gse16717_mrpg_signature import (
            C_RPG,
            M_RPG,
            build_complete_panel_scores,
        )
        cls.np = np
        cls.C_RPG = C_RPG
        cls.M_RPG = M_RPG
        cls.build_complete_panel_scores = staticmethod(build_complete_panel_scores)

    def test_complete_mrpg_panel_is_scored(self):
        values = {gene: self.np.array([1.0, 2.0, 3.0]) for gene in self.M_RPG}
        scores, status = self.build_complete_panel_scores(values)
        self.assertIn("mRPG_8", scores)
        self.assertEqual(status["mRPG_8"]["status"], "COMPLETE")
        self.assertEqual(status["mRPG_8"]["present_genes"], 8)

    def test_incomplete_crpg_panel_is_not_scored(self):
        values = {gene: self.np.array([1.0, 2.0, 3.0]) for gene in self.C_RPG if gene != "RPS6"}
        scores, status = self.build_complete_panel_scores(values)
        self.assertNotIn("cRPG_7", scores)
        self.assertEqual(status["cRPG_7"]["status"], "INCOMPLETE_NO_COMPOSITE_SCORE")
        self.assertEqual(status["cRPG_7"]["missing_genes"], ["RPS6"])


if __name__ == "__main__":
    unittest.main()
