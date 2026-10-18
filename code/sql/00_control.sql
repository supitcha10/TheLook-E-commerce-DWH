-- First installation only. Control tables are not additional business facts/dimensions.
CREATE SCHEMA IF NOT EXISTS etl;
CREATE TABLE etl.batch_ledger (
    batch_id VARCHAR(64) NOT NULL PRIMARY KEY,
    package_hash VARCHAR(64) NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    schema_version VARCHAR(32) NOT NULL,
    rule_version VARCHAR(64) NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    fact_rows BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL
) DISTSTYLE ALL;
CREATE TABLE etl.batch_attempts (
    batch_id VARCHAR(64), attempted_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(32) NOT NULL, detail VARCHAR(4000)
) DISTSTYLE AUTO;
CREATE TABLE etl.batch_inputs (
    batch_id VARCHAR(64) NOT NULL, table_name VARCHAR(64) NOT NULL,
    file_sha256 VARCHAR(64) NOT NULL, expected_rows BIGINT NOT NULL,
    manifest_url VARCHAR(2048) NOT NULL
) DISTSTYLE AUTO;
CREATE TABLE etl.batch_checks (
    batch_id VARCHAR(64) NOT NULL, check_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL, row_count BIGINT, detail VARCHAR(2000)
) DISTSTYLE AUTO;
