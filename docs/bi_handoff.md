# BI handoff — status-separated reporting v1

User decision: แยกยอดตามสถานะ ยังไม่เรียก net sales. Updated 24 October 2026: views installed and all8 AWS checks PASS; user confirmed totals. See [acceptance evidence](report/reporting_acceptance_20261024.md). BI dashboard/connectivity remains pending.

## สำหรับผู้รับงาน

เอกสารและ reporting views ฝั่ง DW พร้อมส่งต่อ แต่ยังไม่มีหลักฐานว่า BI รับมอบ เลือกเครื่องมือ เชื่อมต่อ หรือยืนยัน known issues แล้ว ไม่ต้องรอ BI เพื่อเตรียมเอกสารส่วนนี้ให้พร้อม

1. อ่าน [ข้อมูลต้นทางและ known issues](source_dataset_acceptance.md): ผู้ใช้เลือก Kaggle Version 1 ดาวน์โหลด 6 ตุลาคม 2026 เป็นข้อมูลคงที่; new-snapshot pipeline/schedule อยู่นอกขอบเขต เวลา snapshot และความครบถ้วนทุกแถวจาก BigQuery ยังไม่ทราบ
2. อ่าน Connection, Views และ Metric dictionary ด้านล่าง ใช้ฐาน `thelook_glue_validation` / schema `reporting` ไม่ใช้ `dev` หรือฐาน synthetic `thelook_scd_test`
3. อ่าน [ผลตรวจ reporting](report/reporting_acceptance_20261024.md) และ [DW handoff](dw_handoff.md) สำหรับทรัพยากรและรายการหลักฐาน ห้ามติดตั้ง DDL หรือโหลดข้อมูลซ้ำเพียงเพื่อรับช่วงงาน
4. ให้ BI/Infra ยืนยันเครื่องมือและสิทธิ์บริการ, read-only principal, network/endpoint ที่จะใช้จริง และข้อกำหนด RLS ก่อนเชื่อมต่อ ไม่ถือว่า Glue connection เดิมเป็นเส้นทางที่เครื่องมือ BI ใช้ได้แล้ว
5. หลังเชื่อมได้ ให้ BI ร่วม DW ตรวจ Dashboard ด้วยตัวกรองเดียวกัน: items **181759**, distinct orders **125226**, sale amount ทุกสถานะ **10827118.925100** ตรวจยอดแต่ละสถานะกับรายงานอ้างอิง และคำนวณ DISTINCT ใหม่สำหรับยอดรวม

รายการที่ผู้รับต้องยืนยันภายหลัง:

- [ ] DW/BI รับทราบ known issues พร้อมชื่อและวันที่ตามเอกสารต้นทาง; ไม่เปลี่ยน provisional-v1 เป็น source-confirmed
- [ ] Infra/BI ทดสอบการเชื่อมต่อด้วยสิทธิ์อ่าน และทดสอบสิทธิ์ตามบทบาทที่ตกลง
- [ ] BI/DW ตรวจยอด ตัวกรอง grain และป้ายกำกับ (Unknown, UTC, สถานะ, currency ที่ยังไม่ยืนยัน และข้อจำกัด snapshot)
- [ ] บันทึกผู้รับ วันที่ และหลักฐานการรับมอบจริง

## Connection and scope

- Region us-east-1, cluster thelook-redshift-cluster-1, database thelook_glue_validation, schema reporting.
- Coordinate network and read-only access with Infra. Do not give BI the LabRole/admin password. No permissions are granted by this package.
- Cluster must be Available for direct queries; pause when idle after saving evidence. QuickSight permissions/connectivity remain unconfirmed. No dashboard has been deployed by this package.
- Source lineage: batch 20261023T151247118967Z_f8a02155, rule provisional-v1. This is a validation warehouse, not a declared production endpoint.

## Views / grain

| View | Grain and use |
|---|---|
| v_sales_item | One order_item_id; base dataset for flexible filtering and distinct orders |
| v_sales_daily_status | One order date UTC + item status |
| v_sales_product_daily_status | One date + status + product, current Type1 product attributes |
| v_sales_dc_daily_status | One date + status + distribution center, current Type1 DC attributes |
| v_sales_quality | One batch + rule; item date flags and missing reference indicators |
| v_batch_history | One published batch; audit counts preaggregated to avoid join multiplication |
| v_batch_checks | One recorded check row; counts have meanings specific to check_name |
| v_batch_attempt_history | One attempt; includes failures for unpublished batches |

## Metric dictionary

- item_count = count of item rows; unit_count = SUM(quantity), currently quantity=1.
- distinct_order_count = COUNT(DISTINCT order_id) within the selected group. It is NOT additive across product, DC or status groups. For total/filtered orders compute DISTINCT from v_sales_item again.
- sale_amount = sum of source item sale_price for the selected status; Returned/Cancelled are not negated or subtracted. Mixed-status orders may appear in multiple status groups.
- cost_amount = inventory-item cost, not current product catalog cost.
- sale_minus_cost_amount = arithmetic sale minus item cost. Not recognized profit; excludes tax, shipping, payment fees and other operating costs.
- Money preserves source decimal precision. Round only for display. Currency is not confirmed by the supplied dataset; do not label THB/USD without confirmation.
- order_date_utc = fact order date dimension. Status breakdown is current snapshot item status, NOT a history of status transitions or a daily cash/return event report.
- Traffic source and user demographics join by historical user_key held by fact; do not rejoin all dim_users rows by natural ID or force is_current.
- Product/DC names reflect Type1 attributes. Catalog corrections can change labels for historical facts.
- No name/email/street/postal/IP columns are exposed by these reporting views. Order IDs and demographics are still data requiring access control; these views are not claimed anonymous.
- quality denominator for shipped-before-created = comparable_item_count, not all item rows. Use NULL when denominator=0.
- published_at/loaded_at are pipeline timestamps, not confirmed source freshness. observed_at currently uses an assumed bootstrap anchor; source_observed_at is unconfirmed.

## Suggested dashboard and acceptance

1. Overview: filters order date UTC/status; item count, distinct orders, sale amount and cost amount. Label all-status selection explicitly.
2. Product: category/brand/product and status breakdown; reconcile sums to overview with identical filters.
3. Distribution center: sales items/amount by DC and status. This does not measure current inventory or fulfillment SLA.
4. Quality/operations: known issue numerator/denominator, latest published batch, all attempts, failed checks.

Acceptance: reporting checks all8 PASS, initial item_count181759, distinct orders125226, sale_amount10827118.925100. Category/DC drilldowns must not multiply rows. Verify total orders using detail DISTINCT, not SUM of preaggregated orders. Confirm no PII columns in field list. Add status, UTC and source snapshot limitation to dashboard notes.

Inventory balance/stock aging and events funnel are NOT delivered by fact_sales. They require separate definitions/modeling over inventory_items/events, including what time stock is measured and how sessions/conversions are defined. Do not represent these as finished dashboards.

## Remaining approvals/information

Business/source owner: snapshot time/timezone, currency, revenue/returns recognition rules if net metrics are later needed. BI/Infra: actual read-only principal, QuickSight availability, network path and row-level access requirements. Current status-separated views can be reviewed without inventing these answers.

## หลักฐานที่เตรียมให้ผู้รับแล้ว

ชุดในเครื่อง `outputs/DW-handoff-evidence/` มีภาพ reporting.v_sales_item ที่ item_rows=unique_items181759,distinctorders125226,sale10827118.925100,cost5208355.223564 และยอด5สถานะตรงรายงานเดิม พร้อมภาพ ledger/checks และไฟล์ replay ที่ผ่าน ไม่ใช่หลักฐานว่า BI เชื่อมต่อหรือยอมรับ Dashboard แล้ว

รายงานเดิมระบุ reporting checks8 PASS แต่ภาพ/exportsต้นฉบับครบ8รายการยังไม่ได้รวบรวมในชุด; ภาพ totals/grain/status ที่ได้เพิ่มไม่ใช้รับรอง rollups/references/lineage ทุกข้อแทน การรับทราบ known issues และการรับมอบของทีมยังรอยืนยัน
