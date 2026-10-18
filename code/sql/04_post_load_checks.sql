-- Read-only checks after successful CALL. Run against the most recently published snapshot.
SELECT * FROM etl.batch_ledger ORDER BY observed_at DESC;
SELECT * FROM etl.batch_attempts ORDER BY attempted_at DESC LIMIT 20;
SELECT * FROM etl.batch_checks WHERE batch_id=(SELECT batch_id FROM etl.batch_ledger ORDER BY observed_at DESC LIMIT 1);

SELECT 'stg_orders' AS name, COUNT(*) AS row_count FROM stg.orders UNION ALL
SELECT 'stg_order_items',COUNT(*) FROM stg.order_items UNION ALL
SELECT 'dim_users_versions',COUNT(*) FROM dw.dim_users UNION ALL
SELECT 'dim_users_current',COUNT(*) FROM dw.dim_users WHERE is_current UNION ALL
SELECT 'dim_products',COUNT(*) FROM dw.dim_products UNION ALL
SELECT 'dim_distribution_centers',COUNT(*) FROM dw.dim_distribution_centers UNION ALL
SELECT 'dim_date',COUNT(*) FROM dw.dim_date UNION ALL
SELECT 'fact_sales',COUNT(*) FROM dw.fact_sales;

-- Expected zero rows from both queries.
SELECT user_id FROM dw.dim_users GROUP BY user_id HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END)<>1;
SELECT order_item_id FROM dw.fact_sales GROUP BY order_item_id HAVING COUNT(*)<>1;

-- These are reconciliation totals across ALL statuses, not recognized revenue.
SELECT 'staging' AS source,COUNT(*) row_count,SUM(i.sale_price) sale_price,SUM(inv.cost) product_cost
 FROM stg.order_items i JOIN stg.inventory_items inv ON inv.id=i.inventory_item_id
UNION ALL
SELECT 'warehouse',COUNT(*),SUM(sale_price),SUM(product_cost) FROM dw.fact_sales;

-- Status here is the item status; source order status remains in stg.orders.
SELECT status,COUNT(*) item_rows,COUNT(DISTINCT order_id) orders,SUM(sale_price) item_price_total
FROM dw.fact_sales GROUP BY status ORDER BY status;
