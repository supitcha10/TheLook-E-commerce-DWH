# โฟลการทำงานของทีม Data Warehouse

> สถานะปัจจุบัน24ต.ค.2026 ดู [DW handoff](dw_handoff.md) และ checklist ล่าสุด เนื้อหาที่ระบุว่ายังไม่deploy/ทดสอบด้านล่างเป็นบันทึกหรือแผนเดิม ไม่ใช่สถานะปัจจุบัน ห้ามรันขั้นติดตั้งซ้ำบนฐานที่มีข้อมูล

> สถานะการลงมือทำและ checklist ล่าสุดอยู่ที่ [WORK_PROGRESS.md](../WORK_PROGRESS.md) ส่วนไฟล์นี้อธิบาย workflow โดยรวม คู่มือ SQL อยู่ที่ [sql/README.md](../code/sql/README.md)

โครงการ TheLook E-Commerce  
จัดทำวันที่ 18 ตุลาคม 2026

## เป้าหมายและขอบเขต

นำ CSV ใน `dataset/` มาตรวจสอบ แปลง และโหลดเข้าคลังข้อมูล เพื่อให้ทีม BI ใช้ข้อมูลที่มีนิยามตรงกันและตรวจสอบย้อนกลับได้ งานรอบแรกเสนอให้ทำรายงานยอดขาย สินค้า และลูกค้าจาก 6 ตาราง ส่วน `events` แยกเป็นงานวิเคราะห์พฤติกรรมในระยะถัดไป

โฟลนี้เป็นแนวทางที่เสนอสำหรับโปรเจกต์ ไม่ได้หมายความว่าบริการ AWS หรือ pipeline ทุกส่วนสร้างเสร็จแล้ว

## 1. ภาพรวมการทำงาน

```mermaid
flowchart TD
    A[รับไฟล์ CSV และงานส่งมอบ Infrastructure] --> B[ตกลงคำถามธุรกิจและนิยามตัวชี้วัดกับทีม BI]
    B --> C[กำหนด Data Dictionary และความสัมพันธ์ตาราง]
    C --> D[ตรวจคุณภาพข้อมูลใน project.ipynb]
    D --> E{มีปัญหาที่ยังไม่ตัดสินวิธีจัดการหรือไม่}
    E -->|มี| F[ทบทวนกับเจ้าของข้อมูลและทีม BI]
    F --> G[บันทึกกฎแก้ไข ยอมรับ หรือแยกแถวผิดกฎ]
    G --> D
    E -->|ไม่มี| H[ออกแบบ staging และ star schema]
    H --> I[ตรวจสิทธิ์ Lab เครือข่าย และงบ]
    I --> J[Curated pipeline รันในเครื่อง (Python) → Parquet]
    J --> K[เก็บ CSV ต้นฉบับใน S3 raw พร้อม manifest]
    K --> L[Upload Parquet ไป S3 curated]
    L --> M[ลงทะเบียน schema ใน Glue Data Catalog (optional)]
    M --> N[โหลดเข้า Redshift staging (COPY)]
    N --> O[สร้างและโหลด dimensions กับ facts]
    O --> P{ผ่านการตรวจรับหรือไม่}
    P -->|ไม่ผ่าน| Q[ตรวจ log และแก้กฎหรือโค้ด]
    Q --> J
    P -->|ผ่าน| R[เผยแพร่ตารางหรือ views ให้ทีม BI]
    R --> S[บันทึกรอบโหลด เฝ้าดูข้อผิดพลาด และควบคุมค่าใช้จ่าย]
```

> **หมายเหตุ:** โฟลว์ข้างต้นเป็นสถาปัตยกรรมเต็มรูปแบบ (S3 raw → Glue ETL → curated) สำหรับ production pipeline  
> **สถานะจริงตอนนี้:** Curated ทำในเครื่องด้วย `code/curated_pipeline.py` แล้ว upload Parquet ไป S3 curated โดยตรง  
> Glue ETL ยังไม่ได้สร้าง (รอตกลงกับทีม infra ว่าบังคับใช้ Glue หรือไม่) — ดู [คู่มือ SQL](../code/sql/README.md) สำหรับขั้นตอนโหลดปัจจุบัน

การผ่านจุดตรวจคุณภาพไม่ได้หมายความว่าต้องไม่มีค่าว่างหรือ warning เลย แต่ทุกปัญหาต้องมีวิธีจัดการชัดเจน และไม่มีข้อผิดพลาดที่ทำให้ผลรายงานคลาดเคลื่อนโดยไม่ทราบสาเหตุ Quarantine ต้องถูกนับและรายงาน ไม่ใช่ทิ้งแถวแล้วประกาศว่าผ่าน

## 2. ขั้นตอน งานที่ทำ และสิ่งส่งมอบ

| ขั้นตอน | งานของทีม Data Warehouse | สิ่งส่งมอบ / เงื่อนไขไปขั้นต่อไป |
|---|---|---|
| 1. รับงานและกำหนดขอบเขต | อ่าน handoff ตรวจรายชื่อไฟล์ แหล่งที่มา เวอร์ชัน และคำถามที่ทีม BI ต้องการตอบ | รายการข้อมูลและรายงานเป้าหมาย พร้อมผู้รับผิดชอบ |
| 2. ตกลงนิยามธุรกิจ | ระบุยอดขายนับสถานะใด ใช้วันใด จัดการ Cancelled/Returned อย่างไร และยืนยันสกุลเงิน | Metric definitions ที่ทีม DW และ BI ใช้ร่วมกัน |
| 3. ทำความเข้าใจข้อมูล | กำหนด grain, PK, FK, ชนิดข้อมูล และคอลัมน์ที่ว่างได้ | Data Dictionary และ ER diagram |
| 4. ตรวจคุณภาพต้นทาง | รัน notebook ตรวจค่าว่าง คีย์ซ้ำ FK วันเวลา ตัวเลข และจำนวนรายการต่อคำสั่งซื้อ | ผลตรวจ พร้อมรายการปัญหาและแนวทางจัดการ ห้ามแก้ข้อมูลโดยเดา |
| 5. ออกแบบคลังข้อมูล | ออกแบบ staging, dimensions, facts และวิธีโหลดซ้ำ | แผนผัง star schema, source-to-target mapping และ SQL DDL |
| 6. เตรียม AWS | ประสานทีม Infrastructure ตรวจ LabRole, S3, Glue, Redshift และเส้นทางเชื่อมต่อ | ทรัพยากรและสิทธิ์พร้อมใช้งานตามงบ; ทดสอบการเข้าถึงจริง |
| 7. นำเข้าข้อมูล raw | เก็บ CSV เดิมแยก table/batch พร้อม checksum และจำนวนแถว | Raw ที่ไม่ถูกเขียนทับ พร้อม manifest ย้อนกลับได้ |
| 8. ลงทะเบียน schema | สร้าง Glue database และใช้ crawler หรือกำหนดตารางเอง ตรวจ schema ที่ได้กับ Dictionary | Catalog schema ที่ตรวจแล้ว ไม่ยอมรับผล inference โดยไม่ตรวจ |
| 9. แปลงข้อมูล | ทำ Glue ETL ตามกฎที่ยืนยัน แยกแถวผิดกฎและเขียน curated | Parquet, quarantine และรายงานผลแต่ละ batch |
| 10. โหลดและสร้างโมเดล | โหลด curated เข้า Redshift staging แล้วสร้าง dimension/fact | ตารางคลังข้อมูลตาม grain ที่ตกลง ไม่มีแถวเพิ่มจาก join ผิด |
| 11. ตรวจรับ | เทียบจำนวนแถว คีย์ ยอดเงิน และ query ตัวอย่าง ทดสอบโหลด batch เดิมซ้ำ | ผลตรวจรับและหลักฐานว่ารันซ้ำไม่ทำข้อมูลซ้ำ |
| 12. ส่งมอบและดูแล | ให้ทีม BI ใช้ตาราง/views พร้อมคำอธิบาย metric และข้อจำกัด ติดตามรอบโหลด | คู่มือ query, data freshness, runbook และผู้รับผิดชอบเมื่อผิดพลาด |

## 3. เส้นทางข้อมูลและบทบาทบริการ

```mermaid
flowchart LR
    CSV[CSV ใน dataset] --> LOCAL[Curated Pipeline (Python local)]
    LOCAL --> RAW[S3 raw: CSV + manifest]
    LOCAL --> CUR[S3 curated: Parquet]
    LOCAL --> BAD[S3 quarantine: rejected rows]
    CUR --> STG[Redshift staging (COPY)]
    STG --> DW[Dimensions และ Facts]
    DW --> VIEW[Reporting views]
    VIEW --> BI[เครื่องมือ BI ที่ Lab อนุญาต]
    CAT[Glue Data Catalog] -. schema .-> STG
```

- **S3 raw:** เก็บต้นฉบับ CSV แยกตามตารางและ batch พร้อม manifest/checksum
- **Curated Pipeline (local):** `code/curated_pipeline.py` — อ่าน CSV, ตรวจ DQ, แปลงชนิด, เขียน Parquet + validation report (รันในเครื่อง ไม่ใช้ Glue ETL)
- **S3 quarantine:** เก็บแถวที่ไม่ผ่านกฎ พร้อม rule ID และเหตุผล (จาก curated pipeline)
- **S3 curated:** เก็บ Parquet ที่ผ่าน validation แล้ว รอโหลดเข้า Redshift
- **Glue Data Catalog:** (optional) ลงทะเบียน schema สำหรับ query federation; ไม่ได้ใช้รัน ETL ตอนนี้
- **Redshift staging:** พักข้อมูลแต่ละรอบ (COPY จาก Parquet) เพื่อตรวจก่อนเผยแพร่
- **Dimensions/Facts และ views:** จัดข้อมูลตามการวิเคราะห์และนิยามที่ตกลงกับทีม BI

> **สถาปัตยกรรมเต็มรูปแบบ (อนาคต):** อาจย้าย Curated Pipeline ไป Glue ETL หากทีม infra กำหนด — โค้ดและกฎพร้อมต่อยอดได้

การโหลดจาก curated เข้า Redshift ใช้ **COPY จาก Parquet** (manifest-based) ตาม `code/sql/03_load_batch.sql` ไม่จำเป็นต้องสร้าง Glue connection สำหรับรอบนี้ ส่วน Redshift ให้เลือก Provisioned หรือ Serverless อย่างใดอย่างหนึ่ง แล้วเตรียม networking ตามรูปแบบนั้น

## 4. โมเดลเริ่มต้นสำหรับรายงานยอดขาย

| ตารางปลายทางที่เสนอ | แหล่งข้อมูล | Grain / หมายเหตุ |
|---|---|---|
| `dim_users` | users | หนึ่งแถวต่อผู้ใช้ใน snapshot เริ่มต้น |
| `dim_products` | products | หนึ่งแถวต่อรหัสสินค้าใน snapshot เริ่มต้น |
| `dim_distribution_centers` | distribution_centers | หนึ่งแถวต่อศูนย์กระจายสินค้า |
| `dim_date` | สร้างจากช่วงวันที่จริง | หนึ่งแถวต่อวัน ใช้หลายบทบาท เช่น วันสั่งและวันส่ง |
| `fact_sales` | order_items + orders + inventory_items | หนึ่งแถวต่อ order_items.id; เก็บสถานะไว้และใช้ metric/view กำหนดรายการที่นับเป็นยอดขาย |
| `fact_events` ระยะถัดไป | events | หนึ่งแถวต่อเหตุการณ์ แยกจาก fact_sales |

ใช้ `order_items.inventory_item_id = inventory_items.id` เมื่อต้องการต้นทุนของสินค้ารายชิ้น ไม่ join inventory ด้วย product_id เพียงอย่างเดียว เพราะสินค้าหนึ่งรหัสมี inventory หลายชิ้น

หากเก็บศูนย์กระจายสินค้าใน fact_sales ต้องตกลงว่าจะใช้ค่าจาก inventory หรือ products พร้อมระบุที่มา ห้ามสมมติว่าทั้งสองแหล่งตรงกันทุกครั้ง และไม่ join events กับ fact_sales ผ่าน user_id แล้วรวมยอดขายตรง ๆ เพราะจะทำให้ยอดซ้ำ

## 5. กติกาของแต่ละรอบโหลด

1. สร้าง `batch_id` และ manifest ระบุชื่อไฟล์ checksum จำนวนแถว และเวลานำเข้า วันที่ ingest ไม่ใช่วันที่ snapshot ของต้นทางโดยอัตโนมัติ
2. ตรวจไฟล์ครบและ schema ถูก ก่อนเริ่มแปลง เก็บ raw ตามเดิม
3. โหลดตารางแม่ก่อนตรวจ FK: distribution_centers → products; users → orders; products และ distribution_centers → inventory_items; จากนั้นตรวจ order_items และ events
4. ระหว่าง ETL แยก accepted, quarantined และ duplicates ที่ตัดออกอย่างมีบันทึก แต่ละแถวต้องอยู่ในหมวดการนับเดียวกัน ส่วน warning อาจอยู่กับ accepted ได้
5. ตรวจว่าจำนวนต้นทางเท่ากับผลรวมของหมวดเหล่านี้ และรายงานผลกระทบของแถวที่ถูกแยกต่อยอดเงิน/จำนวน orders
6. โหลดเข้า staging แล้วสร้าง dimensions ก่อน facts ตรวจ FK และ grain ซ้ำ
7. เผยแพร่ข้อมูลเมื่อผ่านเกณฑ์รับงาน หากไม่ผ่านให้คงชุดที่ผ่านล่าสุดไว้ และระบุว่ารอบใหม่ล้มเหลวหรือยังรอทบทวน
8. สำหรับ CSV snapshot ชุดนี้ เสนอเริ่มด้วย full refresh ผ่าน staging ทดสอบรัน batch เดิมซ้ำแล้วผลไม่ซ้ำ ก่อนออกแบบ incremental ในอนาคต

ข้อมูลชุดนี้ไม่มี updated_at ครบทุกตาราง จึงยังไม่ควรใช้ created_at เป็นตัวกรอง incremental โดยสมมติว่าจะจับการเปลี่ยนสถานะย้อนหลังได้ครบ

## 6. แบ่งความรับผิดชอบระหว่างทีม

| ทีม | ความรับผิดชอบหลัก | จุดประสานงาน |
|---|---|---|
| Infrastructure & Security | เครือข่าย สิทธิ์ การเข้าถึงบริการ และข้อจำกัด Lab | ทีม DW แจ้งบริการและเส้นทางที่ต้องใช้ พร้อมทดสอบการเชื่อมต่อร่วมกัน |
| Data Warehouse | Schema, mapping, กฎคุณภาพ, ETL, การโหลด, dimensions/facts และผลตรวจรับ | ส่งนิยามและตารางพร้อมใช้งานให้ BI แจ้งปัญหาข้อมูลและสิทธิ์ที่ติดขัด |
| BI / ผู้กำหนดโจทย์ธุรกิจ | คำถามวิเคราะห์ นิยาม metric และการตรวจรับรายงาน | ยืนยันสถานะยอดขาย วันที่ สกุลเงิน และวิธีนับคืน/ยกเลิกกับ DW |

ผู้สร้าง S3/Glue/Redshift จริงให้แบ่งตามสิทธิ์ของสมาชิก Lab ส่วนทีม DW รับผิดชอบข้อกำหนดด้านข้อมูลและการตรวจว่ากระบวนการทำงานได้ครบ

## 7. สถานะปัจจุบันและงานถัดไป

สถานะด้าน AWS อ้างอิง [handoff1.md](handoff1.md) ไม่ใช่ผลตรวจ AWS สด ณ วันที่จัดทำเอกสาร ใน handoff ระบุว่าเตรียมโครงข่ายไว้แล้ว แต่ยังไม่ได้สร้างบริการคลังข้อมูลและยังไม่ได้ยืนยันการเชื่อมต่อจริงครบทุกเส้นทาง

| งาน | สถานะจากงานในโปรเจกต์นี้ |
|---|---|
| มี CSV ต้นทาง 7 ตาราง | มีแล้ว |
| Data Dictionary, ER diagram และกฎทำความสะอาดฉบับร่าง | มีแล้วใน [dataset_dictionary_and_cleaning.md](dataset_dictionary_and_cleaning.md) |
| โหลดข้อมูล ดูตัวอย่าง และตรวจคุณภาพ | มีโค้ดแล้วใน [project.ipynb](../code/project.ipynb) |
| ผลตรวจรอบที่ทดสอบ | ตรวจ 207 กฎ ไม่พบ FAIL มี WARN 3 กฎ; ไม่ใช่การรับรองคุณภาพทุกด้าน |
| ยืนยันนิยามยอดขาย สกุลเงิน และกติกาแก้ปัญหา | ยังต้องตกลงก่อนใช้จริง |
| Cleaning/curated pipeline | **เสร็จแล้ว** — `code/curated_pipeline.py` ผ่าน validation 52 checks (PASS_WITH_KNOWN_ISSUES) |
| Staging/DW DDL (dw-v1) | **เสร็จแล้ว** — `code/sql/01_staging.sql`, `02_warehouse.sql` |
| Load procedure (atomic, SCD2, idempotent) | **เสร็จแล้ว** — `code/sql/03_load_batch.sql`, `00_control.sql`, `04_post_load_checks.sql` |
| Local contract tests | **ผ่าน 7 tests** — `code/test_warehouse_sql.py` (staging schema, package manifest, bootstrap joins, grain/money) |
| Package generator & runbook | **เสร็จแล้ว** — `code/prepare_aws_batch.py`, `code/sql/README.md` |
| Git-ready files | **พร้อม** — `.gitignore`, `.gitattributes`, `README.md`, `requirements-dev.txt`; notebook outputs cleared |

**สถานะรอบนี้:** พร้อมขึ้น AWS — ตรวจทรัพยากร/สิทธิ์จริง → กรอก config → upload batch → install SQL → run batch → verify

**งานถัดไป (ขึ้น AWS):**

1. ตรวจ AWS resources และสิทธิ์จากบัญชีจริง (S3 bucket/prefix, Redshift IAM role, network)
2. กรอก config จริงใน `code/aws_batch_config.json` และ generate package ด้วย `prepare_aws_batch.py`
3. Upload batch ไป S3 immutable prefix ตรวจขนาดและ hash
4. ติดตั้ง SQL 00–03 ใน Redshift, รัน `run_batch.sql`, ตรวจผลด้วย `04_post_load_checks.sql`
5. ทดสอบ retry, SCD boundaries, rollback ด้วย fixtures แยก
6. Glue/orchestration/monitoring ตามสถาปัตยกรรมและ metric ที่ตกลงกับทีมรายงาน
7. Reporting views (net sales, returns, cancellations) และ BI dashboard

การถามต้นทางเรื่อง known issues (city null, item date order) ทำคู่ขนานได้ — ระหว่างนี้ยังใช้กฎ provisional-v1 ที่ย้อนตรวจได้

## 8. เกณฑ์ถือว่างานทีม DW รอบแรกเสร็จ

- ข้อมูลจาก raw ผ่าน ETL เข้า warehouse ได้ครบตามขอบเขต และทุกแถวที่ไม่ผ่านมีเหตุผลตรวจย้อนกลับได้
- Dimension/fact มี grain และคีย์ถูกต้อง การ join ไม่เพิ่มยอดเงินจากแถวซ้ำ
- นิยามยอดขาย วันรายงาน และการจัดการคืน/ยกเลิกได้รับการยืนยันร่วมกับ BI
- ผลเทียบจำนวนแถวและยอดรวมผ่านเกณฑ์ที่ตกลง โดยแยกผลจากการปัดเศษและการคัดแถวชัดเจน
- โหลดซ้ำไม่เกิดข้อมูลซ้ำ และกรณีโหลดล้มเหลวไม่เผยแพร่ข้อมูลเพียงบางส่วน
- ทีม BI query ตารางหรือ views ได้จริง พร้อมตัวอย่าง SQL และคำอธิบายข้อจำกัด
- มี runbook ระบุวิธีรัน ตรวจผล แก้ปัญหา ผู้รับผิดชอบ และการปิดทรัพยากรที่คิดเงินเมื่อไม่ใช้

QuickSight ถูกระบุว่ามีข้อจำกัดสิทธิ์ใน handoff จึงเลือกเครื่องมือ BI ตามที่ Lab อนุญาต และไม่ใช้การเปิด QuickSight ได้เป็นเงื่อนไขว่าคลังข้อมูลพร้อมใช้งาน
