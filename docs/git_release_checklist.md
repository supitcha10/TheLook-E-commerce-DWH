# Git release checklist

## ขอบเขตที่จะเข้า repository

- [x] Source Python/SQL/tests, schema/configตัวอย่างและMarkdownส่งมอบ
- [x] handoff1.mdเข้าระบบversion control; ลบignoreเฉพาะไฟล์นี้แล้ว
- [x] เก็บประวัติเอกสารเดิมในdocs/archiveพร้อมป้ายhistorical
- [x] Ignore datasetจริง, outputs, Parquet, ZIP, logs/JSONL, virtualenv/cache, .env/.aws/localconfigและkeyfiles
- [ ] ผู้ดูแลreview diffและไฟล์untrackedทั้งหมดก่อนstage
- [ ] Review account/resource IDs สำหรับระดับการเผยแพร่ของremote (ไม่ใช่secretแต่เป็นข้อมูลenvironmentภายใน)
- [ ] ยืนยันbranch/remote/สิทธิ์ผู้รับ ก่อนcommit/push

## ตรวจในเครื่องก่อน stage

```powershell
git status --short
git diff --check
git diff -- .gitignore README.md WORK_PROGRESS.md
git ls-files --others --exclude-standard
git check-ignore dataset/users.csv outputs/aws/reporting-v1.zip code/aws_batch_config.json
git ls-files dataset outputs .env .aws
```

คำสั่งสุดท้ายควรมีเพียงdataset/README.mdในกลุ่มdataset และไม่มีข้อมูลจริง/credentials/output; .gitignoreไม่เอาไฟล์ที่trackedแล้วออกเอง หากพบให้ตรวจและใช้git rm --cached เฉพาะไฟล์ที่ได้รับอนุญาต ไม่ลบข้อมูลบนเครื่อง

Notebook code/project.ipynb ต้องไม่มีoutputs/execution historyที่มีข้อมูลส่วนบุคคล/secretก่อนstage ตรวจdiffของnotebookแยก ไม่stageทุกอย่างโดยไม่ดู

## หลักฐานและข้อจำกัด

ผลAWS screenshots/exportsและpackagesอยู่ข้างนอกGit สรุปตัวเลขที่reviewแล้วอยู่docs/report/reporting_acceptance_20261024.md
Codeบางตัวมีresource IDsจริงและต้องใช้evidenceในoutputsเพื่อbuild; ห้ามอ้างว่าcloneใหม่รันAWS integrationได้ทันที
การสแกนpatternsเป็นเพียงการตรวจเบื้องต้น ไม่ใช่การรับรองว่าไม่มีsecretทุกประเภท อย่าแสดงค่าที่พบในreport ให้บอกเฉพาะpath/lineแล้วแก้ก่อนเผยแพร่

การจัดเอกสารรอบนี้ไม่stage/commit/push และไม่เปลี่ยนremote การpushเป็นขั้นแยกหลังreview
