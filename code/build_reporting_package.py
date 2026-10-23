"""Package reviewed SQL and BI documentation; never connects to AWS."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/aws/reporting-v1'


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'00_preflight.sql').write_text("""-- Run each statement separately. Stop if the selected database is wrong.
SELECT current_database() AS database_name;
CALL etl.assert_glue_validation_database();
SELECT batch_id,status,fact_rows FROM etl.batch_ledger ORDER BY observed_at;
SELECT COUNT(*) AS fact_rows,COUNT(DISTINCT order_id) AS distinct_orders,
       SUM(sale_price) AS sale_amount FROM dw.fact_sales;
SELECT table_name,table_type FROM information_schema.tables
WHERE table_schema='reporting' ORDER BY table_name;
""",encoding='utf-8')
    (OUT/'01_create_schema.sql').write_text('-- Only in thelook_glue_validation; commit this before creating views.\nCREATE SCHEMA IF NOT EXISTS reporting;\n',encoding='utf-8')
    for source,dest in [('code/sql/10_reporting_views.sql','02_create_views.sql'),('code/sql/11_reporting_checks.sql','03_validate_views.sql'),('docs/bi_handoff.md','BI_HANDOFF.md'),('docs/new_snapshot_pipeline_contract.md','NEW_SNAPSHOT_CONTRACT.md')]:
        shutil.copyfile(ROOT/source,OUT/dest)
    (OUT/'04_dashboard_queries.sql').write_text("""-- Use the same filters for comparisons. All amounts remain separated by item status.
SELECT item_status,COUNT(*) AS item_count,COUNT(DISTINCT order_id) AS distinct_orders,
       SUM(item_sale_amount) AS sale_amount,SUM(item_cost_amount) AS cost_amount
FROM reporting.v_sales_item GROUP BY item_status ORDER BY item_status;

-- Recompute DISTINCT at category grain, never sum product-level distinct_order_count.
SELECT category,item_status,COUNT(DISTINCT order_id) AS distinct_orders,
       COUNT(*) AS item_count,SUM(item_sale_amount) AS sale_amount
FROM reporting.v_sales_item GROUP BY category,item_status ORDER BY sale_amount DESC;

SELECT order_date_utc,item_status,item_count,sale_amount
FROM reporting.v_sales_daily_status ORDER BY order_date_utc,item_status;

SELECT source_batch_id,comparable_item_count,shipped_before_created_count,
       100.0*shipped_before_created_count/NULLIF(comparable_item_count,0) AS date_issue_pct
FROM reporting.v_sales_quality;

SELECT batch_id,attempted_at,status,detail FROM reporting.v_batch_attempt_history
WHERE status='FAILED' ORDER BY attempted_at DESC;
""",encoding='utf-8')
    (OUT/'README_TH.md').write_text('''# Reporting v1 — แยกตามสถานะ ยังไม่ใช่ net sales
SQL/เอกสารเตรียมในเครื่อง ยังไม่ได้ติดตั้ง Redshift หรือ QuickSight
## ติดตั้ง
1. Resume cluster รอ Available แล้วเลือก database thelook_glue_validation ใน Query Editor
2. 00_preflight.sql รันทีละคำสั่ง: database ต้องถูก, guard ไม่ error, ledger SUCCEEDED, fact181759/orders125226/sale10827118.925100
   ครั้งแรก schema reporting ควรไม่มี views ของชื่อเดียวกัน หากมีของทีมอื่นอยู่ให้หยุดตรวจ ห้ามทับโดยไม่ review
3. 01_create_schema.sql รันแยกให้สำเร็จ
4. 02_create_views.sql รัน CREATE OR REPLACE VIEW ทีละ statement (8ตัว) ตามลำดับ
   ไม่แก้ tables/facts และไม่โหลดข้อมูลใหม่ หาก error หยุดก่อน
5. 03_validate_views.sql รันตามลำดับ ต้องได้8checks PASS; ตรวจผลแยก status และ totals เทียบข้อ2
6. Export ผล checks/status totals เก็บเป็น reporting-validation.csv และ screenshots แล้วทดลอง04_dashboard_queries.sql
7. ส่ง BI_HANDOFF.md ให้ทีม BI ภายในช่องทางที่ทีมกำหนด (แพ็กนี้ไม่ได้ส่งข้อความให้ทีม)
## วิธีใช้
ไม่ต้อง upload SQL ไป CloudShell/S3; เปิดไฟล์ในเครื่อง คัดลอกไปรัน Query Editor
ขั้นนี้ไม่ติดตั้ง scheduler ไม่สร้าง BI user ไม่ให้สิทธิ์ PUBLIC และไม่มีข้อมูล PII โดยตรงใน views
การให้สิทธิ์ read-only/RLS และ network ให้ทีม Infra+BI ยืนยัน principal และนโยบายก่อน
ห้าม SUM distinct_order_count ข้ามสินค้า/DC/สถานะ ให้ใช้ v_sales_item แล้ว COUNT DISTINCT ใหม่
ข้อมูล current snapshot: sale_amount ทุกสถานะเป็นยอดตามต้นทาง ไม่ใช่เงินรับสุทธิ ไม่หัก Returned/Cancelled อัตโนมัติ
Currency ยังไม่ยืนยัน ไม่แปะหน่วยเงินเอง
ไม่มีข้อมูลภาษี/ค่าขนส่ง/ค่าธรรมเนียม จึงใช้ sale_minus_cost_amount แทนคำว่ากำไรรับรู้
## Verification limits
Local fixture tests5ผ่าน ใช้ SQLite ตรวจ relational logic โดยแปลงชื่อ schema; ไม่ใช่การ compile บน Redshift หรือทดสอบ DECIMAL engine จริง
Redshift queries ใน03ต้องผ่านก่อนถือว่าติดตั้งเสร็จ
Views ไม่ได้พึ่ง session TEMP tables; หลังเก็บผลและไม่มี queryค้าง pause cluster ได้
## งานค้างหลังนี้
BI dashboard/permissions, snapshot observation metadata, new-snapshot orchestration, alert delivery และ schedule ตาม contract
ดู NEW_SNAPSHOT_CONTRACT.md; ไม่มีการอ้างว่าข้อเหล่านี้เสร็จเพียงเพราะ replay ผ่าน
''',encoding='utf-8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='sha256.json'}
    (OUT/'sha256.json').write_text(json.dumps(hashes,indent=2))
    with zipfile.ZipFile(OUT.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.iterdir()):
            if p.is_file():z.write(p,p.name)
    print(OUT.with_suffix('.zip'))

if __name__=='__main__':build()
