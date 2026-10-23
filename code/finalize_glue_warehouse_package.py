"""Read-only S3 verification and deterministic multipart package creation.

Run the bundled copy in AWS CloudShell. Never writes AWS resources or executes
SQL. SHA-256 is computed from streamed object bytes, not inferred from ETags.
"""
import argparse
import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def split_s3(uri):
    value = urlsplit(uri)
    if value.scheme != "s3" or not value.netloc or not value.path or value.query or value.fragment:
        raise ValueError("Invalid S3 URI")
    return value.netloc, value.path.lstrip("/")


def identity(metadata):
    return (metadata.get("VersionId"), metadata["ETag"], metadata["ContentLength"], str(metadata["LastModified"]))


def remote_json(s3, uri):
    bucket, key = split_s3(uri)
    response = s3.get_object(Bucket=bucket, Key=key)
    try:
        return json.loads(response["Body"].read())
    finally:
        response["Body"].close()


def stream_hash(s3, uri, expected_size):
    bucket, key = split_s3(uri)
    response = s3.get_object(Bucket=bucket, Key=key)
    before = identity(response)
    if response["ContentLength"] != expected_size:
        response["Body"].close()
        raise ValueError("Object size changed: " + uri)
    sha, length = hashlib.sha256(), 0
    try:
        while True:
            chunk = response["Body"].read(1024 * 1024)
            if not chunk:
                break
            sha.update(chunk)
            length += len(chunk)
    finally:
        response["Body"].close()
    if length != expected_size or before != identity(s3.head_object(Bucket=bucket, Key=key)):
        raise ValueError("Object changed during verification: " + uri)
    return {"url": uri, "content_length": length, "sha256": sha.hexdigest(),
            "etag": response["ETag"], "version_id": response.get("VersionId"),
            "last_modified": str(response["LastModified"])}


def read_contract(bundle):
    config = load(bundle / "config.json")
    report = load(bundle / "evidence/validation_report.json")
    baseline = load(bundle / "evidence/baseline_report.json")
    inventory = load(bundle / "evidence/glue-batch-files.json")
    schema = load(bundle / "evidence/curated_schema.json")
    batch = report["batch_id"]
    if config["target_database"] != "thelook_glue_validation" or config["scope"] != "isolated-bootstrap-validation":
        raise ValueError("Only the isolated validation database is supported")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", batch):
        raise ValueError("Invalid batch")
    root = f"s3://{config['bucket']}/thelook/curated/{batch}/"
    if report["output_root"] != root or config["bucket"] != "thelook-dwh-20241022":
        raise ValueError("Unexpected S3 prefix")
    if not re.fullmatch(r"arn:aws:iam::006816724683:role/LabRole", config["iam_role"]):
        raise ValueError("Unexpected IAM role")
    if datetime.fromisoformat(config["observed_at"]).tzinfo is None:
        raise ValueError("Observation anchor needs timezone")
    if (report["schema_version"] != "curated-v1" or report["rule_version"] != "provisional-v1"
            or report["status"] != "PASS_WITH_KNOWN_ISSUES" or len(report["checks"]) != 66
            or any(c["status"] != "PASS" for c in report["checks"])
            or set(report["tables"]) != set(schema["tables"])):
        raise ValueError("This bundle requires its reviewed, fully passing Glue report")
    if digest(report) != config["report_digest"] or digest(inventory) != config["inventory_digest"]:
        raise ValueError("Bundled evidence differs from reviewed evidence")
    known = {v["issue_id"]: v for v in report["known_issues"]}
    if set(known) != {"CITY-01-users", "CITY-01-events", "DATE-01-items"} or any(v["status"] != "KNOWN_ISSUE" for v in known.values()):
        raise ValueError("Known issue drift")
    for name, info in report["tables"].items():
        previous = baseline["tables"][name]
        if (info["source_sha256"] != previous["source_sha256"]
                or info["raw_rows"] != info["curated_rows"] or info["quarantined_rows"] != 0
                or info["curated_rows"] != previous["curated_rows"]
                or info["parquet"] != root + name + "/"):
            raise ValueError("Source differs from the prior bootstrap snapshot: " + name)
        columns = {c["name"] for c in schema["tables"][name]["columns"] if c["type"] == "DECIMAL(18,6)"}
        if set(info["money"]) != columns:
            raise ValueError("Incorrect monetary controls")
        for column, metrics in info["money"].items():
            expected = Decimal(metrics["readback_sum"])
            if (not expected.is_finite() or expected != Decimal(metrics["expected_curated_sum"])
                    or expected != Decimal(previous["money"][column]["readback_sum"])):
                raise ValueError("Monetary controls differ from baseline")
    return config, report, inventory, known


def render_run(package):
    batch = literal(package["batch_id"])
    sql = ["-- Execute ALL statements in one persistent session, autocommit ON.",
           "-- Do not wrap CALL in BEGIN. Only thelook_glue_validation is allowed.",
           "-- file_sha256 is the legacy column name: here it stores a content-set SHA256.",
           "-- Its exact algorithm and each individual file SHA256 are in package.json.",
           "CALL etl.assert_glue_validation_database();", "SET timezone TO 'UTC';",
           "CREATE TEMP TABLE IF NOT EXISTS expected_inputs (table_name VARCHAR(64) NOT NULL,expected_rows BIGINT NOT NULL,manifest_url VARCHAR(2048) NOT NULL,file_sha256 VARCHAR(64) NOT NULL,expected_city_tokens BIGINT,expected_date_flags BIGINT,expected_comparable BIGINT);",
           "CREATE TEMP TABLE IF NOT EXISTS expected_money (table_name VARCHAR(64) NOT NULL,column_name VARCHAR(64) NOT NULL,expected_sum DECIMAL(38,6) NOT NULL);",
           "DELETE FROM expected_inputs;", "DELETE FROM expected_money;"]
    for item in package["tables"]:
        optional = ["NULL" if item[k] is None else str(item[k]) for k in ("city_tokens", "date_flags", "comparable")]
        sql.append("INSERT INTO expected_inputs VALUES (" + ",".join([
            literal(item["table_name"]), str(item["rows"]), literal(item["manifest_url"]),
            literal(item["content_set_sha256"]), *optional]) + ");")
    for table, column, value in package["money"]:
        sql.append(f"INSERT INTO expected_money VALUES ({literal(table)}, {literal(column)}, {literal(value)}::DECIMAL(38,6));")
    sql.append("CALL etl.load_batch(" + ",".join([batch, literal(package["package_hash"]),
               literal(package["observed_at"]) + "::TIMESTAMPTZ", literal(package["iam_role"]), "'dw-v1'", "'provisional-v1'"]) + ");")
    sql += [f"SELECT * FROM etl.batch_ledger WHERE batch_id={batch};",
            f"SELECT * FROM etl.batch_checks WHERE batch_id={batch} ORDER BY check_name;"]
    return "\n".join(sql) + "\n"


def finalize(bundle, output, s3, account):
    bundle, output = Path(bundle), Path(output)
    if output.exists():
        raise ValueError("Output already exists; preserve the previously finalized package")
    config, report, inventory, known = read_contract(bundle)
    if account != config["account_id"]:
        raise ValueError("Wrong AWS account")
    root, batch = report["output_root"], report["batch_id"]
    ready = remote_json(s3, root + "_READY.json")
    if (ready.get("batch_id") != batch or ready.get("status") != "PASS_WITH_KNOWN_ISSUES"
            or ready.get("validation_report") != report["control_root"] + "validation_report.json"):
        raise ValueError("Invalid remote READY marker")
    if remote_json(s3, report["control_root"] + "validation_report.json") != report:
        raise ValueError("Remote validation report has changed")
    expected = {e["Key"]: e["Size"] for e in inventory if e["Key"].endswith(".parquet")}
    if len(expected) != 28:
        raise ValueError("Expected the reviewed 28 part files")
    bucket, prefix = split_s3(root)

    def current_files():
        result = {}
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(".parquet"):
                    result[obj["Key"]] = obj["Size"]
        return result

    if current_files() != expected:
        raise ValueError("S3 part listing differs from reviewed inventory")
    tables, money, manifests, verified = [], [], {}, []
    for name, info in report["tables"].items():
        src_bucket, src_key = split_s3(info["source_uri"])
        raw = s3.head_object(Bucket=src_bucket, Key=src_key)
        if raw["ETag"] != info["source_etag"] or raw["ContentLength"] != info["source_bytes"]:
            raise ValueError("Raw CSV metadata changed since Glue validation: " + name)
        entries, parts = [], []
        for key in sorted(expected):
            if key.startswith(prefix + name + "/"):
                uri = "s3://" + bucket + "/" + key
                print("HASHING " + key, flush=True)
                part = stream_hash(s3, uri, expected[key])
                parts.append(part)
                verified.append(part)
                entries.append({"url": uri, "mandatory": True, "meta": {"content_length": expected[key]}})
        if len(parts) != 4:
            raise ValueError("Expected four parts per table")
        manifest = {"entries": entries}
        manifest_url = root + "_manifests/" + name + ".json"
        if remote_json(s3, manifest_url) != manifest:
            raise ValueError("Remote manifest differs: " + name)
        manifests[name] = manifest
        # Immutable content identity excludes transient ETags and verification timestamps.
        content_set = [{k: p[k] for k in ("url", "content_length", "sha256")} for p in parts]
        dates = known.get("DATE-01-items") if name == "order_items" else None
        tables.append({"table_name": name, "rows": info["curated_rows"],
                       "source_sha256": info["source_sha256"], "manifest_url": manifest_url,
                       "manifest_sha256": digest(manifest), "parts": parts,
                       "content_set_sha256": digest(content_set),
                       "city_tokens": known["CITY-01-" + name]["actual_rows"] if name in ("users", "events") else None,
                       "date_flags": dates["actual_rows"] if dates else None,
                       "comparable": dates["comparable_rows"] if dates else None})
        for column, metrics in info["money"].items():
            money.append([name, column, format(Decimal(metrics["readback_sum"]), "f")])
    # Recheck all part identities after the complete scan, not only during each read.
    if current_files() != expected:
        raise ValueError("Batch listing changed during verification")
    for part in verified:
        b, k = split_s3(part["url"])
        meta = s3.head_object(Bucket=b, Key=k)
        if (meta["ETag"], meta.get("VersionId"), str(meta["LastModified"]), meta["ContentLength"]) != (
                part["etag"], part["version_id"], part["last_modified"], part["content_length"]):
            raise ValueError("A verified object changed: " + part["url"])
    package = {"format": "glue-multipart-package-v1", "batch_id": batch,
               "target_database": config["target_database"], "scope": config["scope"],
               "observed_at": config["observed_at"], "observation_time_basis": config["observation_time_basis"],
               "source_observed_at": report["source_observed_at"], "processed_at": report["processed_at"],
               "prior_source_batch": config["prior_source_batch"], "dw_schema": "dw-v1",
               "curated_schema": "curated-v1", "rule_version": "provisional-v1",
               "iam_role": config["iam_role"], "s3_root": root, "tables": tables, "money": sorted(money),
               "report_digest": digest(report),
               "content_set_hash_algorithm": "SHA256(canonical JSON array of sorted {url,content_length,sha256} parts)",
               "canonical_json": "UTF-8, sort_keys=true, separators=(',', ':'), ensure_ascii=false"}
    package["package_hash"] = digest(package)
    # Nothing is emitted until every remote check above passes.
    output.mkdir(parents=True)
    shutil.copytree(bundle / "sql", output / "sql")
    shutil.copytree(bundle / "evidence", output / "evidence")
    (output / "manifests").mkdir()
    for name, manifest in manifests.items():
        (output / "manifests" / (name + ".json")).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "package.json").write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    run = render_run(package)
    (output / "sql/05_run_batch.sql").write_text(run, encoding="utf-8")
    before = (bundle / "noop_before.sql").read_text(encoding="utf-8")
    after = (bundle / "noop_after.sql").read_text(encoding="utf-8")
    (output / "sql/07_test_no_op.sql").write_text(before + "\n" + run + "\n" + after, encoding="utf-8")
    shutil.copyfile(bundle / "README_TH.md", output / "README_TH.md")
    checksums = {str(p.relative_to(output)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(output.rglob("*")) if p.is_file()}
    (output / "artifact_sha256.json").write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")
    zip_path = output.with_suffix(".zip")
    if zip_path.exists():
        raise ValueError("Result ZIP already exists")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(output.rglob("*")):
            if p.is_file():
                archive.write(p, str(Path(output.name) / p.relative_to(output)))
    return package, zip_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--output", default="glue-warehouse-ready")
    args = parser.parse_args()
    import boto3
    session = boto3.Session(region_name="us-east-1")
    account = session.client("sts").get_caller_identity()["Account"]
    package, result_zip = finalize(args.bundle, args.output, session.client("s3"), account)
    print("PACKAGE_READY batch=" + package["batch_id"])
    print("PACKAGE_HASH=" + package["package_hash"])
    print("DOWNLOAD=" + str(result_zip.resolve()))
    print("No AWS writes or Redshift SQL were executed.")


if __name__ == "__main__":
    main()
