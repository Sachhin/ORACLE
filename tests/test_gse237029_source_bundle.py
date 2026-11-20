import gzip
import tempfile
import unittest
from pathlib import Path
from scripts.audit_gse237029_source_bundle import parse_soft

class GSE237029SoftTests(unittest.TestCase):
    def test_sample_accessions_titles_and_characteristics(self):
        content = """^SAMPLE = GSM7593228
!Sample_title = PBMC from old research participant1
!Sample_geo_accession = GSM7593228
!Sample_characteristics_ch1 = age: Old
!Sample_characteristics_ch1 = gender: Female
^SAMPLE = GSM7593233
!Sample_title = PBMC from middle-aged research participant1
!Sample_geo_accession = GSM7593233
!Sample_characteristics_ch1 = age: Middle-aged
!Sample_characteristics_ch1 = gender: Male
"""
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.soft.gz"
            with gzip.open(p,"wt") as f: f.write(content)
            rows=parse_soft(p)
        self.assertEqual([r["accession"] for r in rows],["GSM7593228","GSM7593233"])
        self.assertEqual(rows[0]["characteristics"],["age: Old","gender: Female"])
        self.assertEqual(rows[1]["title"],"PBMC from middle-aged research participant1")

if __name__=="__main__": unittest.main()
