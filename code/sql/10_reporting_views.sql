-- Only thelook_glue_validation. Create reporting schema separately first.
-- Status-separated measures; no recognized/net revenue assumption.
CREATE OR REPLACE VIEW reporting.v_sales_item AS
SELECT f.order_item_id, f.order_id, f.order_date_key,
       d.full_date AS order_date_utc, d.year AS order_year,
       d.month AS order_month, f.status AS item_status, f.quantity,
       f.sale_price AS item_sale_amount, f.product_cost AS item_cost_amount,
       f.gross_profit AS item_sale_minus_cost,
       f.reference_retail_price AS item_reference_retail_amount,
       p.product_id, p.product_name, p.category, p.brand, p.department,
       dc.distribution_center_id, dc.dc_name AS distribution_center_name,
       u.age_group, u.gender, u.country, u.traffic_source,
       f.item_shipped_before_created, f.item_dates_comparable,
       f.source_batch_id, f.rule_version, f.loaded_at
FROM dw.fact_sales f
LEFT JOIN dw.dim_date d ON d.date_key=f.order_date_key
LEFT JOIN dw.dim_products p ON p.product_key=f.product_key
LEFT JOIN dw.dim_distribution_centers dc ON dc.distribution_center_key=f.distribution_center_key
LEFT JOIN dw.dim_users u ON u.user_key=f.user_key;

CREATE OR REPLACE VIEW reporting.v_sales_daily_status AS
SELECT order_date_utc, item_status, COUNT(*) AS item_count,
       COUNT(DISTINCT order_id) AS distinct_order_count,
       SUM(quantity) AS unit_count,
       SUM(item_sale_amount) AS sale_amount,
       SUM(item_cost_amount) AS cost_amount,
       SUM(item_sale_minus_cost) AS sale_minus_cost_amount
FROM reporting.v_sales_item
GROUP BY order_date_utc, item_status;

CREATE OR REPLACE VIEW reporting.v_sales_product_daily_status AS
SELECT order_date_utc,item_status,product_id,product_name,category,brand,department,
       COUNT(*) AS item_count, COUNT(DISTINCT order_id) AS distinct_order_count,
       SUM(quantity) AS unit_count, SUM(item_sale_amount) AS sale_amount,
       SUM(item_cost_amount) AS cost_amount,
       SUM(item_sale_minus_cost) AS sale_minus_cost_amount
FROM reporting.v_sales_item
GROUP BY order_date_utc,item_status,product_id,product_name,category,brand,department;

CREATE OR REPLACE VIEW reporting.v_sales_dc_daily_status AS
SELECT order_date_utc,item_status,distribution_center_id,distribution_center_name,
       COUNT(*) AS item_count, COUNT(DISTINCT order_id) AS distinct_order_count,
       SUM(quantity) AS unit_count, SUM(item_sale_amount) AS sale_amount,
       SUM(item_cost_amount) AS cost_amount,
       SUM(item_sale_minus_cost) AS sale_minus_cost_amount
FROM reporting.v_sales_item
GROUP BY order_date_utc,item_status,distribution_center_id,distribution_center_name;

CREATE OR REPLACE VIEW reporting.v_sales_quality AS
SELECT source_batch_id, rule_version, COUNT(*) AS item_count,
       SUM(CASE WHEN item_dates_comparable THEN 1 ELSE 0 END) AS comparable_item_count,
       SUM(CASE WHEN item_shipped_before_created THEN 1 ELSE 0 END) AS shipped_before_created_count,
       SUM(CASE WHEN order_date_utc IS NULL OR product_id IS NULL OR distribution_center_id IS NULL THEN 1 ELSE 0 END) AS missing_dimension_item_count
FROM reporting.v_sales_item
GROUP BY source_batch_id,rule_version;

CREATE OR REPLACE VIEW reporting.v_batch_history AS
SELECT l.batch_id,l.observed_at,l.published_at,l.status,l.fact_rows,
       l.schema_version,l.rule_version,
       COALESCE(a.attempt_count,0) AS attempt_count,
       COALESCE(a.no_op_count,0) AS no_op_count,
       COALESCE(a.failed_count,0) AS failed_count,a.last_attempt_at
FROM etl.batch_ledger l
LEFT JOIN (
 SELECT batch_id,COUNT(*) AS attempt_count,
        SUM(CASE WHEN status='NO_OP' THEN 1 ELSE 0 END) AS no_op_count,
        SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) AS failed_count,
        MAX(attempted_at) AS last_attempt_at
 FROM etl.batch_attempts GROUP BY batch_id
) a ON a.batch_id=l.batch_id;

CREATE OR REPLACE VIEW reporting.v_batch_checks AS
SELECT batch_id,check_name,status,row_count AS affected_or_checked_rows,detail
FROM etl.batch_checks;

-- Includes failed-only batches that never reached the publication ledger.
CREATE OR REPLACE VIEW reporting.v_batch_attempt_history AS
SELECT batch_id,attempted_at,status,detail FROM etl.batch_attempts;
