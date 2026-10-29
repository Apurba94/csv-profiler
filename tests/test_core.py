import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from csv_profiler.cli import main
from csv_profiler.core import infer_type, profile, profile_column, read_table

CSV = """id,age,weight,site,visit_date,treated,notes
1,34,70.5,North,2026-01-03,yes,ok
2,45,NA,north,2026-01-10,no,
3,29,80.1,South,2026-02-01,yes,late
4,51,65.0,South,2026-02-15,no,ok
4,51,65.0,South,2026-02-15,no,ok
"""


class TypeTests(unittest.TestCase):
    def test_infer(self):
        self.assertEqual(infer_type(["1", "2", "NA"]), "integer")
        self.assertEqual(infer_type(["1.5", "2", "-3e2"]), "float")
        self.assertEqual(infer_type(["2026-01-01", "2026-02-03"]), "date")
        self.assertEqual(infer_type(["yes", "no", "yes"]), "boolean")
        self.assertEqual(infer_type(["a", "b", "a", "a"]), "categorical")
        self.assertEqual(infer_type(["", "NA"]), "empty")


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.header, self.rows = read_table(CSV)
        self.rep = profile(self.header, self.rows)
        self.p = {p["name"]: p for p in self.rep["profiles"]}

    def test_dataset_level(self):
        self.assertEqual((self.rep["rows"], self.rep["columns"], self.rep["duplicate_rows"]), (5, 7, 1))
        self.assertEqual(self.rep["complete_rows"], 4)

    def test_numeric_stats(self):
        a = self.p["age"]
        self.assertEqual((a["min"], a["median"], a["max"]), (29.0, 45.0, 51.0))
        self.assertAlmostEqual(a["mean"], 42.0)
        self.assertEqual(self.p["weight"]["missing"], 1)

    def test_categorical_warnings(self):
        site = self.p["site"]
        self.assertEqual(site["type"], "categorical")
        self.assertIn(["North", "north"], site["case_variants"])
        self.assertIn("inconsistent capitalization/spacing in categories", site["warnings"])

    def test_constant_and_mixed_columns(self):
        self.assertIn("constant column", profile_column("c", ["x", "x", "x"])["warnings"])
        mixed = profile_column("m", ["1", "2", "3", "4", "five"])
        self.assertIn("mostly numeric with 1 non-numeric value(s)", mixed["warnings"])

    def test_cli_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "data.csv")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(CSV)
            with redirect_stdout(io.StringIO()) as buf:
                main([p])
            out = buf.getvalue()
            self.assertIn("| age | integer | 0 (0.0%) | 4 |", out)
            self.assertIn("5 rows x 7 columns", out)


if __name__ == "__main__":
    unittest.main()
