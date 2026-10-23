-- READ ONLY. Select database thelook_glue_validation first.
-- Run statements one by one. Stop if database or any expected result differs.
SELECT current_database() AS database_name, current_user AS user_name,
       CASE WHEN current_database()='thelook_glue_validation' THEN 'PASS' ELSE 'STOP_WRONG_DATABASE' END AS database_check;

SELECT batch_id, package_hash, observed_at, status
FROM etl.batch_ledger
ORDER BY observed_at;

SELECT 'users_total' AS check_name, COUNT(*) AS actual_rows, 100000 AS expected_rows FROM dw.dim_users
UNION ALL SELECT 'users_current', COUNT(*), 100000 FROM dw.dim_users WHERE is_current
UNION ALL SELECT 'products', COUNT(*), 29120 FROM dw.dim_products
UNION ALL SELECT 'distribution_centers', COUNT(*), 10 FROM dw.dim_distribution_centers
UNION ALL SELECT 'fact_sales', COUNT(*), 181759 FROM dw.fact_sales;

SELECT 'duplicate_current_users' AS check_name, COUNT(*) AS violations
FROM (SELECT user_id FROM dw.dim_users WHERE is_current GROUP BY user_id HAVING COUNT(*)<>1) x
UNION ALL
SELECT 'users_without_exactly_one_current', COUNT(*)
FROM (SELECT user_id FROM dw.dim_users GROUP BY user_id HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END)<>1) x
UNION ALL
SELECT 'invalid_scd_boundaries', COUNT(*) FROM dw.dim_users
WHERE is_current<>(valid_to IS NULL)
   OR (valid_from IS NOT NULL AND valid_to<=valid_from)
   OR (valid_from IS NULL AND version_origin NOT IN ('BOOTSTRAP_SNAPSHOT','OBSERVED_NEW'));

SELECT version_origin, COUNT(*) AS row_count FROM dw.dim_users GROUP BY version_origin;

SELECT 'staging' AS source, COUNT(*) AS row_count, SUM(sale_price) AS sale_price FROM stg.order_items
UNION ALL
SELECT 'warehouse', COUNT(*), SUM(sale_price) FROM dw.fact_sales;

-- Inspect keys/flags only; no email, name or address values are exported.
SELECT user_id, user_key, version_origin, observed_at, valid_from, valid_to,
       is_current, city_missing_token, (city IS NULL) AS city_is_null
FROM dw.dim_users WHERE is_current ORDER BY user_id LIMIT 5;
