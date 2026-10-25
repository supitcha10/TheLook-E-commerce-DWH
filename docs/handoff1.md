# Handoff checklist — Infra → DW → BI

อัปเดต 24 ตุลาคม 2026; checklistนี้แทนสถานะเดิมวันที่16ต.ค. เก็บต้นฉบับไว้ใน [archive](archive/handoff1_original_20261016.md) อ่านค่าทรัพยากร/สถาปัตยกรรม/ผลทดสอบที่ [DW handoff](dw_handoff.md)

[x] = มีหลักฐานผ่านตามขอบเขตข้อความ; [ ] = ยังเหลือหรือยังไม่ยืนยัน ไม่ติ๊กว่าเสร็จจากการมีโค้ดอย่างเดียว

## A. ข้อมูลและแบบจำลอง — DW

- [x] ตรวจ schema/type/PK/FK/nulls/duplicates ของ7ตารางและจัดทำ dictionary
- [x] กำหนด raw/curated/temp แยก และเงิน decimal(18,6)
- [x] ตกลงgrain fact_salesหนึ่งแถวต่อorder item; 4dimensions, Type2 users/Type1 productsและDC
- [x] counts/money reconciliation, SCD2/rollback/retry/NO_OP ผ่านบน AWS
- [x] Reporting8viewsและ8checksผ่าน; ผู้ใช้เลือกแยกยอดตามสถานะ ยังไม่ใช่net sales
- [x] ผู้ใช้ตกลงใช้ Kaggle Version 1 ดาวน์โหลด 6 ตุลาคม 2026 เป็นข้อมูลคงที่; S3 URI/ขนาดตรงไฟล์ในเครื่องครบ 7 CSV ตาม [หลักฐานต้นทาง](source_dataset_acceptance.md) ยังไม่ตรวจ checksum เทียบ S3
- ข้อจำกัด: ต้นทางไม่ระบุเวลา export/source_observed_at/timezone และยังไม่ยืนยันความครบถ้วนทุกแถวจาก BigQuery; ไม่อนุมานจากวันดาวน์โหลดหรือ S3
- [ ] DW/BI ยืนยันรับทราบ known issues ตาม provisional-v1 พร้อมชื่อ/วันที่ในเอกสารต้นทาง; ยังไม่มีคำยืนยันสาเหตุจากต้นทาง และข้อตกลงข้อมูลคงที่ไม่ใช่การอนุมัติ known issues

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
- นอกขอบเขตส่งงานข้อมูลคงที่: pipeline รับ snapshot ใหม่/Glue orchestration/schedule ไม่ได้ deploy หากเปลี่ยนขอบเขตต้องทำตาม source contract และทดสอบเพิ่ม ไม่ติ๊กเป็นงานเสร็จ

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
- [x] จัดทำ [ข้อมูลต้นทางและ known issues](source_dataset_acceptance.md); ช่องยืนยันของ DW/BI และรับมอบยังรอหลักฐาน
- [ ] เติมรายละเอียดretention/policy/encryption/endpointID/ค่าใช้จ่ายที่ยังไม่ยืนยัน
- [ ] ส่งเอกสารให้ผู้รับและได้รับการรับมอบจริง (การเตรียมไฟล์ไม่เท่ากับส่งแล้ว)
- [ ] BIเชื่อมข้อมูลและตรวจdashboard; QuickSightสิทธิ์ยังไม่ยืนยัน

## เกณฑ์ปิดงาน

ส่วนข้อมูลคงที่ Version 1/warehouse/reporting พร้อมส่งต่อตามหลักฐาน ไม่เท่ากับทีมยอมรับ known issues หรือรับมอบแล้ว ส่วน continuous ingestion/schedule อยู่นอกขอบเขตครั้งนี้ ไม่ได้ deploy งานร่วมที่ยังเปิดคือ Infra review retention/security/cost/monitoring, สิทธิ์ BI, Dashboard และการรับมอบจริง handoffเดิมไม่ได้บังคับสร้างNAT/CMK/schedulerทุกอย่าง ห้ามสร้างresourceเพิ่มเพียงเพื่อให้checkboxเต็ม

## สถานะชุดหลักฐานที่รวบรวมแล้ว

- [x] จัดชุด `outputs/DW-handoff-evidence/` พร้อม inventory และตรวจ SHA-256 สำเนาเทียบต้นฉบับในเครื่อง (ไม่ใช่ checksum เทียบ S3)
- [x] รวม READY/report/Glue-CloudWatch linkage, Redshift/reporting totals, SCD audit และ replay result/statements รอบที่ผ่าน
- หลักฐานที่ยังไม่มีต้นฉบับในชุด: rollback before/after, atomic patch verification และ reporting checks8รายการรอบเดิม; ไม่เปลี่ยนสถานะการทดสอบเดิมเป็นการทดสอบใหม่ และไม่ใช้ audit/totals แทนหลักฐานเหล่านี้
- DW พร้อมส่งต่อภายใต้ขอบเขตข้อมูลคงที่; checklist เรื่อง known issues/Infra/BI/รับมอบที่ยังว่างข้างต้นยังคงรอหลักฐาน ไม่ต้องรัน Glue/loader/replay ซ้ำเพื่อรับช่วงงาน

## เพิ่ม SQL12 — 25 ตุลาคม 2026

- [x] มี [SQL12](../code/sql/12_bi_role_views_final.sql) และ [dictionary/permission map](bi_role_views.md) สำหรับbi8views/users-groups5ฝ่าย
- สถานะรัน/ทดสอบแล้วเป็นข้อความจากผู้จัดทำSQL ยังไม่มีหลักฐานต้นฉบับSQL12แนบแยกจากreportingเดิม
- [ ] เก็บผล10SELECTส่วน8, ตรวจgrain/reference/inventory/eventsและeffective privileges/positive-negativeครบ5กลุ่ม
- การให้สิทธิ์ตามview/groupไม่ใช่RLS การยืนยันBI connection/Dashboard/known issues/รับมอบยังเปิดตามรายการก่อนหน้า
