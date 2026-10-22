ขอบคุณข้อมูลจาก Claude อีกตัวครับ — **ตรงจุดมาก** ให้ปรับแผนให้ตรงกับ Learner Lab จริง

---

## 🔧 **ปรับแผน Deploy ใหม่ (Learner Lab Optimized)**

### ✅ **สิ่งที่แก้แล้ว / ตรวจสอบแล้ว**

| จุด | สถานะ |
|-----|-------|
| **Quick Fixes (SCD bug)** | ✅ แก้แล้วใน `03_load_batch.sql` + `load_body.sql.inc` + `build_warehouse_sql.py` (lines 198, 224) |
| **Batch ID Auto Timestamp Only** | ✅ ลบ `--batch-id` แล้ว |
| **Tests ผ่าน 7/7** | ✅ |
| **README.md ครบทุกขั้นตอน** | ✅ |

---

## 🚀 **ลำดับขั้นตอนใหม่ (Cost Optimized)**

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: ไม่ต้อง Redshift (ทำได้เลยตอนนี้)                    │
├─────────────────────────────────────────────────────────────┤
│ 1. Build SQL          → python code/build_warehouse_sql.py   │
│ 2. สร้าง S3 Bucket     → aws s3api create-bucket             │
│ 3. ดึง LabRole ARN    → aws iam get-role                     │
│ 4. Config aws_batch_config.json (แก้ 5 field)                │
│ 5. Generate Package   → python prepare_aws_batch.py          │
│ 6. Upload S3          → .\upload.ps1                         │
│ 7. Verify S3          → aws s3 ls s3://bucket/...            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: สร้าง Redshift → โหลด → ทดสอบ → ลบ (คิดเงินน้อยที่สุด) │
├─────────────────────────────────────────────────────────────┤
│ 8. สร้าง Redshift Serverless (Same Region as Bucket)        │
│ 9. ผูก LabRole + Trust Policy                                │
│ 10. รัน SQL 00-03 ใน Query Editor v2                         │
│ 11. รัน run_batch.sql (session เดียว)                        │
│ 12. Verify (04_post_load_checks.sql)                         │
│ 13. ทดสอบ Re-run (NO_OP) + SCD edge case                     │
│ 14. Pause/Delete Redshift                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 **สิ่งที่ต้องเช็กตอนสร้าง Redshift (3 จุดสำคัญ)**

| # | เช็กอะไร | ทำยังไง |
|---|----------|---------|
| **1. Region** | Bucket และ Redshift ต้อง **region เดียวกัน** | `aws configure get region` → สร้าง Redshift ใน region เดียว |
| **2. LabRole + Trust Policy** | ผูก LabRole ให้ Redshift + Trust Policy มี `redshift.amazonaws.com` | Console → Redshift → Manage IAM roles / IAM Console → Role → Trust relationships |
| **3. Query Editor v2** | ใช้แทน `psql` (ง่ายกว่า ไม่ต้องเปิด public access) | Console → Redshift → Query Editor v2 → รัน 00-03 แล้ว `run_batch.sql` ใน session เดียว |

---

## ⚠️ **จุดระวัง**

| จุด | รายละเอียด |
|-----|-----------|
| **Credentials** | อย่าใส่ Access Key/Secret/Token ในแชท/โค้ด — ใช้ CloudShell หรือตั้งค่า local เอง |
| **SCD Bug Fix** | ✅ แก้แล้ว (lines 198, 224 ใน `03_load_batch.sql`) — batch แรก OK, batch ที่ 2 จะใช้ `OBSERVED_NEW` with `valid_from=NULL` |
| **Session เดียว** | `expected_inputs` + `expected_money` เป็น TEMP table → ต้องรัน 00-03 + `run_batch.sql` **ใน session เดียว** (Query Editor v2 รันแบบต่อเนื่องได้) |

---

## 🎯 **Next Action: เริ่ม Phase 1 กันเลย**

### ขั้นตอนที่ 1-3 (Build SQL + Bucket + LabRole ARN)

```powershell
# 1. Build SQL (รวม quick fixes)
python code/build_warehouse_sql.py

# 2. เช็ค Region + สร้าง Bucket
aws configure get region
aws s3api create-bucket --bucket my-unique-bucket-name-12345 --region us-east-1

# 3. ดึง LabRole ARN
aws iam get-role --role-name LabRole --query 'Role.Arn' --output text
```

---

**อยากเริ่มทีละขั้นตอนกันไหมครับ?** เริ่มจาก **Build SQL** ก่อน (ขั้นตอนที่ 1) — แล้วค่อยไปทีละขั้นตอนครับ