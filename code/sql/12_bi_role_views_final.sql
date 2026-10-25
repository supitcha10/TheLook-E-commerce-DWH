-- 12_bi_role_views.sql — view แยกตามฝ่าย + สิทธิ์ สำหรับ Dashboard
--
-- รันที่: cluster thelook-redshift-cluster-1 / database thelook_glue_validation
--
-- สถานะ: รันบน Redshift จริงแล้ว 
--   - ส่วน 0–5 สร้าง view ครบ 8 ตัว
--   - ส่วน 8 ตรวจยอดผ่านครบ 9 ข้อ
--   - ส่วน 6 สร้าง group/user แล้ว (ห้ามรันส่วน 6 ซ้ำ — จะขึ้น already exists)
--   - ส่วน 7 ทดสอบสิทธิ์ผ่านครบ หลังเพิ่ม GRANT USAGE บน schema ต้นทาง (ดู 6.3)
--
-- นิยามของกลุ่ม BI:
--   net sales = รวม item_sale_amount ที่ item_status ไม่ใช่ Cancelled หรือ Returned
--   ยอดอ้างอิงจากผลตรวจของทีม DW: ทุกสถานะ 10,827,118.93 → net sales 8,127,336.73
--   (Complete + Processing + Shipped) / net items 136,437

CREATE SCHEMA IF NOT EXISTS bi;

-- ---------------------------------------------------------------------
-- 0) ฐานของกลุ่ม BI: reporting.v_sales_item + user_id + ป้ายนิยาม
--    ไม่ให้ฝ่ายไหนเห็นโดยตรง
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW bi.v_sales_base AS
SELECT
    s.*,
    u.user_id,
    CASE WHEN s.item_status IN ('Cancelled', 'Returned') THEN FALSE ELSE TRUE END AS is_net_sale,
    CASE WHEN s.item_status = 'Cancelled' THEN TRUE ELSE FALSE END                AS is_cancelled,
    CASE WHEN s.item_status = 'Returned'  THEN TRUE ELSE FALSE END                AS is_returned
FROM reporting.v_sales_item s
JOIN dw.fact_sales f      ON f.order_item_id = s.order_item_id
LEFT JOIN dw.dim_users u  ON u.user_key = f.user_key;


-- 1) EXECUTIVE — ภาพรวมรายเดือน

CREATE OR REPLACE VIEW bi.v_exec_monthly AS
SELECT
    order_year,
    order_month,
    COUNT(DISTINCT CASE WHEN is_net_sale THEN order_id END)        AS net_orders,
    SUM(CASE WHEN is_net_sale THEN item_sale_amount     ELSE 0 END) AS net_sales,
    SUM(CASE WHEN is_net_sale THEN item_sale_minus_cost ELSE 0 END) AS gross_profit,
    COUNT(DISTINCT CASE WHEN is_net_sale THEN user_id END)          AS active_customers,
    SUM(item_sale_amount)                                           AS gross_sales_all_status,
    AVG(CASE WHEN is_cancelled THEN 1.0 ELSE 0 END)                 AS cancel_rate,
    AVG(CASE WHEN is_returned  THEN 1.0 ELSE 0 END)                 AS return_rate
FROM bi.v_sales_base
GROUP BY order_year, order_month;


-- 2) SALES — ไม่มีต้นทุนและกำไร

CREATE OR REPLACE VIEW bi.v_sales_detail AS
SELECT
    order_item_id,
    order_id,
    item_status,
    is_net_sale,
    order_date_utc,
    order_year,
    order_month,
    product_name,
    category,
    brand,
    department,
    country,
    age_group,
    gender,
    item_sale_amount
FROM bi.v_sales_base;



-- 3) FINANCE — รายได้ ต้นทุน กำไร ยอดคืน/ยกเลิก (รายเดือน × หมวด)

CREATE OR REPLACE VIEW bi.v_finance_monthly AS
SELECT
    order_year,
    order_month,
    category,
    SUM(CASE WHEN is_net_sale  THEN item_sale_amount     ELSE 0 END) AS net_sales,
    SUM(CASE WHEN is_net_sale  THEN item_cost_amount     ELSE 0 END) AS net_cost,
    SUM(CASE WHEN is_net_sale  THEN item_sale_minus_cost ELSE 0 END) AS gross_profit,
    SUM(CASE WHEN is_returned  THEN item_sale_amount     ELSE 0 END) AS returned_value,
    SUM(CASE WHEN is_cancelled THEN item_sale_amount     ELSE 0 END) AS cancelled_value,
    SUM(item_sale_amount)                                            AS gross_sales_all_status
FROM bi.v_sales_base
GROUP BY order_year, order_month, category;



-- 4) OPERATIONS


-- 4.1 การจัดส่ง
--     shipping_duration_days = order shipped -> delivered

CREATE OR REPLACE VIEW bi.v_ops_fulfillment AS
SELECT
    f.order_item_id,
    f.order_id,
    f.status AS item_status,
    dc.dc_name AS distribution_center_name,
    dc.latitude,
    dc.longitude,
    p.category,
    f.order_created_at,
    f.order_shipped_at,
    f.order_delivered_at,
    f.shipping_duration_days
FROM dw.fact_sales f
JOIN dw.dim_distribution_centers dc ON dc.distribution_center_key = f.distribution_center_key
JOIN dw.dim_products             p  ON p.product_key = f.product_key;

-- 4.2 สต็อก

CREATE OR REPLACE VIEW bi.v_ops_inventory AS
SELECT
    i.id                AS inventory_item_id,
    i.product_category  AS category,
    i.product_department AS department,
    dc.name             AS distribution_center_name,
    i.created_at        AS stocked_at,
    i.sold_at,
    CASE WHEN i.sold_at IS NULL THEN TRUE ELSE FALSE END AS not_sold_yet,
    i.cost
FROM stg.inventory_items i
JOIN stg.distribution_centers dc ON dc.id = i.product_distribution_center_id;


-- 5) MARKETING — ไม่มีชื่อ อีเมลเต็ม ที่อยู่ หรือ IP

-- 5.1 ลูกค้า 1 แถวต่อคน (โปรไฟล์ล่าสุด + ยอดซื้อรวมทุกเวอร์ชัน)
CREATE OR REPLACE VIEW bi.v_mkt_customers AS
SELECT
    u.user_id,
    u.age_group,
    u.gender,
    u.country,
    u.traffic_source,
    '***@' || SPLIT_PART(u.email, '@', 2) AS email_masked,
    COUNT(DISTINCT CASE WHEN s.is_net_sale THEN s.order_id END)              AS net_orders,
    COALESCE(SUM(CASE WHEN s.is_net_sale THEN s.item_sale_amount END), 0)    AS net_spend
FROM dw.dim_users u
LEFT JOIN bi.v_sales_base s ON s.user_id = u.user_id
WHERE u.is_current = TRUE
GROUP BY u.user_id, u.age_group, u.gender, u.country, u.traffic_source, u.email;

-- 5.2 funnel จาก web events — ข้อมูลประกอบ
--     เช็คค่าจริงก่อน: SELECT event_type, COUNT(*) FROM stg.events GROUP BY 1;

CREATE OR REPLACE VIEW bi.v_mkt_funnel AS
SELECT
    traffic_source,
    event_type,
    COUNT(DISTINCT session_id) AS sessions
FROM stg.events
GROUP BY traffic_source, event_type;


-- 6) สิทธิ์ตามฝ่าย — 1 group + 1 user ต่อฝ่าย (read-only, ไม่ใช่ admin)
--    Redshift บังคับ: 8 ตัวขึ้นไป มีพิมพ์ใหญ่ พิมพ์เล็ก ตัวเลข

-- 6.1 group + user
CREATE GROUP grp_executive;
CREATE GROUP grp_sales;
CREATE GROUP grp_finance;
CREATE GROUP grp_operations;
CREATE GROUP grp_marketing;

CREATE USER bi_executive  PASSWORD '<ตั้งรหัสเอง>' IN GROUP grp_executive;
CREATE USER bi_sales      PASSWORD '<ตั้งรหัสเอง>' IN GROUP grp_sales;
CREATE USER bi_finance    PASSWORD '<ตั้งรหัสเอง>' IN GROUP grp_finance;
CREATE USER bi_operations PASSWORD '<ตั้งรหัสเอง>' IN GROUP grp_operations;
CREATE USER bi_marketing  PASSWORD '<ตั้งรหัสเอง>' IN GROUP grp_marketing;

-- 6.2 สิทธิ์อ่าน view ของฝ่ายตัวเอง
GRANT USAGE ON SCHEMA bi TO GROUP grp_executive, GROUP grp_sales, GROUP grp_finance,
                            GROUP grp_operations, GROUP grp_marketing;

GRANT SELECT ON bi.v_exec_monthly, bi.v_finance_monthly, bi.v_mkt_funnel TO GROUP grp_executive;
GRANT SELECT ON bi.v_sales_detail                                        TO GROUP grp_sales;
GRANT SELECT ON bi.v_finance_monthly                                     TO GROUP grp_finance;
GRANT SELECT ON bi.v_ops_fulfillment, bi.v_ops_inventory                 TO GROUP grp_operations;
GRANT SELECT ON bi.v_mkt_customers, bi.v_mkt_funnel                      TO GROUP grp_marketing;

-- 6.3 USAGE บน schema ต้นทาง
--     USAGE = เข้า schema ได้เท่านั้น ไม่ได้ให้ SELECT บนตารางใน dw / reporting / stg
GRANT USAGE ON SCHEMA reporting TO GROUP grp_executive, GROUP grp_sales,
                                   GROUP grp_finance, GROUP grp_marketing;
GRANT USAGE ON SCHEMA dw        TO GROUP grp_executive, GROUP grp_sales, GROUP grp_finance,
                                   GROUP grp_operations, GROUP grp_marketing;
GRANT USAGE ON SCHEMA stg       TO GROUP grp_executive, GROUP grp_operations,
                                   GROUP grp_marketing;
-- ไม่มีใครได้สิทธิ์ SELECT ใน bi.v_sales_base, reporting, dw หรือ stg โดยตรง

-- 6.4 ตารางสรุปสิทธิ์
--   SELECT v.viewname AS view_name,
--     CASE WHEN HAS_TABLE_PRIVILEGE('bi_executive',  'bi.' || v.viewname, 'select') THEN 'Y' ELSE '-' END AS executive,
--     CASE WHEN HAS_TABLE_PRIVILEGE('bi_sales',      'bi.' || v.viewname, 'select') THEN 'Y' ELSE '-' END AS sales,
--     CASE WHEN HAS_TABLE_PRIVILEGE('bi_finance',    'bi.' || v.viewname, 'select') THEN 'Y' ELSE '-' END AS finance,
--     CASE WHEN HAS_TABLE_PRIVILEGE('bi_operations', 'bi.' || v.viewname, 'select') THEN 'Y' ELSE '-' END AS operations,
--     CASE WHEN HAS_TABLE_PRIVILEGE('bi_marketing',  'bi.' || v.viewname, 'select') THEN 'Y' ELSE '-' END AS marketing
--   FROM pg_views v WHERE v.schemaname = 'bi' ORDER BY 1;


-- 7) Permission testing — รันด้วย admin ใน Isolated session
--    คลุมรันทีละบล็อก และจบด้วย RESET เสมอ (เช็คว่า current_user = thelook-admin)

--   SET SESSION AUTHORIZATION 'bi_marketing';
--   SELECT current_user, user_id, country, traffic_source, email_masked, net_orders, net_spend
--   FROM bi.v_mkt_customers LIMIT 5;                         -- ผ่าน, อีเมลเป็น ***@...
--   SELECT * FROM bi.v_finance_monthly LIMIT 1;              -- permission denied (ข้ามฝ่าย)
--   SELECT * FROM dw.dim_users LIMIT 1;                      -- permission denied for relation dim_users
--   RESET SESSION AUTHORIZATION;
--
--   SET SESSION AUTHORIZATION 'bi_sales';
--   SELECT current_user, COUNT(*), SUM(item_sale_amount) FROM bi.v_sales_detail;  -- ผ่าน, 181759
--   SELECT item_cost_amount FROM bi.v_sales_base LIMIT 1;    -- permission denied
--   SELECT item_cost_amount FROM bi.v_sales_detail LIMIT 1;  -- column does not exist
--   RESET SESSION AUTHORIZATION;
--   SELECT current_user;                                     -- thelook-admin



-- 8) ตรวจยอดกับผลของทีม DW 

--   SELECT COUNT(*) FROM bi.v_sales_base;                          -- 181759
--   SELECT SUM(item_sale_amount) FROM bi.v_sales_base;             -- 10827118.925100
--   SELECT SUM(net_sales) FROM bi.v_exec_monthly;                  -- 8127336.728623
--   SELECT SUM(net_sales) FROM bi.v_finance_monthly;               -- 8127336.728623
--   SELECT COUNT(DISTINCT order_id) FROM bi.v_sales_base;          -- 125226
--   SELECT COUNT(*) FROM bi.v_sales_base WHERE is_net_sale;        -- 136437
--   SELECT SUM(cancelled_value) FROM bi.v_finance_monthly;         -- 1602475.453897
--   SELECT SUM(returned_value) FROM bi.v_finance_monthly;          -- 1097306.74258
--   SELECT COUNT(*) FROM bi.v_ops_fulfillment;                     -- 181759
--   SELECT COUNT(*) FROM bi.v_sales_base WHERE user_id IS NULL;    -- ต้องได้ 0
