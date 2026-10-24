import tempfile
import unittest
from pathlib import Path

from _support import ROOT
from clientes_confiables.customer_quality import (
    StructureError, evaluate_row, read_source, selected_versions, summarize, valid_email,
)


def row(**overrides):
    return dict(customer_id="TEST-1", name="Fixture", age="18", country="PE",
                email="fixture@example.test", **{}) | overrides


def evaluate(**overrides):
    return evaluate_row(row(**overrides), 1, {"PE", "CL"}, 18)


class QualityTests(unittest.TestCase):
    def test_normalization_preserves_original(self):
        result = evaluate(customer_id=" TEST-1 ", name=" Fixture  Name ", age=" 18 ", country=" pe ")
        self.assertEqual(result.normalized["name"], "Fixture  Name")
        self.assertEqual(result.normalized["country"], "PE")
        self.assertEqual(result.original["country"], " pe ")
        self.assertTrue(result.is_contactable)

    def test_ages(self):
        for text in ("0", "17", "18", "2147483647", "00018", "0" * 5000):
            with self.subTest(age=text[:30]):
                result = evaluate(age=text)
                self.assertEqual(result.reasons, [])
                self.assertEqual(result.is_adult, int(text.lstrip("0") or "0") >= 18)
        for text in ("-1", "18.0", "abc", "2147483648", "+18", "１８", "9" * 5000):
            with self.subTest(age=text[:30]):
                self.assertEqual(evaluate(age=text).reasons, ["AGE_INVALID"])
        self.assertEqual(evaluate(age=" ").reasons, ["AGE_MISSING"])

    def test_all_mandatory_reasons_once(self):
        result = evaluate(customer_id=" ", name=" ", age="", country="")
        self.assertEqual(result.reasons, ["CUSTOMER_ID_MISSING", "NAME_MISSING", "AGE_MISSING", "COUNTRY_MISSING"])
        self.assertEqual(evaluate(country="ZZ").reasons, ["COUNTRY_UNKNOWN"])
        self.assertEqual(summarize([result], "hash", 30)["rejected_rows"], 1)

    def test_email_format(self):
        for email in ("a@example.test", "first.last+tag@sub.example.test", "a@a.b"):
            self.assertTrue(valid_email(email), email)
        for email in ("", "a@mail", "a@@mail.com", "@mail.com", "a@.com", "a@x..com",
                      "a b@mail.com", ".a@mail.com", "a..b@mail.com", "a@-x.com", "a@x-.com"):
            self.assertFalse(valid_email(email), email)
        for email in ("", "bad"):
            result = evaluate(email=email)
            self.assertFalse(result.is_contactable)
            self.assertEqual(result.reasons, [])
            self.assertTrue(result.warnings)

    def test_minor_is_valid_not_contactable(self):
        result = evaluate(age="17")
        self.assertEqual(result.reasons, [])
        self.assertTrue(result.has_valid_email)
        self.assertFalse(result.is_contactable)

    def test_last_invalid_version_does_not_fallback(self):
        first = evaluate()
        last = evaluate_row(row(age="bad"), 2, {"PE"}, 18)
        self.assertEqual(selected_versions([first, last]), [last])
        report = summarize([first, last], "hash", 100)
        self.assertEqual(report["valid_selected"], 0)
        self.assertEqual(report["superseded_rows"], 1)
        self.assertEqual(report["rejected_rows"], 1)

    def test_unknown_ids_are_not_customers(self):
        result = summarize([evaluate(customer_id=""), evaluate(customer_id=" ")], "hash", 100)
        self.assertEqual(result["unique_customers"], 0)
        self.assertEqual(result["superseded_rows"], 0)
        self.assertIsNone(result["simulated_contactable_pct"])

    def test_rejected_adult_stays_in_denominator(self):
        result = summarize([evaluate(name="")], "hash", 100)
        self.assertEqual(result["adult_denominator"], 1)
        self.assertEqual(result["contactable_adults"], 0)


class StructureTests(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            path.write_bytes(text.encode("utf-8"))
            return read_source(path)

    def test_valid_bom_quoted_newline_and_crlf(self):
        digest, rows = self.parse('\ufeffcustomer_id,name,age,country,email\r\nTEST-1,"Two\nLines",18,PE,a@example.test\r\n')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Two\nLines")
        self.assertEqual(len(digest), 64)

    def test_reject_malformed_sources(self):
        header = "customer_id,name,age,country,email\n"
        cases = ["", header, header + "\n", header + "TEST-1,Fixture,18,PE\n",
                 header + "TEST-1,Fixture,18,PE,a@example.test,extra\n",
                 header + 'TEST-1,"open,18,PE,a@example.test',
                 "customer_id,name,age,country\n", "customer_id,name,age,country,email,extra\n",
                 "name,customer_id,age,country,email\n", "customer_id,name,age,country,name\n"]
        for text in cases:
            with self.subTest(source=text[:20]), self.assertRaises(StructureError):
                self.parse(text)

    def test_same_bytes_same_snapshot(self):
        text = "customer_id,name,age,country,email\nTEST-1,Fixture,18,PE,a@example.test\n"
        self.assertEqual(self.parse(text)[0], self.parse(text)[0])
