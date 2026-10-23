CALL etl.assert_glue_validation_database();
SELECT current_database() AS database_name;

SELECT 'item_rows' AS check_name,
 CASE WHEN (SELECT COUNT(*) FROM reporting.v_sales_item)=(SELECT COUNT(*) FROM dw.fact_sales) THEN 'PASS' ELSE 'FAIL' END AS status
UNION ALL
SELECT 'item_grain',CASE WHEN NOT EXISTS(SELECT order_item_id FROM reporting.v_sales_item GROUP BY order_item_id HAVING COUNT(*)<>1) THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'dimension_references',CASE WHEN NOT EXISTS(
 SELECT 1 FROM dw.fact_sales f
 LEFT JOIN dw.dim_users u ON u.user_key=f.user_key
 LEFT JOIN dw.dim_products p ON p.product_key=f.product_key
 LEFT JOIN dw.dim_distribution_centers dc ON dc.distribution_center_key=f.distribution_center_key
 LEFT JOIN dw.dim_date d ON d.date_key=f.order_date_key
 WHERE u.user_key IS NULL OR p.product_key IS NULL OR dc.distribution_center_key IS NULL OR d.date_key IS NULL
) THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'item_money',CASE WHEN
 (SELECT SUM(item_sale_amount) FROM reporting.v_sales_item)=(SELECT SUM(sale_price) FROM dw.fact_sales)
 AND (SELECT SUM(item_cost_amount) FROM reporting.v_sales_item)=(SELECT SUM(product_cost) FROM dw.fact_sales)
 AND (SELECT SUM(item_sale_minus_cost) FROM reporting.v_sales_item)=(SELECT SUM(gross_profit) FROM dw.fact_sales)
 THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'daily_rollup',CASE WHEN
 (SELECT SUM(item_count) FROM reporting.v_sales_daily_status)=(SELECT COUNT(*) FROM dw.fact_sales)
 AND (SELECT SUM(sale_amount) FROM reporting.v_sales_daily_status)=(SELECT SUM(sale_price) FROM dw.fact_sales)
 AND (SELECT SUM(cost_amount) FROM reporting.v_sales_daily_status)=(SELECT SUM(product_cost) FROM dw.fact_sales)
 THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'product_rollup',CASE WHEN
 (SELECT SUM(item_count) FROM reporting.v_sales_product_daily_status)=(SELECT COUNT(*) FROM dw.fact_sales)
 AND (SELECT SUM(sale_amount) FROM reporting.v_sales_product_daily_status)=(SELECT SUM(sale_price) FROM dw.fact_sales)
 AND (SELECT SUM(cost_amount) FROM reporting.v_sales_product_daily_status)=(SELECT SUM(product_cost) FROM dw.fact_sales)
 THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'dc_rollup',CASE WHEN
 (SELECT SUM(item_count) FROM reporting.v_sales_dc_daily_status)=(SELECT COUNT(*) FROM dw.fact_sales)
 AND (SELECT SUM(sale_amount) FROM reporting.v_sales_dc_daily_status)=(SELECT SUM(sale_price) FROM dw.fact_sales)
 AND (SELECT SUM(cost_amount) FROM reporting.v_sales_dc_daily_status)=(SELECT SUM(product_cost) FROM dw.fact_sales)
 THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'lineage',CASE WHEN NOT EXISTS(
 SELECT 1 FROM dw.fact_sales f LEFT JOIN etl.batch_ledger l ON l.batch_id=f.source_batch_id
 WHERE l.batch_id IS NULL OR l.status<>'SUCCEEDED'
) THEN 'PASS' ELSE 'FAIL' END;

SELECT item_status,COUNT(*) AS item_count,COUNT(DISTINCT order_id) AS distinct_order_count,
       SUM(item_sale_amount) AS sale_amount,SUM(item_cost_amount) AS cost_amount
FROM reporting.v_sales_item GROUP BY item_status ORDER BY item_status;

SELECT COUNT(*) AS item_count,COUNT(DISTINCT order_id) AS distinct_order_count,
       SUM(item_sale_amount) AS sale_amount FROM reporting.v_sales_item;
SELECT * FROM reporting.v_sales_quality;
SELECT * FROM reporting.v_batch_history ORDER BY observed_at DESC;
