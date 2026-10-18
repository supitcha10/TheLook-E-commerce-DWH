# TheLook E-Commerce Data Warehouse

โปรเจกต์เตรียมข้อมูล CSV → curated Parquet → Amazon Redshift staging → Data Warehouse สำหรับงานวิเคราะห์ e-commerce

**สถานะ:** curated ผ่านการตรวจในเครื่อง มี staging/load SQL แล้ว แต่ยังไม่ได้ติดตั้งหรือทดสอบ SQL บน AWS ดู [สถานะงานและ checklist](WORK_PROGRESS.md)

## โครงสร้าง

```text
project/
├── code/                 # Python, notebook, SQL, schema/config และ requirements
├── docs/                 # เอกสารออกแบบและเอกสารทีม
│   ├── report/           # เก็บรายงานเดิมครบ
│   ├── workload.txt
│   └── handoff1.md
├── dataset/              # CSV ต้นทางในเครื่อง
├── outputs/              # ผลลัพธ์ batch ในเครื่อง
├── README.md
└── WORK_PROGRESS.md
```

คำสั่งด้านล่างรันจาก project root เปิด notebook จาก root หรือ `code/` ได้ ส่วน `docs/handoff1.md` และ binary reports ยังคงอยู่ในเครื่อง แต่ถูกกันออกจาก Git ตามการตั้งค่าก่อนหน้า

| ไฟล์/โฟลเดอร์ | หน้าที่ |
|---|---|
| `code/project.ipynb` | สำรวจข้อมูล ตรวจ DQ และอธิบายขั้นตอนเตรียมข้อมูล |
| `code/curated_pipeline.py` | สร้าง Parquet 7 ตารางและรายงานตรวจเทียบ |
| `code/curated_schema.json` | ชนิดข้อมูล curated |
| `code/dq_known_issues_baseline.json` | baseline ของ known issues ที่ยังรอยืนยันกับต้นทาง |
| `docs/dataset_dictionary_and_cleaning.md` | dictionary และกฎทำความสะอาด |
| `docs/data_warehouse_schema_design.md` | DW schema dw-v1, precision, keys และ SCD |
| `code/sql/` | DDL, atomic load procedure และ post-load checks |
| `code/prepare_aws_batch.py` | สร้าง manifest/package/SQL สำหรับ batch โดยไม่เชื่อมต่อ AWS |
| `docs/report/*.md` | รายงานและผลตรวจที่บันทึกไว้ |
| `WORK_PROGRESS.md` | flow, งานที่เสร็จ, งานค้าง และประวัติการเปลี่ยนแปลง |

`dataset/` และ `outputs/` ต้องเตรียมในเครื่อง ไม่ได้แนบข้อมูลไว้ใน Git; `docs/handoff1.md` เป็นเอกสาร infrastructure ภายในที่ขอจากทีมแยกต่างหาก

## เริ่มใช้งานในเครื่อง

ใช้ Python 3.12 จาก project root (ตัวอย่าง PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r code/requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s code -p test_curated_pipeline.py -v
```

เตรียม CSV ตาม [คำแนะนำ dataset](dataset/README.md) แล้วรัน:

```powershell
.\.venv\Scripts\python.exe code/curated_pipeline.py
.\.venv\Scripts\python.exe -m jupyterlab code/project.ipynb
```

Pipeline สร้าง batch ใหม่ใต้ `outputs/curated/` ตรวจ validation_report.json ก่อนใช้งาน สถานะ accepted ปัจจุบันคือ PASS_WITH_KNOWN_ISSUES ซึ่งไม่ได้แปลว่าเจ้าของข้อมูลยืนยันสมมติฐานแล้ว

## SQL และ AWS

อ่าน [คู่มือ SQL](code/sql/README.md) ก่อนใช้งาน สร้าง SQL จากต้นฉบับด้วย:

```powershell
.\.venv\Scripts\python.exe code/build_warehouse_sql.py
Copy-Item code/aws_batch_config.example.json code/aws_batch_config.json
```

ใส่ bucket, IAM role ARN, curated_dir และ observed_at ของ batch ที่ตรวจผ่านใน config จริง ก่อนใช้ `code/prepare_aws_batch.py` ห้าม commit credentials หรือ config ของบัญชีจริง ตัวอย่าง config อ้าง batch ในเครื่องผู้พัฒนาเดิม ต้องปรับตาม batch ของตนเอง

## การทดสอบ

- `python -m unittest discover -s code -p test_curated_pipeline.py -v`: unit tests ของการแปลงข้อมูล ไม่ต้องใช้ dataset จริง
- `python -m unittest discover -s code -p test_warehouse_sql.py -v`: contract tests ในเครื่อง เลือก accepted batch ด้วย `CURATED_TEST_BATCH` (path จาก project root หรือ absolute path) ค่าเริ่มต้นคือ `outputs/curated/20261018T121017059766Z` ต้องมี Parquet และ validation report ของ batch ที่เลือก ส่วนรายงาน FAIL สร้างเป็น fixture ชั่วคราว ไม่ต้องมี failed batch เก่า
- ผลใน [รายงาน local validation](docs/report/warehouse_sql_local_validation.md) เป็นผลของ batch เดิม ไม่ใช่ผลรันหลัง clone และไม่ใช่ Redshift integration test

## ก่อนนำขึ้น Git

เลือก batch สำหรับ warehouse tests จากจุดเดียวใน PowerShell โดยไม่ต้องแก้ example AWS config:

```powershell
$env:CURATED_TEST_BATCH = 'outputs/curated/20261018T121017059766Z'
.\.venv\Scripts\python.exe -m unittest discover -s code -p test_warehouse_sql.py -v
```

ทุก test ใช้ batch นี้ร่วมกัน รวมถึง config สำหรับ package; `observed_at` คำนวณจาก batch ID ใน validation report ตามรูปแบบ timestamp ของ pipeline ไม่ใช่เวลาที่รัน tests ตัวแปรนี้มีผลเฉพาะ tests และอยู่ใน PowerShell session ปัจจุบัน

`.gitignore` แยก CSV, Parquet, outputs, runtime, local config, infrastructure handoff และเอกสาร binary ออก; Git จะเก็บ source, SQL, notebook, schema, baseline และ Markdown เป็นหลัก `.gitattributes` กำหนด line endings เพื่อใช้ข้ามเครื่อง

1. ล้าง output และ execution count ของ notebook ก่อน commit เพื่อไม่เก็บข้อมูลตัวอย่างระดับแถว
2. ตรวจ `git status` และ `git diff --cached` ทุกครั้ง โดยเฉพาะ secret หรือข้อมูลส่วนบุคคลที่เผลอเขียนใน code/Markdown
3. อัปเดต WORK_PROGRESS.md เมื่อจบงาน ระบุผลตรวจจริงและงานที่ยังค้าง

กรณีสร้าง repository ใหม่ คำสั่งตัวอย่าง (ยังไม่ได้ execute ให้):

```powershell
git init -b main
git add .
git status --short
git diff --cached --stat
# ตรวจ staged content ก่อน commit
git diff --cached
git commit -m "Add data warehouse pipeline and SQL workflow"
# เพิ่ม remote URL ของ repository ที่ทีมสร้างแล้ว จึง push
```

หากไฟล์เคยถูก track มาก่อน `.gitignore` จะไม่เอาไฟล์นั้นออกจาก history ต้องตรวจแยกต่างหาก โครงการยังไม่ได้กำหนด license การแจกจ่าย source/dataset ให้ทีมตัดสินใจก่อนเผยแพร่ public
