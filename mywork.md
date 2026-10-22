---

## 🎯 **ขั้นตอนต่อไป: Deploy จริงขึ้น AWS**

จากสถานะตอนนี้ **Code/Tests/Pipeline พร้อมหมดแล้ว** — ขั้นตอนต่อไปคือ **Deploy ขึ้น AWS จริง** ตาม [README.md](README.md) ส่วน "SQL และ AWS"

---

## 📋 **Checklist ก่อนเริ่ม Deploy**

| ✅ | สิ่งที่พร้อมแล้ว |
|---|----------------|
| | Curated Pipeline รันได้ → `PASS_WITH_KNOWN_ISSUES` |
| | `observed_at` บันทึกใน `validation_report.json` อัตโนมัติ |
| | SQL (00-04) สร้างแล้ว รวม quick fixes |
| | Tests ผ่าน 7/7 (3 curated + 4 warehouse) |
| | README.md มีคำแนะนำครบทุกขั้นตอน |

---

## 🚀 **Next Steps: ตามลำดับใน README**

### 1. **Build SQL** (ถ้ายังไม่รันหลังแก้ quick fixes)
```powershell
python code/build_warehouse_sql.py
```

### 2. **สร้าง S3 Bucket** (Same Region as Redshift)
```powershell
aws configure get region
aws s3api create-bucket --bucket my-unique-bucket-name-12345 --region us-east-1
```

### 3. **ดึง LabRole ARN**
```powershell
aws iam get-role --role-name LabRole --query 'Role.Arn' --output text
```

### 4. **ตั้งค่า AWS Credentials** (Learner Lab ต้องมี session token)
```powershell
aws configure set aws_access_key_id YOUR_ACCESS_KEY
aws configure set aws_secret_access_key YOUR_SECRET_KEY
aws configure set aws_session_token YOUR_SESSION_TOKEN
aws configure set region us-east-1
```

### 5. **Verify Access**
```powershell
aws sts get-caller-identity
aws s3 ls s3://my-unique-bucket-name-12345
```

### 6. **Config aws_batch_config.json**
```powershell
cp code/aws_batch_config.example.json code/aws_batch_config.json
code code/aws_batch_config.json
```
แก้ 5 field:
- `curated_dir`: `outputs/curated/20261022T184906775876Z` (จาก `RESULT_PATH` ล่าสุด)
- `bucket`: `my-unique-bucket-name-12345`
- `prefix`: `thelook/curated`
- `iam_role`: `arn:aws:iam::111122223333:role/LabRole`
- `observed_at`: **copy จาก `validation_report.json`** (ห้ามแต่งเอง)

### 7. **Generate Package + Upload S3**
```powershell
python code/prepare_aws_batch.py --config code/aws_batch_config.json --output outputs/aws/20261022T184906775876Z
cd outputs/aws/20261022T184906775876Z
.\upload.ps1
```

### 8. **ติดตั้ง SQL ใน Redshift** (เรียงลำดับสำคัญ)
```powershell
psql -h <endpoint> -U <user> -d <db> -f code/sql/00_control.sql
psql -h <endpoint> -U <user> -d <db> -f code/sql/01_staging.sql
psql -h <endpoint> -U <user> -d <db> -f code/sql/02_warehouse.sql
psql -h <endpoint> -U <user> -d <db> -f code/sql/03_load_batch.sql
```

### 9. **รัน Batch Load**
```powershell
psql -h <endpoint> -U <user> -d <db> -f outputs/aws/20261022T184906775876Z/run_batch.sql
```

### 10. **Verify ผลลัพธ์**
```powershell
psql -h <endpoint> -U <user> -d <db> -f code/sql/04_post_load_checks.sql
```

---

## 🔍 **สิ่งที่ต้องขอจากเพื่อน/Infra Team ก่อนเริ่ม**

| ข้อมูล | ตัวอย่าง |
|----------|---------|
| **Redshift Endpoint** | `xxx.redshift.amazonaws.com:5439/dbname` |
| **Redshift Region** | `us-east-1` (สำคัญ: Bucket ต้องอยู่ region เดียวกัน) |
| **LabRole ARN** | `arn:aws:iam::111122223333:role/LabRole` |
| **Learner Lab AWS Details** | Access Key, Secret Key, **Session Token** |

---

## ❓ **อยากเริ่มข้อไหนก่อน?**

บอกมาว่าจะเริ่มที่ข้อไหน (1-6) — แล้วเราจะทำทีละขั้นตอนครับ