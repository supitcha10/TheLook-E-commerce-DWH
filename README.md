# TheLook E-Commerce Data Warehouse

CSV7ตาราง → AWS Glue → curated Parquet → Redshift staging → star schema → reporting views สำหรับวิเคราะห์ยอดตามสถานะ

**สถานะ24ต.ค.2026:** initial snapshot, ETL/Catalog/COPY/SCD2/rollback/retry, DataAPI replay และreporting validationผ่านบนAWSตามหลักฐานผู้ใช้ ยังไม่deploy new-snapshot orchestration/schedule/BI dashboard

## เริ่มอ่าน

1. [DW handoff](docs/dw_handoff.md) — ขอบเขตที่ส่งมอบ ทรัพยากรจริง ผลทดสอบและงานค้าง
2. [handoff1 checklist](docs/handoff1.md) — DW/Infra/BIทำอะไรแล้ว ใครปิดงานที่เหลือ
3. [BI handoff](docs/bi_handoff.md) — views/metrics; แยกสถานะ ยังไม่เรียกnet sales
4. [สถานะงาน](WORK_PROGRESS.md), [reporting acceptance](docs/report/reporting_acceptance_20261024.md)

## โครงสร้าง

| Path | หน้าที่ |
|---|---|
| code/ | Python generators, ETL, verification/replay runners และtests |
| code/sql/ | DDL/atomic loader/reporting SQL; ไม่รันทุกไฟล์อัตโนมัติ |
| docs/ | schema/dictionary/runbooks/handoffs |
| docs/archive/ | คู่มือและสถานะเดิม เก็บเป็นประวัติเท่านั้น |
| dataset/ | CSVในเครื่อง ไม่เข้าGit ยกเว้นREADME |
| outputs/ | Parquet/reports/packages/ZIP/evidence ไม่เข้าGit |

## การใช้งานที่ต้องแยกกัน

- [Local curated](dataset/README.md): เตรียมdatasetเอง แล้วใช้ code/curated_pipeline.py
- [Glue ETL](docs/glue_raw_to_curated_runbook.md): code/glue_raw_to_curated.py
- [AWS multipart package](docs/glue_warehouse_package_runbook.md): ต้องมีreport/inventory/baselineevidence; ไม่ใช่แพ็กไฟล์เดียวจากprepare_aws_batch.py
- [SCD/rollback tests](docs/scd_rollback_test_runbook.md): syntheticฐานthelook_scd_testแยกจากข้อมูลจริง
- Replay: code/run_validation_replay.py ใช้เฉพาะbatchเดิมและthelook_glue_validation; --mode verifyอ่านS3, --mode runเพิ่มNO_OPและตรวจผล ต้องมีbundleประกอบ ไม่ใช่standaloneไฟล์เดียว
- Reporting: code/build_reporting_package.pyสร้างoutputs/aws/reporting-v1.zip;ติดตั้งแล้วในฐานvalidation ไม่ติดตั้งซ้ำเพื่อรับช่วงงาน
- [New snapshot contract](docs/new_snapshot_pipeline_contract.md): observation timeต้องยืนยัน ไม่อนุมานจากเวลาGlue/S3/batchID

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r code/requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s code -p test_reporting_views.py -v
.\.venv\Scripts\python.exe -m unittest discover -s code -p test_validation_replay_runner.py -v
```

สองชุดนี้ใช้fixtures/mocks ไม่ต้องต่อAWS ส่วนtestsอื่นบางชุดต้องมีdataset/acceptedbatch/generatedpackageในoutputsซึ่งไม่แนบGit การcloneอย่างเดียวจึงไม่ใช่full integration environment ดูrunbookก่อนbuild/run

Buildersบางตัวอ้างexisting evidence/install artifactsใต้outputs; รับไฟล์จากผู้ดูแลภายในหรือสร้างตามrunbookให้ครบ ไม่ใช้ข้อมูลปลอมแทนเพื่อให้ผ่าน CloudShellที่ใช้venvติดตั้งsqlparseด้วย `python3 -m pip install sqlparse==0.5.3` โดยไม่ใช้ --user

## Git / การส่งมอบ

[Release checklist](docs/git_release_checklist.md). รวมsource/tests/MarkdownและhandoffในGit; ไม่รวมCSV/Parquet/ZIP/ผลquery/secrets/localcredentials ให้เก็บและส่งหลักฐานทางช่องทางทีมแยกกัน

Account/resource IDsที่จำเป็นยังอยู่ในcode/docsเป็นconfiguration references ไม่ใช่credentials เหมาะกับrepositoryทีมที่ตกลงสิทธิ์เข้าถึง หากจะเปิดpublicต้องreview/redactตามนโยบายทีมก่อน ไม่มีการcommit/pushอัตโนมัติจากการจัดเอกสาร

คู่มือเดิมที่ถูกแทนที่อยู่ [archive](docs/archive/readme_legacy.md); ห้ามใช้ข้อความเดิมที่อนุมานobservation timeจากbatch timestampเป็นข้อกำหนดปัจจุบัน
