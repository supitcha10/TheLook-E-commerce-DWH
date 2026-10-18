# ตรวจความพร้อมนำ Data Warehouse ขึ้น AWS

> อัปเดตหลังรายงานนี้: มี schema dw-v1 และชุด staging/load SQL แล้ว ดู [WORK_PROGRESS.md](../../WORK_PROGRESS.md) และ [คู่มือ SQL](../../code/sql/README.md) ข้อความงาน SQL ที่ยังค้างด้านล่างเป็นสถานะ ณ ตอนตรวจเดิม; การติดตั้งและทดสอบ AWS ยังไม่ได้ทำ

วันที่ตรวจ: 18 ตุลาคม 2026

## ข้อสรุป

**ข้อมูลพร้อมสำหรับอัปโหลด S3 และเริ่มทดสอบการโหลด เมื่อ bucket/สิทธิ์พร้อม แต่ยังไม่พร้อม deploy pipeline หรือเปิดใช้ warehouse ครบวงจร**

ขอบเขตการตรวจคือไฟล์ในโปรเจกต์ แบบ schema ใหม่ โค้ด รายงานผล และเอกสาร AWS อย่างเป็นทางการ ไม่ได้เข้าบัญชี AWS จริง จึงยังยืนยันไม่ได้ว่าทรัพยากร IAM งบและเส้นทางเครือข่ายใน Lab พร้อมใช้งาน ณ ปัจจุบัน เอกสาร schema ใช้เป็นสิ่งที่ตรวจทาน ไม่ใช่คำสั่งให้สร้างทรัพยากร

## สิ่งที่ตรวจและยืนยันได้

- อ่าน [แบบ DW schema](../data_warehouse_schema_design.md), [Data Dictionary](../dataset_dictionary_and_cleaning.md), [handoff](../handoff1.md), โค้ด curated และรายงานผล
- รัน unit tests ของ curated pipeline ซ้ำ: 3 tests ผ่าน
- ตรวจ SHA-256 ของ CSV ทั้ง 7 ไฟล์ ยังตรงกับ manifest ของ batch ที่ผ่าน
- ตรวจ metadata ของ Parquet ทั้ง 7 ไฟล์ จำนวนแถวและคอลัมน์ตรงกับผลที่บันทึกไว้
- ผลตรวจรับเดิมของ batch `20261018T070120429459Z` คือ 52 checks ผ่าน รวม 3,358,783 แถว ไม่มี quarantine; รอบ review นี้ไม่ได้รัน conversion และ 52 checks ทั้งหมดใหม่
- ตรวจเพิ่มโดย join order_items กับ products: sale_price เท่ากับ products.retail_price ทั้ง 181,759 รายการใน curated snapshot นี้ ดังนั้นสูตรส่วนลดที่เสนอให้ค่า 0 ทุกแถวเมื่อใช้ราคาจากแค็ตตาล็อกนี้ ไม่ใช่หลักฐานว่าส่วนลดจริงของธุรกิจเป็นศูนย์

## ความพร้อมแยกส่วน

| ส่วน | สถานะ | หลักฐาน / สิ่งที่ขาด |
|---|---|---|
| Raw CSV และ Data Dictionary | พร้อมสำหรับงานทดลอง | มี 7 ตาราง schema และกฎชั่วคราว |
| Curated Parquet | พร้อมสำหรับ upload | ใช้เฉพาะ batch ที่ผ่านตามด้านบน; known issue ยังรอยืนยัน |
| Local pipeline | ทดสอบในเครื่องแล้ว | ใช้ Python 3.12, pandas 3.0.1, pyarrow 26.0.0 และ local paths |
| DW conceptual model | มีร่าง | 1 fact/4 dimensions; ต้องแก้รายละเอียดก่อน implementation |
| Redshift staging/COPY | ยังไม่พร้อม | ไม่มี DDL staging 7 ตาราง และไม่มี COPY script |
| Dimension/fact load | ยังไม่พร้อม | ไม่มี SQL mapping, key generation, SCD processing หรือ reload transaction |
| Glue execution | ยังไม่พร้อม | ไม่มี job สำหรับ S3 I/O, arguments, runtime dependencies และการรันใน AWS |
| AWS resources/IAM/network | ยังยืนยันไม่ได้ | อ้างอิง handoff เท่านั้น ต้องตรวจบัญชีจริง |
| BI และการส่งมอบ | ยังไม่ครบ | มีแนวคิด views แต่ยังไม่มี executable views/dashboard และผลตรวจรับบน AWS |

## จุดที่ต้องแก้/ตกลงก่อนโหลด warehouse

### 1. ต้องมี staging ที่ตรง Parquet และ mapping เข้า star schema

Curated เป็นตารางต้นทาง ไม่ใช่ dim/fact: users มี 17 คอลัมน์, events 15, order_items 13 รวมคอลัมน์ flags ที่เพิ่มแล้ว ไม่สามารถใช้ COPY ชุดเหล่านี้เข้าตารางมิติตาม DDL ปัจจุบันโดยตรงได้

ต้องเขียน staging DDL ให้สอดคล้องกับชนิดและลำดับคอลัมน์ของ Parquet จริง แล้วทำ INSERT/transform จาก staging ไป dim/fact โดยระบุคอลัมน์ชัดเจน ทดสอบ timestamp UTC และ Decimal กับ Redshift จริงก่อนโหลดครบชุด AWS ระบุว่า COPY จาก columnar files จับคู่ตามลำดับคอลัมน์ และ S3 bucket ต้องอยู่ region เดียวกับ Redshift [AWS: COPY from columnar formats](https://docs.aws.amazon.com/redshift/latest/dg/copy-usage_notes-copy-from-columnar.html)

### 2. ชนิดเงินไม่ตรงกันระหว่าง curated และ DW

Curated ใช้ DECIMAL(18,6) แต่แบบ DW ใช้ DECIMAL(10,2) ทั้งต้นทุน ราคา และ measures การลดเป็นสองตำแหน่งทำให้เกิด rounding อีกชั้น และทำให้ยอดเงินเปลี่ยนจากค่าที่เพิ่งตรวจรับ

ข้อเสนอ: เก็บราคา/ต้นทุนที่ 6 ตำแหน่งใน storage และกำหนด precision ของค่าคำนวณให้รองรับผลลัพธ์ ปัดเพื่อแสดงผลใน BI หากต้องการ 2 ตำแหน่งใน DW จริง ต้องกำหนดกฎและตรวจยอดใหม่ ไม่ถือว่า 52 checks ของ curated รับรองผลสองตำแหน่งแล้ว

### 3. SCD Type 2 ยังขาดกติกาเริ่มต้นและ logic โหลด

ข้อมูล users เป็น snapshot เดียว จึงสร้างประวัติย้อนหลังจริงไม่ได้ `valid_from DEFAULT CURRENT_TIMESTAMP` ทำให้วันที่เริ่มต้นเป็นวันโหลด ซึ่งใหม่กว่าคำสั่งซื้อปี 2019–2024 หาก join facts แบบ as-of จะไม่พบเวอร์ชันลูกค้าที่ครอบคลุมคำสั่งซื้อเหล่านั้น

ต้องเลือกว่าเริ่มแบบ snapshot/Type 1 หรือเริ่ม SCD2 โดยประกาศชัดว่าเวอร์ชันแรกเป็น bootstrap snapshot ไม่ใช่ประวัติจริง และกำหนดการผูก facts เก่ากับเวอร์ชันนี้ รวมถึงคอลัมน์ที่ติดตาม วิธีปิด valid_to การตรวจช่วงเวลาซ้อน และการโหลดซ้ำไม่สร้างเวอร์ชันซ้ำ

Surrogate keys ใน DDL เป็น INT PRIMARY KEY อย่างเดียว ยังไม่มี IDENTITY หรือ logic สร้าง key ใน ETL ต้องเลือกและเขียนวิธีสร้าง/lookup ให้ครบ

### 4. Mapping และ known issue ต้องไม่หายเมื่อเข้ามิติ/fact

ต้องระบุอย่างน้อย:

- dim_users.city มาจาก users.city_clean; เก็บ raw city และแฟล็กใน staging/ตารางตรวจสอบไว้ย้อนกลับได้
- fact order_date ใช้ orders.created_at ไม่ใช้ order_items.created_at ที่ยังมี known issue
- product_cost มาจาก inventory_items.cost โดย join ผ่าน inventory_item_id หากเลือกต้นทุนรายชิ้น
- distribution_center เลือกแหล่งอ้างอิงให้ชัดระหว่าง inventory_items.product_distribution_center_id กับ products.distribution_center_id
- เก็บ item_shipped_before_created และข้อมูล batch/เวอร์ชันกฎในตำแหน่งที่ติดตาม fact กลับไปหา source ได้ แม้ไม่จำเป็นต้องวางทุก flag ใน fact
- shipping_duration_days ระบุคู่วันและวิธีคำนวณให้ชัด: สั่ง→ส่งออก, ส่งออก→ส่งถึง, หรือสั่ง→ส่งถึงเป็นคนละ metric; อย่ารวมระยะเวลาข้ามแถวเป็นยอดรวมแบบ measure เงิน

### 5. นิยาม metrics และขอบเขตพฤติกรรมยังต้องตกลง

sale_price ยังไม่ใช่ยอดขายสุทธิหลังคืน/ยกเลิกโดยอัตโนมัติ ต้องเลือก status และวันที่สำหรับแต่ละ view และไม่ SUM profit ของ Cancelled/Returned เป็น realized profit โดยไม่มีข้อตกลง

discount_amount = retail_price - sale_price ใช้ไม่ได้เป็นหลักฐานส่วนลดธุรกรรมจริงจากแค็ตตาล็อก snapshot เพียงอย่างเดียว การตรวจครั้งนี้ได้ส่วนต่างศูนย์ทั้งชุดเมื่อเทียบกับ products.retail_price ถ้าจะเก็บต้องอธิบายว่าเป็นส่วนต่างเทียบราคา snapshot หรือพัก metric นี้ไว้

Single fact_sales รองรับพฤติกรรมการซื้อ เช่น ซื้อซ้ำ/cohort ได้ แต่ไม่ครอบคลุม clickstream, session funnel หรือ conversion ที่ต้องใช้ events ถ้าขอบเขตหมายถึงพฤติกรรมเว็บไซต์ ต้องมีวิธีใช้ events แยกต่างหาก ไม่จำเป็นต้องเพิ่ม fact โดยพลการหากโครงการยืนยัน single fact แต่ต้องระบุว่ารอบแรกไม่ครอบคลุมโจทย์นั้น

### 6. กติกาวันที่ Unknown/Pending ยังไม่สอดคล้อง DDL

เอกสารแนะนำ date_key=-1 แต่ dim_date.full_date และ attributes หลายตัวเป็น NOT NULL จึงยังไม่มีวิธีสร้าง sentinel row ที่ไม่ใส่วันที่สมมติ ต้องเลือกระหว่าง nullable fact date keys กับ sentinel rows ที่ออกแบบ attributes รองรับ และแยก Unknown, Not applicable และ Pending เมื่อจำเป็น

การใช้ NULL ไม่ได้ผิดโดยตัวมันเอง; LEFT JOIN และกติกา grouping ที่ชัดเจนรักษาข้อมูลได้ ห้ามอ้างว่าค่า -1 เร็วกว่าหรือถูกต้องกว่าเสมอโดยไม่มีการวัด

### 7. คำแนะนำ physical design ต้องปรับให้เป็น Redshift

ข้อความให้ partition fact_sales รายเดือนและสร้าง index แบบฐานข้อมูลทั่วไปไม่ตรงกับ internal tables ของ Redshift ควรใช้แนวทาง sort/distribution/encoding หรือ automatic optimization ตาม workload การ partition S3 external tables เป็นอีกเรื่องหนึ่ง [AWS: unsupported PostgreSQL features](https://docs.aws.amazon.com/redshift/latest/dg/c_unsupported-postgresql-features.html), [AWS: CREATE TABLE](https://docs.aws.amazon.com/redshift/latest/dg/r_CREATE_TABLE_NEW.html)

PK/FK/UNIQUE ที่ประกาศใน Redshift เป็น informational constraints ไม่ได้บังคับความไม่ซ้ำหรือความสัมพันธ์ขณะโหลด ต้องมี SQL ตรวจรับจริงเหมือนที่ตรวจในเครื่อง และห้ามประกาศ constraint แล้วปล่อยข้อมูลละเมิด เพราะ query planner ใช้ข้อสมมติจาก constraints เหล่านี้ [AWS: unsupported PostgreSQL features](https://docs.aws.amazon.com/redshift/latest/dg/c_unsupported-postgresql-features.html)

## รายการงานที่เหลือและลำดับแนะนำ

### A. ก่อนรัน warehouse บน AWS

1. ปรับ schema และบันทึกการตัดสินใจข้อ 1–7 โดยคง grain หนึ่งแถวต่อ order item
2. สร้าง source-to-target mapping รายคอลัมน์ พร้อม key generation และ nullable/date rules
3. แยก SQL ที่รันได้จริง เช่น `01_staging.sql`, `02_dimensions_fact.sql`, `03_copy.sql`, `04_load_dimensions.sql`, `05_load_fact.sql`, `06_validation.sql` (เป็นรายการที่เสนอ ยังไม่ได้สร้าง)
4. เตรียม schema ของ staging จาก Parquet จริง ไม่คัด DDL dim/fact มาใช้แทน
5. กำหนดวิธี full refresh/transaction/publish ให้โหลดซ้ำไม่ทำ facts/versions ซ้ำ และไม่เผยแพร่ข้อมูลครึ่งชุด

### B. ตรวจ AWS Lab และนำข้อมูลขึ้น

1. ตรวจบัญชี region `us-east-1`, งบ เวลาคงเหลือ และข้อจำกัดบริการ
2. ตรวจ VPC/subnets/route tables/SG ตาม handoff อีกครั้ง รวม ID private subnet ที่มีการแก้ไขในเอกสาร
3. ตรวจ LabRole/trust/policies และ role ที่บริการใช้จริง ไม่สรุปจากชื่อ policy อย่างเดียว
4. เลือก Provisioned หรือ Serverless ตามสิทธิ์และงบ แล้วตรวจ subnet requirements ของรูปแบบที่เลือกก่อนสร้าง
5. สร้าง S3 พร้อม prefix แยก raw/curated/table/batch และ permissions ที่ต้องใช้ ส่งขึ้นเฉพาะ batch ที่ผ่าน ห้ามชี้ COPY ไป parent prefix ที่รวม 7 schemas หรือรวม batch ทดสอบที่ FAIL
6. วางไฟล์รายงาน/checksum แยกจาก prefix ที่ COPY อ่าน เพื่อไม่ให้สแกน JSON/Markdown เป็นข้อมูล Parquet
7. เตรียม Redshift และทดสอบ S3 access/COPY กับข้อมูลหนึ่งตารางก่อน แล้วจึงโหลดครบและสร้าง dim/fact

S3 Gateway Endpoint อย่างเดียวไม่ยืนยันสิทธิ์ S3/IAM หรือการเข้าถึงทุกบริการ ต้องทดสอบเส้นทางที่เลือกจริง ไม่เพิ่ม NAT/endpoint อื่นโดยอัตโนมัติโดยไม่มีความจำเป็น งาน KMS customer key/Flow Logs/alarms เพิ่มเติมขึ้นกับข้อกำหนดโครงการและสิทธิ์ Lab ไม่ใช่ต้องสร้างทุกอย่างก่อน upload ไฟล์

### C. ทำ Glue pipeline เมื่อพร้อม

`curated_pipeline.py` เป็น local pipeline: อ่านด้วย Path/open/pandas จากดิสก์ อาศัยไฟล์ schema/baseline ข้างโค้ด และเขียนผลลง local folder จึงไม่ใช่ Glue job พร้อม deploy

ต้องเพิ่มการรับ job arguments, การอ่าน/เขียน S3 หรือ download/upload ผ่านพื้นที่ชั่วคราว, packaging schema/baseline, dependency ที่รองรับ runtime ของ Glue, logging และสถานะ batch อาจรักษา pandas logic หรือแปลงเป็น Spark ตาม runtime ที่เลือก ไม่ควรนำ `.runtime_dependencies` ที่ติดตั้งสำหรับ Windows ไปใช้เป็น dependency package ของ Glue โดยตรง

สร้าง Glue database/Catalog ตามต้องใช้ ใช้ crawler หรือกำหนด schema โดยตรงก็ได้ ตรวจว่าตรวจจับ DECIMAL/timezone/flags ถูก Connection จำเป็นตามวิธีเชื่อมที่เลือก ไม่ต้องสร้างโดยไม่มี use case

### D. ตรวจรับระบบและส่งต่อ BI

- ตรวจ row counts, PK/FK, joins ไม่เพิ่มแถว และจำนวน fact ควรเท่ากับ 181,759 ถ้าเก็บทุกสถานะ/รายการตามแบบ
- เทียบยอดตามสูตร/precision/status เดียวกัน แยกผลจาก rounding และกฎธุรกิจ
- ทดสอบรันซ้ำ การโหลดล้มเหลวกลางทาง และการรักษา batch ล่าสุดที่ผ่าน
- สร้าง reporting views/queries และ dashboard ตามโจทย์จริง ไม่สรุปว่า file upload สำเร็จคือ warehouse เสร็จ
- ตรวจเครื่องมือ BI ที่ Lab อนุญาต handoff ระบุ QuickSight มีข้อจำกัด จึงต้องเลือกเส้นทางที่ใช้งานได้จริง
- จัดทำ runbook, owners, วิธีตรวจ log, data freshness, วิธีหยุด/ล้างทรัพยากรที่คิดเงิน และคู่มือส่งมอบ
- ติดตามคำยืนยัน city/null และวันที่ item ต่อได้ขนานกับงานอื่น โดยรักษาธงและสถานะ provisional

## งานถัดไปที่มีผลมากที่สุด

**ปรับแบบ DW schema ให้สอดคล้องกับ curated และ Redshift แล้วเขียน staging + load SQL** เป็นช่องว่างที่ควรปิดก่อนเริ่ม compute ที่คิดเงิน การสร้าง/ตรวจ bucket และสิทธิ์สามารถทำขนานได้ แต่ยังไม่ควรประกาศว่าระบบพร้อมใช้งานจนผ่านการโหลดและ query ในบัญชีจริง

การตรวจครั้งนี้ไม่ได้แก้ DDL ในเอกสารที่ส่งมา ไม่ได้ deploy และไม่ได้ยืนยัน AWS live state
