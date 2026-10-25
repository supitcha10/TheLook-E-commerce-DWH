# วิธีติดตั้งและโหลดข้อมูลเข้า Redshift

สถานะ24ต.ค.2026: ติดตั้งและทดสอบAWSแล้ว รวมSCD/rollback/retry/reporting ดู [DW handoff](../../docs/dw_handoff.md). คู่มือด้านล่างเป็นขั้นติดตั้งครั้งแรก ไม่รันซ้ำกับฐานที่มีข้อมูล. Reporting SQL10/11ติดตั้งและตรวจแล้ว.

## ไฟล์และหน้าที่

| ไฟล์ | ใช้ทำอะไร |
|---|---|
| `00_control.sql` | สร้าง ledger, attempt log, input audit และผลตรวจแต่ละ batch |
| `01_staging.sql` | สร้าง `stg` 7 ตารางตามลำดับและชนิดคอลัมน์ใน curated Parquet |
| `02_warehouse.sql` | สร้าง `dw` 4 dimensions และ `fact_sales` ตาม dw-v1 |
| `03_load_batch.sql` | ติดตั้ง procedure `etl.load_batch` สำหรับ COPY, ตรวจข้อมูล, SCD และ publish |
| `04_post_load_checks.sql` | ตรวจสถานะโหลด จำนวนแถว คีย์ และยอดเงินหลังโหลด |
| `load_body.sql.inc` | ต้นฉบับส่วนโหลด ใช้กับ generator; ไม่ execute แยกไฟล์ |

`01`–`03` สร้างด้วย `python code/build_warehouse_sql.py`: staging มาจาก curated_schema.json, DW DDL มาจาก data_warehouse_schema_design.md และ procedure มาจาก load_body.sql.inc หากแก้ logic ให้แก้ต้นฉบับแล้ว generate ใหม่

คำสั่งในคู่มือนี้ให้รันจาก project root; ไฟล์ SQL อยู่ที่ `code/sql/` และเอกสาร schema อยู่ที่ `docs/`

## 1. เตรียม AWS และ config

- ใช้ S3 bucket กับ Redshift ใน `us-east-1` ตาม handoff โครงการ ตรวจ account/region จริงก่อนใช้งาน
- เตรียม Redshift provisioned หรือ Serverless, database และสิทธิ์สร้าง schema/table/procedure
- ผูก IAM role กับ Redshift และอนุญาตอ่าน S3 prefix ทั้งข้อมูลและ manifests; ถ้าใช้ SSE-KMS ต้องมีสิทธิ์ decrypt ของ key นั้น
- ตรวจ network/S3 endpoint และ policy ให้ COPY Parquet เข้าถึงไฟล์ได้
- SQL นี้อ่าน S3 Parquet โดยตรง ไม่ต้องรอ Glue crawler; Glue catalog/job เป็นงาน orchestration ที่ยังต้องทำหากใช้ตามสถาปัตยกรรมโครงการ
- กำหนด single writer สำหรับ pipeline นี้ ห้ามมี job อื่นเขียน stg/dw ระหว่างโหลด

คัดลอก `code/aws_batch_config.example.json` เป็น `code/aws_batch_config.json` แล้วใส่ bucket และ IAM role ARN จริง ห้ามใส่ access key ลง config

`observed_at` คือเวลา observation ของ snapshot ต้องคงเดิมเมื่อ retry; batch ใหม่ต้องมีเวลาหลัง batch ที่ publish ล่าสุด ไม่ใช่เวลาสุ่มใหม่ทุกครั้งที่เรียก SQL สำหรับข้อมูลชุดนี้กำหนดเวลา observation จาก batch curated ไว้เป็นค่าเริ่มต้น ไม่ใช่เวลาเปลี่ยนแปลงจริงในระบบต้นทาง

```powershell
python code/prepare_aws_batch.py --config code/aws_batch_config.json --output outputs/aws/20261018T070120429459Z
```

คำสั่งนี้สร้างเฉพาะไฟล์ในเครื่อง:

- `package.json`: identity ของ batch, hash, จำนวนแถว, ยอดเงินและตำแหน่ง S3
- `manifests/*.json`: 7 manifest ระบุไฟล์ตรงตัว พร้อม mandatory และ content_length
- `upload.ps1`: คำสั่ง upload ที่ต้องตรวจแล้วจึงเรียกใช้เอง
- `run_batch.sql`: temp control tables และ CALL ที่ใช้กับ batch นี้

จะไม่เขียนทับ output directory เดิม และปฏิเสธ config placeholder หรือ curated batch ที่ไม่ผ่าน DQ อย่าใช้ batch `20261018T065840511275Z` ที่ FAIL

## 2. Upload และติดตั้ง

1. ตรวจ `package.json` และ `upload.ps1` ว่าชี้ bucket/account/prefix ถูกต้อง
2. เก็บ prefix แต่ละ batch แบบ immutable อย่าแก้หรือเขียนทับหลังส่งมอบให้ loader หากไฟล์เปลี่ยนให้สร้าง curated batch ใหม่และตรวจ DQ ใหม่
3. เรียก `upload.ps1` ที่ generate แล้วเมื่อ AWS CLI ใช้ credentials ของบัญชีโครงการ ตรวจ upload สำเร็จครบ 7 data objects และ 7 manifests
4. ตรวจ object sizes กับ manifest และยืนยันไฟล์ที่ upload ตรงกับ SHA256 ของ package ด้วยการอ่านกลับตรวจ hash หรือใช้ S3 checksum ที่ตรงวิธีคำนวณ ห้ามเทียบ SHA256 กับ ETag โดยตรง
5. ใน Redshift database เป้าหมาย รัน `00_control.sql`, `01_staging.sql`, `02_warehouse.sql`, `03_load_batch.sql` ตามลำดับ

DDL เป็นการติดตั้งครั้งแรก หากมีตารางอยู่แล้วต้องตรวจ schema และทำ migration ที่เหมาะสม ไม่รัน DROP เพื่อเริ่มใหม่อัตโนมัติ COPY manifest ตรวจขนาด/ตำแหน่ง แต่ไม่ได้ตรวจ SHA256 ใน ledger ให้เอง จึงต้องรักษา immutable prefix และตรวจ upload

## 3. โหลดและตรวจผล

รัน `run_batch.sql` ทั้งไฟล์ **ใน session เดียว เปิด autocommit และไม่ครอบด้วย BEGIN** เพราะ procedure ใช้ temp tables ของ session นั้น หากใช้ Data API ต้องรักษา session เดิมระหว่างคำสั่ง

ขั้นตอนภายใน CALL:

1. Lock ledger เพื่อจัดลำดับ writer ตรวจ batch/version และเวลา observation
2. COPY Parquet ผ่าน manifest เข้า staging ทั้ง 7 ตารางด้วย DELETE + COPY
3. ตรวจจำนวนแถว, PK/FK, จำนวน items ต่อ order, parent mapping, city/date flags และยอดเงิน 5 คอลัมน์
4. Bootstrap หรือเพิ่ม SCD2 ของ users; update/insert products และ distribution centers แบบ Type1 โดยรักษาคีย์เดิม
5. สร้างปฏิทิน UTC และเตรียม fact หนึ่งแถวต่อ order item ตรวจ as-of user lookup ว่าตรงหนึ่ง version
6. ตรวจ grain, เงินและ date references ก่อนแทน fact ทั้ง snapshot แล้วบันทึก ledger

รัน `04_post_load_checks.sql` แล้วเก็บผลเป็นหลักฐาน ต้องมี `SUCCEEDED` ใน ledger, จำนวน fact 181,759 แถวสำหรับ batch ปัจจุบัน และไม่มี duplicate/current-version violation ยอดเงินควรตรง staging **ยอดรวมนี้รวมทุกสถานะ ไม่ใช่นิยาม net sales ที่อนุมัติแล้ว**

### Retry / failure

- Batch เดิม hash และ observed_at เดิมที่สำเร็จแล้วจะเป็น `NO_OP` ไม่เพิ่ม SCD version หรือโหลดซ้ำ
- Batch ID เดิมแต่ hash/เวลาเปลี่ยนจะ reject; rule/schema version เปลี่ยนต้องทำ migration ที่ review แล้ว
- Default atomic CALL ออกแบบให้ rollback staging, dimensions, fact และ success ledger พร้อมกันเมื่อเกิด error; handler บันทึก FAILED แล้วส่ง error ต่อ พฤติกรรมนี้ **ยังต้องพิสูจน์บน Redshift**
- Query cancellation ไม่เข้า `WHEN OTHERS` จึงอาจไม่มี FAILED ใน attempt log ตรวจ query history ร่วมด้วย
- First snapshot ของ users ใช้ valid_from=NULL เพื่อบอกว่าไม่รู้จุดเริ่มประวัติ ไม่อ้างว่าเป็นประวัติจริง; snapshot ถัดไปใช้ observation time และช่วง `[valid_from,valid_to)`
- User ใหม่ใน batch ถัดไปที่มี order ก่อน observation time จะไม่ถูกทิ้งเงียบ ๆ: as-of lookup จะ reject เพื่อให้ตัดสินใจ late-arriving policy

## 4. ทดสอบก่อน production

```powershell
python -m unittest discover -s code -p test_warehouse_sql.py -v
```

Local tests ตรวจ column order/types/nulls ของ Parquet จริง, manifest/hash, การปฏิเสธ batch FAIL, bootstrap joins/เงิน และสูตรระยะเวลาขนส่ง ไม่ใช่ SQL compilation หรือ integration test ของ Redshift

ผลล่าสุด: **4 tests PASS** ดู [รายงานผล](../../docs/report/warehouse_sql_local_validation.md) ต้องมี pandas และ pyarrow ตาม environment ของ curated pipeline (`code/requirements-curated.txt`) ก่อนรัน

- [ ] ติดตั้ง DDL/procedure ใน database ทดสอบสำเร็จ
- [ ] COPY Parquet ครบ 7 ตารางผ่านชนิดข้อมูลจริงบน Redshift
- [ ] Bootstrap และ post-load checks ผ่าน
- [ ] เรียก batch เดิมซ้ำได้ NO_OP และ key/version ไม่เปลี่ยน
- [ ] ใช้ fixture แยกทดสอบ user ไม่เปลี่ยน / เปลี่ยนรวม NULL / user ใหม่ / as-of ที่ขอบเวลา
- [ ] ทำ failure injection ในฐานทดสอบ ยืนยัน rollback และ FAILED log
- [ ] ทดสอบ late-arriving facts, concurrent writers และ query cancellation
- [ ] ตกลง metric/reporting status filters ก่อน BI

อ้างอิง: [COPY Parquet](https://docs.aws.amazon.com/redshift/latest/dg/copy-usage_notes-copy-from-columnar.html), [S3 manifest](https://docs.aws.amazon.com/redshift/latest/dg/copy-parameters-data-source-s3.html), [Procedure transactions](https://docs.aws.amazon.com/redshift/latest/dg/stored-procedure-transaction-management.html), [Error handling](https://docs.aws.amazon.com/redshift/latest/dg/stored-procedure-trapping-errors.html)

## SQL12: BI views และสิทธิ์ตามฝ่าย

เพิ่ม [12_bi_role_views_final.sql](12_bi_role_views_final.sql) บนฐาน thelook_glue_validation หลังชั้นreportingเดิม อ่าน [คู่มือBI role views](../../docs/bi_role_views.md) ก่อนรับช่วง:bi8views,5users/groups,นิยามnet_salesแยกจากยอดstatusเดิม

หัวSQLระบุรันแล้วแต่ยังไม่มีผลSQL12แนบ ห้ามexecuteทั้งไฟล์ซ้ำโดยเฉพาะส่วน6CREATE GROUP/USER รหัสในไฟล์เป็นplaceholderไม่ใช่credentialจริง SQLนี้ไม่ได้รวมในgeneratorหรือreporting package10/11อัตโนมัติ ส่วน8มีตัวอย่างตรวจ10SELECT; ส่วน7เป็นตัวอย่างmarketing/salesไม่ใช่testครบ5ฝ่าย ไม่มีRLS policyในไฟล์นี้
