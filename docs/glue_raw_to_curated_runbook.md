# รัน Glue raw → curated

ไฟล์สำหรับวางใน AWS Glue Studio: `code/glue_raw_to_curated.py` ทั้งไฟล์
เป็น Spark job สำหรับ Glue 4.0 รวม schema และ known-issue baseline ไว้แล้ว
ไม่ต้องติดตั้ง pandas/pyarrow หรือเพิ่ม additional Python modules

## ตั้งค่าและเริ่มรัน

1. เปิด job `thelook-raw-to-curated` → Script
2. แทนที่โค้ดเริ่มต้นทั้งหมดด้วยไฟล์ `code/glue_raw_to_curated.py`
3. ตั้ง Script filename เป็น `glue_raw_to_curated.py`
4. Script path: `s3://thelook-dwh-20241022/thelook/scripts/`
5. ใช้ LabRole, Glue 4.0, Python 3, G.1X จำนวน 2 workers
6. Bookmark Disable, retries 0, timeout 20 นาที, concurrency 1
7. Temporary path: `s3://thelook-dwh-20241022/thelook/glue-temp/raw-to-curated/`
8. Spark UI logs path: `s3://thelook-dwh-20241022/thelook/spark-history/`
9. Connections ว่างได้สำหรับงาน S3 นี้ ไม่ต้องเปิด Redshift
10. ไม่ต้องเพิ่ม custom Job parameters โค้ดรับ JOB_NAME ที่ Glue ส่งให้
11. กด Save แล้ว Run หนึ่งครั้ง ติดตามจาก Runs

## Input

`s3://thelook-dwh-20241022/thelook/raw/initial-extract/`

ชื่อไฟล์: distribution_centers.csv, products.csv, users.csv, orders.csv,
order_items.csv, inventory_items.csv, events.csv
ต้องเป็น UTF-8 CSV มี header ตรง schema ทั้งชื่อและลำดับ
รองรับ quoted commas, doubled quotes และ quoted multiline fields
อย่าเปลี่ยนไฟล์ต้นฉบับระหว่างรัน

## สิ่งที่ script ทำ

- อ่าน CSV เป็นข้อความก่อนแปลงชนิด ตรวจ header และหยุดเมื่อ CSV ผิดรูปแบบ
- ตรวจ required, UTF-8 byte limits, integer ranges, positive IDs, finite coordinates
- เวลา ISO ต้องมี timezone และเก็บ UTC ที่ความละเอียด microseconds
- เงิน Decimal(18,6), ROUND_HALF_UP พร้อมผลรวมก่อน/หลังปัดเศษแบบ Decimal
- เก็บข้อความเดิม รวมทั้ง city แล้วเพิ่ม city_clean/city_missing_token
- ติดธง item_shipped_before_created โดยเก็บวันที่เดิม
- แถวแปลงไม่ได้แยก quarantine พร้อมเหตุผล และทำให้ validation ไม่ผ่าน
- ไม่ลบ duplicate หรือแก้ FK/date ให้ผ่านโดยอัตโนมัติ
- ตรวจ PK, FK, จำนวน items ต่อ order, user/order และ product/inventory consistency
- อ่าน Parquet กลับมาตรวจ schema, จำนวน, ค่าทุกแถวแบบ multiset และยอดเงิน
- คำนวณ SHA-256 ของ CSV เพื่อตรวจ known issues เทียบ baseline เดิม
- ตรวจ S3 version/ETag/ขนาด/last-modified ก่อนและหลังอ่านแต่ละตาราง
- ไม่มีการลบ raw, ไม่มีการโหลด Redshift, ไม่มีการสร้าง schedule

## Output และเกณฑ์ผ่าน

ทุกครั้งใช้ batch ID ใหม่ที่มี timestamp+random suffix ไม่ทับ batch เดิม

```text
s3://thelook-dwh-20241022/thelook/
  curated/<batch_id>/<table>/part-....snappy.parquet
  curated/<batch_id>/_READY.json
  control/<batch_id>/validation_report.json
  control/<batch_id>/validation_report.md
  quarantine/<batch_id>/<table>/...  (เฉพาะเมื่อพบ rejected rows)
```

ตรวจทั้งสามอย่าง:

1. Job run เป็น Succeeded
2. รายงาน status เป็น PASS_WITH_KNOWN_ISSUES และ checks ทุกข้อ PASS
3. มี curated/<batch_id>/_READY.json

Log จะมี RAW_TO_CURATED_START, VALIDATION_REPORT, TABLE_COMPLETE,
RAW_TO_CURATED_PASSED และ CURATED_OUTPUT พิมพ์ทั้ง stdout และ Glue logger
ใช้ batch ID ให้ตรงรอบล่าสุดเมื่อเปิด logs/report

Known issues เดิมที่ยังรอ source confirmation:

| Issue | จำนวน | จำนวนที่ตรวจเทียบ |
|---|---:|---:|
| users city NULL token | 958 | 100000 |
| events city NULL token | 23080 | 2431963 |
| order_items shipped ก่อน created | 35872 | 118281 |

จะนับเป็น KNOWN_ISSUE เฉพาะจำนวนและ SHA-256 ตรง baseline เท่านั้น
ถ้าต่างจะ REVIEW_REQUIRED และ job Failed เพื่อให้ตรวจข้อมูล ไม่ปรับ baseline อัตโนมัติ
ไฟล์ที่เปลี่ยน newline/encoding แม้ค่าคล้ายเดิมก็อาจ hash ต่าง ต้องตรวจที่มา

FAIL = quality checks ไม่ผ่าน; FAILED_INCOMPLETE = exception ระหว่างทำงาน
รายงานอัปเดตหลังแต่ละตาราง ถ้า timeout/ถูกหยุดอาจค้าง RUNNING
candidate Parquet อาจมีบางส่วน แต่ห้ามใช้ถ้าไม่มี _READY.json
อย่าใช้ไฟล์ _SUCCESS ของ Spark เป็นหลักฐานว่า data quality ผ่าน
Quarantine มีข้อมูลต้นฉบับ จึงไม่ควรเปิดเผยไฟล์หรือแถวเหล่านั้นในแชต

## ขอบเขตก่อนโหลด Redshift

Spark เขียนหลาย part files ต่อหนึ่งตาราง ซึ่งต่างจากตัวสร้าง package เดิมที่คาดหวัง
ไฟล์เดียวต่อหนึ่งตาราง ห้ามใช้ manifest/package เก่ากับ output ใหม่นี้
ต้องทำขั้น package/manifests สำหรับทุก part file หลังผลรันผ่านก่อนโหลด Redshift
script ไม่เดาเวลา source snapshot: source_observed_at เป็น null; processed_at คือเวลารันเท่านั้น
การโหลดข้อมูลเดิมซ้ำผ่าน Glue ไม่ได้ทำให้เป็น snapshot ใหม่โดยอัตโนมัติ

## การตรวจในเครื่อง

แก้กรณี Spark 3.3.0 SPARK-39612 (`Couldn't find ... in [sum...]`):
การตรวจ readback ใช้ union ของแถว typed พร้อมน้ำหนัก +1/-1 แล้ว groupBy ทั้งแถว
แทน exceptAll().count() โดยยังตรวจจำนวนแถวซ้ำและ NULL ครบ ไม่ใช้ hash แทนค่าจริง
หากเคยเจอ error นี้ ให้คัดลอก script เวอร์ชันล่าสุดทั้งไฟล์ Save แล้ว Run ใหม่หนึ่งครั้ง
batch ที่ล้มเหลวไม่มี _READY.json และไม่ต้องนำไปโหลด Redshift

`python -m unittest discover -s code -p test_glue_raw_to_curated.py -v`

ทดสอบ pure conversion functions และตัวอย่าง 1,000 แถวแรกต่อ CSV (distribution_centers มีเพียง 10)
ไม่ใช่การทดสอบ Spark/Glue/S3 จริง ต้องยืนยัน integration ด้วย job run บน AWS
