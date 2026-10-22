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

**วิธีที่ 1: Activate ครั้งเดียว (แนะนำสำหรับพัฒนาแบบ interactive)**
```powershell
# สร้าง venv (ครั้งแรกเท่านั้น)
python -m venv .venv

# Activate
.\.venv\Scripts\Activate.ps1

# ตั้งแต่นี้เป็นต้นไป ใช้ python โดยตรงได้เลย
python -m pip install -r code/requirements-dev.txt
python -m unittest discover -s code -p test_curated_pipeline.py -v
python code/curated_pipeline.py --batch-id v1-baseline
python -m jupyterlab code/project.ipynb
python code/build_warehouse_sql.py
```

> **หมายเหตุ**: ถ้า PowerShell บล็อก script ให้รัน `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` ก่อนครั้งแรก

**วิธีที่ 2: ใช้ full path ทุกคำสั่ง (เหมาะสำหรับ CI/CD หรือ script ที่ไม่ได้ activate)**
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r code/requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s code -p test_curated_pipeline.py -v
```

---

### สำหรับ Git Bash / WSL / Linux / macOS

**วิธีที่ 1: Activate ครั้งเดียว (แนะนำสำหรับพัฒนาแบบ interactive)**
```bash
# สร้าง venv (ครั้งแรกเท่านั้น)
python -m venv .venv

# Activate
source .venv/bin/activate

# ตั้งแต่นี้เป็นต้นไป ใช้ python โดยตรงได้เลย
python -m pip install -r code/requirements-dev.txt
python -m unittest discover -s code -p test_curated_pipeline.py -v
python code/curated_pipeline.py --batch-id v1-baseline
python -m jupyterlab code/project.ipynb
python code/build_warehouse_sql.py
```

**วิธีที่ 2: ใช้ full path ทุกคำสั่ง**
```bash
python -m venv .venv
.venv/bin/python -m pip install -r code/requirements-dev.txt
.venv/bin/python -m unittest discover -s code -p test_curated_pipeline.py -v
```

---

เตรียม CSV ตาม [คำแนะนำ dataset](dataset/README.md) แล้วรัน:

### รัน Curated Pipeline (Auto Timestamp Only)

Pipeline สร้าง Batch ID แบบ timestamp อัตโนมัติ (รูปแบบ `YYYYMMDDTHHMMSSffffffZ`) เพื่อให้ `observed_at` เพิ่มขึ้นเรื่อยๆ ตามลำดับเวลาจริง — **รองรับ AWS Deployment และ NO_OP logic ได้โดยอัตโนมัติ**

> **หมายเหตุ**: `observed_at` ถูกบันทึกใน `validation_report.json` อัตโนมัติ

**วิธีที่ 1 (Activate แล้ว):**
```powershell
python code/curated_pipeline.py
```

**วิธีที่ 2 (Full path):**
```powershell
.\.venv\Scripts\python.exe code/curated_pipeline.py
```

**Output ที่คาดหวัง:**
```
distribution_centers: 10 curated rows, 0 quarantined
products: 29,120 curated rows, 0 quarantined
users: 100,000 curated rows, 0 quarantined
orders: 125,226 curated rows, 0 quarantined
order_items: 181,759 curated rows, 0 quarantined
inventory_items: 490,705 curated rows, 0 quarantined
events: 2,431,963 curated rows, 0 quarantined
RESULT_PATH=outputs\curated\20261023T143022123456Z
STATUS=PASS_WITH_KNOWN_ISSUES
```

**ตรวจสอบ validation ผ่าน:**
```powershell
Get-Content outputs\curated\20261023T143022123456Z\validation_report.json | ConvertFrom-Json | Select-Object batch_id, status, observed_at
# ต้องได้ status = PASS_WITH_KNOWN_ISSUES และมี observed_at (ISO 8601 UTC)
```

> **Batch ID แบบ timestamp จำเป็น** เพื่อให้ `etl.load_batch` procedure ทำงานได้ถูกต้อง:
> - `observed_at` เพิ่มขึ้นเรื่อยๆ (strictly increasing) ตามลำดับเวลาจริง
> - NO_OP logic ทำงานได้ถูกต้อง (เทียบ `observed_at` + `package_hash`)
> - Test framework อ่าน `observed_at` จาก `validation_report.json` ได้โดยตรง

จากนั้นเปิด notebook:

**วิธีที่ 1 (Activate แล้ว):**
```powershell
python -m jupyterlab code/project.ipynb
```

**วิธีที่ 2 (Full path):**
```powershell
.\.venv\Scripts\python.exe -m jupyterlab code/project.ipynb
```

Pipeline สร้าง batch ใหม่ใต้ `outputs/curated/` ตรวจ validation_report.json ก่อนใช้งาน สถานะ accepted ปัจจุบันคือ PASS_WITH_KNOWN_ISSUES ซึ่งไม่ได้แปลว่าเจ้าของข้อมูลยืนยันสมมติฐานแล้ว

## SQL และ AWS

อ่าน [คู่มือ SQL](code/sql/README.md) ก่อนใช้งาน

### 1. สร้าง SQL (หลัง Curated Pipeline เสร็จ)
```powershell
# วิธีที่ 1 (Activate แล้ว)
python code/build_warehouse_sql.py

# วิธีที่ 2 (Full path)
.\.venv\Scripts\python.exe code/build_warehouse_sql.py
```
> สร้าง `01_staging.sql`, `02_warehouse.sql`, `03_load_batch.sql` ใหม่ (รวม quick fixes)

### 2. สร้าง Bucket S3 (Same Region as Redshift)
```powershell
# ดู region ของ Redshift / Learner Lab
aws configure get region

# สร้าง bucket (ชื่อต้อง unique ทั้ง AWS, ต้องอยู่ region เดียวกับ Redshift)
aws s3api create-bucket --bucket my-unique-bucket-name-12345 --region us-east-1
```
> ⚠️ Bucket ต้องอยู่ region เดียวกับ Redshift (COPY ใน `03_load_batch.sql` ไม่มี REGION parameter)

### 3. ดึง LabRole ARN
```powershell
aws iam get-role --role-name LabRole --query 'Role.Arn' --output text
# Output: arn:aws:iam::111122223333:role/LabRole
```

### 4. ตั้งค่า AWS Credentials (Learner Lab)
```powershell
# ใช้ค่าจาก "AWS Details" ของ Learner Lab
aws configure set aws_access_key_id YOUR_ACCESS_KEY
aws configure set aws_secret_access_key YOUR_SECRET_KEY
aws configure set aws_session_token YOUR_SESSION_TOKEN  # สำคัญ! เปลี่ยนทุกครั้งที่เริ่ม session
aws configure set region us-east-1  # หรือ region ที่ได้จากข้อ 2
```
> CloudShell ไม่ต้องตั้งค่า — ใช้ได้เลย

### 5. เช็คสิทธิ์ก่อนต่อ
```powershell
aws sts get-caller-identity
aws s3 ls s3://my-unique-bucket-name-12345
```

### 6. Copy Config Template และแก้ค่าจริง
```powershell
cp code/aws_batch_config.example.json code/aws_batch_config.json
code code/aws_batch_config.json
```

**แก้ด้วยค่าจริง (5 field):**
```json
{
  "curated_dir": "outputs/curated/v1-baseline",
  "bucket": "my-unique-bucket-name-12345",
  "prefix": "thelook/curated",
  "iam_role": "arn:aws:iam::111122223333:role/LabRole",
  "observed_at": "2026-10-22T18:21:40.634926+00:00"
}
```

**Key Points:**
- `curated_dir` = batch ที่เพิ่งสร้าง (จาก `RESULT_PATH` รองรับทั้ง custom และ timestamp format)
- `observed_at` = **copy จาก validation_report.json** (field `observed_at`) **ห้ามแต่งเอง**
- `bucket` = bucket ที่สร้างเอง (unique, same region as Redshift)
- `iam_role` = LabRole ARN จริงจาก `aws iam get-role`
- `prefix` = ตามโครงสร้าง S3 ในเอกสาร (`curated/<batch_id>/<table>/*.parquet`)

> **Batch ID แบบ timestamp จำเป็น** สำหรับ AWS deployment และ NO_OP logic

### 7. Verify ก่อน Generate Package
```powershell
# 1. validation_report.json สถานะ PASS_WITH_KNOWN_ISSUES
Get-Content outputs\curated\20261023T143022123456Z\validation_report.json | ConvertFrom-Json | Select-Object batch_id, status, observed_at

# 2. AWS credentials ทำงาน
aws sts get-caller-identity
aws s3 ls s3://my-unique-bucket-name-12345
```

### 8. Generate Package และ Upload S3
```powershell
python code/prepare_aws_batch.py --config code/aws_batch_config.json --output outputs/aws/20261023T143022123456Z
cd outputs/aws/20261023T143022123456Z
.\upload.ps1
```

### 9. ติดตั้ง SQL ใน Redshift (เรียงลำดับสำคัญ)
```powershell
psql -h <endpoint> -U <user> -d <db> -f code/sql/00_control.sql
psql -h <endpoint> -U <user> -d <db> -f code/sql/01_staging.sql
psql -h <endpoint> -U <user> -d <db> -f code/sql/02_warehouse.sql
psql -h <endpoint> -U <user> -d <db> -f code/sql/03_load_batch.sql
```

### 10. รัน Batch Load (Autocommit ON, Single Session)
```powershell
psql -h <endpoint> -U <user> -d <db> -f outputs/aws/20261023T143022123456Z/run_batch.sql
```

### 11. Verify ผลลัพธ์
```powershell
psql -h <endpoint> -U <user> -d <db> -f code/sql/04_post_load_checks.sql
```

## การทดสอบ

### Local Unit Tests (ไม่ต้องมี dataset จริง)
```powershell
# วิธีที่ 1 (Activate แล้ว)
python -m unittest discover -s code -p test_curated_pipeline.py -v

# วิธีที่ 2 (Full path)
.\.venv\Scripts\python.exe -m unittest discover -s code -p test_curated_pipeline.py -v
```

### Contract Tests (ต้องมี accepted batch + validation report)
```powershell
# ตั้ง batch ที่จะทดสอบ (ใช้ batch timestamp format จากการรัน pipeline)
$env:CURATED_TEST_BATCH = 'outputs/curated/20261023T143022123456Z'

# วิธีที่ 1 (Activate แล้ว)
python -m unittest discover -s code -p test_warehouse_sql.py -v

# วิธีที่ 2 (Full path)
.\.venv\Scripts\python.exe -m unittest discover -s code -p test_warehouse_sql.py -v
```

**รายละเอียด:**
- `test_curated_pipeline.py`: unit tests การแปลงข้อมูล — ไม่ต้องใช้ dataset จริง
- `test_warehouse_sql.py`: contract tests — ต้องมี accepted batch + validation report
  - เลือก batch ด้วย `$env:CURATED_TEST_BATCH` (path จาก project root หรือ absolute path)
  - Batch ต้องมี Parquet และ validation report สถานะ `PASS_WITH_KNOWN_ISSUES`
  - `observed_at` อ่านจาก `validation_report.json` (field `observed_at`) — pipeline บันทึกอัตโนมัติ
  - รายงาน FAIL สร้างเป็น fixture ชั่วคราว ไม่ต้องมี failed batch เก่า
- ผลใน [รายงาน local validation](docs/report/warehouse_sql_local_validation.md) เป็นผลของ batch เดิม ไม่ใช่ผลรันหลัง clone และไม่ใช่ Redshift integration test

## ก่อนนำขึ้น Git

เลือก batch สำหรับ warehouse tests จากจุดเดียวใน PowerShell โดยไม่ต้องแก้ example AWS config (ใช้ batch timestamp format):

**วิธีที่ 1 (Activate แล้ว):**
```powershell
$env:CURATED_TEST_BATCH = 'outputs/curated/20261023T143022123456Z'
python -m unittest discover -s code -p test_warehouse_sql.py -v
```

**วิธีที่ 2 (Full path):**
```powershell
$env:CURATED_TEST_BATCH = 'outputs/curated/20261023T143022123456Z'
.\.venv\Scripts\python.exe -m unittest discover -s code -p test_warehouse_sql.py -v
```

ทุก test ใช้ batch นี้ร่วมกัน รวมถึง config สำหรับ package; `observed_at` อ่านจาก `validation_report.json` (field `observed_at`) — pipeline บันทึกอัตโนมัติ ตัวแปรนี้มีผลเฉพาะ tests และอยู่ใน PowerShell session ปัจจุบัน

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
