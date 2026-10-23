"""Local conversion tests; these do not substitute for a Glue/Spark runtime run."""
import csv
import json
import unittest
from decimal import Decimal
from pathlib import Path

import glue_raw_to_curated as job

ROOT = Path(__file__).resolve().parent.parent


class GlueConversionTests(unittest.TestCase):
    def convert(self, value, kind, name="value", nullable=False):
        return job.convert_value(value, {"name": name, "type": kind, "nullable": nullable})

    def test_embedded_contracts_match_project(self):
        self.assertEqual(job.SCHEMA, json.loads((ROOT / "code/curated_schema.json").read_text(encoding="utf-8")))
        self.assertEqual(job.BASELINE, json.loads((ROOT / "code/dq_known_issues_baseline.json").read_text(encoding="utf-8")))

    def test_large_integer_exactness_and_range(self):
        self.assertEqual(self.convert("9007199254740993.0", "BIGINT", "id"), (9007199254740993, None))
        for value in ["9223372036854775808", "0", "-1", "1.5", "1e2"]:
            self.assertIsNotNone(self.convert(value, "BIGINT", "id")[1])
        self.assertIsNotNone(self.convert("32768", "SMALLINT")[1])

    def test_money_round_half_up_and_invalid_values(self):
        self.assertEqual(self.convert("1.0000005", "DECIMAL(18,6)")[0], Decimal("1.000001"))
        self.assertEqual(self.convert("-1.0000005", "DECIMAL(18,6)")[0], Decimal("-1.000001"))
        for value in ["NaN", "Infinity", "1000000000000", "999999999999.9999999"]:
            self.assertIsNotNone(self.convert(value, "DECIMAL(18,6)")[1])

    def test_blank_nullable_and_required(self):
        for value in [None, "", " \t "]:
            self.assertEqual(self.convert(value, "BIGINT", nullable=True), (None, None))
            self.assertIsNotNone(self.convert(value, "BIGINT")[1])

    def test_strings_preserve_spacing_utf8_and_null_literal(self):
        self.assertEqual(self.convert(" NULL ", "VARCHAR(20)"), (" NULL ", None))
        self.assertIsNotNone(self.convert("ก" * 7, "VARCHAR(20)")[1])
        self.assertEqual(self.convert("  Alice  ", "VARCHAR(20)"), ("  Alice  ", None))

    def test_finite_coordinate_ranges(self):
        for value in ["NaN", "inf", "91", "-91"]:
            self.assertIsNotNone(self.convert(value, "DOUBLE PRECISION", "latitude")[1])
        self.assertEqual(self.convert("-180", "DOUBLE PRECISION", "longitude"), (-180.0, None))

    def test_timezone_and_timestamp_precision(self):
        value, error = self.convert("2024-01-01T07:00:00.123456+07:00", "TIMESTAMPTZ")
        self.assertIsNone(error)
        self.assertEqual(value.isoformat(), "2024-01-01T00:00:00.123456+00:00")
        for value in ["2024-01-01", "2024-01-01T00:00:00", "2024-01-01T00:00:00.123456789Z"]:
            self.assertIsNotNone(self.convert(value, "TIMESTAMPTZ")[1])
        self.assertIsNone(self.convert("2024-01-01T00:00:00.123456000Z", "TIMESTAMPTZ")[1])

    def test_city_flag_does_not_replace_raw_city(self):
        spec = {"columns": [{"name": "city", "type": "VARCHAR(256)", "nullable": False}]}
        data, reasons, _ = job.convert_record([" NULL "], spec, "users")
        self.assertEqual(reasons, [])
        self.assertEqual(data["city"], " NULL ")
        self.assertIsNone(data["city_clean"])
        self.assertTrue(data["city_missing_token"])

    def test_item_date_flags_preserve_nulls(self):
        spec = {"columns": [{"name": name, "type": "TIMESTAMPTZ", "nullable": nullable}
                            for name, nullable in [("created_at", False), ("shipped_at", True)]]}
        data, reasons, _ = job.convert_record(["2024-01-02T00:00:00Z", ""], spec, "order_items")
        self.assertEqual(reasons, [])
        self.assertFalse(data["item_dates_comparable"])
        self.assertIsNone(data["item_shipped_before_created"])
        data, reasons, _ = job.convert_record(["2024-01-02T00:00:00Z", "2024-01-01T00:00:00Z"], spec, "order_items")
        self.assertEqual(reasons, [])
        self.assertTrue(data["item_shipped_before_created"])

    def test_exact_money_partition_reconciliation(self):
        a = list(job.money_partition([([("cost", "1.0000005", "1.000001")],)]))
        b = list(job.money_partition([([("cost", "2.0000004", "2.000000")],)]))
        result = job.combine_money(a + b)["cost"]
        self.assertEqual(result["source_accepted_sum"], Decimal("3.0000009"))
        self.assertEqual(result["expected_curated_sum"], Decimal("3.000001"))
        self.assertEqual(result["rounding_delta"], Decimal("0.0000001"))
        self.assertEqual(result["rounded_rows"], 2)

    def test_first_thousand_rows_of_each_local_csv(self):
        for name, spec in job.SCHEMA["tables"].items():
            with self.subTest(table=name):
                with (ROOT / "dataset" / (name + ".csv")).open(encoding="utf-8-sig", newline="") as stream:
                    reader = csv.reader(stream)
                    self.assertEqual(next(reader), [c["name"] for c in spec["columns"]])
                    for index, values in enumerate(reader):
                        if index >= 1000:
                            break
                        self.assertEqual(len(values), len(spec["columns"]))
                        _, reasons, _ = job.convert_record(values, spec, name)
                        self.assertEqual(reasons, [], f"{name} record {index + 2}: {reasons}")


if __name__ == "__main__":
    unittest.main()
