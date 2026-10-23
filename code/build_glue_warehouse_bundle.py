"""Prepare the reviewed offline bundle. Final hashes are computed in CloudShell."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from finalize_glue_warehouse_package import digest, read_contract

ROOT = Path(__file__).resolve().parent.parent
BATCH = "20261023T151247118967Z_f8a02155"


def build(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    evidence, sql = output / "evidence", output / "sql"
    evidence.mkdir()
    sql.mkdir()
    prior = ROOT / "outputs/aws" / ("glue-copy-" + BATCH)
    for filename in ("validation_report.json", "glue-batch-files.json"):
        shutil.copyfile(prior / filename, evidence / filename)
    shutil.copyfile(ROOT / "outputs/curated/v1-baseline/validation_report.json", evidence / "baseline_report.json")
    shutil.copyfile(ROOT / "code/curated_schema.json", evidence / "curated_schema.json")
    config = json.loads((ROOT / "code/aws_batch_config.json").read_text(encoding="utf-8"))
    report = json.loads((evidence / "validation_report.json").read_text(encoding="utf-8"))
    inventory = json.loads((evidence / "glue-batch-files.json").read_text(encoding="utf-8"))
    recipe = {"account_id": "006816724683", "bucket": config["bucket"],
              "iam_role": config["iam_role"], "target_database": "thelook_glue_validation",
              "scope": "isolated-bootstrap-validation", "observed_at": config["observed_at"],
              "source_observed_at": None, "prior_source_batch": config["batch_id"],
              "observation_time_basis": "Inherited prior bootstrap anchor for the identical raw snapshot; originally inferred from prior deployment timestamp, NOT source-confirmed. Isolated validation only.",
              "report_digest": digest(report), "inventory_digest": digest(inventory)}
    (output / "config.json").write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
    read_contract(output)
    shutil.copyfile(ROOT / "code/finalize_glue_warehouse_package.py", output / "finalize_package.py")
    shutil.copyfile(ROOT / "docs/glue_warehouse_package_runbook.md", output / "README_TH.md")
    preflight = """-- READ ONLY. Connect to the existing thelook_glue_validation database.
SELECT current_database(), current_user;
-- Stop if current_database is not thelook_glue_validation.
-- Expect zero existing tables in etl/stg/dw for first installation.
SELECT table_schema, table_name FROM information_schema.tables
WHERE table_schema IN ('etl','stg','dw') ORDER BY 1,2;
-- glue_copy_check holds the successful COPY test and is intentionally retained.
"""
    (sql / "00_preflight.sql").write_text(preflight, encoding="utf-8")
    (sql / "00a_create_schemas.sql").write_text(
        "-- ONLY in thelook_glue_validation. Autocommit ON; run each statement separately.\n"
        "CREATE SCHEMA IF NOT EXISTS etl;\nCREATE SCHEMA IF NOT EXISTS stg;\nCREATE SCHEMA IF NOT EXISTS dw;\n", encoding="utf-8")
    for source, target in [("00_control.sql", "01_control_tables.sql"),
                           ("01_staging.sql", "02_staging_tables.sql"),
                           ("02_warehouse.sql", "03_warehouse_tables.sql")]:
        text = (ROOT / "code/sql" / source).read_text(encoding="utf-8")
        for name in ("etl", "stg", "dw"):
            text = text.replace(f"CREATE SCHEMA IF NOT EXISTS {name};", "")
        (sql / target).write_text("-- ONLY in thelook_glue_validation; first installation, stop on errors.\n" + text, encoding="utf-8")
    guard = """CREATE OR REPLACE PROCEDURE etl.assert_glue_validation_database()
AS $$
BEGIN
    IF current_database() <> 'thelook_glue_validation' THEN
        RAISE EXCEPTION 'Wrong database: this package is isolated-validation only';
    END IF;
END;
$$ LANGUAGE plpgsql;

"""
    proc = (ROOT / "code/sql/03_load_batch.sql").read_text(encoding="utf-8")
    proc = proc.replace("BEGIN\n    -- Serialize", "BEGIN\n    CALL etl.assert_glue_validation_database();\n    -- Serialize", 1)
    # Never write an error-audit row to another database after the guard rejects it.
    original = "    INSERT INTO etl.batch_attempts(batch_id, attempted_at, status, detail)\n    VALUES (p_batch_id, GETDATE(), 'FAILED', LEFT(SQLERRM, 4000));"
    replacement = "    IF current_database() = 'thelook_glue_validation' THEN\n" + original + "\n    END IF;"
    if original not in proc:
        raise ValueError("Loader template changed: inspect exception handler")
    proc = proc.replace(original, replacement)
    proc = "-- Legacy file_sha256 audit field stores the documented multi-file content-set digest for this package.\n" + proc
    (sql / "04_install_procedures.sql").write_text(guard + proc, encoding="utf-8")
    checks = ["-- READ ONLY after 05_run_batch.sql. All status rows should PASS.",
              "SELECT current_database();", f"SELECT * FROM etl.batch_ledger WHERE batch_id='{BATCH}';",
              f"SELECT * FROM etl.batch_checks WHERE batch_id='{BATCH}' ORDER BY check_name;"]
    count_queries = []
    for name, info in report["tables"].items():
        count_queries.append(f"SELECT 'stg.{name}' AS table_name, COUNT(*) AS actual_rows, {info['curated_rows']}::BIGINT AS expected_rows FROM stg.{name}")
    for name, count in [("dim_distribution_centers", 10), ("dim_products", 29120), ("dim_users", 100000), ("fact_sales", 181759)]:
        count_queries.append(f"SELECT 'dw.{name}', COUNT(*), {count}::BIGINT FROM dw.{name}")
    count_queries.append("SELECT 'dw.dim_users.current', COUNT(*), 100000::BIGINT FROM dw.dim_users WHERE is_current")
    checks.append("SELECT *, CASE WHEN actual_rows=expected_rows THEN 'PASS' ELSE 'FAIL' END AS status FROM (\n" + "\nUNION ALL\n".join(count_queries) + "\n) counts ORDER BY table_name;")
    checks += ["-- Expected zero rows: duplicate facts or not exactly one current user version.",
               "SELECT order_item_id FROM dw.fact_sales GROUP BY 1 HAVING COUNT(*)<>1;",
               "SELECT user_id FROM dw.dim_users GROUP BY 1 HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END)<>1;",
               "-- Whole-snapshot reconciliation, not a recognized-revenue definition.",
               "SELECT 'staging' AS source,COUNT(*) AS row_count,SUM(i.sale_price) AS sale_price,SUM(inv.cost) AS product_cost FROM stg.order_items i JOIN stg.inventory_items inv ON inv.id=i.inventory_item_id UNION ALL SELECT 'warehouse',COUNT(*),SUM(sale_price),SUM(product_cost) FROM dw.fact_sales;",
               "SELECT COUNT(*) AS compared_inventory_rows, SUM(CASE WHEN p.distribution_center_id<>i.product_distribution_center_id THEN 1 ELSE 0 END) AS drift_rows FROM stg.products p JOIN stg.inventory_items i ON i.product_id=p.id;",
               f"SELECT * FROM etl.batch_attempts WHERE batch_id='{BATCH}' ORDER BY attempted_at DESC;"]
    (sql / "06_post_load_checks.sql").write_text("\n\n".join(checks) + "\n", encoding="utf-8")
    # Independent exact snapshots of DW and batch audit tables around the NO_OP.
    targets = ["dw.dim_date", "dw.dim_users", "dw.dim_products", "dw.dim_distribution_centers", "dw.fact_sales",
               "etl.batch_ledger", "etl.batch_inputs", "etl.batch_checks"]
    before = ["-- Run only AFTER the first successful publication, in one session.",
              "CALL etl.assert_glue_validation_database();"]
    after = ["-- Expected all PASS: exact values and counts unchanged by the repeated package."]
    comparisons = []
    for table in targets:
        temp = "noop_before_" + table.replace(".", "_")
        before.append(f"CREATE TEMP TABLE {temp} AS SELECT * FROM {table};")
        comparisons.append(f"SELECT '{table}' AS table_name, CASE WHEN (SELECT COUNT(*) FROM {table})=(SELECT COUNT(*) FROM {temp}) AND NOT EXISTS (SELECT * FROM {table} EXCEPT SELECT * FROM {temp}) AND NOT EXISTS (SELECT * FROM {temp} EXCEPT SELECT * FROM {table}) THEN 'PASS' ELSE 'FAIL' END AS status")
    before.append(f"CREATE TEMP TABLE noop_attempts_before AS SELECT COUNT(*) AS n FROM etl.batch_attempts WHERE batch_id='{BATCH}' AND status='NO_OP';")
    after.append("\nUNION ALL\n".join(comparisons) + ";")
    after.append(f"SELECT CASE WHEN COUNT(*)=(SELECT n+1 FROM noop_attempts_before) THEN 'PASS' ELSE 'FAIL' END AS new_no_op_attempt FROM etl.batch_attempts WHERE batch_id='{BATCH}' AND status='NO_OP';")
    after.append(f"SELECT * FROM etl.batch_attempts WHERE batch_id='{BATCH}' ORDER BY attempted_at DESC;")
    (output / "noop_before.sql").write_text("\n".join(before) + "\n", encoding="utf-8")
    (output / "noop_after.sql").write_text("\n".join(after) + "\n", encoding="utf-8")
    files = {str(p.relative_to(output)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(output.rglob("*")) if p.is_file()}
    (output / "bundle_sha256.json").write_text(json.dumps(files, indent=2) + "\n", encoding="utf-8")
    archive_path = output.with_suffix(".zip")
    if archive_path.exists():
        raise ValueError("Archive already exists")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(output.rglob("*")):
            if p.is_file():
                archive.write(p, str(Path(output.name) / p.relative_to(output)))
    return archive_path


if __name__ == "__main__":
    print(build(ROOT / "outputs/aws/glue-warehouse-bundle"))
