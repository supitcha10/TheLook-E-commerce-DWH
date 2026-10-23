# Glue Data Catalog — ทำขณะ Redshift paused

ชุดนี้เตรียมไว้ในเครื่อง ยังไม่ได้สร้างหรือรัน crawler บน AWS ใช้ CloudShell region us-east-1 บัญชี 006816724683 และ LabRole เดิม ไม่มี schedule และไม่มีการแก้ Glue ETL/Redshift/S3 data

## 1. Upload script

ดาวน์โหลด `code/setup_glue_catalog.py` จาก workspace แล้วเปิด AWS Console → CloudShell → Actions → Upload file เลือกไฟล์นี้ ใน CloudShell รัน:

```bash
cd /home/cloudshell-user
python3 setup_glue_catalog.py plan curated
```

ตรวจ DatabaseName `thelook_curated`, Role ลงท้าย `LabRole` และ S3Targets 7 paths ใต้ batch `20261023T151247118967Z_f8a02155` แต่ละ target จบด้วยชื่อตาราง `/` ไม่ใช้ root `thelook/curated/` เพื่อไม่รวม batch เก่ากับใหม่

## 2. สร้างและรัน curated ก่อน

```bash
python3 setup_glue_catalog.py create curated
python3 setup_glue_catalog.py start curated
```

รอใน Glue → Crawlers ให้จบ แล้วรัน:

```bash
python3 setup_glue_catalog.py status curated
```

ต้องได้ `state: READY`, `last_crawl.Status: SUCCEEDED`, table_count 7 พร้อม classification parquet; READY อย่างเดียวไม่ได้แปลว่า crawl ผ่าน ส่ง `catalog_curated_status.json` กลับมาตรวจ schema ถ้า FAILED ให้ส่ง ErrorMessage และ crawler log

แต่ละ table location ต้องตรงโฟลเดอร์ตารางใน batch นี้ ไม่มี batch/table name ถูกสร้างเป็น partition ปนกัน ชื่อตารางอาจถูก crawler เติม suffix ให้ตรวจด้วย location แทนเดาชื่อ

## 3. สร้าง raw catalog

```bash
python3 setup_glue_catalog.py plan raw
python3 setup_glue_catalog.py create raw
python3 setup_glue_catalog.py start raw
```

เมื่อจบ:

```bash
python3 setup_glue_catalog.py status raw
```

Database `thelook_raw`, crawler `thelook-raw-crawler`; custom CSV classifier comma / double quote / header PRESENT; แต่ละ target เป็นไฟล์ CSV ของตารางนั้นโดยเฉพาะ ไม่ย้ายหรือเขียนข้อมูลต้นทางใหม่

ตรวจ 7 ตาราง, classification csv และชื่อ columns ตรง CSV header ผล infer types ของ raw ยังไม่ใช่ schema contract; decimal/timestamp อาจ infer ต่างจาก curated

Raw CSV ทั้งเจ็ดอยู่ folder เดียวกัน: catalog นี้ใช้ตรวจ discovery/metadata ก่อน ไม่ถือว่าพร้อมให้ Athena query เพราะ table location ที่ชี้ folder ร่วมอาจอ่านข้ามไฟล์ ต้องจัด source แยกโฟลเดอร์ตารางและตรวจ CSV SerDe ก่อนเปิดใช้ raw SQL ถ้าจำเป็น ส่วน BI ใช้ warehouse/views เป็นหลัก

## 4. เก็บหลักฐานและ gate

CloudShell Actions → Download file:

```text
/home/cloudshell-user/catalog_curated_status.json
/home/cloudshell-user/catalog_raw_status.json
```

เทียบ curated columns ตามลำดับกับ `code/curated_schema.json`: BIGINT→bigint, DOUBLE PRECISION→double, DECIMAL(18,6)→decimal(18,6), VARCHAR→string, BOOLEAN→boolean, DATE→date, TIMESTAMP→timestamp ตรวจ column เพิ่มจาก ETL กับ schema/report จริงด้วย อย่ากด Update schema ให้ตาม crawler โดยไม่ review

ถ้า table_count ไม่ใช่ 7 หรือ schema/location ผิด ให้หยุดส่งผลมาตรวจ ไม่รัน ETL ใหม่เพื่อแก้ Catalog และไม่ลบตารางเดิมเพื่อบังคับผ่าน

Script ไม่ overwrite crawler/classifier เดิมที่ชื่อซ้ำแต่ config ต่างกัน หากเจอ conflict ให้เปิดดู configuration เดิม; ถ้า AccessDenied ให้ส่ง action/resource ที่ถูกปฏิเสธให้ทีม Infra ไม่สร้าง role หรือ policy กว้างเพิ่มเอง

## ขอบเขตและขั้นถัดไป

Crawler สร้าง metadata ไม่ได้ตรวจ PK/FK/money/row counts แทน report เดิม หลัง schema review ผ่านจึงปิด checklist Catalog แล้วเตรียม SCD2/rollback fixtures ในฐานทดสอบ ก่อน orchestration และ schedule

ETL ปัจจุบันยังอ่าน S3 โดยตรงด้วย explicit schema; diagram ต้องแสดง Catalog เป็น metadata branch จนกว่าจะเพิ่มและทดสอบ Catalog contract check ใน pipeline

การรัน crawler ใช้บริการที่คิดค่าใช้จ่าย จึงสั่งรันครั้งละหนึ่งตัวและไม่ตั้ง schedule; ไม่ต้อง Resume cluster เพื่อ crawl S3

อ้างอิง AWS:
- [S3 include paths สามารถระบุไฟล์ได้](https://docs.aws.amazon.com/glue/latest/dg/define-crawler-choose-data-sources.html)
- [ใช้ include path แยกแต่ละ schema](https://docs.aws.amazon.com/glue/latest/dg/add-crawler.html)
- [Crawler grouping policy](https://docs.aws.amazon.com/glue/latest/dg/crawler-grouping-policy.html)
