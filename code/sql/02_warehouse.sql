-- First-time installation; no DROP or automatic migration.
CREATE SCHEMA IF NOT EXISTS dw;
SET timezone TO 'UTC';

CREATE TABLE dw.dim_date (
    date_key INTEGER NOT NULL PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day_of_week SMALLINT NOT NULL,
    day_name VARCHAR(10) NOT NULL,
    day_of_month SMALLINT NOT NULL,
    month SMALLINT NOT NULL,
    month_name VARCHAR(10) NOT NULL,
    quarter SMALLINT NOT NULL,
    year INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL
) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;

CREATE TABLE dw.dim_users (
    user_key BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    full_name VARCHAR(1024) NOT NULL,
    email VARCHAR(512) NOT NULL,
    age SMALLINT NOT NULL,
    age_group VARCHAR(20),
    gender VARCHAR(32) NOT NULL,
    city VARCHAR(256),
    city_missing_token BOOLEAN NOT NULL,
    state VARCHAR(256) NOT NULL,
    country VARCHAR(128) NOT NULL,
    postal_code VARCHAR(32) NOT NULL,
    traffic_source VARCHAR(64) NOT NULL,
    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ,
    is_current BOOLEAN NOT NULL,
    version_origin VARCHAR(32) NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    source_batch_id VARCHAR(64) NOT NULL,
    rule_version VARCHAR(64) NOT NULL
) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;

CREATE TABLE dw.dim_products (
    product_key BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    product_name VARCHAR(1024),
    category VARCHAR(128) NOT NULL,
    brand VARCHAR(256),
    department VARCHAR(32) NOT NULL,
    sku VARCHAR(128) NOT NULL,
    retail_price DECIMAL(18,6) NOT NULL,
    cost DECIMAL(18,6) NOT NULL,
    source_batch_id VARCHAR(64) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;

CREATE TABLE dw.dim_distribution_centers (
    distribution_center_key BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    distribution_center_id BIGINT NOT NULL,
    dc_name VARCHAR(256) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    source_batch_id VARCHAR(64) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;

CREATE TABLE dw.fact_sales (
    order_item_id BIGINT NOT NULL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    inventory_item_id BIGINT NOT NULL,
    user_key BIGINT NOT NULL REFERENCES dw.dim_users(user_key),
    product_key BIGINT NOT NULL REFERENCES dw.dim_products(product_key),
    distribution_center_key BIGINT NOT NULL REFERENCES dw.dim_distribution_centers(distribution_center_key),
    order_created_at TIMESTAMPTZ NOT NULL,
    order_shipped_at TIMESTAMPTZ,
    order_delivered_at TIMESTAMPTZ,
    order_returned_at TIMESTAMPTZ,
    order_date_key INTEGER NOT NULL REFERENCES dw.dim_date(date_key),
    shipped_date_key INTEGER REFERENCES dw.dim_date(date_key),
    delivered_date_key INTEGER REFERENCES dw.dim_date(date_key),
    returned_date_key INTEGER REFERENCES dw.dim_date(date_key),
    status VARCHAR(32) NOT NULL,
    quantity INTEGER NOT NULL,
    sale_price DECIMAL(18,6) NOT NULL,
    product_cost DECIMAL(18,6) NOT NULL,
    reference_retail_price DECIMAL(18,6) NOT NULL,
    gross_profit DECIMAL(19,6) NOT NULL,
    catalog_price_difference DECIMAL(19,6) NOT NULL,
    discount_amount DECIMAL(19,6),
    shipping_duration_days DECIMAL(18,6),
    item_shipped_before_created BOOLEAN,
    item_dates_comparable BOOLEAN NOT NULL,
    source_batch_id VARCHAR(64) NOT NULL,
    rule_version VARCHAR(64) NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL
) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;
