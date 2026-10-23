# ส่งมอบงาน Data Warehouse — 24 ตุลาคม 2026

เอกสารนี้เป็นทางเข้าอ่านงานล่าสุดสำหรับ Infra/BI และผู้รับช่วง งาน AWS ยืนยันจากผล query/log/ภาพที่ผู้ใช้ส่ง ไม่ใช่การตรวจบัญชีสดโดยผู้จัดทำเอกสาร

## ขอบเขตที่ส่งมอบ

Initial snapshot ของ TheLook: CSV7ตาราง → Glue cleaning/validation → Parquet → Redshift staging → 4dimensions + fact_sales → reporting8views พร้อม audit, retry/NO_OP และชุดทดสอบ SCD2/rollback

ตัวรัน CloudShell รวม S3 validation กับ Data API replay ได้แล้ว แต่ล็อกเฉพาะ batch ที่เผยแพร่สำเร็จ ไม่ใช่ pipeline รับ snapshot ใหม่ ไม่ใช่ scheduler และไม่ใช่ dashboard ที่ deploy แล้ว

## เริ่มอ่านและใช้งาน

1. อ่าน checklist [handoff1](handoff1.md) เพื่อแยกงาน DW/Infra/BI ที่เสร็จและค้าง
2. อ่าน [schema](data_warehouse_schema_design.md) และ [dictionary/cleaning](dataset_dictionary_and_cleaning.md)
3. อ่าน [BI handoff](bi_handoff.md) ก่อนใช้ reporting views; ผู้ใช้เลือกยอดแยกสถานะ ไม่เรียก net sales
4. อ่าน runbook เฉพาะงานก่อนรัน: [Glue ETL](glue_raw_to_curated_runbook.md), [warehouse package](glue_warehouse_package_runbook.md), [SCD tests](scd_rollback_test_runbook.md)
5. หากจะรับข้อมูลใหม่ อ่าน [new snapshot contract](new_snapshot_pipeline_contract.md) ก่อน ไม่มีเหตุให้ติดตั้ง schema/โหลด bootstrap ซ้ำเพียงเพื่อรับช่วงงาน

## ทรัพยากรและเส้นทาง

| รายการ | ค่าที่ใช้งาน |
|---|---|
| Account / region | 006816724683 / us-east-1 |
| Bucket | thelook-dwh-20241022 |
| Raw | s3://thelook-dwh-20241022/thelook/raw/initial-extract/ |
| Curated batch | thelook/curated/20261023T151247118967Z_f8a02155/ |
| Control report | thelook/control/20261023T151247118967Z_f8a02155/validation_report.json |
| Scripts / Spark logs / temp | thelook/scripts/ ; thelook/spark-history/ ; thelook/glue-temp/ |
| Cluster | thelook-redshift-cluster-1, provisioned ra3.large, 1 node, port5439, public off ตามหลักฐานก่อนหน้า |
| Database ที่ผ่าน full Glue batch / reporting | thelook_glue_validation |
| Synthetic test database | thelook_scd_test — ไม่ใช้เป็นข้อมูล BI |
| dev | ใช้ smoke/การทดลองเดิม ไม่ถือว่ามีสถานะเท่าฐาน validation |
| Role | arn:aws:iam::006816724683:role/LabRole |
| Secret reference | thelook/redshift — ไม่มี password/token ในเอกสาร |
| Glue connection | thelook-redshift-conn, JDBC เดิมชี้ /dev |
| Glue jobs | thelook-redshift-smoke-test; thelook-raw-to-curated |
| Glue ETL settings | Glue4, G.1X2, retry0, concurrency1, bookmark off; raw-to-curated timeout20นาที |
| Catalog | thelook_raw / thelook_curated; crawlers thelook-raw-crawler / thelook-curated-crawler |

**Network ต่างจากแผนเดิม:** cluster อยู่ default VPC vpc-0a0534d5310421fae; Glue JDBC อยู่ thelook-vpc vpc-03aaf81c62341e797 และเข้าผ่าน Redshift-managed endpoint vpce-0d6093443a00b58bc ชื่อ thelook-glue-redshift-endpoint

Glue subnet A: subnet-0c93df6636668db96; Glue SG sg-0045646501501b218; endpoint Redshift SG sg-0b074777ad7bd781a; Secrets endpoint SG sg-04bf4a8ceb28cd273; S3 gateway vpce-09c521c76d4613f00. Secrets endpoint ID ยังไม่มีหลักฐานบันทึก ต้องเก็บเพิ่ม ส่วน SG/endpoint policies และค่าใช้จ่ายจริงให้ Infra ตรวจสถานะปัจจุบัน

```mermaid
flowchart LR
  RAW[S3 raw CSV] --> ETL[Glue ETL explicit schema]
  RAW --> RC[Raw crawler / Catalog]
  ETL --> CUR[S3 curated Parquet]
  ETL --> REPORT[Validation report / READY]
  CUR --> CC[Curated crawler / Catalog]
  CUR --> COPY[Redshift COPY / atomic load]
  COPY --> STG[stg 7 tables]
  STG --> DW[dw 4 dimensions / fact_sales]
  DW --> V[reporting 8 views]
  REPORT --> GATE[CloudShell verification]
  CUR --> GATE
  GATE --> API[Data API guarded replay]
  API --> AUDIT[NO_OP / audit checks]
```

Catalog เป็น metadata branch; ETL ที่ทดสอบอ่าน S3 โดย explicit schema ยังไม่ได้อ่านผ่าน Catalog จึงไม่แสดงว่า Catalog เป็น input ที่บังคับใช้ใน ETL

## หลักฐานที่ผ่าน

| งาน | ผลยืนยัน |
|---|---|
| Glue connection/smoke | เชื่อมและอ่าน distribution centers10แถว |
| Raw → curated | 66checks PASS, quarantine0, PASS_WITH_KNOWN_ISSUES |
| Catalog | raw/curatedครบ7ตาราง, locations/header/typed curated schema ตรวจแล้ว |
| COPY | Parquet28parts; counts/PK/5money totals ผ่าน |
| Warehouse | ledger SUCCEEDED, fact181759; staging/warehouseเงินตรง |
| SCD/rollback/retry | attempts9: SUCCEEDED4/NO_OP1/FAILED4; ledger4; users7versions/current4 |
| Atomic handler patch | SHOW PROCEDUREไม่มี bare RAISE; before/after4ตาราง PASS |
| Manual replay | before/after8ตาราง PASS และ new_no_op_attempt PASS |
| CloudShell Data API runner | ผู้ใช้ยืนยัน REPLAY_PASSED: eight tables unchanged; one new NO_OP |
| Reporting | item_rows/grain/references/money/daily/product/DC/lineage8checks PASS บน AWS |

Package hash ของ batch จริง: d897e3ee9663b725c6a226b99712094cc5d536346c9577fe14a634e3cc2ac7d7

หลักฐาน raw exports/screenshots/Parquet/ZIP อยู่ outputs หรือที่ผู้ใช้เก็บ ไม่แนบ Git รายงานสรุปที่ review แล้วอยู่ [reporting acceptance](report/reporting_acceptance_20261024.md) การไม่พบไฟล์ outputs ใน clone ใหม่ไม่ได้หมายความว่าต้องรัน deployment ซ้ำ

## ส่งต่อและเจ้าของงานค้าง

| งาน | ผู้รับผิดชอบร่วม | เกณฑ์ปิด |
|---|---|---|
| Snapshot time/version/completeness | Source owner + DW | source_observed_at พร้อม timezone/evidence และ full-snapshot contract |
| Known issues | Source owner + DW | ยืนยัน city token และ item timestamp semantics; ไม่เปลี่ยน baselineเพื่อให้ผ่าน |
| Lifecycle/retention/encryption/policies | Infra + DW | ระบุ retentionแต่ละprefix/logs, owner, หลักฐานค่าจริงและสิทธิ์ที่จำเป็น |
| Read-only/RLS/BI connectivity | Infra + BI | ยืนยัน principal/สิทธิ์/เส้นทาง; ไม่ใช้ admin credentials เป็นการส่งมอบ |
| Dashboard acceptance | BI + DW | ยอด/filtersตรงviews, distinctordersไม่บวกข้ามกลุ่ม, labelsตรงmetricdictionary |
| New-snapshot orchestration/schedule | DW + Infra | metadataพร้อม, negative testsผ่าน, monitoringปลายทางตกลงแล้ว จึง deploy |
| Budget/stop policy | Infra + ผู้ดูแลLab | ยอดจริง, ผู้รับผิดชอบและเวลาเปิด/พัก/เก็บ/ลบ |

ยังไม่รับรอง concurrency/cancellation/late-arriving acceptance; inventory stock metrics และ web funnel ต้องนิยามเพิ่ม ไม่ได้เสร็จจาก fact_sales

## ปฏิบัติงานและข้อควรระวัง

- ไม่ติดตั้ง DDL ซ้ำในฐานที่มีข้อมูล; ตรวจ current_database ทุกครั้ง
- ใช้ต้นฉบับ generator ใน code; แก้ SQL generated อย่างเดียวอาจถูกทับตอน build
- ห้ามใช้แพ็กเก่าที่มี bare RAISE; ใน atomic error handler; ต้องใช้รุ่นที่แก้แล้ว Default atomic modeบันทึกFAILEDแล้วส่งerrorเดิมกลับอัตโนมัติ
- Replay runner: verifyใช้ขณะclusterพักได้; runต้องAvailable; CloudShell venvติดตั้ง sqlparseโดยไม่ใช้ --user. เก็บ run UUID/result.json/statements.jsonl; timeoutที่ผลไม่แน่นอนต้องตรวจstatementก่อนretry
- รัน NO_OP เพิ่ม auditเป็นเรื่องปกติ อย่าคาดยอดattemptรวมเท่าภาพเก่าตลอดไป
- เก็บผลและไม่มีqueryค้างก่อนpause;สถานะclusterปัจจุบันต้องตรวจConsole เอกสารนี้ไม่อ้างว่าพักอยู่ตอนอ่าน
- observed_at anchor ของ bootstrap ไม่ใช่source-confirmed; processed_at/published_atไม่ใช้แทนเวลาsnapshot
- ไม่สร้าง NAT/CMK/custom roles เพิ่มเพื่อให้ครบchecklistโดยไม่มีความจำเป็น/สิทธิ์ที่ยืนยัน
