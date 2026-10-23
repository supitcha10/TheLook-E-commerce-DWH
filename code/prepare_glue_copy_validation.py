"""Build manifests and an isolated Redshift COPY test from a saved S3 listing.

Reads local evidence only. Does not access AWS or claim Parquet content hashes.
"""
import argparse
import json
import re
import shutil
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
DATABASE = "thelook_glue_validation"
ROLE = "arn:aws:iam::006816724683:role/LabRole"


def prepare(report_path, inventory_path, output):
    report = json.loads(Path(report_path).read_text(encoding="utf-8-sig"))
    inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8-sig"))
    schema = json.loads((ROOT / "code/curated_schema.json").read_text(encoding="utf-8"))
    batch = report["batch_id"]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", batch):
        raise ValueError("Invalid batch ID")
    if (report["status"] != "PASS_WITH_KNOWN_ISSUES" or not report["checks"]
            or any(c["status"] != "PASS" for c in report["checks"])
            or len(report["known_issues"]) != 3
            or any(c["status"] != "KNOWN_ISSUE" for c in report["known_issues"])
            or set(report["tables"]) != set(schema["tables"])):
        raise ValueError("Unapproved/incomplete report")
    root = urlsplit(report["output_root"])
    if root.scheme != "s3" or root.netloc != "thelook-dwh-20241022" or root.path != f"/thelook/curated/{batch}/":
        raise ValueError("Unexpected output prefix")
    prefix = root.path.lstrip("/")
    keys = [item["Key"] for item in inventory]
    if len(set(keys)) != len(keys) or prefix + "_READY.json" not in keys:
        raise ValueError("Duplicate objects or missing READY marker in listing")
    files = {name: [] for name in schema["tables"]}
    for item in inventory:
        key, size = item["Key"], item["Size"]
        if not key.startswith(prefix) or not isinstance(size, int) or size < 0:
            raise ValueError("Invalid listing entry")
        relative = key[len(prefix):]
        if relative == "_READY.json" or relative.endswith("/_SUCCESS"):
            continue
        table, sep, filename = relative.partition("/")
        if table not in files or not sep or not re.fullmatch(r"part-[A-Za-z0-9_-]+\.snappy\.parquet", filename) or size <= 0:
            raise ValueError("Unexpected object in batch: " + relative)
        files[table].append({"url": "s3://" + root.netloc + "/" + key,
                             "mandatory": True, "meta": {"content_length": size}})
    for name, entries in files.items():
        info = report["tables"][name]
        if (not entries or info["quarantined_rows"] != 0 or info["raw_rows"] != info["curated_rows"]
                or info["parquet"] != report["output_root"] + name + "/"):
            raise ValueError("Invalid table evidence: " + name)
        for metrics in info["money"].values():
            if Decimal(metrics["expected_curated_sum"]) != Decimal(metrics["readback_sum"]):
                raise ValueError("Money mismatch")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    manifests = output / "manifests"
    manifests.mkdir()
    for name, entries in files.items():
        entries.sort(key=lambda item: item["url"])
        (manifests / (name + ".json")).write_text(json.dumps({"entries": entries}, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(report_path, output / "validation_report.json")
    shutil.copyfile(inventory_path, output / "glue-batch-files.json")
    (output / "01_create_database.sql").write_text(
        "-- Run once on the existing cluster, with autocommit ON. No new cluster.\n"
        f"CREATE DATABASE {DATABASE};\n"
        f"-- Then reconnect Query Editor to {DATABASE}, not dev.\n", encoding="utf-8")
    ddl = (ROOT / "code/sql/01_staging.sql").read_text(encoding="utf-8")
    ddl = ddl.replace("CREATE SCHEMA IF NOT EXISTS stg;", "CREATE SCHEMA IF NOT EXISTS glue_copy_check;")
    ddl = ddl.replace("stg.", "glue_copy_check.")
    (output / "02_setup_validation_tables.sql").write_text(
        f"-- Connect to {DATABASE}. Run CREATE SCHEMA separately first, then the CREATE TABLE statements.\n"
        "-- Autocommit ON. Stop on any error; no DROP or data deletion is performed.\n" + ddl, encoding="utf-8")
    body = [f"IF current_database() <> '{DATABASE}' THEN",
            "    RAISE EXCEPTION 'Connect to thelook_glue_validation before CALL';", "END IF;",
            "-- Schema/tables must already be created and committed before CALL.",
            "-- Atomic procedure: a COPY/assertion failure rolls back inserted data."]
    for name in report["tables"]:
        body += [f"IF EXISTS (SELECT 1 FROM glue_copy_check.{name}) THEN",
                 f"RAISE EXCEPTION '{name}: test table must be empty; do not append another copy'; END IF;"]
    for name, info in report["tables"].items():
        table = "glue_copy_check." + name
        body += [f"COPY {table} FROM '{report['output_root']}_manifests/{name}.json'",
                 f"IAM_ROLE '{ROLE}' MANIFEST FORMAT AS PARQUET;",
                 f"SELECT COUNT(*) INTO v_count FROM {table};",
                 f"IF v_count <> {int(info['curated_rows'])} THEN RAISE EXCEPTION '{name}: row count mismatch'; END IF;"]
        pk = schema["tables"][name]["primary_key"]
        body += [f"IF EXISTS (SELECT {pk} FROM {table} GROUP BY {pk} HAVING {pk} IS NULL OR COUNT(*) > 1) THEN",
                 f"RAISE EXCEPTION '{name}: invalid primary key'; END IF;"]
        for column, metrics in info["money"].items():
            total = format(Decimal(metrics["readback_sum"]), "f")
            body += [f"SELECT SUM({column}) INTO v_total FROM {table};",
                     f"IF v_total IS NULL OR v_total <> {total}::DECIMAL(38,6) THEN",
                     f"RAISE EXCEPTION '{name}.{column}: amount mismatch'; END IF;"]
    body += ["RAISE INFO 'GLUE_PARQUET_COPY_PASSED: seven counts, primary keys and five money totals';"]
    sql = ["-- This tests Spark Parquet -> Redshift COPY only, not a warehouse publication.",
           f"-- Connect to {DATABASE}. Run the CREATE PROCEDURE, then CALL with autocommit ON.",
           "-- Run 02_setup_validation_tables.sql first. Do not wrap CALL in BEGIN.",
           "-- Successful CALL is one-time; rerunning rejects populated test tables.",
           "CREATE OR REPLACE PROCEDURE public.validate_glue_copy()",
           "AS $$", "DECLARE v_count BIGINT; v_total DECIMAL(38,6);", "BEGIN", *body,
           "END;", "$$ LANGUAGE plpgsql;", "", "CALL public.validate_glue_copy();"]
    counts = [f"SELECT '{name}' AS table_name, COUNT(*) AS actual_rows, {info['curated_rows']}::BIGINT AS expected_rows FROM glue_copy_check.{name}"
              for name, info in report["tables"].items()]
    sql += ["", "\nUNION ALL\n".join(counts) + "\nORDER BY table_name;"]
    (output / "02_validate_parquet_copy.sql").write_text("\n".join(sql) + "\n", encoding="utf-8")
    summary = {"batch_id": batch, "table_files": {n: len(v) for n, v in files.items()},
               "parquet_files": sum(len(v) for v in files.values()),
               "bytes": sum(e["meta"]["content_length"] for v in files.values() for e in v),
               "manifest_destination": report["output_root"] + "_manifests/",
               "evidence": "User-provided S3 listing; no remote content hashes verified",
               "scope": "isolated COPY validation only; not an etl.load_batch publication"}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.report, args.inventory, args.output), indent=2))
