# รายงานตรวจรับ curated ทั้ง 7 ตาราง

สถานะ: **PASS_WITH_KNOWN_ISSUES**

Batch: `20261018T070120429459Z`  
Schema: `curated-v1` · กฎ: `provisional-v1` (รอยืนยันต้นทาง)

สร้าง Parquet ครบ 7 ตาราง รวม 3,358,783 แถว ไม่มีแถวถูกคัดออก และการตรวจรับ 52 รายการผ่านทั้งหมด CSV ต้นฉบับไม่เปลี่ยน

## ไฟล์ผลลัพธ์และจำนวนแถว

| ตาราง | ก่อน | หลัง | Quarantine |
|---|---:|---:|---:|
| [distribution_centers](../../outputs/curated/20261018T070120429459Z/distribution_centers.parquet) | 10 | 10 | 0 |
| [products](../../outputs/curated/20261018T070120429459Z/products.parquet) | 29,120 | 29,120 | 0 |
| [users](../../outputs/curated/20261018T070120429459Z/users.parquet) | 100,000 | 100,000 | 0 |
| [orders](../../outputs/curated/20261018T070120429459Z/orders.parquet) | 125,226 | 125,226 | 0 |
| [order_items](../../outputs/curated/20261018T070120429459Z/order_items.parquet) | 181,759 | 181,759 | 0 |
| [inventory_items](../../outputs/curated/20261018T070120429459Z/inventory_items.parquet) | 490,705 | 490,705 | 0 |
| [events](../../outputs/curated/20261018T070120429459Z/events.parquet) | 2,431,963 | 2,431,963 | 0 |

## ยอดเงินก่อน–หลังและผลจากการปัดเศษ

ค่าทั้งหมดรวมทุกสถานะเพื่อการตรวจรับ ไม่ใช่นิยามยอดขายของรายงาน BI ราคา/ต้นทุนใช้ Decimal(18,6) และ ROUND_HALF_UP ผลหลังอ่าน Parquet ตรงกับค่าที่คาดหลังปัดเศษทุกคอลัมน์ ไม่ใช้ tolerance กลบความต่าง

| ตาราง.คอลัมน์ | ยอดดิบ | ยอดหลังอ่านกลับ | ผลต่างจาก rounding |
|---|---:|---:|---:|
| products.cost | 829389.2658815243043789 | 829389.266488 | 0.0006064756956211 |
| products.retail_price | 1724491.1717701144445122 | 1724491.173926 | 0.0021558855554878 |
| order_items.sale_price | 10827118.9117501899145094 | 10827118.925100 | 0.0133498100854906 |
| inventory_items.cost | 14063107.7949022851004252 | 14063107.805139 | 0.0102367148995748 |
| inventory_items.product_retail_price | 29231022.2916349767389429 | 29231022.327644 | 0.0360090232610571 |

## Known issues ที่ยังรอยืนยัน

| ประเด็น | จำนวน | ตัวหาร | สถานะ |
|---|---:|---:|---|
| CITY-01-users | 958 | 100,000 | KNOWN_ISSUE |
| CITY-01-events | 23,080 | 2,431,963 | KNOWN_ISSUE |
| DATE-01-items | 35,872 | 118,281 | KNOWN_ISSUE |

เก็บ city ต้นฉบับและเพิ่ม city_clean/city_missing_token โดยไม่เติมเมืองหรือลบแถว เก็บค่าของวันเวลา item เดิมในรูปแบบ UTC และเพิ่มแฟล็กวันที่ แถวที่วันไม่ครบมีแฟล็กเป็น NULL ไม่ใช่ False

## ตรวจอะไรแล้ว

- จำนวนแถวก่อน–หลังและแถว quarantine
- schema และค่าทุกคอลัมน์หลังอ่าน Parquet กลับ เทียบกับการแปลง CSV โดยตรง รวมตำแหน่ง NULL และลำดับแถว
- PK ไม่ว่าง/ไม่ซ้ำ, FK ทั้ง 9 เส้นทาง และจำนวน item ต่อ order
- user_id ของ item ตรงกับ order และ product_id ตรงกับ inventory ที่อ้างถึง
- ค่าตัวเลข/วันที่ที่แปลงไม่ได้, overflow และความยาวข้อความ UTF-8 ตาม schema
- ยอด Decimal แบบ exact และผลต่างจากการปัดเศษ
- SHA-256 ต้นทางก่อน–หลัง และ known issue เทียบ baseline เดิม

## วิธีใช้

เปิด [project.ipynb](../../code/project.ipynb) แล้วรันส่วนท้าย สร้าง curated ครบ 7 ตาราง และตรวจเทียบก่อน–หลัง ส่วนนี้อ่าน CSV เอง จึงรันแยกจากเซลล์สำรวจก่อนหน้าได้ ใช้ read_curated(ชื่อของตาราง) เพื่ออ่านข้อมูลที่สร้างใหม่

หากรันใหม่จะสร้าง batch ใหม่ ไม่เขียนทับ batch นี้ สถานะ FAIL/FAILED_INCOMPLETE/REVIEW_REQUIRED ต้องทบทวนก่อนใช้ มี batch ทดสอบก่อนหน้าที่ไม่ผ่านการตรวจ hash แบบไบนารี ให้ใช้ batch ที่ระบุในรายงานฉบับนี้เท่านั้น

โค้ด: [curated_pipeline.py](../../code/curated_pipeline.py) · schema: [curated_schema.json](../../code/curated_schema.json)

ผลตรวจแบบเครื่องอ่านได้: [validation_report.json](../../outputs/curated/20261018T070120429459Z/validation_report.json)

## สิ่งที่ยังไม่รวม

ยังไม่ได้รับคำยืนยันความหมายของ city/null และสาเหตุวันที่ผิดลำดับจากเจ้าของ dataset ยังไม่ได้สร้างตาราง star schema, Glue หรือ Redshift และยังไม่ได้ส่งขึ้น AWS ผลผ่านนี้ครอบคลุมกฎที่ระบุ ไม่ได้ยืนยันความถูกต้องทางธุรกิจทั้งหมด
