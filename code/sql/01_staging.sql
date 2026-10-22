-- First-time installation only. Do not use this file as a schema migration.

CREATE SCHEMA IF NOT EXISTS stg;

CREATE TABLE stg.distribution_centers (
    id BIGINT NOT NULL,
    name VARCHAR(256) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL
) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;

CREATE TABLE stg.products (
    id BIGINT NOT NULL,
    cost DECIMAL(18,6) NOT NULL,
    category VARCHAR(128) NOT NULL,
    name VARCHAR(1024),
    brand VARCHAR(256),
    retail_price DECIMAL(18,6) NOT NULL,
    department VARCHAR(32) NOT NULL,
    sku VARCHAR(128) NOT NULL,
    distribution_center_id BIGINT NOT NULL
) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;

CREATE TABLE stg.users (
    id BIGINT NOT NULL,
    first_name VARCHAR(256) NOT NULL,
    last_name VARCHAR(256) NOT NULL,
    email VARCHAR(512) NOT NULL,
    age SMALLINT NOT NULL,
    gender VARCHAR(32) NOT NULL,
    state VARCHAR(256) NOT NULL,
    street_address VARCHAR(2048) NOT NULL,
    postal_code VARCHAR(32) NOT NULL,
    city VARCHAR(256) NOT NULL,
    country VARCHAR(128) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    traffic_source VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    city_clean VARCHAR(256),
    city_missing_token BOOLEAN NOT NULL
) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;

CREATE TABLE stg.orders (
    order_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL,
    gender VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    returned_at TIMESTAMPTZ,
    shipped_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    num_of_item INTEGER NOT NULL
) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;

CREATE TABLE stg.order_items (
    id BIGINT NOT NULL,
    order_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    inventory_item_id BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    shipped_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    returned_at TIMESTAMPTZ,
    sale_price DECIMAL(18,6) NOT NULL,
    item_shipped_before_created BOOLEAN,
    item_dates_comparable BOOLEAN NOT NULL
) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;

CREATE TABLE stg.inventory_items (
    id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    sold_at TIMESTAMPTZ,
    cost DECIMAL(18,6) NOT NULL,
    product_category VARCHAR(128) NOT NULL,
    product_name VARCHAR(1024),
    product_brand VARCHAR(256),
    product_retail_price DECIMAL(18,6) NOT NULL,
    product_department VARCHAR(32) NOT NULL,
    product_sku VARCHAR(128) NOT NULL,
    product_distribution_center_id BIGINT NOT NULL
) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;

CREATE TABLE stg.events (
    id BIGINT NOT NULL,
    user_id BIGINT,
    sequence_number INTEGER NOT NULL,
    session_id VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    ip_address VARCHAR(64) NOT NULL,
    city VARCHAR(256) NOT NULL,
    state VARCHAR(256) NOT NULL,
    postal_code VARCHAR(32) NOT NULL,
    browser VARCHAR(128) NOT NULL,
    traffic_source VARCHAR(64) NOT NULL,
    uri VARCHAR(8192) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    city_clean VARCHAR(256),
    city_missing_token BOOLEAN NOT NULL
) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;
