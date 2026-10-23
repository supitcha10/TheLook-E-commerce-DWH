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

## ยังไม่ปิด

- [ ] Source observation time/version/frequencyและknownissuesยืนยันโดยต้นทาง
- [ ] New-snapshot orchestration/schedule/alerts; replayที่ผ่านไม่ใช่ส่วนนี้
- [ ] Infra review retention/encryption/policies/costs/operational owner
- [ ] BI read-only connectivity/RLS/dashboard acceptance
- [ ] Inventory/events metricsถ้าทีมต้องการใช้ในdashboard ต้องนิยามและทำmodelเพิ่ม
- [ ] ส่งมอบเอกสารและได้รับacceptanceจริง

## เอกสารหลัก

- [DW handoff](docs/dw_handoff.md): อ่านภาพรวม การใช้งานจริงและข้อจำกัด
- [Checklist ตาม handoff1](docs/handoff1.md): เจ้าของงานและหลักฐาน
- [BI handoff](docs/bi_handoff.md): views/grain/metric rules
- [Reporting acceptance](docs/report/reporting_acceptance_20261024.md): ตัวเลขที่ตรวจแล้ว
- [Git release checklist](docs/git_release_checklist.md): ขอบเขตไฟล์และก่อนpush
- [บันทึกงานเก่า](docs/archive/work_progress_history.md): ประวัติ ไม่ใช่คำสั่งติดตั้งซ้ำ

สถานะclusterปัจจุบันต้องตรวจConsole ไม่ถือว่าพักหรือเปิดอยู่ตลอดตามบันทึกเก่า ไม่อ้างว่าagentรันAWSเอง
