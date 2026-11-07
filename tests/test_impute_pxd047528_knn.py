import csv, tempfile, unittest
from pathlib import Path
from scripts.impute_pxd047528_knn import impute


class PXD047528KNNTests(unittest.TestCase):
    def test_imputes_missing_values_and_preserves_observed(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/"observed.tsv"; output=Path(d)/"imputed.tsv"
            with source.open("w",newline="") as f:
                w=csv.writer(f,delimiter="\t")
                w.writerow(["Sequence","s1","s2","s3"])
                for i in range(40):
                    a=float(i+1)
                    w.writerow([f"p{i}",a,a+2,"" if i==0 else a+4])
            report=impute(source,output,neighbors=2,min_overlap=10)
            self.assertEqual(report["imputed_cells"],1)
            self.assertTrue(report["observed_cells_preserved"])
            with output.open() as f:
                rows=list(csv.DictReader(f,delimiter="\t"))
            self.assertNotEqual(rows[0]["s3"],"")
            self.assertEqual(float(rows[1]["s1"]),2.0)

if __name__=="__main__":unittest.main()
