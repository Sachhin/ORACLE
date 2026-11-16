import tempfile
import unittest
from pathlib import Path

from scripts.build_gse32493_sra_counts import parse_sam


class GSE32493SraCountTests(unittest.TestCase):
    def test_unique_alignments_counted_and_multimappers_excluded(self):
        sam = (
            "@HD\tVN:1.0\tSO:unsorted\n"
            "read1\t0\thsa-miR-1\t1\t255\t22M\t*\t0\t0\tACGT\tIIII\n"
            "read2\t0\thsa-miR-2\t1\t255\t22M\t*\t0\t0\tACGT\tIIII\n"
            "read2\t256\thsa-miR-3\t1\t255\t22M\t*\t0\t0\tACGT\tIIII\n"
            "read3\t4\t*\t0\t0\t*\t*\t0\t0\tACGT\tIIII\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.sam"
            path.write_text(sam, encoding="utf-8")
            counts, stats = parse_sam(path)
        self.assertEqual(counts["hsa-miR-1"], 1)
        self.assertEqual(counts["hsa-miR-2"], 0)
        self.assertEqual(counts["hsa-miR-3"], 0)
        self.assertEqual(stats["mapped_reads_with_at_least_one_best_alignment"], 2)
        self.assertEqual(stats["uniquely_mapped_reads_counted"], 1)
        self.assertEqual(stats["multi_mapped_reads_excluded"], 1)

    def test_multiple_alignments_to_same_reference_are_one_read(self):
        sam = (
            "read1\t0\thsa-miR-1\t1\t255\t22M\t*\t0\t0\tACGT\tIIII\n"
            "read1\t256\thsa-miR-1\t2\t255\t22M\t*\t0\t0\tACGT\tIIII\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.sam"
            path.write_text(sam, encoding="utf-8")
            counts, stats = parse_sam(path)
        self.assertEqual(counts["hsa-miR-1"], 1)
        self.assertEqual(stats["multi_mapped_reads_excluded"], 0)


if __name__ == "__main__":
    unittest.main()
