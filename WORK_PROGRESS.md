# สถานะงาน Data Warehouse

อัปเดต24ตุลาคม2026 ตามผลที่ผู้ใช้รันบนAWSและส่งหลักฐาน

## ผ่านแล้ว

- [x] Raw CSV7ตาราง / Glue cleaning → curated Parquet / validation66checks
- [x] Catalog rawและcurated7ตารางต่อฐาน
- [x] Redshift COPY/staging/DW, rowcounts/keys/5moneytotals
- [x] SCD2/new user/NULL changes/unchanged snapshot/NO_OP/failure rollback/retry
- [x] Atomic error handler patchในฐานvalidationและbefore/after4ตารางPASS
- [x] S3 verification + DataAPI guarded replay, REPLAY_PASSED
- [x] Reporting8views: row/grain/references/money/rollups/lineage8checksPASS
- [x] ยอด181759items,125226distinctorders,10827118.925100; ยอดแยกstatusตามผู้ใช้ตกลง
- [x] รวมhandoff/checklist/BI dictionaryและปรับGitignore

## ขอบเขตส่งมอบที่ตกลงแล้ว

- [x] ใช้ Kaggle Version 1 ดาวน์โหลด 6 ตุลาคม 2026 เป็นข้อมูลคงที่; ตรวจ S3 URI/ขนาด CSV ครบ 7 ไฟล์ตาม [หลักฐานต้นทาง](docs/source_dataset_acceptance.md)
- New-snapshot orchestration และ schedule อยู่นอกขอบเขตครั้งนี้ ไม่ได้ deploy และไม่ใช่รายการที่ต้องทำเพื่อส่งข้อมูลคงที่
- เวลา export/source snapshot และความครบถ้วนทุกแถวจาก BigQuery ยังไม่ทราบ เป็นข้อจำกัดที่ต้องระบุ ไม่ใช้วันดาวน์โหลดหรือเวลา S3 แทน

## งานร่วมและการรับมอบที่ยังไม่ปิด

- [ ] DW/BI ยืนยันรับทราบ known issues ตาม provisional-v1 พร้อมชื่อ/วันที่; การเลือกข้อมูลคงที่ไม่ใช่การยอมรับ known issues และยังไม่มีคำยืนยันสาเหตุจากต้นทาง
- [ ] Infra ร่วม DW กำหนด monitoring/failure alert ปลายทางและหลักฐานทดสอบตามขอบเขตการดูแลที่ตกลง
- [ ] Infra review retention/encryption/policies/costs/operational owner
- [ ] BI read-only connectivity/RLS/dashboard acceptance
- [ ] Inventory/events metricsถ้าทีมต้องการใช้ในdashboard ต้องนิยามและทำmodelเพิ่ม
- [ ] ส่งมอบเอกสารและได้รับacceptanceจริง

## เอกสารหลัก

- [DW handoff](docs/dw_handoff.md): อ่านภาพรวม การใช้งานจริงและข้อจำกัด
- [ข้อมูลต้นทางและ known issues](docs/source_dataset_acceptance.md): ขอบเขตข้อมูลคงที่ หลักฐาน S3 และช่องยืนยันที่ยังรอทีม
- [Checklist ตาม handoff1](docs/handoff1.md): เจ้าของงานและหลักฐาน
- [BI handoff](docs/bi_handoff.md): views/grain/metric rules
- [Reporting acceptance](docs/report/reporting_acceptance_20261024.md): ตัวเลขที่ตรวจแล้ว
- [Git release checklist](docs/git_release_checklist.md): ขอบเขตไฟล์และก่อนpush
- [บันทึกงานเก่า](docs/archive/work_progress_history.md): ประวัติ ไม่ใช่คำสั่งติดตั้งซ้ำ

สถานะclusterปัจจุบันต้องตรวจConsole ไม่ถือว่าพักหรือเปิดอยู่ตลอดตามบันทึกเก่า ไม่อ้างว่าagentรันAWSเอง

## สถานะพร้อมส่งต่อและหลักฐานล่าสุด

งานพัฒนาและตรวจสอบ DW สำหรับข้อมูลคงที่ Version 1 พร้อมส่งต่อแล้ว; การรับมอบจริง การรับทราบ known issues และสิทธิ์/การเชื่อมต่อ/Dashboard ของ BI ยังไม่ปิด

ชุดหลักฐานในเครื่อง: `outputs/DW-handoff-evidence/README.md` (ถูก ignore จาก Git ต้องส่งแยก) ได้รับ READY/report, ภาพ Glue/CloudWatch ที่ผูก Run ID กับ batch, ภาพ ledger/checks/totals/reporting/SCD audit และ replay result/statements แล้ว รอบ replay `ae45e3c1-e6e0-4d29-b70f-e63d3da1ea43` มี16 statements FINISHED, comparison8ตาราง PASS และ new NO_OP PASS

รายการผ่านเดิมด้านบนอ้างหลักฐานที่ผู้ใช้เคยรายงาน ไม่ได้แปลว่ามีต้นฉบับครบในชุดส่งมอบ: ยังขาด SCD rollback before/after, atomic patch verification และภาพ/exports reporting checks8รายการรอบเดิม ผล SELECT ล่าสุดยืนยันยอด/grain/สถานะปัจจุบัน ไม่ใช้แทน checksทุกข้อหรือ rollback ไม่มีการรันทดสอบซ้ำเพื่อรวบรวมหลักฐานนี้
