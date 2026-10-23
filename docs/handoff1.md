# Handoff checklist — Infra → DW → BI

อัปเดต 24 ตุลาคม 2026; checklistนี้แทนสถานะเดิมวันที่16ต.ค. เก็บต้นฉบับไว้ใน [archive](archive/handoff1_original_20261016.md) อ่านค่าทรัพยากร/สถาปัตยกรรม/ผลทดสอบที่ [DW handoff](dw_handoff.md)

[x] = มีหลักฐานผ่านตามขอบเขตข้อความ; [ ] = ยังเหลือหรือยังไม่ยืนยัน ไม่ติ๊กว่าเสร็จจากการมีโค้ดอย่างเดียว

## A. ข้อมูลและแบบจำลอง — DW

- [x] ตรวจ schema/type/PK/FK/nulls/duplicates ของ7ตารางและจัดทำ dictionary
- [x] กำหนด raw/curated/temp แยก และเงิน decimal(18,6)
- [x] ตกลงgrain fact_salesหนึ่งแถวต่อorder item; 4dimensions, Type2 users/Type1 productsและDC
- [x] counts/money reconciliation, SCD2/rollback/retry/NO_OP ผ่านบน AWS
- [x] Reporting8viewsและ8checksผ่าน; ผู้ใช้เลือกแยกยอดตามสถานะ ยังไม่ใช่net sales
- [ ] ยืนยันเวอร์ชันต้นทาง/source_observed_at/timezone/full-snapshotและความถี่โหลด
- [ ] ยืนยันknown issuesกับต้นทาง; ปัจจุบันprovisional-v1

## B. S3 / network — DW ร่วม Infra

- [x] Bucket thelook-dwh-20241022, us-east-1; raw/curated/control/scripts/temp/logsใช้งานจริง
- [x] Glueอ่านเขียนS3และRedshift COPYผ่าน; S3 Gateway Endpointมีหลักฐานเดิม
- [x] เส้นทางGlue→Redshiftผ่านmanaged endpointและSecrets Manager endpointทดสอบแล้ว
- [ ] ยืนยันowner/lifecycle/retentionของแต่ละprefixและlog
- [ ] เก็บหลักฐานencryption/bucket policy/endpoint policyปัจจุบันและreviewสิทธิ์จำเป็น
- [ ] เก็บSecrets Manager endpoint IDให้ครบในinventory

## C. Redshift — DW ร่วม Infra

- [x] Provisioned ra3.large1node/port5439/publicoffตามหลักฐาน; LabRole COPYทำงาน
- [x] Secret authenticationและGlueconnectionผ่าน; ไม่มีpasswordในscript
- [x] แยกฐาน thelook_glue_validation, thelook_scd_test และ dev ชัดเจน
- [x] ติดตั้งatomic loaderและแก้exception handler; validation before/after4ตารางPASS
- [x] บันทึกEnhanced VPC Routing disabledตามconfigurationที่รายงานไว้
- [ ] Infraรับทราบ/รับรองความต่างจากแผน: clusterอยู่defaultVPC เข้าจากthelook-vpcด้วยmanagedendpoint ไม่ได้สร้างclusterในprivateA/Bตามแผนเดิม

## D. Glue / execution — DW

- [x] Connectionและsmoke testอ่าน10distribution centers
- [x] Raw→curated jobเต็มชุดสำเร็จ; 66checksPASS/quarantine0พร้อมknownissues
- [x] Raw/curatedCrawlerและCatalogครบ7ตาราง/schema/locationตรวจแล้ว
- [x] ตั้งtemporary/logpaths, workers2/retry0/concurrency1/bookmarkoff
- [x] CloudShell runnerตรวจS3→DataAPI replay→8ตารางไม่เปลี่ยนและNO_OPเพิ่ม1
- [ ] Pipelineรับsnapshotใหม่/Glue orchestration/schedule: ไม่ได้deploy; ต้องรอsource contractและทดสอบเพิ่ม

Catalogเป็นmetadata branch; ETLอ่านS3โดยexplicit schema ยังไม่ใช่ETLที่ใช้Catalogเป็นinputบังคับ

## E. Security / monitoring — Infra ร่วม DW และ BI

- [x] LabRoleใช้งานS3/Glue/RedshiftและDataAPIได้จริงในเส้นทางที่ทดสอบ
- [x] เก็บGluelogs, ledger/checks/attemptauditและrunner statement IDs
- [ ] Review policy/trust/least privilegeตามข้อจำกัดLab การใช้งานผ่านไม่ได้แปลว่าตรวจpolicyครบแล้ว
- [ ] กำหนดlog retention, failure alertปลายทางและทดสอบส่งแจ้งเตือน
- [ ] ยืนยันencryption choiceและหลักฐาน ไม่บังคับสร้างCMK/customroleใหม่
- [ ] สิทธิ์read-only/RLSและnetworkสำหรับBI; ไม่ส่งadminpassword

## F. Budget / operation — Infra + ผู้ดูแลLab

- [x] ทดสอบpause/resumeและแยกงานตรวจS3ออกจากงานที่ต้องเปิดcluster
- [ ] เก็บbudget/ค่าใช้จ่ายจริง/วันหมดอายุLabล่าสุด
- [ ] ระบุผู้รับผิดชอบ เวลาเปิด/พัก และretention/cleanupหลังส่งงาน
- [ ] ประเมินstorage/endpoints/Secrets/logsที่ยังคิดเงินขณะclusterพัก

## 5. ส่งกลับ Infra / BI

- [x] รวมbucket/prefix, cluster/database, role, Glue settingsและnetworkที่ทราบใน [DW handoff](dw_handoff.md)
- [x] รวมผลconnection/ETL/COPY/SCD/rollback/replay/reportingโดยไม่แนบsecret
- [x] จัดทำ [BI metric dictionary](bi_handoff.md) และ [reporting acceptance](report/reporting_acceptance_20261024.md)
- [ ] เติมรายละเอียดretention/policy/encryption/endpointID/ค่าใช้จ่ายที่ยังไม่ยืนยัน
- [ ] ส่งเอกสารให้ผู้รับและได้รับการรับมอบจริง (การเตรียมไฟล์ไม่เท่ากับส่งแล้ว)
- [ ] BIเชื่อมข้อมูลและตรวจdashboard; QuickSightสิทธิ์ยังไม่ยืนยัน

## เกณฑ์ปิดงาน

ส่วนinitial snapshot/warehouse/reportingผ่านแล้วตามหลักฐาน เป็นขอบเขตส่งมอบปัจจุบัน ส่วนcontinuous ingestion/schedule/dashboardยังเปิดงานไว้ตามเจ้าของด้านบน handoffเดิมไม่ได้บังคับสร้างNAT/CMK/schedulerทุกอย่าง ห้ามสร้างresourceเพิ่มเพียงเพื่อให้checkboxเต็ม
