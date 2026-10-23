# Reporting acceptance — 24 October 2026

Evidence supplied by user: Query Editor result screenshots for reporting checks and totals, database thelook_glue_validation in the established installation flow. No independent live query was performed by the documentation editor.

- [x] item_rows
- [x] item_grain
- [x] dimension_references
- [x] item_money
- [x] daily_rollup
- [x] product_rollup
- [x] dc_rollup
- [x] lineage

| item_status | item_count | distinct_order_count within status | sale_amount |
|---|---:|---:|---:|
| Cancelled | 27090 | 18609 | 1602475.453897 |
| Complete | 45609 | 31354 | 2715783.746481 |
| Processing | 36388 | 25156 | 2155331.514966 |
| Returned | 18232 | 12530 | 1097306.742580 |
| Shipped | 54440 | 37577 | 3256221.467176 |
| **All items / recomputed DISTINCT orders** | **181759** | **125226** | **10827118.925100** |

Distinct order counts are generally not additive across statuses/products/DCs, even if this snapshot happens to reconcile across status groups. Use COUNT(DISTINCT order_id) on detail for a new grouping.

Quality screenshot: item_count181759, comparable_item_count118281, provisional-v1. Other quality columns are not visible in that screenshot and are not independently certified by it. Ledger screenshot: SUCCEEDED, published_at2026-10-23 16:34:59+00. Batch identity from earlier verified flow: 20261023T151247118967Z_f8a02155.

This closes AWS reporting installation/reconciliation for status-separated metrics. It does not certify net revenue, currency, source snapshot freshness, BI connectivity/dashboard deployment or source confirmation of known issues.
