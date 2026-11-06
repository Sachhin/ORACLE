import importlib.util
import unittest

from oracle.pxd018408 import DDA_1X, DDA_2X, DIA_1X, DIA_2X, DDA_SAMPLES


class PXD018408DesignTests(unittest.TestCase):
    def test_published_design_has_eight_replicates_per_group_and_modality(self):
        self.assertEqual(len(DDA_1X), 8)
        self.assertEqual(len(DDA_2X), 8)
        self.assertEqual(len(DIA_1X), 8)
        self.assertEqual(len(DIA_2X), 8)
        self.assertEqual(len(set(DDA_1X + DDA_2X)), 16)
        self.assertEqual(len(set(DIA_1X + DIA_2X)), 16)

    def test_dda_and_dia_are_group_matched_not_falsely_one_to_one(self):
        self.assertEqual(set(DDA_SAMPLES), set(DDA_1X + DDA_2X))
        self.assertNotEqual(set(DDA_1X), set(DIA_1X))
        self.assertNotEqual(set(DDA_2X), set(DIA_2X))


if __name__ == "__main__":
    unittest.main()
