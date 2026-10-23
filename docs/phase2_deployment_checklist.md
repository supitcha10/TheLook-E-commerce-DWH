# Phase 2 — Redshift deployment checklist

วันที่จัดทำ: 2026-10-23 | ใช้ PowerShell จาก `D:\DSBA\31\cti\project` และ SQL ใน Query Editor v2

เอกสารนี้เป็นคู่มือ ไม่ใช่หลักฐานว่า deploy หรือ tests บน AWS ผ่านแล้ว ค่า `REPLACE_*` ต้องแทนด้วยค่าจริงก่อนรัน ตัวอย่างชื่อทรัพยากรเปลี่ยนได้ตามทีมและข้อจำกัด Learner Lab

เพิ่มรายการ C. Redshift จากข้อความ handoff1 ที่ผู้ใช้ส่งมา: ต้องเลือก provisioned หรือ Serverless ก่อนสร้างจริง ขั้น 5 เดิมเป็นเส้นทาง Serverless; หากเลือก provisioned ใช้ขั้น 5P แทน และเลือก cluster ใน Query Editor ส่วน SQL/การตรวจข้อมูลขั้น 6–10 ใช้ร่วมกัน

## ลำดับงานและสิ่งที่ทำล่วงหน้าได้

| ขั้น | งาน | ก่อนรับ Phase 1 ทำได้หรือไม่ |
|---|---|---|
| 0 | ตัดสินใจชนิด Redshift และผู้รับผิดชอบตาม handoff | ได้; ยืนยันสิทธิ์และราคาใน Lab ก่อนสร้าง |
| 1 | เตรียมเครื่อง อ่านโค้ด และกำหนด revision | ได้; revision สุดท้ายยืนยันตอนรับงาน |
| 2 | ตรวจบัญชี Lab, role, สิทธิ์ และ network | ได้ เมื่อมีสิทธิ์เข้า Lab |
| 3 | เตรียม parameters และแผนทดสอบ | ได้; ค่า batch/S3 รอยืนยัน |
| 4 | รับและตรวจ package/upload | ต้องรอ Phase 1 |
| 5 | สร้าง namespace/workgroup และจำกัด usage | ทำก่อนได้ทางเทคนิค แต่แนะนำรอขั้น 4 ผ่าน |
| 6 | เชื่อมต่อและติดตั้ง SQL | ต้องมี Redshift และ revision ที่ยืนยันแล้ว |
| 7 | โหลด batch แรก | ต้องรอ package/upload และขั้น 6 |
| 8 | ตรวจรับข้อมูล | หลังโหลดสำเร็จ |
| 9 | ทดสอบ NO_OP และ identity rejection | หลังโหลดสำเร็จ |
| 10 | SCD/rollback/concurrency/cancellation | เตรียม fixture ล่วงหน้าได้; execute ใน DB ทดสอบ |
| 11 | ส่งหลักฐานและจัดการทรัพยากร | หลังตรวจรับและตกลงกับทีม BI |

## 0. รับเงื่อนไข C. Redshift จาก handoff — ทำล่วงหน้าได้

- [ ] ตัดสินใจ provisioned cluster หรือ Serverless ตามสิทธิ์ Learner Lab, workload/ช่วงเวลาที่ใช้, วิธีหยุด/ลบ และราคาใน us-east-1 ณ วันสร้างจริง
- [ ] จดประเภทที่เลือก เหตุผล ผู้สร้าง ผู้ทดสอบ และผู้รับผิดชอบ cleanup; อย่าสร้างทั้งสองแบบเพื่อทดลองโดยไม่มีแผนงบ
- [ ] ตรวจราคา compute และ storage/snapshots แยกกัน รวมค่า network ที่เกี่ยวข้อง ใช้ [AWS pricing](https://aws.amazon.com/redshift/pricing/) และเลือก region us-east-1; ไม่ใช้ตัวเลขเริ่มต้นของหน้าเว็บแทน estimate ของ configuration จริง
- [ ] ยืนยันสิทธิ์สร้าง/ผูก role/เชื่อมต่อของประเภทที่เลือก; การอ่าน resource ได้ไม่ยืนยันสิทธิ์สร้าง

| ประเด็นตัดสินใจ | Provisioned | Serverless |
|---|---|---|
| Parameters หลัก | node type, จำนวน nodes, cluster identifier | base/max RPU, namespace/workgroup |
| Network | cluster subnet group; ตรวจ private subnet A/B และ AZ | subnet IDs ของ workgroup; ตรวจ coverage ตาม configuration ไม่ถือว่า A/B เพียงพออัตโนมัติ |
| หยุดใช้งาน | ตรวจว่า cluster configuration รองรับ pause/resume; storage/backup ยังต้องคิด | จัดการ workload/usage limit; การหยุด query ไม่ใช่ลบ storage |
| Cleanup | ตัดสินใจ final snapshot ก่อนลบ cluster | workgroup, namespace และ snapshots เป็นรายการที่ต้องตรวจแยก |

### สถานะบางส่วนที่ได้รับจาก handoff (ยังไม่ได้ตรวจ AWS ซ้ำ)

| รายการ | หลักฐานที่ handoff ระบุ | สิ่งที่ยังต้องทำ |
|---|---|---|
| TCP 5439 | SG เตรียม inbound จาก Glue SG เท่านั้นแล้ว | ยืนยัน port ของ endpoint ตอนสร้าง และทดสอบจาก client ที่อนุญาต |
| LabRole | trust มี redshift แล้ว | ตรวจ principal ให้ตรงประเภท Redshift, ทดลอง association จริง และ COPY/UNLOAD ตามขอบเขตงาน |

สองรายการนี้ยังไม่ติ๊กว่าผ่านครบ เพราะ SG rule ไม่ยืนยัน endpoint และ trust ไม่ยืนยันว่า Lab อนุญาตให้ผูก role

## 1. เตรียมเครื่องและโค้ด — ทำล่วงหน้าได้

- [ ] ตรวจสถานะ Git ก่อน pull; ถ้ามีงานค้างให้จัดการก่อน ไม่ใช้ reset ทิ้งงาน

```powershell
Set-Location 'D:\DSBA\31\cti\project'
git status
git log -1 --format='%H %s'
aws --version
.\.venv\Scripts\python.exe --version
```

- [ ] ถ้า working tree clean และต้องการอัปเดตจากทีม ใช้ `git pull --ff-only origin main`; ถ้า branch diverge ให้ตกลงวิธีรวมงานก่อน
- [ ] อ่าน `code/sql/README.md`, schema design และไฟล์ SQL 00–04
- [ ] ตรวจ generator ใน working copy แล้วตรวจ diff; คำสั่ง build เขียนไฟล์ SQL ใหม่

```powershell
.\.venv\Scripts\python.exe code/build_warehouse_sql.py
git diff -- code/sql
```

- [ ] หากมี curated batch ในเครื่อง ให้รัน local tests; ถ้ายังไม่มีให้ทำหลังรับ Phase 1

```powershell
$env:CURATED_TEST_BATCH = 'outputs/curated/REPLACE_BATCH_ID'
.\.venv\Scripts\python.exe -m unittest discover -s code -v
```

เกณฑ์ผ่าน: tests ที่รันผ่านจริงและจดจำนวน tests/commit/batch ไว้ ไม่คัดลอกผล “7/7” จากบันทึกเก่า Local tests ไม่ใช่หลักฐานว่า SQL compile บน Redshift

สถานะที่ตรวจขณะเขียนคู่มือนี้: SQL และ template ปัจจุบันให้ `OBSERVED_NEW` มี `valid_from=NULL` แล้ว ต่างจากการตรวจครั้งก่อน ต้องให้ทีมยืนยันนโยบายใช้ snapshot แทนประวัติที่ไม่ทราบ และตรวจเอกสารให้ตรงก่อนรับรอง SCD

## 2. ตรวจ Lab และ IAM — ทำล่วงหน้าได้

- [ ] Start Lab; จดเวลาหมดอายุและงบคงเหลือ
- [ ] ตั้ง credentials ตามหน้า Lab ในเครื่องเอง รวม session token; ไม่เก็บ credentials ใน repo/รายงาน
- [ ] ตรวจบัญชีและ role ด้วยคำสั่งอ่านอย่างเดียว

```powershell
$AwsRegion = 'us-east-1' # ยืนยันกับ Phase 1 อีกครั้ง
aws sts get-caller-identity --region $AwsRegion --no-cli-pager
aws iam get-role --role-name LabRole --query 'Role.{Arn:Arn,Trust:AssumeRolePolicyDocument}' --output json --no-cli-pager
aws redshift-serverless list-workgroups --region $AwsRegion --no-cli-pager
aws redshift-serverless list-namespaces --region $AwsRegion --no-cli-pager
aws ec2 describe-subnets --region $AwsRegion --query 'Subnets[].{ID:SubnetId,VPC:VpcId,AZ:AvailabilityZone,FreeIPs:AvailableIpAddressCount}' --output table
aws ec2 describe-security-groups --region $AwsRegion --query 'SecurityGroups[].{ID:GroupId,VPC:VpcId,Name:GroupName}' --output table
```

- [ ] ตรวจ Lab อนุญาตประเภท Redshift ที่เลือก, Query Editor v2, การสร้างทรัพยากร และ `iam:PassRole`; คำสั่ง redshift-serverless ข้างต้นใช้เฉพาะเส้นทาง Serverless
- [ ] Provisioned ตรวจ trust ของ `redshift.amazonaws.com`; Serverless ตรวจ `redshift.amazonaws.com` และ `redshift-serverless.amazonaws.com` ตามเอกสาร AWS
- [ ] Role มี S3 read/list ที่ต้องใช้กับ prefix ข้อมูลและ manifests; มี KMS decrypt หากใช้ SSE-KMS หากต้อง UNLOAD ให้ตรวจ S3 write และสิทธิ์ KMS ที่เกี่ยวข้องกับ encryption ของปลายทางด้วย
- [ ] เลือก subnet/security group ใน VPC เดียวกัน จำนวน AZ และ IP ต้องผ่านข้อกำหนดที่ Console/API แสดงสำหรับ configuration นั้น
- [ ] หาก list/read สำเร็จ ยังไม่ถือว่ามีสิทธิ์ create/COPY ครบ; ถ้า AccessDenied เก็บ action/error ให้ผู้ดูแล Lab ไม่เปลี่ยน trust policy แบบเดา

### Network, port, routing และ authentication จาก handoff

- [ ] ตั้ง Publicly accessible = false และตรวจ SG ไม่เปิด inbound กว้างเกินที่ตกลง
- [ ] รักษา inbound TCP 5439 จาก Glue SG ตาม handoff; เพิ่มผู้ทดสอบเฉพาะที่จำเป็นและระบุ source SG/CIDR ที่เจาะจง หากใช้ Query Editor ไม่จำเป็นต้องเพิ่ม IP เครื่องส่วนตัวเพียงเพื่อเปิด editor
- [ ] จด Redshift SG ID, Glue SG ID, private subnet A/B และ VPC ID; ตรวจว่ามาจาก VPC/region ที่ตั้งใจ
- [ ] ยืนยัน endpoint port จริงเป็น 5439 หลัง resource AVAILABLE; ถ้าเปลี่ยน port ต้องปรับ SG และ Glue connection ให้ตรงกัน
- [ ] ตัดสินใจ Enhanced VPC Routing = เปิด/ปิด พร้อมเหตุผล ก่อนสร้าง resource
- [ ] ถ้าเปิด ตรวจ S3 endpoint, associated route tables ของ subnets, endpoint/bucket policies, SG/NACL และ DNS ให้ตรงเส้นทางใช้งาน
- [ ] ทดสอบ COPY Parquet ของโปรเจกต์จริง ไม่ถือว่า UNLOAD สำเร็จแล้ว COPY Parquet จะผ่านด้วย เพราะ columnar COPY มีข้อกำหนด Spectrum/S3 เพิ่มเติม
- [ ] หากต้องพิสูจน์ว่า traffic ผ่าน endpoint ให้เก็บ configuration และหลักฐาน network/audit ที่เข้าถึงได้ด้วย; การ query สำเร็จอย่างเดียวไม่ยืนยัน route
- [ ] ตกลง authentication ของ Query Editor และ Glue/JDBC แยกกัน; หากใช้ Secrets Manager ตรวจ Lab อนุญาตและ client อ่าน secret ได้
- [ ] ไม่ใส่ password/access keys/session token ในไฟล์, notebook, Git, shell command ที่ถูกบันทึก หรือภาพหน้าจอ; ใช้ Console/secret reference ตามวิธีที่ Lab รองรับ

ตรวจ SG ที่รับส่งมอบ (อ่านอย่างเดียว):

```powershell
$RedshiftSgId = 'sg-REPLACE_REDSHIFT'
$GlueSgId = 'sg-REPLACE_GLUE'
aws ec2 describe-security-groups --group-ids $RedshiftSgId $GlueSgId --region $AwsRegion --output json
aws ec2 describe-vpc-endpoints --region $AwsRegion --output json
aws ec2 describe-route-tables --region $AwsRegion --output json
```

อ่าน `IpPermissions`: protocol TCP, FromPort/ToPort 5439 และ source group เป็น `$GlueSgId`; ตรวจ outbound/route ของ Glue สำหรับการเชื่อมต่อด้วย SG อย่างเดียวไม่พิสูจน์ connectivity

## 3. เตรียม parameters — ทำล่วงหน้าได้บางส่วน

รันใน PowerShell session เดียวกันกับคำสั่ง CLI ถัดไป:

```powershell
$AwsRegion = 'us-east-1'
$NamespaceName = 'thelook-ns'
$WorkgroupName = 'thelook-wg'
$DatabaseName = 'thelook'
$RoleArn = 'arn:aws:iam::REPLACE_ACCOUNT_ID:role/LabRole'
$PackageDir = 'D:\DSBA\31\cti\project\outputs\aws\REPLACE_BATCH_ID'
$EvidenceDir = 'D:\DSBA\31\cti\project\outputs\phase2-evidence\REPLACE_BATCH_ID'
```

| Parameter | ที่มา/เงื่อนไข |
|---|---|
| `$AwsRegion` | region จริงของ bucket; config CLI default ไม่ยืนยัน location ของ bucket |
| `$NamespaceName` | ชื่อ namespace ที่ทีมเลือก; เก็บ database/storage/role association |
| `$WorkgroupName` | ชื่อ workgroup ที่ใช้ compute/network |
| `$DatabaseName` | DB เดียวกันสำหรับติดตั้ง 00–03 และ run_batch |
| `$RoleArn` | ARN จริงของ LabRole และต้องตรง package |
| `$PackageDir` | โฟลเดอร์ที่มี package.json, run_batch.sql และ manifests |
| `$EvidenceDir` | ผลตรวจท้องถิ่น ไม่ใช่ที่เก็บ credentials |
| batch_id / observed_at / package_hash | ใช้ค่าจาก package เท่านั้น ไม่ตั้งใหม่ตอน retry |
| Base/Max RPU | ตกลงงบและค่าที่ Lab/region รองรับ; ไม่รับค่า default โดยไม่ตรวจ |

- [ ] นัดช่วงโหลดโดยมีผู้เขียน stg/dw เพียงคนเดียว
- [ ] ขอ test fixtures สำหรับ unchanged/changed/new user, boundary และ rollback ก่อนวัน deploy
- [ ] ตกลงว่าจะส่ง DB ให้ BI ใช้ต่อหรือเก็บหลักฐานแล้วลบเมื่อใด

## 4. รับ Phase 1 และตรวจ S3 — ต้องรอ Phase 1

- [ ] รับ commit SHA, validation_report.json, package.json, run_batch.sql, manifests ทั้ง 7 และหลักฐาน upload
- [ ] batch เดียวกันทุกไฟล์; validation เป็น PASS_WITH_KNOWN_ISSUES, checks PASS, quarantine 0
- [ ] รับ known issue baseline และจำนวนแถว/ยอดเงินของ batch นี้
- [ ] ยืนยัน prefix จะไม่ถูกเขียนทับหลังส่งมอบ

```powershell
$Package = Get-Content -LiteralPath (Join-Path $PackageDir 'package.json') -Raw | ConvertFrom-Json
$Package | Select-Object batch_id,observed_at,package_hash,dw_schema,curated_schema,rule_version,s3_root,iam_role
$Package.files | Select-Object table_name,rows,content_length,sha256,data_url,manifest_url
if ($Package.files.Count -ne 7) { throw 'Expected seven tables' }
if ($Package.iam_role -ne $RoleArn) { throw 'Role ARN differs from package' }
$S3Root = [Uri]$Package.s3_root
$BucketName = $S3Root.Host
aws s3api get-bucket-location --bucket $BucketName --region $AwsRegion --no-cli-pager
aws s3 ls $Package.s3_root --recursive --region $AwsRegion
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
```

`LocationConstraint=null` หมายถึง us-east-1 ต้องเทียบ region จริงกับ `$AwsRegion` ก่อนขั้น 5

หากไม่มีหลักฐานตรวจ checksum หลัง upload ใช้การอ่านกลับเพื่อตรวจทั้ง data และ manifests (มีการดาวน์โหลดและใช้พื้นที่):

```powershell
$VerifyDir = Join-Path $EvidenceDir 's3-readback'
New-Item -ItemType Directory -Force -Path $VerifyDir | Out-Null
foreach ($Entry in $Package.files) {
    $DataPath = Join-Path $VerifyDir ($Entry.table_name + '.parquet')
    aws s3 cp $Entry.data_url $DataPath --region $AwsRegion --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw "Download failed: $($Entry.table_name)" }
    if ((Get-Item -LiteralPath $DataPath).Length -ne $Entry.content_length) { throw 'Data size mismatch' }
    if ((Get-FileHash -LiteralPath $DataPath -Algorithm SHA256).Hash -ne $Entry.sha256) { throw 'Data SHA256 mismatch' }
    $ManifestPath = Join-Path $VerifyDir ($Entry.table_name + '.json')
    aws s3 cp $Entry.manifest_url $ManifestPath --region $AwsRegion --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw 'Manifest download failed' }
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
    if ($Manifest.entries.Count -ne 1) { throw 'Expected one object per generated manifest' }
    $Object = $Manifest.entries[0]
    if ($Object.url -ne $Entry.data_url -or $Object.mandatory -ne $true -or $Object.meta.content_length -ne $Entry.content_length) { throw 'Manifest differs from package' }
}
```

เกณฑ์ผ่าน: 7 data objects ตรง size/SHA256 และ 7 manifests ตรง package ไม่ใช้ ETag แทน SHA256 การตรวจนี้ยืนยัน upload เทียบ package; ต้องมี validation report ที่เชื่อถือได้ประกอบ

## 5. สร้าง Serverless — ใช้เฉพาะเมื่อเลือก Serverless; แนะนำหลังรับงานผ่าน

ใช้ Console: Amazon Redshift → Serverless → สร้าง/ตั้งค่า workgroup และ namespace (ชื่อเมนูอาจเปลี่ยนตาม UI)

- [ ] Region = `$AwsRegion`
- [ ] Namespace = `$NamespaceName`; Database = `$DatabaseName`
- [ ] Associated IAM roles = `$RoleArn`; ตั้ง default role ตามทีม
- [ ] Workgroup = `$WorkgroupName`; เชื่อม namespace ข้างต้น
- [ ] เลือก VPC/subnets/security group จากขั้น 2; ใช้ private access สำหรับแนวทาง Query Editor นี้ ไม่เปิด public เพียงเพื่อแก้ปัญหาสิทธิ์
- [ ] เลือก authentication ที่ Lab รองรับ; หากใช้ admin password ให้กรอกใน Console ไม่วางใน shell history
- [ ] ตั้ง Base capacity และ Maximum capacity ตามงบ/ข้อจำกัด; RPU ต่ำสุดอาจไม่ใช่ต้นทุนรวมต่ำสุดหาก query ช้าลง
- [ ] ตรวจ network route/policy ให้ COPY เข้าถึง S3 โดยเฉพาะหากเปิด enhanced VPC routing
- [ ] รอ namespace/workgroup AVAILABLE
- [ ] ตรวจ workgroup endpoint port = 5439 และทดสอบ role association จริงตาม handoff

ตรวจค่าหลังสร้าง:

```powershell
aws redshift-serverless get-namespace --namespace-name $NamespaceName --region $AwsRegion --query 'namespace.{Status:status,DB:dbName,Roles:iamRoles,DefaultRole:defaultIamRoleArn}' --output json
aws redshift-serverless get-workgroup --workgroup-name $WorkgroupName --region $AwsRegion --query 'workgroup.{Status:status,Namespace:namespaceName,Base:baseCapacity,Max:maxCapacity,Public:publiclyAccessible,Subnets:subnetIds,SecurityGroups:securityGroupIds}' --output json
aws redshift-serverless get-workgroup --workgroup-name $WorkgroupName --region $AwsRegion --query 'workgroup.{Endpoint:endpoint,EnhancedVpcRouting:enhancedVpcRouting}' --output json
```

ตั้ง usage limit หาก Lab อนุญาต ตัวอย่าง 16 RPU-hours/วันเป็นเพียงค่าตัวอย่าง ต้องเลือกตามงบจริง; ไม่ใช่ 16 ดอลลาร์ และไม่ครอบคลุม storage/S3:

```powershell
$DailyRpuHours = 16
$WorkgroupArn = aws redshift-serverless get-workgroup --workgroup-name $WorkgroupName --region $AwsRegion --query 'workgroup.workgroupArn' --output text
if ($LASTEXITCODE -ne 0) { throw 'Cannot read workgroup ARN' }
aws redshift-serverless create-usage-limit --resource-arn $WorkgroupArn --usage-type serverless-compute --amount $DailyRpuHours --period daily --breach-action deactivate --region $AwsRegion
```

`deactivate` หยุดการใช้งานเมื่อถึงขีดจำกัดและอาจกระทบงานที่กำลังทดสอบ ไม่ใช่การรับประกันเพดานค่าใช้จ่ายทั้งหมด ตรวจ limits เดิมใน Console ก่อนสร้างซ้ำ

## 5P. เส้นทาง provisioned — ทำแทนขั้น 5 หากทีมเลือก cluster

- [ ] เตรียม `$ClusterIdentifier`, `$ClusterSubnetGroup`, `$PrivateSubnetA`, `$PrivateSubnetB`, `$RedshiftSgId`; ใช้ ID จริงจาก handoff
- [ ] ตรวจ A/B เป็น private subnets ใน VPC เดียวกันและ AZ coverage ตรง configuration ที่เลือก รวมเงื่อนไข relocation/Multi-AZ หากเปิดใช้

```powershell
$ClusterIdentifier = 'thelook-cluster'
$ClusterSubnetGroup = 'thelook-private-subnets'
$PrivateSubnetA = 'subnet-REPLACE_A'
$PrivateSubnetB = 'subnet-REPLACE_B'
aws ec2 describe-subnets --subnet-ids $PrivateSubnetA $PrivateSubnetB --region $AwsRegion --output json
aws redshift describe-cluster-subnet-groups --region $AwsRegion --output json
```

ถ้ายังไม่มี subnet group และมีสิทธิ์สร้าง รันคำสั่งนี้ (สร้าง resource):

```powershell
aws redshift create-cluster-subnet-group --cluster-subnet-group-name $ClusterSubnetGroup --description 'TheLook private subnets A and B' --subnet-ids $PrivateSubnetA $PrivateSubnetB --region $AwsRegion
```

- [ ] Console → Provisioned clusters → Create cluster: เลือก node type/count ที่ Lab อนุญาตและประเมินราคาแล้ว
- [ ] กำหนด Cluster identifier = `$ClusterIdentifier`, Database = `$DatabaseName`, Port = 5439
- [ ] Network = VPC ของ subnets; subnet group = `$ClusterSubnetGroup`; SG = `$RedshiftSgId`; Public access = false
- [ ] ตั้ง Enhanced VPC Routing ตามข้อสรุปขั้น 2 และผูก `$RoleArn` เป็น IAM role ของ cluster
- [ ] ตั้ง authentication/secret ตามที่ตกลง; รอ cluster available แล้วตรวจค่าจริง:

```powershell
aws redshift describe-clusters --cluster-identifier $ClusterIdentifier --region $AwsRegion --query 'Clusters[0].{Status:ClusterStatus,DB:DBName,Endpoint:Endpoint,Public:PubliclyAccessible,SubnetGroup:ClusterSubnetGroupName,SGs:VpcSecurityGroups,Roles:IamRoles,EnhancedVpcRouting:EnhancedVpcRouting,NodeType:NodeType,Nodes:NumberOfNodes}' --output json
```

เกณฑ์ผ่าน: endpoint port=5439, public=false, SG/subnet group ถูกชุด, role association สำเร็จ จากนั้นทำขั้น 6–10 โดยเลือก cluster แทน workgroup ไม่รันคำสั่ง redshift-serverless กับ cluster

## 6. เชื่อมต่อและติดตั้ง SQL

- [ ] เปิด Query Editor v2 เลือก workgroup หรือ provisioned cluster ตามที่สร้าง และ database ตามขั้น 3 พร้อมวิธี authentication ที่ Lab อนุญาต
- [ ] ทดสอบ:

```sql
SELECT current_database(), current_user;
SET timezone TO 'UTC';
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname IN ('etl','stg','dw')
ORDER BY schemaname, tablename;
```

- [ ] ถ้า objects มีอยู่ก่อน ให้ตรวจ installation/schema เดิม ไม่ DROP เพื่อเริ่มใหม่อัตโนมัติ
- [ ] รันแต่ละไฟล์ตามลำดับและเก็บผลสำเร็จ/query ID:

| ลำดับ | ไฟล์จาก project root | ผลที่ต้องได้ |
|---|---|---|
| 1 | code/sql/00_control.sql | etl: batch_ledger, batch_attempts, batch_inputs, batch_checks |
| 2 | code/sql/01_staging.sql | stg ครบ 7 ตาราง |
| 3 | code/sql/02_warehouse.sql | dw: dim_date, dim_users, dim_products, dim_distribution_centers, fact_sales |
| 4 | code/sql/03_load_batch.sql | etl.load_batch ติดตั้งสำเร็จ |

รัน CREATE PROCEDURE ทั้ง definition รวม `$$` อย่าตัดตาม semicolon ภายใน body; `load_body.sql.inc` ไม่ใช่ไฟล์ที่รันแยก

00–03 เป็น objects ถาวรจึงติดตั้งคนละ session ได้ แต่ต้อง database เดียวกัน ส่วนขั้น 7 ต้องรักษา session ของ TEMP tables

## 7. โหลด batch แรก — รอ Phase 1 และขั้น 6

- [ ] เปิด `run_batch.sql` จาก `$PackageDir` ตรวจ CALL และ S3 URLs ตรง package
- [ ] ใช้ editor tab/session เดียวสำหรับ TEMP tables, INSERT controls และ CALL ทั้งหมด
- [ ] ใช้ autocommit และไม่ใส่ BEGIN ครอบ CALL; อย่าใช้วิธีส่งชุดคำสั่งที่บังคับรวมทุก statement เป็น transaction เดียว
- [ ] ถ้าแบ่งรัน ให้ทำตามลำดับใน tab เดิม; อย่าเปลี่ยน connection/database ระหว่างทาง
- [ ] รันไฟล์ที่ generate มา ไม่คัดลอกเฉพาะ CALL ด้านล่างไปใช้โดยไม่มี TEMP tables

รูปแบบเพื่ออธิบาย parameters เท่านั้น:

```sql
CALL etl.load_batch(
    'BATCH_ID_FROM_PACKAGE',
    'PACKAGE_HASH_FROM_PACKAGE',
    'OBSERVED_AT_FROM_PACKAGE'::TIMESTAMPTZ,
    'ROLE_ARN_FROM_PACKAGE',
    'dw-v1',
    'provisional-v1'
);
```

| Parameter | ความหมาย |
|---|---|
| p_batch_id | identity ของ input batch |
| p_package_hash | hash ของ package/config ที่ generator คำนวณ |
| p_observed_at | เวลา observation คงเดิมเมื่อ retry; batch ใหม่ต้องมากกว่า batch ที่ publish ล่าสุด |
| p_iam_role | role ที่ผูก namespace และอ่าน S3 ได้ |
| p_schema_version | DW schema version ไม่ใช่ curated schema version |
| p_rule_version | cleaning/business rule version ที่ procedure รองรับ |

ก่อน CALL หากแบ่งรัน ตรวจ controls ได้ด้วย `SELECT COUNT(*) FROM expected_inputs;` ต้อง 7 และ `SELECT COUNT(*) FROM expected_money;` ต้อง 5

เกณฑ์ผ่าน: CALL สำเร็จและ ledger ของ batch นี้เป็น SUCCEEDED หาก connection ขาด ให้ตรวจ ledger/query history ก่อน retry ด้วยไฟล์เดิม

### ทดสอบ UNLOAD หากอยู่ในขอบเขต handoff

- [ ] รับ S3 prefix สำหรับ test output ที่แยกจาก immutable input batch และตรวจสิทธิ์ write ของ role
- [ ] แทน bucket/prefix/ARN จริงและใช้ prefix ใหม่ต่อรอบ (คำสั่งนี้เขียน object ใน S3):

```sql
UNLOAD ('SELECT 1 AS connection_probe')
TO 's3://REPLACE_BUCKET/phase2-network-probe/REPLACE_UNIQUE_RUN_ID/probe_'
IAM_ROLE 'arn:aws:iam::REPLACE_ACCOUNT_ID:role/LabRole'
FORMAT AS PARQUET;
```

- [ ] ตรวจ output ด้วย `aws s3 ls` ที่ prefix นี้ และบันทึก query ID/role/routing configuration
- [ ] ถ้าใช้ Glue จริง ให้ทดสอบ connection/job จาก Glue SG ไป endpoint:5439 ด้วย secret/auth ที่ตกลง; Query Editor ผ่านไม่พิสูจน์ Glue connectivity
- [ ] หากไม่ใช้ UNLOAD/Glue ในรอบนี้ ให้ระบุ DEFERRED พร้อมผู้รับผิดชอบ ไม่ติ๊กว่าทดสอบผ่าน

## 8. ตรวจรับหลังโหลด

- [ ] รัน `code/sql/04_post_load_checks.sql` และ export CSV/JSON ของผลรวม
- [ ] ใช้ batch เฉพาะที่รับมา ไม่อาศัย latest batch หากมีทีมอื่นใช้งาน

```sql
-- แทน REPLACE_BATCH_ID ทุกจุดด้วยค่าจริง
SELECT * FROM etl.batch_ledger WHERE batch_id='REPLACE_BATCH_ID';
SELECT * FROM etl.batch_inputs WHERE batch_id='REPLACE_BATCH_ID' ORDER BY table_name;
SELECT * FROM etl.batch_checks WHERE batch_id='REPLACE_BATCH_ID' ORDER BY check_name;
SELECT * FROM etl.batch_attempts WHERE batch_id='REPLACE_BATCH_ID' ORDER BY attempted_at;

SELECT 'distribution_centers' AS table_name,COUNT(*) AS rows FROM stg.distribution_centers
UNION ALL SELECT 'products',COUNT(*) FROM stg.products
UNION ALL SELECT 'users',COUNT(*) FROM stg.users
UNION ALL SELECT 'orders',COUNT(*) FROM stg.orders
UNION ALL SELECT 'order_items',COUNT(*) FROM stg.order_items
UNION ALL SELECT 'inventory_items',COUNT(*) FROM stg.inventory_items
UNION ALL SELECT 'events',COUNT(*) FROM stg.events;

SELECT COUNT(*) AS fact_rows,COUNT(DISTINCT order_item_id) AS unique_items,
       SUM(sale_price) AS sale_price,SUM(product_cost) AS cost,
       SUM(reference_retail_price) AS reference_price
FROM dw.fact_sales;

SELECT COUNT(*) AS expected_fact_rows,SUM(i.sale_price) AS sale_price,
       SUM(inv.cost) AS cost,SUM(inv.product_retail_price) AS reference_price
FROM stg.order_items i JOIN stg.inventory_items inv ON inv.id=i.inventory_item_id;

-- ต้องไม่คืนแถว
SELECT user_id FROM dw.dim_users GROUP BY user_id
HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END)<>1;

SELECT a.user_id,a.user_key,b.user_key
FROM dw.dim_users a JOIN dw.dim_users b ON a.user_id=b.user_id AND a.user_key<b.user_key
WHERE (a.valid_from IS NULL OR b.valid_to IS NULL OR a.valid_from<b.valid_to)
  AND (b.valid_from IS NULL OR a.valid_to IS NULL OR b.valid_from<a.valid_to);

SELECT i.id,COUNT(u.user_key) AS matches
FROM stg.order_items i JOIN stg.orders o ON o.order_id=i.order_id
LEFT JOIN dw.dim_users u ON u.user_id=i.user_id
 AND (u.valid_from IS NULL OR o.created_at>=u.valid_from)
 AND (u.valid_to IS NULL OR o.created_at<u.valid_to)
GROUP BY i.id HAVING COUNT(u.user_key)<>1;
```

- [ ] Staging counts ตรง package ทั้ง 7 ตาราง
- [ ] fact_rows = unique_items = order_items ของ batch นี้; 181,759 ใช้ได้เฉพาะ baseline ที่มีจำนวนนี้จริง
- [ ] ยอด sale_price/cost/reference_price ตรงกันแบบ decimal
- [ ] ตรวจ FK, nullable dates และ flags ตาม checks ใน loader; ไม่มี WARN ใหม่ที่ยังไม่อธิบาย
- [ ] Known issues ตรงรายงาน ไม่ได้หมายความว่าต้นทางถูกต้องแล้ว

ข้อควรระวังใน SQL 04 ปัจจุบัน: `mismatched_products` ใช้ COUNT(*) ของ join ทั้งหมด จึงไม่ใช่จำนวน product ที่ต่าง ให้ใช้ query เพิ่มนี้เพื่อรายงานอย่างถูกต้อง:

```sql
SELECT COUNT(*) AS compared_inventory_rows,
       SUM(CASE WHEN p.distribution_center_id<>i.product_distribution_center_id THEN 1 ELSE 0 END) AS mismatched_inventory_rows,
       COUNT(DISTINCT CASE WHEN p.distribution_center_id<>i.product_distribution_center_id THEN p.id END) AS mismatched_product_count
FROM stg.products p JOIN stg.inventory_items i ON i.product_id=p.id;
```

ยอดเงินรวมทุกสถานะไม่ใช่ net sales/realized profit; รายงานตามเมือง/อายุย้อนหลังใช้ snapshot attributes ตามข้อจำกัด SCD

## 9. ทดสอบ NO_OP และ identity rejection

- [ ] ก่อน rerun สร้าง baseline ใน session เดียวกับที่จะตรวจหลัง rerun (ใช้พื้นที่ชั่วคราว)

```sql
CREATE TEMP TABLE phase2_fact_before AS SELECT * FROM dw.fact_sales;
CREATE TEMP TABLE phase2_users_before AS SELECT * FROM dw.dim_users;
CREATE TEMP TABLE phase2_products_before AS SELECT * FROM dw.dim_products;
CREATE TEMP TABLE phase2_dc_before AS SELECT * FROM dw.dim_distribution_centers;
CREATE TEMP TABLE phase2_date_before AS SELECT * FROM dw.dim_date;
```

- [ ] รัน run_batch.sql เดิมอีกครั้งโดยไม่เปลี่ยนค่าใด
- [ ] batch_attempts มี NO_OP; batch_ledger มี batch นี้หนึ่งแถว
- [ ] เปรียบเทียบก่อน/หลังทั้งสองทิศทาง พร้อม COUNT(*) และ duplicate checks (EXCEPT ใช้ set semantics)

```sql
SELECT * FROM dw.fact_sales EXCEPT SELECT * FROM phase2_fact_before;
SELECT * FROM phase2_fact_before EXCEPT SELECT * FROM dw.fact_sales;
SELECT * FROM dw.dim_users EXCEPT SELECT * FROM phase2_users_before;
SELECT * FROM phase2_users_before EXCEPT SELECT * FROM dw.dim_users;
```

ทำแบบเดียวกันกับ dim_products/phase2_products_before, dim_distribution_centers/phase2_dc_before และ dim_date/phase2_date_before: ต้องไม่มีแถวต่างและ counts เท่าเดิม

- [ ] ใน DB ทดสอบ คัดลอก CALL เดิม เปลี่ยนเฉพาะ hash เป็น string 64 ตัวที่ต่างจากของจริง โดยคง batch ID เดิม ต้อง reject
- [ ] ทดสอบเวลาเปลี่ยนโดยคง ID/hash เดิม ต้อง reject เช่นกัน
- [ ] ตรวจข้อมูลยังเท่าเดิม; ไม่แก้ package ต้นฉบับหรือ S3 objects เพื่อทดสอบ

## 10. Integration tests — เตรียมได้ก่อน แต่ต้องมี fixture จริงจึงรันได้

ใช้ database แยก เช่น `thelook_test` ซึ่งผู้ใช้มีสิทธิ์สร้าง แล้วติดตั้ง SQL 00–03 ใน DB นั้นด้วย revision เดียวกับของจริง ไม่ทดสอบ destructive/error cases บน DB ที่ส่งให้ BI

```sql
-- รันเฉพาะเมื่อยังไม่มี DB นี้และได้รับสิทธิ์สร้าง
CREATE DATABASE thelook_test;
```

เปลี่ยน connection เป็น thelook_test และยืนยัน `SELECT current_database();` ก่อนทดสอบ

Fixture ต้องมี Parquet ครบ 7 ตารางที่ schema/FK/ยอดเงินถูกต้อง, controls/manifest ตรงกับ fixture, batch ID แยก และเวลาตามลำดับ ชุด synthetic อาจไม่ผ่าน production DQ baseline จึงต้องมีผู้พัฒนาเตรียม test harness แยก ห้ามลดการตรวจรับ production เพื่อให้ fixture ผ่าน

| Test | Input/parameters ที่ต้องเตรียม | เกณฑ์ผ่าน |
|---|---|---|
| Bootstrap | batch A, T0; warehouse ว่าง | 1 version/user, BOOTSTRAP_SNAPSHOT, open-start |
| Unchanged | batch B, T1>T0, attributes เดิม | user_key และ versions เดิม |
| Changed | batch C, T2>T1; เปลี่ยน attribute หนึ่ง user | รุ่นเก่า valid_to=T2; รุ่นใหม่ valid_from=T2; current หนึ่ง |
| NULL transition | nullable attribute NULL→ค่า และค่า→NULL | ตรวจพบ change ทั้งสองทิศทาง |
| Boundary | orders ของ user ที่เปลี่ยน ณ T2−1 microsecond, T2 และ T2+1 microsecond | ก่อน T2 ใช้รุ่นเก่า; ตั้งแต่ T2 ใช้รุ่นใหม่ |
| New historical user | user ใหม่พร้อม orders ก่อน observed_at และ FK ครบ | โค้ดปัจจุบันใช้ OBSERVED_NEW, valid_from=NULL, match หนึ่งครั้ง |
| Rollback | batch ใหม่ valid; ใน test harness ทำให้ check หลัง dimension update ล้ม เช่นขาด user as-of version แต่ source FK ยังครบ | stg/dw กลับเท่าก่อน CALL, ไม่มี success ledger ใหม่, ตรวจ FAILED log |
| Concurrency | สอง sessions เตรียม TEMP inputs ของตนเอง เรียก batch เดียวพร้อมกัน | ไม่สำเร็จซ้ำ; session หลัง NO_OP หรือเกิด conflict ที่ retry แล้ว NO_OP |
| Cancellation | ยกเลิก CALL ทดสอบขณะทำงาน | ตรวจ query history/transaction สิ้นสุด; ไม่มีข้อมูล publish ครึ่งทาง |

Rollback ต้องเทียบ contents/counts ของ stg ทั้ง 7, dw ทั้ง 5 และ success ledger ก่อน–หลัง ไม่ใช้แค่ row count หรือยอดเงิน; identity sequence อาจมีช่องว่างหลัง rollback ไม่ถือว่า rows เสีย

วิธีสร้างกรณี rollback ข้างต้น: ใน DB ทดสอบปรับ valid_from ของ user version ที่รู้จักให้ช้ากว่า order, คง current/valid_to ให้ valid; จับ baseline หลังจัด fixture แล้วใช้ batch ใหม่ที่เปลี่ยน user อีกคนเพื่อให้มี dimension mutation ก่อน as-of check ล้ม บันทึกการตั้ง fixture และเปรียบเทียบกับ baseline นี้ ไม่แก้ SQL production

Cancellation อาจไม่สร้าง FAILED attempt ให้ใช้ query history ประกอบ หากไม่มี fixture/ผลทดสอบจริง ให้ระบุ NOT TESTED และห้ามรายงานว่า Phase 2 integration tests ผ่านครบ

## 11. ส่งมอบและ cleanup

เส้นทาง provisioned: ตรวจ configuration รองรับ pause/resume หากจะพัก; หากลบให้ตกลง final snapshot/การกู้คืนก่อน ใช้หน้า cluster ของทรัพยากรนั้น ไม่ใช้ขั้นลบ workgroup/namespace ด้านล่าง ตรวจด้วย `aws redshift describe-clusters --region $AwsRegion` และ `aws redshift describe-cluster-snapshots --region $AwsRegion` หลังดำเนินการ ส่วนรายการ workgroup/namespace ต่อไปนี้ใช้เฉพาะ Serverless

- [ ] Export ledger/checks/counts/money/SCD results และ query IDs ลง EvidenceDir
- [ ] บันทึก Git commit, batch/hash/observed_at, region, workgroup/namespace/database และ test results PASS/FAIL/NOT TESTED
- [ ] ส่งข้อมูลเชื่อมต่อให้ BI ตามช่องทางทีม โดยไม่ส่ง credentials ใน Git
- [ ] นัดยืนยันว่าไม่มีผู้ใช้ DB ต่อก่อนลบ; ถ้าจะเก็บ snapshot ให้บันทึกชื่อและเจ้าของค่าใช้จ่าย
- [ ] ปิด scheduled queries/งานต่อเนื่องที่ทีมไม่ใช้ ตรวจไม่มี query หรือ transaction ค้าง
- [ ] ถ้าเลือกเก็บ DB ให้ติดตาม usage/storage ต่อ; Serverless ไม่มีขั้นตอน manual pause แบบ provisioned ที่ใช้แทน cleanup ทั้งหมดได้
- [ ] ถ้าเลือกยุติ environment: Console → ลบ workgroup ที่ระบุ ตรวจว่าลบเสร็จ → พิจารณาลบ namespace ตามแผนเก็บข้อมูล และตัดสินใจ final snapshot อย่างชัดเจน
- [ ] ตรวจ snapshots, S3, logs และ resources ที่ยังคงอยู่; ไม่ลบ bucket ที่ทีมอื่นยังใช้

ตรวจ resource หลัง cleanup (เป็นคำสั่งอ่าน ไม่ใช่คำสั่งลบ):

```powershell
aws redshift-serverless list-workgroups --region $AwsRegion --no-cli-pager
aws redshift-serverless list-namespaces --region $AwsRegion --no-cli-pager
aws redshift-serverless list-snapshots --region $AwsRegion --no-cli-pager
```

### แบบบันทึกปิดงาน

| รายการ | ค่าจริง/หลักฐาน |
|---|---|
| ผู้ดำเนินการ / วันเวลา | |
| Git commit / Batch ID / Package hash | |
| Account / Region / Workgroup / Namespace / Database | |
| Install / COPY / Reconciliation | |
| NO_OP / Identity rejection | |
| SCD / Rollback / Concurrency / Cancellation | |
| Known issues / WARN / NOT TESTED | |
| ตำแหน่งหลักฐานและผู้รับมอบ | |
| Resources ที่เก็บ/ลบ และวันสิ้นสุดการใช้งาน | |

## เอกสารอ้างอิง

- [AWS: เปรียบเทียบ provisioned และ Serverless](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-console-comparison.html)
- [AWS: ราคา — ตรวจ region/configuration ณ วัน deploy](https://aws.amazon.com/redshift/pricing/)
- [AWS: Cluster subnet groups และ VPC](https://docs.aws.amazon.com/redshift/latest/mgmt/managing-clusters-vpc.html)
- [AWS: Enhanced VPC Routing และข้อจำกัด](https://docs.aws.amazon.com/redshift/latest/mgmt/enhanced-vpc-routing.html)
- [AWS: Pause/resume provisioned cluster](https://docs.aws.amazon.com/redshift/latest/mgmt/rs-mgmt-pause-resume-cluster.html)

- [คู่มือ SQL ของโปรเจกต์](../code/sql/README.md)
- [AWS: Serverless role association และ trust](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-security-other-services.html)
- [AWS: Query Editor sessions](https://docs.aws.amazon.com/redshift/latest/mgmt/query-editor-v2-query-run.html)
- [AWS: COPY Parquet — same region, column order และข้อจำกัด](https://docs.aws.amazon.com/redshift/latest/dg/copy-usage_notes-copy-from-columnar.html)
- [AWS: Create namespace parameters](https://docs.aws.amazon.com/cli/latest/reference/redshift-serverless/create-namespace.html)
- [AWS: Create workgroup parameters](https://docs.aws.amazon.com/cli/latest/reference/redshift-serverless/create-workgroup.html)
- [AWS: Capacity](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-capacity.html)
- [AWS: Usage limits และ breach actions](https://docs.aws.amazon.com/cli/latest/reference/redshift-serverless/create-usage-limit.html)
- [AWS: Billing แยก compute/storage/snapshots](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-billing.html)
- [AWS: Delete workgroup และ namespace ที่เหลืออยู่](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless_delete-workgroup.html)
