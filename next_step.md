

## 🚀 **Step-by-Step: ขึ้น AWS จริง**

### 1. **ตรวจสอบ AWS Resources & Permissions** (ทำกับเพื่อน/Infra Team)

```bash
# เช็คสิทธิ์
aws sts get-caller-identity

# เช็ค Bucket
aws s3 ls

# เช็ค Redshift
aws redshift describe-clusters
# หรือ Serverless
aws redshift-serverless list-workgroups

# ขอ LabRole ARN และเช็ค policy
aws iam get-role --role-name LabRole
aws iam list-attached-role-policies --role-name LabRole
```

**บันทึกค่าที่ได้:**
- `S3_BUCKET` = `your-bucket-name`
- `REDSHIFT_ENDPOINT` = `xxx.redshift.amazonaws.com:5439/dbname` (หรือ workgroup name สำหรับ serverless)
- `IAM_ROLE_ARN` = `arn:aws:iam::123456789012:role/LabRole`
- `AWS_REGION` = `us-east-1` (หรือ region ที่ใช้)

> ⚠️ **สำคัญ**: LabRole ต้องมี policy `s3:GetObject/ListBucket` บน `s3://your-bucket/thelook/curated/*` และ trust policy ให้ `redshift.amazonaws.com`

---

### 2. **รัน Curated Pipeline สร้าง Batch ใหม่**

```bash
# Activate venv
.\.venv\Scripts\Activate.ps1

# สร้าง batch ตั้งชื่อเอง
python code/curated_pipeline.py --batch-id v1-aws-deploy

# ตรวจ validation ผ่าน
cat outputs/curated/v1-aws-deploy/validation_report.json | jq .status
# ต้องได้ "PASS_WITH_KNOWN_ISSUES"
```

---

### 3. **สร้าง Config จริงสำหรับ AWS**

```bash
# Copy template
cp code/aws_batch_config.example.json code/aws_batch_config.json

# แก้ code/aws_batch_config.json ด้วยค่าจริง
{
  "curated_dir": "outputs/curated/v1-aws-deploy",
  "bucket": "your-bucket-name",
  "prefix": "thelook/curated",
  "iam_role": "arn:aws:iam::123456789012:role/LabRole",
  "observed_at": "2026-10-23T10:00:00+00:00"   # ISO 8601 with timezone
}
```

---

### 4. **Generate AWS Package**

```bash
python code/prepare_aws_batch.py \
  --config code/aws_batch_config.json \
  --output outputs/aws/v1-aws-deploy
```

จะได้ใน `outputs/aws/v1-aws-deploy/`:
- `manifests/*.json` — S3 manifest files
- `package.json` — batch metadata + hash
- `run_batch.sql` — SQL เรียก `etl.load_batch()`
- `upload.ps1` — PowerShell script upload ไฟล์ไป S3

---

### 5. **Upload ไป S3**

```powershell
cd outputs/aws/v1-aws-deploy
.\upload.ps1
```

ตรวจสอบหลัง upload:
```bash
aws s3 ls s3://your-bucket/thelook/curated/v1-aws-deploy/ --recursive --human-readable --summarize
```

---

### 6. **ติดตั้ง SQL ใน Redshift** (เรียงลำดับสำคัญ)

```bash
# เชื่อมต่อ Redshift
psql -h <endpoint> -U <user> -d <db>

# หรือ Redshift Serverless
psql -h <workgroup>.<region>.redshift-serverless.amazonaws.com -U <user> -d <db>
```

```sql
-- 1. Control tables
\i code/sql/00_control.sql

-- 2. Staging tables
\i code/sql/01_staging.sql

-- 3. Warehouse tables
\i code/sql/02_warehouse.sql

-- 4. Load procedure
\i code/sql/03_load_batch.sql

-- Verify
\dt etl.*
\dt stg.*
\dt dw.*
\df etl.load_batch
```

---

### 7. **รัน Batch Load** (Autocommit ON, Single Session)

```bash
psql -h <endpoint> -U <user> -d <db> -f outputs/aws/v1-aws-deploy/run_batch.sql
```

**คาดหวัง output:**
```
 batch_id       | package_hash | observed_at        | schema_version | rule_version | loaded_at        | row_count | status
----------------+--------------+--------------------+----------------+--------------+------------------+-----------+--------
 v1-aws-deploy  | abc123...    | 2026-10-23 10:00:00| dw-v1          | provisional-v1| 2026-10-23 10:05|   181759  | SUCCEEDED
```

---

### 8. **ตรวจสอบผล (Post-Load Checks)**

```bash
psql -h <endpoint> -U <user> -d <db> -f code/sql/04_post_load_checks.sql
```

**Key checks ที่ต้องดู:**
- `fact_sales` row count = 181,759
- `distribution_center_drift` = PASS หรือ KNOWN_ISSUE (ดูจำนวน mismatch)
- `dc_comparison` = จำนวน products ที่ DC ไม่ตรง
- ยอดเงิน staging = warehouse (reconciliation)
- `batch_attempts` = SUCCEEDED

---

### 9. **ทดสอบ Edge Cases** (แนะนำก่อน production)

```sql
-- ทดสอบ Re-run batch เดิม (ต้องเป็น NO_OP)
CALL etl.load_batch('v1-aws-deploy', '<same-hash>', '2026-10-23T10:00:00+00:00', '<role>', 'dw-v1', 'provisional-v1');

-- ทดสอบ SCD2: insert user ใหม่ใน batch ถัดไป + order ย้อนหลัง
-- ทดสอบ Rollback: ทำให้ COPY fail แล้วดู batch_attempts = FAILED
```

---

### 10. **Phase ถัดไป (หลัง Load สำเร็จ)**

| Task | Description |
|------|-------------|
| **Reporting Views** | สร้าง views สำหรับ net sales, returns, cancellations (แยกตาม status/date) |
| **Glue Catalog** | (Optional) สร้าง Glue Database/Crawler register schema |
| **Orchestration** | Step Functions / Airflow / cron สำหรับ automation |
| **Monitoring** | CloudWatch alarms สำหรับ batch failure, row count drift |
| **BI Dashboard** | QuickSight / Redash / Metabase / Power BI |

---

## 📋 **Quick Checklist ก่อนเริ่ม**

| ✅ | Item |
|---|------|
| | LabRole ARN ได้แล้ว + attach S3 read policy แล้ว |
| | Redshift cluster/serverless รันอยู่ + เข้าถึงได้ |
| | Security group เปิด port 5439 (หรือ 5432 serverless) |
| | `python code/curated_pipeline.py --batch-id v1-aws-deploy` ผ่านแล้ว |
| | `aws_batch_config.json` กรอกค่าจริงครบ |
| | `upload.ps1` รันสำเร็จ ไฟล์ครบใน S3 |

---

## 🆘 **Troubleshooting Cheatsheet**

| ปัญหา | เช็ค/แก้ |
|--------|---------|
| COPY fail "Access Denied" | LabRole policy + bucket policy + KMS key (ถ้ามี) |
| COPY fail "Manifest not found" | S3 path ใน manifest_url ตรงไหม? upload.ps1 รันทุกไฟล์ไหม? |
| `String exceeds max length` | `ALTER TABLE stg.events ALTER COLUMN uri TYPE VARCHAR(8192);` |
| Procedure param error | `VARCHAR` (ไม่ใส่ความยาว) — แก้ใน `03_load_batch.sql` line 5 |
| SCD2 fail | ดู `etl.batch_attempts` detail, ตรวจ `valid_from`/`version_origin` |
| Fact row count ผิด | รัน `04_post_load_checks.sql` ดู `dc_comparison` และ grain check |

---

# ต่อ
**ได้ทั้ง 2 แบบครับ** — ใช้ตัวที่สะดวกกว่า

---

## 1. **VS Code Integrated Terminal** (แนะนำ — ใช้งานง่ายที่สุด)

```bash
# ใน VS Code: Terminal → New Terminal (หรือ Ctrl+Shift+` )
# จะเปิด PowerShell (Windows) หรือ bash (Linux/macOS) ที่ project root แล้ว

# ทำงานได้เลย
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python code/curated_pipeline.py --batch-id v1-aws-deploy
```

**ข้อดี:**
- อยู่ใน VS Code เดียว ไม่ต้องสลับหน้าต่าง
- Working directory = project root อัตโนมัติ
- Copy/Paste โค้ดจาก editor → terminal ได้เลย
- ดู output ข้างโค้ดพร้อมกัน

---

## 2. **External Terminal** (PowerShell / Command Prompt / Git Bash / Windows Terminal)

```powershell
# เปิด PowerShell แล้ว cd มาที่โปรเจกต์
cd C:\Users\khims\OneDrive\Desktop\3_1\CTI\TheLook-E-commerce-DWH

# แล้วรันคำสั่งเหมือนกัน
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python code/curated_pipeline.py --batch-id v1-aws-deploy
```

**เหมาะสำหรับ:**
- คนชอบ terminal แบบเต็มจอ
- รันคำสั่งที่นานมาก (build, upload) ไม่ต้องมั่วใน VS Code
- ใช้ Windows Terminal / Git Bash / WSL

---

## 3. **สำหรับ AWS CLI / psql** (ขั้นตอนขึ้น AWS)

| Tool | ใช้ใน VS Code Terminal ได้ไหม? | หมายเหตุ |
|------|------------------------------|----------|
| `aws s3 cp`, `aws redshift ...` | ✅ ได้เลย | ต้อง `aws configure` ก่อน |
| `psql -h ... -f file.sql` | ✅ ได้เลย | ต้องติดตั้ง PostgreSQL client (`psql`) |
| `.\upload.ps1` | ✅ ได้เลย | PowerShell script รันใน VS Code Terminal ได้ |

> **Tip**: `psql` บน Windows — ติดตั้งผ่าน PostgreSQL installer หรือ `choco install postgresql` แล้วเพิ่ม `C:\Program Files\PostgreSQL\16\bin` ใน PATH

---

## 🎯 **แนะนำ: ใช้ VS Code Integrated Terminal**

1. เปิด VS Code ที่โฟลเดอร์โปรเจกต์
2. `Ctrl+Shift+` ` → เปิด Terminal
3. รันคำสั่งทีละขั้นตาม guide ข้างบน
4. ถ้าต้องการหลาย terminal พร้อมกัน → คลิก `+` ด้านขวา terminal panel

**ทั้งหมดรันใน VS Code Terminal ได้หมดครับ** — ไม่ต้องเปิดโปรแกรมอื่น

# ต่อ
---

## 📍 **คุณอยู่ที่ไหน ตอนนี้ทำอะไรอยู่**

| สถานะ | รายละเอียด |
|--------|------------|
| **โฟลเดอร์** | `C:\Users\khims\OneDrive\Desktop\3_1\CTI\TheLook-E-commerce-DWH` |
| **Git** | ยังไม่ได้ commit/push (มี `.gitignore` พร้อมแล้ว) |
| **Code/SQL** | พร้อมหมด — curated pipeline, SQL (00-04), tests, quick fixesApplied |
| **AWS** | **ยังไม่ได้ทำอะไรเลย** — รอขั้นตอนนี้ |
| **เป้าหมายขั้นนี้** | **รัน Curated Pipeline → Upload S3 → ติดตั้ง SQL → Load ข้อมูล → Verify** |

---

## 🎯 **ขั้นตอนต่อไป: ขึ้น AWS จริง (8 ขั้นตอน)**

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. เปิด Terminal + Activate venv                                    │
│  2. รัน Curated Pipeline (สร้าง batch)                               │
│  3. ตั้งค่า AWS Config (bucket, role, region)                       │
│  4. Generate Package + Upload S3                                     │
│  5. ติดตั้ง SQL ใน Redshift (00→01→02→03)                            │
│  6. รัน Batch Load (run_batch.sql)                                   │
│  7. Verify ผลลัพธ์ (04_post_load_checks.sql)                        │
│  8. (Optional) ทดสอบ Edge Cases                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ⌨️ **เริ่มขั้นตอนที่ 1: เปิด Terminal + Activate venv**

### ใน VS Code:
1. กด `Ctrl + Shift + \` ` (เปิด Terminal)
2. ตรวจว่า prompt อยู่ที่โฟลเดอร์โปรเจกต์:
   ```
   PS C:\Users\khims\OneDrive\Desktop\3_1\CTI\TheLook-E-commerce-DWH>
   ```

### พิมพ์คำสั่งทีละบรรทัด (กด Enter ทีละบรรทัด):

```powershell
# 1. สร้าง virtual environment (ถ้ายังไม่มี)
python -m venv .venv

# 2. Activate venv
.\.venv\Scripts\Activate.ps1

# 3. ตรวจสอบว่า activate แล้ว (prompt จะมี .venv นำหน้า)
# (.venv) PS C:\Users\khims\OneDrive\Desktop\3_1\CTI\TheLook-E-commerce-DWH>

# 4. ติดตั้ง dependencies
python -m pip install -r code/requirements-dev.txt
```

> **ถ้า PowerShell แจ้ง error "running scripts is disabled"**:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> แล้วรัน `.\.venv\Scripts\Activate.ps1` ใหม่

---

## ✅ **Checkpoint: Activate สำเร็จแล้ว**

Prompt ควรจะเป็น:
```
(.venv) PS C:\Users\khims\OneDrive\Desktop\3_1\CTI\TheLook-E-commerce-DWH>
```

**พร้อมขั้นตอนที่ 2 แล้ว** — บอกมาได้เลยครับ จะสอนขั้นตอน **รัน Curated Pipeline**