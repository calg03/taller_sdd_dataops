import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _support import ROOT, FIXTURES
from clientes_confiables.customer_quality import validate_source
from clientes_confiables.project_config import load_config


class SourceTests(unittest.TestCase):
    def validate(self, source):
        config = load_config()
        return validate_source(source, ROOT / config["reference"], config)

    def test_workshop_expected_counts(self):
        result = self.validate(ROOT / "data/source/customers.csv")
        expected = dict(input_rows=21, rejected_rows=5, unique_customers=20, superseded_rows=1,
                        valid_selected=15, valid_minors=2, valid_adults=13,
                        adult_denominator=16, contactable_adults=10,
                        simulated_contactable_pct=62.5, status="SUCCESS")
        for name, value in expected.items():
            self.assertEqual(result[name], value, name)
        self.assertAlmostEqual(result["rejection_pct"], 100 * 5 / 21)
        self.assertEqual(result["reason_counts"], {"NAME_MISSING": 2, "AGE_MISSING": 1,
                                                "AGE_INVALID": 1, "COUNTRY_MISSING": 1})

    def test_boundary_threshold_fixtures(self):
        self.assertEqual(self.validate(FIXTURES / "exactly_30.csv")["status"], "SUCCESS")
        self.assertEqual(self.validate(FIXTURES / "above_30.csv")["status"], "FAILED")
        self.assertEqual(self.validate(FIXTURES / "valid.csv")["rejected_rows"], 0)

    def test_cli_status_and_privacy(self):
        for filename, code in (("valid.csv", 0), ("exactly_30.csv", 0),
                               ("above_30.csv", 1), ("invalid_header.csv", 1)):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "result.json"
                process = subprocess.run([sys.executable, str(ROOT / "scripts/validate_source.py"),
                                          "--source", str(FIXTURES / filename), "--report", str(path)],
                                         capture_output=True, text=True)
                self.assertEqual(process.returncode, code, process.stderr)
                self.assertNotIn("fixture@example.test", process.stdout + process.stderr)
                self.assertNotIn("TEST-", process.stdout + process.stderr)
                result = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("run_id", result)
                self.assertNotIn("original", result)
