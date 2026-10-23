"""Offline S3-fixture tests. Never connect to AWS or certify real file hashes."""
import copy
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import finalize_glue_warehouse_package as fp

ROOT = Path(__file__).resolve().parent.parent


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.change_after_read = None

    def add(self, uri, body):
        bucket, key = fp.split_s3(uri)
        self.objects[(bucket, key)] = (body, {"ETag": '"fixture-' + hashlib.md5(body).hexdigest() + '"',
                                            "ContentLength": len(body), "LastModified": "2026-10-23T15:20:00+00:00"})

    def add_json(self, uri, data):
        self.add(uri, json.dumps(data).encode())

    def get_object(self, Bucket, Key):
        body, meta = self.objects[(Bucket, Key)]
        result = {**meta, "Body": io.BytesIO(body)}
        if Key == self.change_after_read:
            self.objects[(Bucket, Key)][1]["ETag"] = '"changed"'
        return result

    def head_object(self, Bucket, Key):
        return dict(self.objects[(Bucket, Key)][1])

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return self

    def paginate(self, Bucket, Prefix):
        values = [{"Key": k, "Size": m["ContentLength"]} for (b, k), (_, m) in self.objects.items()
                  if b == Bucket and k.startswith(Prefix)]
        # Exercise pagination rather than assume one page.
        yield {"Contents": values[:10]}
        yield {"Contents": values[10:]}


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / "bundle"
        shutil.copytree(ROOT / "outputs/aws/glue-warehouse-bundle", self.bundle)
        self.report = fp.load(self.bundle / "evidence/validation_report.json")
        self.config = fp.load(self.bundle / "config.json")
        self.inventory = fp.load(self.bundle / "evidence/glue-batch-files.json")
        self.s3 = FakeS3()
        root = self.report["output_root"]
        self.s3.add_json(root + "_READY.json", {"batch_id": self.report["batch_id"],
                         "status": "PASS_WITH_KNOWN_ISSUES", "validation_report": self.report["control_root"] + "validation_report.json"})
        self.s3.add_json(self.report["control_root"] + "validation_report.json", self.report)
        for row in self.inventory:
            if row["Key"].endswith(".parquet"):
                # Deliberately synthetic small bodies, not real Parquet data.
                body = ("fixture:" + row["Key"]).encode()
                row["Size"] = len(body)
                self.s3.add("s3://" + self.config["bucket"] + "/" + row["Key"], body)
        self.config["inventory_digest"] = fp.digest(self.inventory)
        (self.bundle / "config.json").write_text(json.dumps(self.config), encoding="utf-8")
        (self.bundle / "evidence/glue-batch-files.json").write_text(json.dumps(self.inventory), encoding="utf-8")
        for name, info in self.report["tables"].items():
            self.s3.add(info["source_uri"], b"synthetic raw")
            _, meta = self.s3.objects[fp.split_s3(info["source_uri"])]
            meta.update(ETag=info["source_etag"], ContentLength=info["source_bytes"])
            prefix = fp.split_s3(info["parquet"])[1]
            entries = [{"url": "s3://" + self.config["bucket"] + "/" + row["Key"],
                        "mandatory": True, "meta": {"content_length": row["Size"]}}
                       for row in sorted(self.inventory, key=lambda x: x["Key"]) if row["Key"].startswith(prefix)]
            self.s3.add_json(root + "_manifests/" + name + ".json", {"entries": entries})

    def finish(self, name="ready"):
        return fp.finalize(self.bundle, self.root / name, self.s3, "006816724683")

    def test_complete_package_and_exact_file_hashes(self):
        package, archive = self.finish()
        self.assertTrue(archive.exists())
        self.assertEqual(len(package["tables"]), 7)
        self.assertEqual(len(package["money"]), 5)
        self.assertEqual(package["source_observed_at"], None)
        self.assertEqual(package["observed_at"], "2026-10-22T18:59:01.935624+00:00")
        self.assertNotEqual(package["observed_at"], package["processed_at"])
        for table in package["tables"]:
            self.assertEqual(len(table["parts"]), 4)
            content = []
            for part in table["parts"]:
                body, _ = self.s3.objects[fp.split_s3(part["url"])]
                self.assertEqual(part["sha256"], hashlib.sha256(body).hexdigest())
                content.append({k: part[k] for k in ("url", "content_length", "sha256")})
            self.assertEqual(table["content_set_sha256"], fp.digest(content))
        data = dict(package)
        expected_hash = data.pop("package_hash")
        self.assertEqual(expected_hash, fp.digest(data))
        run = (self.root / "ready/sql/05_run_batch.sql").read_text()
        self.assertEqual(run.count("INSERT INTO expected_inputs"), 7)
        self.assertEqual(run.count("INSERT INTO expected_money"), 5)
        self.assertEqual(run.count("CALL etl.load_batch("), 1)
        self.assertIn(expected_hash, run)
        self.assertIn("CALL etl.assert_glue_validation_database();", run)
        self.assertNotIn("DROP TABLE", run)
        self.assertTrue((self.root / "ready/sql/07_test_no_op.sql").exists())

    def test_repeated_finalization_is_deterministic(self):
        first, _ = self.finish("first")
        second, _ = self.finish("second")
        self.assertEqual(first, second)

    def test_reject_wrong_account(self):
        with self.assertRaisesRegex(ValueError, "Wrong AWS account"):
            fp.finalize(self.bundle, self.root / "ready", self.s3, "000000000000")
        self.assertFalse((self.root / "ready").exists())

    def test_reject_changed_report(self):
        changed = copy.deepcopy(self.report)
        changed["status"] = "FAIL"
        self.s3.add_json(self.report["control_root"] + "validation_report.json", changed)
        with self.assertRaisesRegex(ValueError, "report has changed"):
            self.finish()

    def test_reject_missing_part(self):
        key = next(k for k in self.s3.objects if k[1].endswith(".parquet"))
        del self.s3.objects[key]
        with self.assertRaisesRegex(ValueError, "listing differs"):
            self.finish()

    def test_reject_wrong_manifest(self):
        self.s3.add_json(self.report["output_root"] + "_manifests/distribution_centers.json", {"entries": []})
        with self.assertRaisesRegex(ValueError, "manifest differs"):
            self.finish()
        self.assertFalse((self.root / "ready").exists())

    def test_reject_change_while_hashing(self):
        self.s3.change_after_read = next(k for b, k in self.s3.objects if k.endswith(".parquet"))
        with self.assertRaisesRegex(ValueError, "changed during verification"):
            self.finish()

    def test_reject_modified_raw_source(self):
        key = fp.split_s3(self.report["tables"]["distribution_centers"]["source_uri"])
        self.s3.objects[key][1]["ETag"] = '"new-raw"'
        with self.assertRaisesRegex(ValueError, "Raw CSV metadata changed"):
            self.finish()

    def test_do_not_overwrite_result(self):
        (self.root / "ready").mkdir()
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.finish()

    def test_loader_guard_and_ddl_separation(self):
        sql = (self.bundle / "sql/04_install_procedures.sql").read_text()
        self.assertNotIn("CREATE SCHEMA", sql)
        self.assertLess(sql.index("CALL etl.assert_glue_validation_database();"), sql.index("LOCK TABLE"))
        handler = sql[sql.index("EXCEPTION WHEN OTHERS"):]
        self.assertIn("IF current_database() = 'thelook_glue_validation' THEN", handler)


if __name__ == "__main__":
    unittest.main()
