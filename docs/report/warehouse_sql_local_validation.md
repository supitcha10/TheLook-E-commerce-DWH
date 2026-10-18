# ผลตรวจชุด SQL ในเครื่อง

วันที่: 2026-10-18 • ผล: **4 tests PASS** (`python -m unittest test_warehouse_sql -v`)

ข้อมูล: `outputs/curated/20261018T070120429459Z` • curated-v1 / provisional-v1 • เป้าหมาย dw-v1

| Test | สิ่งที่ตรวจ | ผล |
|---|---|---|
| staging_matches_actual_parquet_order_types_and_nulls | อ่าน Parquet จริงทั้ง 7 ตาราง เทียบลำดับคอลัมน์ Arrow types กับ staging DDL, จำนวนแถว และ NOT NULL | PASS |
| package_manifest_and_repeatable_identity | สร้าง package 2 ครั้งด้วย config fixture; identity เหมือนกัน; 7 manifests พร้อม size/hash/mandatory และ 5 monetary controls | PASS |
| placeholder_and_failed_batch_rejected | ปฏิเสธ config placeholder และ batch เดิมที่ FAIL | PASS |
| bootstrap_joins_grain_money_and_calendar | จำลอง join ด้วยข้อมูลจริงแบบ many-to-one ได้ 181,759 fact rows, item ID unique, ยอดเงินและกำไรตรง, calendar อยู่ในช่วงรองรับ และสูตรเวลา HALF_UP ตรง Decimal | PASS |

Package tests ใช้ bucket/role สมมติใน temporary directory และไม่ execute upload.ps1 ไม่มีการ upload ข้อมูลหรือเรียก AWS

ข้อจำกัด: ยังไม่ได้ compile/execute DDL หรือ procedure บน Redshift; ยังไม่ได้พิสูจน์ COPY ของ TIMESTAMPTZ/DECIMAL, transaction rollback, IDENTITY, retry no-op หรือ SCD updates บน engine จริง Local join test ตรวจ bootstrap เท่านั้น ไม่ใช่การทดสอบ SCD lifecycle ดู integration checklist ใน [คู่มือ](../../code/sql/README.md)

การรันครั้งแรกติดข้อจำกัด sandbox ใน temporary directory; รันใหม่ด้วยสิทธิ์ที่ได้รับอนุญาตแล้วผ่านครบ ไม่ใช่ข้อผิดพลาดของข้อมูล
