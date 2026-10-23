# Glue → warehouse: package และ SQL สำหรับฐานข้อมูลทดสอบ

Batch: `20261023T151247118967Z_f8a02155`

เป้าหมาย: `thelook_glue_validation` บน cluster เดิม ไม่ใช่ `dev`
เก็บ `glue_copy_check` ที่ทดสอบ COPY สำเร็จแล้วไว้ ไม่ต้องลบหรือโหลดซ้ำ

## A. ทำ package ให้สมบูรณ์ใน CloudShell (Redshift ยัง Paused ได้)

1. เปิด AWS CloudShell ใน account 006816724683, us-east-1
2. Actions → Upload file → อัปโหลด `glue-warehouse-bundle.zip`
3. รัน:

```bash
unzip glue-warehouse-bundle.zip
python3 glue-warehouse-bundle/finalize_package.py --output glue-warehouse-ready
```

สคริปต์ตรวจ READY/report/manifest จาก S3, ตรวจรายชื่อ+ขนาด 28 part files,
อ่านข้อมูลจริงประมาณ 226.6 MB เพื่อคำนวณ SHA-256 แล้วตรวจ metadata ซ้ำ
ไม่ใช้ ETag แทน SHA-256 ไม่เขียน S3 ไม่เรียก Redshift ไม่อ่าน secret
พิมพ์ HASHING ทีละไฟล์ แล้วจบด้วย PACKAGE_READY / PACKAGE_HASH / DOWNLOAD
ถ้า error ให้หยุดและส่งข้อความ error ไม่แก้ evidence เพื่อข้ามการตรวจ

4. Actions → Download file → ใช้ path จาก DOWNLOAD เช่น
   `/home/cloudshell-user/glue-warehouse-ready.zip`
5. แตก ZIP ในเครื่อง จะได้ package.json, manifests 7 ไฟล์, SQL ครบ และ artifact_sha256.json

ไม่ต้องอัปโหลด Parquet หรือ manifest ใหม่: สคริปต์ตรวจว่า manifest ที่อัปโหลดและทดสอบ COPY แล้วตรงกัน
เก็บ package/SQL/hash เป็นหลักฐาน ถ้าต้องเก็บใน S3 ใช้ prefix control ของ batch นี้ภายหลัง
ห้ามแก้/แทนที่ข้อมูลใน curated batch หลัง finalize เพราะ COPY ไม่ตรวจ SHA-256 ใน package ให้เอง
หากเว้นช่วงนาน ให้ตรวจไฟล์อีกครั้งก่อนโหลด และเปรียบเทียบ package hash เดิม
ไม่ใช้ `--output` ซ้ำกับโฟลเดอร์ที่มีอยู่; ใช้ชื่อใหม่เพื่อตรวจซ้ำและเก็บฉบับเดิม

## B. ความหมายของเวลาและ hash

CSV ทั้งเจ็ดตรง SHA-256 กับ local baseline เดิม ไม่มีการอ้างว่าเป็น snapshot ใหม่
`source_observed_at` ยังคง null เพราะไม่มีเวลาที่ต้นทางยืนยัน
ใช้ `2026-10-22T18:59:01.935624+00:00` เป็น observation anchor เดิมสำหรับ bootstrap
ในฐานข้อมูลทดสอบเท่านั้น ค่านี้เดิมอนุมานจาก deployment timestamp ไม่ใช่เวลาเปลี่ยนแปลงต้นทาง
ระบุข้อจำกัดใน package.observation_time_basis ไม่ใช้ processed_at ของ Glue แทนเวลา source

package เก็บ SHA-256 ของแต่ละ part และ content-set SHA256 ต่อตาราง:
SHA256 ของ canonical JSON ของรายการ {url,content_length,sha256} เรียง URL
ฟิลด์เดิม `etl.batch_inputs.file_sha256` เก็บ content-set digest นี้สำหรับ multipart package
ไม่ใช่การอ้างว่ามีไฟล์เดี่ยวชื่อ data.parquet; ตรวจรายละเอียดทุก part ได้ใน package.json
package_hash คือ SHA256 ของ canonical JSON ทั้ง package ก่อนเพิ่มฟิลด์ package_hash

## C. Resume และตรวจ database

1. Resume cluster รอ Available; ไม่ต้องสร้าง cluster/database ใหม่
2. Query Editor v2 เลือก database `thelook_glue_validation`
3. เปิด Autocommit ไม่ครอบขั้นตอนด้วย BEGIN และอย่าเปิด writer อื่นพร้อมกัน
4. รัน `sql/00_preflight.sql`
5. ต้องเห็น current_database=thelook_glue_validation และยังไม่มีตารางใน etl/stg/dw
   ถ้ามีตารางอยู่แล้ว หยุดตรวจสถานะก่อน ไม่รัน DROP หรือติดตั้งซ้ำอัตโนมัติ

## D. ติดตั้งครั้งแรก

1. `00a_create_schemas.sql`: รัน CREATE SCHEMA แต่ละคำสั่งแยกและให้ commit ก่อน
2. `01_control_tables.sql`: สร้าง control tables
3. `02_staging_tables.sql`: สร้าง stg เจ็ดตาราง
4. `03_warehouse_tables.sql`: สร้าง dw สี่ dimensions และ fact_sales
5. `04_install_procedures.sql`: เลือกรัน CREATE PROCEDURE ทีละก้อนจนถึง $$ LANGUAGE plpgsql;
   มีสอง procedure คือ assert_glue_validation_database และ load_batch

ทุกไฟล์ต้องอยู่ database ทดสอบ หยุดทันทีเมื่อ error อย่ารันข้ามไฟล์ที่ล้มเหลว
load_batch ฉบับ bundle ตรวจ database ก่อนเขียนข้อมูล ใช้ procedure ต้นฉบับของโปรเจกต์
ที่เพิ่ม database guard และคุม error-audit ให้เขียนเฉพาะ database ทดสอบ
ไม่ได้แก้ SQL ต้นฉบับสำหรับ dev และไม่ได้เพิ่มการสร้าง schema ไว้ใน procedure

## E. โหลดและตรวจผล

1. รัน `05_run_batch.sql` จาก finalized ZIP ทั้งไฟล์ใน session เดียว
   ถ้าต้องเลือกทีละ statement ให้คง query tab/connection/session เดิม
   temp expected_inputs/expected_money ต้องอยู่ session เดียวกับ CALL
2. ต้องได้ ledger SUCCEEDED ของ batch นี้และ package_hash ตรง package.json
3. รัน `06_post_load_checks.sql`
4. จำนวน staging ต้องตรงรายงาน: 10, 29120, 100000, 125226, 181759, 490705, 2431963
5. dim_distribution_centers=10, dim_products=29120, dim_users total/current=100000,
   fact_sales=181759; duplicate queries ต้องคืน 0 แถว
6. ยอด sale_price และ product_cost ระหว่าง staging join กับ warehouse ต้องตรง
   ยอดเหล่านี้รวมทุก status ไม่ใช่นิยาม recognized revenue
7. etl.batch_checks ต้องไม่มี FAIL; known issues เดิมยังคงแสดงอย่างชัดเจน

## F. ทดสอบ NO_OP

รัน `07_test_no_op.sql` หลัง E ผ่านแล้ว ใน session เดียวและ Autocommit ON
ไฟล์จะ snapshot ข้อมูล dw ทั้งห้าตารางและ ledger/inputs/checks ใน temp tables,
เรียก package เดิม แล้วเปรียบเทียบค่าจริงและจำนวนแถวก่อน/หลัง
ต้องได้ PASS ทุกแถว และมี NO_OP attempt เพิ่มหนึ่งรายการ
อย่ารันไฟล์ทดสอบนี้ซ้ำใน session เดิมเพราะ temp snapshots มีอยู่แล้ว
ถ้าต้องทดสอบใหม่ให้เปิด session ใหม่หลังยืนยันผลเดิม

## สิ่งที่ยังไม่ใช่ผลทดสอบบน AWS

การเตรียม bundle และ unit tests ในเครื่องไม่ยืนยันการติดตั้ง/โหลด warehouse บน AWS
ต้องเก็บผล E/F เป็นหลักฐานจริง การ COPY ใน glue_copy_check ที่ผ่านแล้วเป็นคนละขั้น
ไม่ต้องแก้ JDBC connection เดิมที่ชี้ /dev เพื่อทดสอบผ่าน Query Editor นี้
เมื่อสำเร็จจึงเตรียม orchestration/schedule ภายหลัง ยังไม่เปิด schedule อัตโนมัติ
