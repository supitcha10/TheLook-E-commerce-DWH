# BI views ตามฝ่าย — SQL 12

อัปเดต 25 ตุลาคม 2026 (พ.ศ. 2569) อ้างอิง [12_bi_role_views_final.sql](../code/sql/12_bi_role_views_final.sql) ใน repository เป้าหมาย cluster `thelook-redshift-cluster-1` / database `thelook_glue_validation`

## ขอบเขตและระดับหลักฐาน

SQL เพิ่ม schema `bi` และ 8 views เหนือ `reporting`/`dw`/`stg` เดิม ไม่เปลี่ยน grain ของ fact_sales หรือขอบเขต Kaggle Version 1 แบบคงที่ และไม่เพิ่ม scheduler

หัวไฟล์ SQL ระบุว่ารันจริงแล้ว สร้าง group/user และตรวจสิทธิ์ผ่านหลังเพิ่ม schema USAGE เอกสารนี้บันทึกเป็น **สถานะตามผู้จัดทำ SQL** ยังไม่มีภาพ/CSV/log ของ SQL12 แนบในชุดหลักฐาน จึงไม่รับรอง live deployment หรือ effective privileges โดยการอ่านโค้ดอย่างเดียว การมี SQL ไม่ใช่การรับมอบ Dashboard หรือการเชื่อมต่อเครื่องมือ BI แล้ว

SQL10/11 และ reporting8checks เป็นชั้นเดิมแยกต่างหาก ส่วน SQL12 มี 8 views (base ภายใน1 + viewsสำหรับฝ่าย7) และมีตัวอย่าง SELECT ตรวจยอดในส่วน8 **10คำสั่ง** แม้หัว SQL เขียนว่า9ข้อ ยังไม่แก้ไฟล์ SQL ของผู้ใช้หรือสร้างผลทดสอบแทน

## Views และ grain

| View | Grain / ความหมาย |
|---|---|
| `bi.v_sales_base` | 1 order item; reporting detail join fact ด้วย order_item_id แล้ว join dim_users ด้วย historical user_key เพื่อเพิ่ม user_id/flags; ไม่ให้ฝ่ายอ่าน base โดยตรงตาม GRANT ที่เขียน |
| `bi.v_exec_monthly` | ปี+เดือนตาม order date UTC; net_orders/net_sales/gross_profit/active_customers และ all-status amount/cancel/return rates |
| `bi.v_sales_detail` | 1 order item ทุกสถานะ; ไม่มีคอลัมน์ต้นทุน/กำไร; ใช้ is_net_sale สำหรับกรองยอด BI |
| `bi.v_finance_monthly` | ปี+เดือน+category; net sales/cost, arithmetic margin, returned/cancelled values และยอดทุกสถานะ |
| `bi.v_ops_fulfillment` | 1 order item; วันระดับ order, DC, category; shipping_duration_days คือ order shipped→delivered ไม่ใช่เวลารวมตั้งแต่สั่งซื้อ |
| `bi.v_ops_inventory` | 1 inventory item ที่ join DC ได้; อ่าน staging, not_sold_yet = sold_at IS NULL ณข้อมูลชุดนี้ ไม่ใช่ stock ณวันนี้หรือ stockย้อนหลังที่ยืนยันแล้ว |
| `bi.v_mkt_customers` | 1 current user profile พร้อมยอด net orders/spend รวม facts ทุก version ด้วย user_id; รวมผู้ไม่มีการซื้อด้วยค่า0 |
| `bi.v_mkt_funnel` | traffic_source+event_type; COUNT(DISTINCT session_id) ภายในกลุ่ม เป็นจำนวน sessions ต่อ event ไม่ใช่ ordered funnel/conversion rate ที่พิสูจน์แล้ว |

Inventory และ events เป็น views อ่าน staging เพิ่ม ไม่ใช่ fact_inventory/fact_events ใหม่ และไม่ใช่ Dashboard ที่ deploy แล้ว inner join อาจตัดแถวหาก reference ไม่ครบ จึงต้องตรวจ count แยกสำหรับ inventory/fulfillment

## นิยาม metric ของ BI

- SQL12 ใช้ `net_sales` = ยอดของ items ที่ status ไม่ใช่ Cancelled/Returned สำหรับชุดปัจจุบันคือ Complete+Processing+Shipped เป็นนิยาม BI ในไฟล์ ไม่ใช่ recognized revenue; รวม Processing/Shipped ด้วย
- Net items **136437**, net sales **8127336.728623** คำนวณอ้างอิงจากยอดสถานะเดิม ทุกสถานะ **10827118.925100** หัก Cancelled **1602475.453897** และ Returned **1097306.742580** ตัวเลขอ้างอิงนี้ไม่ใช่ผล execute SQL12 ใหม่
- `gross_profit` เป็น sale minus inventory-item cost ของ net population ไม่รวมค่าใช้จ่ายอื่น ไม่รับรองกำไรทางบัญชี
- cancel_rate/return_rate เป็นสัดส่วน **itemsทุกสถานะ** ในแต่ละเดือน ค่า0–1 ไม่ใช่สัดส่วน orders และไม่เฉลี่ยเปอร์เซ็นต์รายเดือนแบบไม่ถ่วงน้ำหนัก
- net_orders และ active_customers เป็น DISTINCT ภายในกลุ่ม ห้าม SUM ข้ามเดือน/category แล้วเรียก unique รวม ให้คำนวณใหม่จาก detail ที่มีสิทธิ์เข้าถึง
- Monthly views ไม่มี status/dateละเอียดครบทุกคอลัมน์ จึงไม่ใช่แหล่งสำหรับ filter ทุกแบบเหมือน detail
- `v_mkt_customers` ใช้ demographics ปัจจุบัน ต่างจาก reporting detail ที่ใช้ attributes ตาม historical user_key; จึงไม่ควรคาดว่าแบ่งกลุ่มลูกค้าตรงกันเสมอ
- `email_masked` เก็บ domain ของ email และยังมี user_id/demographics ไม่ถือว่า anonymous; ไม่แสดงชื่อ อีเมลเต็ม ที่อยู่ หรือ IP ใน marketing views ตามคอลัมน์ที่เลือก
- Currency, source snapshot time และ known issues ยังมีข้อจำกัดตาม [ข้อมูลต้นทาง](source_dataset_acceptance.md); การเพิ่ม views ไม่ยืนยันต้นทางหรือยกเลิก provisional-v1

## ตาราง GRANT ที่เขียนใน SQL

| User / group | Views ที่ GRANT SELECT |
|---|---|
| `bi_executive` / `grp_executive` | v_exec_monthly, v_finance_monthly, v_mkt_funnel |
| `bi_sales` / `grp_sales` | v_sales_detail |
| `bi_finance` / `grp_finance` | v_finance_monthly |
| `bi_operations` / `grp_operations` | v_ops_fulfillment, v_ops_inventory (มี cost) |
| `bi_marketing` / `grp_marketing` | v_mkt_customers, v_mkt_funnel |

ใช้ database users/groups ไม่ใช่ IAM roles และยังไม่มี row-level security policy ใน SQLนี้ ข้อกำหนด RLS ต้องตกลงแยก SQLให้ schema USAGE ตาม dependencies แต่ไม่ได้เขียน GRANT SELECT บน base/source tables โดยตรง อย่างไรก็ตามไม่มี REVOKE สิทธิ์เดิม และอาจมี PUBLIC/สมาชิกกลุ่ม/เจ้าของ/superuser privileges อยู่ก่อน จึงต้องตรวจ effective privileges จริงก่อนรับรองการแยกฝ่าย

## วิธีรับช่วงและเกณฑ์ตรวจ

1. ยืนยัน database และ inventory ของ views/users/groups เดิมก่อน หากติดตั้งแล้วห้ามรันทั้งไฟล์ซ้ำ โดยเฉพาะส่วน6 CREATE GROUP/USER และไม่วาง password จริงลง repository Placeholder `<ตั้งรหัสเอง>` ไม่ใช่รหัสสำหรับใช้งาน
2. SQLนี้ไม่ถูกเพิ่มเข้า generator/package SQL10/11 อัตโนมัติ ต้องจัดส่งไฟล์12แยก การปรับเอกสารรอบนี้ไม่ execute CREATE/GRANT/SET SESSION AUTHORIZATION ใดบน AWS
3. เก็บผล SELECT ส่วน8ทั้ง10คำสั่ง: base count/amount, executive+finance net, distinctorders, netitems, cancelled/returned, fulfillment count และ user_id NULL=0 นอกจากนี้ตรวจ grain/reference ของ viewsใหม่ และ inventory/events counts/schema ให้ตรงต้นทางก่อนใช้ metric
4. เก็บ permission matrix ของทั้ง5users แล้วทดสอบ positive/negative ตามกลุ่มจริง ทั้งอ่าน viewตนเอง อ่านข้ามฝ่ายที่ไม่อนุญาต อ่าน base/source และตรวจ column exposure; ตัวอย่างส่วน7 มีเฉพาะ marketing/sales ยังไม่ใช่ผลครบทุกฝ่าย หากใช้ session authorization ให้ RESET และตรวจ current_user หลังทุกบล็อก
5. ต้องมีหลักฐาน effective privileges และผล query ระบุฐาน/ผู้ใช้/วันที่ก่อนติ๊กเป็น verified; การจัดทำ SQLและคำบรรยายว่าผ่านแล้วแยกจากหลักฐานที่รวบรวมจริง

- [x] มี SQL12 และจัดทำ dictionary/grain/permission map จากโค้ด
- [ ] รวบรวมผลตรวจยอดส่วน8และกรณีเสริมของ viewsใหม่
- [ ] รวบรวม matrix และ positive/negative access tests ครบ5กลุ่ม
- [ ] ยืนยันเครื่องมือ BI, network, RLS requirement และ Dashboard acceptance
- [ ] DW/BI ยืนยัน known issues และรับมอบจริง

ดู [BI handoff](bi_handoff.md), [DW handoff](dw_handoff.md) และ [reporting acceptanceเดิม](report/reporting_acceptance_20261024.md) ประกอบ
