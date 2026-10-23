# AWS Glue à¹ƒà¸™ Learner Lab â€” à¸„à¸¹à¹ˆà¸¡à¸·à¸­à¸•à¸±à¹‰à¸‡à¸„à¹ˆà¸²à¹à¸¥à¸°à¸•à¸£à¸§à¸ˆà¸£à¸±à¸š

à¸ˆà¸±à¸”à¸—à¸³ 2026-10-23 à¸ªà¸³à¸«à¸£à¸±à¸š TheLook | region us-east-1 | à¸„à¸¹à¹ˆà¸¡à¸·à¸­à¸™à¸µà¹‰à¸¢à¸±à¸‡à¹„à¸¡à¹ˆà¹ƒà¸Šà¹ˆà¸œà¸¥ deploy/test à¸šà¸™ AWS

## 1. Glue à¸—à¸³à¸­à¸°à¹„à¸£ à¹à¸¥à¸° Learner Lab à¹ƒà¸Šà¹‰à¹„à¸”à¹‰à¹„à¸«à¸¡

Glue à¹€à¸›à¹‡à¸™à¸šà¸£à¸´à¸à¸²à¸£à¸ˆà¸±à¸”à¸à¸²à¸£à¸‡à¸²à¸™à¸‚à¹‰à¸­à¸¡à¸¹à¸¥ à¸¡à¸µà¸«à¸¥à¸²à¸¢à¸ªà¹ˆà¸§à¸™à¸—à¸µà¹ˆà¹à¸¢à¸à¸«à¸™à¹‰à¸²à¸—à¸µà¹ˆà¸à¸±à¸™:

| à¸ªà¹ˆà¸§à¸™ | à¸«à¸™à¹‰à¸²à¸—à¸µà¹ˆ | à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¸—à¸³à¸­à¸°à¹„à¸£à¹ƒà¸«à¹‰à¹‚à¸”à¸¢à¸­à¸±à¸•à¹‚à¸™à¸¡à¸±à¸•à¸´ |
|---|---|---|
| Data Catalog database/table | à¹€à¸à¹‡à¸š metadata à¹€à¸Šà¹ˆà¸™ schema à¹à¸¥à¸° S3 location | à¹„à¸¡à¹ˆà¸„à¸±à¸”à¸¥à¸­à¸à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¹€à¸‚à¹‰à¸² Redshift |
| Crawler | à¸­à¹ˆà¸²à¸™à¹à¸«à¸¥à¹ˆà¸‡à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¹€à¸žà¸·à¹ˆà¸­à¸­à¸™à¸¸à¸¡à¸²à¸™ schema/partitions à¹à¸¥à¹‰à¸§à¸¥à¸‡ Catalog | à¹„à¸¡à¹ˆà¸¢à¸·à¸™à¸¢à¸±à¸™ business rules, DQ à¸«à¸£à¸·à¸­à¸ªà¸£à¹‰à¸²à¸‡ warehouse à¸•à¸²à¸¡à¹à¸šà¸šà¹‚à¸„à¸£à¸‡à¸à¸²à¸£ |
| Connection | à¹€à¸à¹‡à¸šà¸à¸²à¸£à¹€à¸Šà¸·à¹ˆà¸­à¸¡à¸•à¹ˆà¸­à¹à¸¥à¸° network/auth configuration | à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¹‚à¸«à¸¥à¸”à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸ˆà¸™à¸à¸§à¹ˆà¸²à¸ˆà¸°à¸¡à¸µ job à¹ƒà¸Šà¹‰à¸‡à¸²à¸™ |
| Job | à¸£à¸±à¸™ Python/Spark à¹€à¸žà¸·à¹ˆà¸­à¹à¸›à¸¥à¸‡à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸«à¸£à¸·à¸­à¸ªà¸±à¹ˆà¸‡ workflow | à¸•à¹‰à¸­à¸‡à¹€à¸‚à¸µà¸¢à¸™ logic, error handling à¹à¸¥à¸° validation |
| Trigger/workflow | à¸ªà¸±à¹ˆà¸‡à¹à¸¥à¸°à¸ˆà¸±à¸”à¸¥à¸³à¸”à¸±à¸š jobs/crawlers | à¹„à¸¡à¹ˆà¹ƒà¸Šà¹ˆà¸«à¸¥à¸±à¸à¸à¸²à¸™à¸§à¹ˆà¸²à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸–à¸¹à¸à¸•à¹‰à¸­à¸‡à¹€à¸¡à¸·à¹ˆà¸­ job à¸ªà¸³à¹€à¸£à¹‡à¸ˆ |

**à¹ƒà¸Šà¹‰à¹„à¸”à¹‰à¹€à¸¡à¸·à¹ˆà¸­ Lab à¸‚à¸­à¸‡à¸Šà¸±à¹‰à¸™à¹€à¸£à¸µà¸¢à¸™à¸­à¸™à¸¸à¸à¸²à¸•à¸šà¸£à¸´à¸à¸²à¸£/action/runtime à¸—à¸µà¹ˆà¸•à¹‰à¸­à¸‡à¹ƒà¸Šà¹‰ à¹à¸¥à¸° role/network à¸žà¸£à¹‰à¸­à¸¡** à¸¢à¸±à¸‡à¸¢à¸·à¸™à¸¢à¸±à¸™à¸šà¸±à¸à¸Šà¸µà¸™à¸µà¹‰à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¸ˆà¸²à¸à¹€à¸­à¸à¸ªà¸²à¸£à¸­à¸¢à¹ˆà¸²à¸‡à¹€à¸”à¸µà¸¢à¸§ à¹ƒà¸«à¹‰à¹€à¸›à¸´à¸” Learner Lab â†’ README/Services and restrictions â†’ AWS Glue à¹à¸¥à¸°à¸•à¸£à¸§à¸ˆà¸ªà¸´à¸—à¸˜à¸´à¹Œà¸ˆà¸£à¸´à¸‡ à¸£à¸²à¸¢à¸à¸²à¸£à¸šà¸£à¸´à¸à¸²à¸£à¹à¸¥à¸°à¸‡à¸šà¹€à¸›à¹‡à¸™à¸‚à¸­à¸‡ Lab à¸™à¸±à¹‰à¸™ à¹„à¸¡à¹ˆà¸„à¸§à¸£à¸–à¸·à¸­à¸§à¹ˆà¸² Glue à¸—à¸¸à¸à¸Ÿà¸µà¹€à¸ˆà¸­à¸£à¹Œà¹€à¸›à¸´à¸”à¹ƒà¸Šà¹‰à¹€à¸ªà¸¡à¸­ à¸«à¸£à¸·à¸­à¹ƒà¸Šà¹‰à¸Ÿà¸£à¸µà¹„à¸¡à¹ˆà¸«à¸±à¸à¹€à¸„à¸£à¸”à¸´à¸•

handoff1 à¸£à¸°à¸šà¸¸à¸§à¹ˆà¸²à¹€à¸•à¸£à¸µà¸¢à¸¡ Glue SG à¹à¸¥à¹‰à¸§à¹à¸¥à¸° trust à¸‚à¸­à¸‡ LabRole à¸¡à¸µ glue à¹à¸•à¹ˆà¸¢à¸±à¸‡à¹„à¸¡à¹ˆà¸¡à¸µ connection/job à¹à¸¥à¸°à¸¢à¸±à¸‡à¹„à¸¡à¹ˆà¸—à¸”à¸ªà¸­à¸šà¸ªà¸´à¸—à¸˜à¸´à¹Œà¸ˆà¸£à¸´à¸‡ à¸ˆà¸¶à¸‡à¹€à¸›à¹‡à¸™ â€œà¹€à¸•à¸£à¸µà¸¢à¸¡à¸šà¸²à¸‡à¸ªà¹ˆà¸§à¸™â€ à¹„à¸¡à¹ˆà¹ƒà¸Šà¹ˆ â€œGlue à¸žà¸£à¹‰à¸­à¸¡à¹ƒà¸Šà¹‰à¸‡à¸²à¸™à¹à¸¥à¹‰à¸§â€

## 2. à¹€à¸¥à¸·à¸­à¸à¸šà¸—à¸šà¸²à¸— Glue à¸à¹ˆà¸­à¸™à¸ªà¸£à¹‰à¸²à¸‡

à¹‚à¸„à¹‰à¸”à¸›à¸±à¸ˆà¸ˆà¸¸à¸šà¸±à¸™: local curated_pipeline.py â†’ Parquet/validation â†’ S3 â†’ etl.load_batch (COPY + SCD + checks + publish)

**à¹à¸™à¸§à¸—à¸²à¸‡à¸—à¸µà¹ˆà¹€à¸‚à¹‰à¸²à¸à¸±à¸šà¸£à¸°à¸šà¸šà¸›à¸±à¸ˆà¸ˆà¸¸à¸šà¸±à¸™:** à¹ƒà¸Šà¹‰ Glue Python shell job à¹€à¸›à¹‡à¸™à¸•à¸±à¸§à¸ªà¸±à¹ˆà¸‡à¹‚à¸«à¸¥à¸” `run_batch.sql` à¸œà¹ˆà¸²à¸™ database connection à¹€à¸”à¸µà¸¢à¸§ à¹‚à¸”à¸¢à¹ƒà¸Šà¹‰ procedure à¹€à¸”à¸´à¸¡ à¹„à¸¡à¹ˆà¹ƒà¸«à¹‰ Spark à¹€à¸‚à¸µà¸¢à¸™à¸¥à¸‡ dw.fact_sales à¸«à¸£à¸·à¸­ dim_users à¸•à¸£à¸‡ à¹† à¹€à¸žà¸£à¸²à¸°à¸ˆà¸°à¸‚à¹‰à¸²à¸¡ ledger/SCD/checks

| à¹à¸™à¸§à¸—à¸²à¸‡ | à¹ƒà¸Šà¹‰à¹€à¸¡à¸·à¹ˆà¸­ | à¸ªà¸´à¹ˆà¸‡à¸—à¸µà¹ˆà¸•à¹‰à¸­à¸‡à¹€à¸žà¸´à¹ˆà¸¡ |
|---|---|---|
| Query Editor à¸£à¸±à¸™ SQL à¹€à¸”à¸´à¸¡ | à¸•à¹‰à¸­à¸‡à¸à¸²à¸£à¹‚à¸«à¸¥à¸” DW à¸£à¸­à¸šà¹à¸£à¸à¹à¸¥à¸° Glue à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¸šà¸±à¸‡à¸„à¸±à¸š | à¹„à¸¡à¹ˆà¸•à¹‰à¸­à¸‡à¸£à¸­ crawler/job |
| Glue orchestration (à¸„à¸¹à¹ˆà¸¡à¸·à¸­à¸™à¸µà¹‰) | à¸•à¹‰à¸­à¸‡à¸à¸²à¸£à¹ƒà¸«à¹‰ Glue à¸ªà¸±à¹ˆà¸‡à¹‚à¸«à¸¥à¸” batch à¹€à¸”à¸´à¸¡ | Python shell, driver, secret, network, SQL script à¸—à¸µà¹ˆà¸­à¸™à¸¸à¸¡à¸±à¸•à¸´ |
| Glue Spark ETL | à¹‚à¸ˆà¸—à¸¢à¹Œà¸šà¸±à¸‡à¸„à¸±à¸š raw â†’ cleaning à¸šà¸™ Glue | à¸¢à¹‰à¸²à¸¢à¸à¸Ž cleaning, decimal/timezone, quarantine, DQ baseline, manifest/package à¹à¸¥à¸°à¸—à¸”à¸ªà¸­à¸šà¹ƒà¸«à¸¡à¹ˆ |

Glue orchestration à¹„à¸¡à¹ˆà¸„à¸§à¸£à¸–à¸¹à¸à¸™à¸³à¹€à¸ªà¸™à¸­à¸§à¹ˆà¸²à¹€à¸›à¹‡à¸™à¸à¸²à¸£à¸—à¸³ cleaning ETL à¸šà¸™ Glue à¸«à¸²à¸ rubric à¸•à¹‰à¸­à¸‡ Spark ETL à¸•à¹‰à¸­à¸‡à¸”à¸³à¹€à¸™à¸´à¸™à¸‡à¸²à¸™à¹à¸™à¸§à¸—à¸²à¸‡à¸—à¸µà¹ˆà¸ªà¸²à¸¡à¹€à¸žà¸´à¹ˆà¸¡à¹€à¸•à¸´à¸¡ `curated_pipeline.py` à¸›à¸±à¸ˆà¸ˆà¸¸à¸šà¸±à¸™à¹ƒà¸Šà¹‰ pandas/pyarrow, local filesystem à¹à¸¥à¸° environment Python 3.12 à¸ˆà¸¶à¸‡à¹„à¸¡à¹ˆà¸„à¸§à¸£ upload à¹à¸¥à¹‰à¸§à¸–à¸·à¸­à¸§à¹ˆà¸²à¸£à¸±à¸™à¹ƒà¸™ Glue Python 3.9 à¹„à¸”à¹‰à¸—à¸±à¸™à¸—à¸µ

## 3. à¸¥à¸³à¸”à¸±à¸šà¹à¸¥à¸°à¸‡à¸²à¸™à¸—à¸µà¹ˆà¹€à¸•à¸£à¸µà¸¢à¸¡à¸¥à¹ˆà¸§à¸‡à¸«à¸™à¹‰à¸²à¹„à¸”à¹‰

| à¸‚à¸±à¹‰à¸™ | à¸‡à¸²à¸™ | à¸à¹ˆà¸­à¸™à¸£à¸±à¸š S3/Redshift à¸—à¸³à¹„à¸”à¹‰à¹„à¸«à¸¡ |
|---|---|---|
| A | à¸•à¸à¸¥à¸‡ orchestration à¸«à¸£à¸·à¸­ Spark ETL à¹à¸¥à¸°à¸•à¸£à¸§à¸ˆà¸‚à¹‰à¸­à¸ˆà¸³à¸à¸±à¸” Lab | à¹„à¸”à¹‰ |
| B | à¸•à¸£à¸§à¸ˆ IAM, VPC, SG à¹à¸¥à¸° API endpoints | à¹„à¸”à¹‰; endpoint DB à¸£à¸­ Redshift |
| C | à¹€à¸•à¸£à¸µà¸¢à¸¡ parameters/scripts/dependencies/test plan | à¹„à¸”à¹‰ |
| D | à¸£à¸±à¸š S3 package à¹à¸¥à¸° Redshift endpoint/DB/procedure | à¸•à¹‰à¸­à¸‡à¸£à¸±à¸šà¸‡à¸²à¸™ |
| E | à¸ªà¸£à¹‰à¸²à¸‡ secret/connection à¹à¸¥à¸°à¸—à¸”à¸ªà¸­à¸š network | à¸•à¹‰à¸­à¸‡à¸¡à¸µ Redshift à¹à¸¥à¸°à¸§à¸´à¸˜à¸µ auth |
| F | Catalog/crawler (optional) | à¸•à¹‰à¸­à¸‡à¸¡à¸µ S3 data; à¹„à¸¡à¹ˆà¸•à¹‰à¸­à¸‡à¸£à¸­ Redshift |
| G | à¸ªà¸£à¹‰à¸²à¸‡ job à¸£à¸±à¸™ smoke test à¸à¹ˆà¸­à¸™à¹‚à¸«à¸¥à¸”à¸ˆà¸£à¸´à¸‡ | à¸•à¹‰à¸­à¸‡à¸žà¸£à¹‰à¸­à¸¡à¸—à¸±à¹‰à¸‡ S3/Redshift/network |
| H | à¹‚à¸«à¸¥à¸” à¸•à¸£à¸§à¸ˆà¸‚à¹‰à¸­à¸¡à¸¹à¸¥ NO_OP/failure à¹à¸¥à¹‰à¸§à¸ªà¹ˆà¸‡à¸¡à¸­à¸š | à¸«à¸¥à¸±à¸‡ smoke test à¸œà¹ˆà¸²à¸™ |

## A. à¸•à¸£à¸§à¸ˆ Learner Lab à¹à¸¥à¸°à¸à¸³à¸«à¸™à¸”à¹€à¸ˆà¹‰à¸²à¸‚à¸­à¸‡

- [ ] à¸­à¹ˆà¸²à¸™à¸šà¸£à¸´à¸à¸²à¸£à¸—à¸µà¹ˆà¸­à¸™à¸¸à¸à¸²à¸•: Glue job/connection/crawler/catalog, job type, workers/DPU, concurrency, region à¹à¸¥à¸° session/budget limit
- [ ] à¹€à¸¥à¸·à¸­à¸ role à¸—à¸µà¹ˆ Lab à¸­à¸™à¸¸à¸à¸²à¸• à¹€à¸Šà¹ˆà¸™ LabRole; à¸­à¸¢à¹ˆà¸²à¸ªà¸¡à¸¡à¸•à¸´à¸§à¹ˆà¸²à¸ªà¸£à¹‰à¸²à¸‡ role à¹ƒà¸«à¸¡à¹ˆà¹„à¸”à¹‰
- [ ] à¸•à¸£à¸§à¸ˆà¸ªà¸´à¸—à¸˜à¸´à¹Œà¸‚à¸­à¸‡à¸œà¸¹à¹‰à¸ªà¸£à¹‰à¸²à¸‡ resource à¹à¸¥à¸° `iam:PassRole` à¹à¸¢à¸à¸ˆà¸²à¸à¸ªà¸´à¸—à¸˜à¸´à¹Œà¸‚à¸­à¸‡ job runtime
- [ ] à¸£à¸°à¸šà¸¸à¹€à¸ˆà¹‰à¸²à¸‚à¸­à¸‡ job, Redshift, S3, network, secret à¹à¸¥à¸°à¸œà¸¹à¹‰à¸›à¸´à¸” schedule/cleanup
- [ ] à¸ˆà¸”à¸‡à¸šà¸à¹ˆà¸­à¸™/à¸«à¸¥à¸±à¸‡à¸£à¸±à¸™; budget meter à¸­à¸²à¸ˆà¸­à¸±à¸›à¹€à¸”à¸•à¸Šà¹‰à¸²

PowerShell à¸ˆà¸²à¸ project root (à¸­à¹ˆà¸²à¸™à¸­à¸¢à¹ˆà¸²à¸‡à¹€à¸”à¸µà¸¢à¸§):

```powershell
$AwsRegion = 'us-east-1'
aws sts get-caller-identity --region $AwsRegion
aws iam get-role --role-name LabRole --query 'Role.{Arn:Arn,Trust:AssumeRolePolicyDocument}' --output json
aws glue get-jobs --region $AwsRegion --query 'Jobs[].{Name:Name,Role:Role,Command:Command}' --output json
aws glue get-connections --hide-password --region $AwsRegion --query 'ConnectionList[].{Name:Name,Type:ConnectionType,Network:PhysicalConnectionRequirements}' --output json
```

à¸à¸²à¸£ get/list à¸œà¹ˆà¸²à¸™à¸¢à¸±à¸‡à¹„à¸¡à¹ˆà¸¢à¸·à¸™à¸¢à¸±à¸™ create/start job à¸«à¸£à¸·à¸­à¸à¸²à¸£à¹€à¸‚à¹‰à¸²à¸–à¸¶à¸‡ S3/Redshift à¸«à¸²à¸ AccessDenied à¹€à¸à¹‡à¸š action/resource/error à¹ƒà¸«à¹‰à¸œà¸¹à¹‰à¸”à¸¹à¹à¸¥à¸•à¸£à¸§à¸ˆ à¹„à¸¡à¹ˆà¹à¸à¹‰à¹€à¸›à¹‡à¸™ wildcard à¸«à¸£à¸·à¸­à¸›à¸´à¸” security à¹€à¸žà¸·à¹ˆà¸­à¹ƒà¸«à¹‰à¸œà¹ˆà¸²à¸™

## B. IAM à¹à¸¥à¸° network â€” à¸ˆà¸¸à¸”à¸—à¸µà¹ˆ handoff à¸¢à¸±à¸‡à¹„à¸¡à¹ˆà¸„à¸£à¸š

### B1. à¹à¸¢à¸ role à¸‚à¸­à¸‡ Glue à¸à¸±à¸š Redshift à¹à¸¡à¹‰à¹ƒà¸Šà¹‰ ARN à¹€à¸”à¸µà¸¢à¸§à¸à¸±à¸™

| à¸œà¸¹à¹‰à¹ƒà¸Šà¹‰à¸ªà¸´à¸—à¸˜à¸´à¹Œ | à¸ªà¸´à¸—à¸˜à¸´à¹Œà¸—à¸µà¹ˆà¸•à¹‰à¸­à¸‡à¸•à¸£à¸§à¸ˆ |
|---|---|
| Glue execution role | trust glue.amazonaws.com, à¸­à¹ˆà¸²à¸™ script/dependencies/SQL/package/à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸—à¸µà¹ˆà¸•à¹‰à¸­à¸‡à¹ƒà¸Šà¹‰, à¹€à¸‚à¸µà¸¢à¸™ logs à¹à¸¥à¸° prefix output/temp à¹€à¸¡à¸·à¹ˆà¸­à¹ƒà¸Šà¹‰, EC2 ENI permissions à¸ªà¸³à¸«à¸£à¸±à¸š VPC job |
| Glue job à¹€à¸£à¸µà¸¢à¸ Secrets Manager | GetSecretValue à¹€à¸‰à¸žà¸²à¸° secret à¹à¸¥à¸° KMS decrypt à¸«à¸²à¸ key policy à¸à¸³à¸«à¸™à¸” |
| Glue crawler | à¸­à¹ˆà¸²à¸™ source prefixes à¹à¸¥à¸°à¸ªà¸£à¹‰à¸²à¸‡/à¹à¸à¹‰ Catalog à¸•à¸²à¸¡à¸‚à¸­à¸šà¹€à¸‚à¸• |
| Redshift IAM role | à¸œà¸¹à¸ cluster/namespace à¸ˆà¸£à¸´à¸‡; à¸­à¹ˆà¸²à¸™ Parquet/manifests; à¹€à¸‚à¸µà¸¢à¸™ temp/output à¹€à¸¡à¸·à¹ˆà¸­ UNLOAD; KMS à¸•à¸²à¸¡ encryption |
| DB user | à¹€à¸Šà¸·à¹ˆà¸­à¸¡ DB, TEMP privileges, execute etl.load_batch à¹à¸¥à¸°à¸ªà¸´à¸—à¸˜à¸´à¹Œà¸•à¸²à¸¡ security mode à¸‚à¸­à¸‡ procedure; à¹„à¸¡à¹ˆà¸–à¸·à¸­à¸§à¹ˆà¸² IAM role à¹ƒà¸«à¹‰à¸­à¸³à¸™à¸²à¸ˆ SQL à¸„à¸£à¸š |

- [ ] à¸«à¸²à¸à¹ƒà¸Šà¹‰ LabRole à¸£à¹ˆà¸§à¸¡à¸à¸±à¸™ à¸•à¸£à¸§à¸ˆ trust à¸‚à¸­à¸‡à¸—à¸±à¹‰à¸‡ Glue à¹à¸¥à¸°à¸›à¸£à¸°à¹€à¸ à¸— Redshift à¸—à¸µà¹ˆà¹€à¸¥à¸·à¸­à¸
- [ ] à¸•à¸£à¸§à¸ˆ identity policy, bucket policy, endpoint policy, KMS policy à¸£à¹ˆà¸§à¸¡à¸à¸±à¸™; endpoint Full access à¹„à¸¡à¹ˆà¸—à¸”à¹à¸—à¸™ IAM
- [ ] à¹„à¸¡à¹ˆà¹€à¸£à¸µà¸¢à¸ get-secret-value à¹ƒà¸™ shell à¹€à¸žà¸·à¹ˆà¸­à¹à¸ªà¸”à¸‡ password; à¹„à¸¡à¹ˆ print secret/connection properties à¸¥à¸‡ logs

### B2. Network à¸—à¸µà¹ˆà¸£à¸±à¸šà¸ˆà¸²à¸ handoff

à¸„à¹ˆà¸²à¸•à¹ˆà¸­à¹„à¸›à¸™à¸µà¹‰à¹€à¸›à¹‡à¸™à¸«à¸¥à¸±à¸à¸à¸²à¸™à¸ˆà¸²à¸ handoff à¹„à¸¡à¹ˆà¹ƒà¸Šà¹ˆà¸à¸²à¸£à¸•à¸£à¸§à¸ˆ AWS à¸ªà¸”; à¸•à¹‰à¸­à¸‡à¸•à¸£à¸§à¸ˆà¸§à¹ˆà¸²à¸šà¸±à¸à¸Šà¸µ/à¸—à¸£à¸±à¸žà¸¢à¸²à¸à¸£à¸¢à¸±à¸‡à¸•à¸£à¸‡:

| à¸£à¸²à¸¢à¸à¸²à¸£ | à¸„à¹ˆà¸² |
|---|---|
| VPC | vpc-03aaf81c62341e797 |
| Private subnet A | subnet-0c93df663668db96 (us-east-1a) |
| Private subnet B | subnet-07441cbf39f0a9f33 (us-east-1b) |
| Glue SG | sg-REPLACE_GLUE_SG |
| Redshift SG | sg-REPLACE_REDSHIFT_SG |
| S3 gateway endpoint | vpce-09c521c76d4613f00 |
| Private route table | rtb-074e7eeb21b5e9d0d |

handoff à¸£à¸°à¸šà¸¸ private route à¸¡à¸µ local à¹à¸¥à¸° S3 endpoint à¹à¸•à¹ˆ **à¹„à¸¡à¹ˆà¸¡à¸µ NAT à¹à¸¥à¸°à¹„à¸¡à¹ˆà¸¡à¸µ interface endpoints à¸­à¸·à¹ˆà¸™**; à¸ªà¹ˆà¸§à¸™à¸•à¸²à¸£à¸²à¸‡ SG à¸šà¸­à¸ outbound à¹à¸¥à¹‰à¸§ à¹à¸•à¹ˆ checklist D à¸¢à¸±à¸‡à¸£à¸°à¸šà¸¸à¸£à¸­à¸•à¸£à¸§à¸ˆ à¸ˆà¸¶à¸‡à¸•à¹‰à¸­à¸‡à¸•à¸£à¸§à¸ˆà¸‹à¹‰à¸³à¸à¹ˆà¸­à¸™à¹ƒà¸Šà¹‰à¸‡à¸²à¸™

- [ ] à¹€à¸¥à¸·à¸­à¸ private subnet à¸«à¸™à¸¶à¹ˆà¸‡à¹à¸«à¹ˆà¸‡à¹ƒà¸«à¹‰ Glue connection à¹ƒà¸Šà¹‰; à¸•à¹‰à¸­à¸‡à¸¡à¸µ IP à¸§à¹ˆà¸²à¸‡à¹à¸¥à¸° route à¸–à¸¶à¸‡ Redshift à¸—à¸¸à¸à¸›à¸¥à¸²à¸¢à¸—à¸²à¸‡à¸—à¸µà¹ˆ job à¸•à¹‰à¸­à¸‡à¹ƒà¸Šà¹‰
- [ ] Glue SG inbound All TCP à¸ˆà¸²à¸à¸•à¸±à¸§à¹€à¸­à¸‡ à¹à¸¥à¸° outbound à¸£à¸°à¸«à¸§à¹ˆà¸²à¸‡ Glue components à¸•à¸²à¸¡à¸‚à¹‰à¸­à¸à¸³à¸«à¸™à¸” Spark/Glue
- [ ] Glue SG outbound TCP 5439 à¹„à¸› Redshift SG; Redshift SG inbound TCP 5439 à¸ˆà¸²à¸ Glue SG; à¸•à¸£à¸§à¸ˆ endpoint port à¸ˆà¸£à¸´à¸‡
- [ ] Glue/Redshift outbound HTTPS à¹„à¸› S3 endpoint/prefix list à¸•à¸²à¸¡à¸à¸²à¸£à¹ƒà¸Šà¹‰à¸‡à¸²à¸™
- [ ] DNS resolution/hostnames, NACL à¹à¸¥à¸° return traffic à¸–à¸¹à¸à¸•à¹‰à¸­à¸‡; à¹„à¸¡à¹ˆà¸•à¹‰à¸­à¸‡à¹€à¸›à¸´à¸” inbound à¸ˆà¸²à¸ Internet
- [ ] Secrets Manager à¸ªà¸³à¸«à¸£à¸±à¸šà¸•à¸±à¸§à¸­à¸¢à¹ˆà¸²à¸‡ job à¸™à¸µà¹‰à¸•à¹‰à¸­à¸‡à¸¡à¸µà¸—à¸²à¸‡à¸–à¸¶à¸‡ API: interface endpoint à¸žà¸£à¹‰à¸­à¸¡ private DNS à¸«à¸£à¸·à¸­ NAT à¸—à¸µà¹ˆà¸­à¸™à¸¸à¸¡à¸±à¸•à¸´
- [ ] à¸«à¸²à¸à¹€à¸žà¸´à¹ˆà¸¡ interface endpoint à¸•à¹‰à¸­à¸‡à¸¡à¸µ endpoint SG inbound TCP 443 à¸ˆà¸²à¸ Glue SG à¹à¸¥à¸° Glue SG outbound TCP 443 à¹„à¸› endpoint SG; S3-only egress à¹€à¸”à¸´à¸¡à¸¢à¸±à¸‡à¹„à¸¡à¹ˆà¸žà¸­
- [ ] à¸žà¸´à¸ˆà¸²à¸£à¸“à¸² Glue/Logs/KMS/STS endpoints à¹€à¸‰à¸žà¸²à¸° API à¸—à¸µà¹ˆ job/connector à¹€à¸£à¸µà¸¢à¸à¸ˆà¸£à¸´à¸‡ à¹„à¸¡à¹ˆà¸ªà¸£à¹‰à¸²à¸‡à¸—à¸¸à¸ endpoint à¹‚à¸”à¸¢à¸­à¸±à¸•à¹‚à¸™à¸¡à¸±à¸•à¸´
- [ ] à¸à¸²à¸£à¸•à¸´à¸”à¸•à¸±à¹‰à¸‡ packages à¸ˆà¸²à¸ PyPI à¸•à¹‰à¸­à¸‡à¸¡à¸µ Internet egress; à¸–à¹‰à¸²à¹„à¸¡à¹ˆà¸¡à¸µ à¹ƒà¸«à¹‰à¹€à¸•à¸£à¸µà¸¢à¸¡ wheels/dependencies à¸šà¸™ S3 à¸—à¸µà¹ˆà¹€à¸‚à¹‰à¸²à¸–à¸¶à¸‡à¹„à¸”à¹‰à¹à¸¥à¸°à¸£à¸­à¸‡à¸£à¸±à¸š runtime
- [ ] à¸­à¸¢à¹ˆà¸²à¸¢à¹‰à¸²à¸¢ Glue à¹„à¸› public subnet à¹à¸¥à¹‰à¸§à¸„à¸²à¸”à¸§à¹ˆà¸²à¸ˆà¸°à¹„à¸”à¹‰ Internet à¸­à¸±à¸•à¹‚à¸™à¸¡à¸±à¸•à¸´; à¸•à¸£à¸§à¸ˆ network design à¸‚à¸­à¸‡ Glue ENIs

```powershell
aws ec2 describe-security-groups --group-ids sg-REPLACE_GLUE_SG sg-REPLACE_REDSHIFT_SG --region $AwsRegion
aws ec2 describe-route-tables --route-table-ids rtb-074e7eeb21b5e9d0d --region $AwsRegion
aws ec2 describe-vpc-endpoints --region $AwsRegion
```

## C. à¸‚à¸­à¸‡à¸—à¸µà¹ˆà¸•à¹‰à¸­à¸‡à¸£à¸±à¸šà¸ˆà¸²à¸ S3 à¹à¸¥à¸° Redshift

### C1. S3 checklist

- [ ] Bucket à¸ˆà¸£à¸´à¸‡à¹ƒà¸™ us-east-1; region à¹€à¸”à¸µà¸¢à¸§à¸à¸±à¸š Redshift à¸ªà¸³à¸«à¸£à¸±à¸š COPY Parquet
- [ ] immutable curated batch: 7 Parquet + 7 manifests; size/hash à¸•à¸£à¸§à¸ˆà¹€à¸—à¸µà¸¢à¸š package à¹à¸¥à¹‰à¸§
- [ ] validation_report.json à¸œà¹ˆà¸²à¸™ checks à¹à¸¥à¸° known issue baseline à¸•à¸²à¸¡ batch
- [ ] package.json à¹à¸¥à¸° run_batch.sql à¸ˆà¸²à¸ generator à¸Šà¸¸à¸”à¹€à¸”à¸µà¸¢à¸§à¸à¸±à¸™; batch/hash/observed_at à¸•à¸£à¸‡à¸à¸±à¸™
- [ ] upload run_batch.sql à¹„à¸› prefix à¸„à¸§à¸šà¸„à¸¸à¸¡à¹à¸¢à¸à¹à¸¥à¸°à¸ˆà¸³à¸à¸±à¸”à¸œà¸¹à¹‰à¹€à¸‚à¸µà¸¢à¸™ à¹€à¸žà¸£à¸²à¸° job à¸ˆà¸° execute SQL à¸ˆà¸²à¸à¹„à¸Ÿà¸¥à¹Œà¸™à¸µà¹‰
- [ ] à¸šà¸±à¸™à¸—à¸¶à¸ SHA256 à¸‚à¸­à¸‡ run_batch.sql à¹€à¸žà¸·à¹ˆà¸­à¸ªà¹ˆà¸‡à¹€à¸›à¹‡à¸™ job parameter
- [ ] scripts/dependencies à¸¡à¸µ prefix à¹à¸¢à¸à¸ˆà¸²à¸ data
- [ ] glue-temp à¸¡à¸µ prefix à¹à¸¢à¸ à¸«à¸²à¸à¹ƒà¸Šà¹‰ Spark Redshift connector; à¹„à¸¡à¹ˆà¹ƒà¸Šà¹‰ curated prefix à¹€à¸›à¹‡à¸™ temp
- [ ] encryption à¹à¸¥à¸° lifecycle à¸ªà¸³à¸«à¸£à¸±à¸š temp/log/output à¸à¸³à¸«à¸™à¸”à¹à¸¥à¹‰à¸§; à¹„à¸¡à¹ˆà¸—à¸³ lifecycle à¸¥à¸š inputs à¸—à¸µà¹ˆà¸¢à¸±à¸‡à¸•à¹‰à¸­à¸‡ retry

à¸•à¸±à¸§à¸­à¸¢à¹ˆà¸²à¸‡ layout; à¸•à¹‰à¸­à¸‡à¹ƒà¸Šà¹‰ manifest URLs à¸ˆà¸£à¸´à¸‡à¸ˆà¸²à¸ package à¹„à¸¡à¹ˆà¸¢à¹‰à¸²à¸¢ data à¹€à¸­à¸‡:

```text
s3://BUCKET/thelook/curated/BATCH_ID/<table>/data.parquet
s3://BUCKET/thelook/curated/BATCH_ID/_manifests/<table>.json
s3://BUCKET/thelook/control/BATCH_ID/run_batch.sql
s3://BUCKET/thelook/control/BATCH_ID/package.json
s3://BUCKET/thelook/scripts/glue_load_batch.py
s3://BUCKET/thelook/dependencies/<tested-wheel-files>
s3://BUCKET/thelook/glue-temp/<job>/<run>/
```

à¸•à¸±à¸§à¸­à¸¢à¹ˆà¸²à¸‡ job à¸”à¹‰à¸²à¸™à¸¥à¹ˆà¸²à¸‡à¹„à¸¡à¹ˆà¹ƒà¸Šà¹‰ Spark connector à¸ˆà¸¶à¸‡à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¹ƒà¸Šà¹‰ glue-temp à¹ƒà¸™à¸à¸²à¸£à¸ªà¹ˆà¸‡ data; Redshift procedure COPY à¸ˆà¸²à¸ curated à¹‚à¸”à¸¢à¸•à¸£à¸‡ à¸­à¸¢à¹ˆà¸²à¸ªà¸±à¸šà¸ªà¸™ temp S3 à¸‚à¸­à¸‡ connector à¸à¸±à¸š TEMP tables à¹ƒà¸™ database

### C2. Redshift checklist

- [ ] à¸£à¸°à¸šà¸¸ provisioned cluster identifier à¸«à¸£à¸·à¸­ Serverless workgroup/namespace
- [ ] endpoint hostname, port 5439, database à¹à¸¥à¸° DB user/secret ARN
- [ ] resource AVAILABLE à¹à¸¥à¸° private endpoint à¹€à¸‚à¹‰à¸²à¸–à¸¶à¸‡à¹„à¸”à¹‰à¸ˆà¸²à¸ Glue subnet
- [ ] à¸•à¸´à¸”à¸•à¸±à¹‰à¸‡ SQL 00â€“03 revision à¸—à¸µà¹ˆà¸¢à¸·à¸™à¸¢à¸±à¸™à¹à¸¥à¹‰à¸§; à¸—à¸”à¸ªà¸­à¸š run_batch à¸œà¹ˆà¸²à¸™ Query Editor à¸à¹ˆà¸­à¸™à¹€à¸žà¸´à¹ˆà¸¡ orchestration
- [ ] LabRole à¸œà¸¹à¸ cluster/namespace à¸ˆà¸£à¸´à¸‡à¹à¸¥à¸°à¸­à¹ˆà¸²à¸™ S3 batch à¹„à¸”à¹‰
- [ ] DB user à¸¡à¸µà¸ªà¸´à¸—à¸˜à¸´à¹Œà¸•à¸²à¸¡ procedure (à¸•à¸£à¸§à¸ˆ SECURITY INVOKER/DEFINER à¸ˆà¸£à¸´à¸‡); loader à¸›à¸±à¸ˆà¸ˆà¸¸à¸šà¸±à¸™à¹„à¸¡à¹ˆà¸„à¸§à¸£à¸–à¸¹à¸à¸–à¸·à¸­à¸§à¹ˆà¸² SECURITY DEFINER à¹‚à¸”à¸¢à¸›à¸£à¸´à¸¢à¸²à¸¢
- [ ] à¸¢à¸·à¸™à¸¢à¸±à¸™ SCD policy, full snapshot, single writer, retry identity à¹à¸¥à¸° autocommit
- [ ] à¹€à¸•à¸£à¸µà¸¢à¸¡ DB à¸—à¸”à¸ªà¸­à¸šà¹à¸¢à¸à¸ªà¸³à¸«à¸£à¸±à¸š failure/SCD; à¸«à¹‰à¸²à¸¡ Glue connector à¹€à¸‚à¸µà¸¢à¸™ dw.* à¸•à¸£à¸‡

## D. à¸ªà¸£à¹‰à¸²à¸‡ secret à¹à¸¥à¸° Glue connection

1. Console â†’ Secrets Manager â†’ à¸ªà¸£à¹‰à¸²à¸‡/à¹ƒà¸Šà¹‰ secret à¸‚à¸­à¸‡ DB user à¸•à¸²à¸¡à¸ªà¸´à¸—à¸˜à¸´à¹Œ Lab; à¸•à¸±à¸§à¸­à¸¢à¹ˆà¸²à¸‡à¹‚à¸„à¹‰à¸”à¸™à¸µà¹‰à¸•à¹‰à¸­à¸‡à¸¡à¸µ `username` à¹à¸¥à¸° `password` à¹ƒà¸™ secret JSON (à¸à¸£à¸­à¸à¹ƒà¸™ Console à¹„à¸¡à¹ˆà¸§à¸²à¸‡à¸£à¸«à¸±à¸ªà¹ƒà¸™à¸„à¸¹à¹ˆà¸¡à¸·à¸­)
2. à¹ƒà¸«à¹‰ Glue role à¸­à¹ˆà¸²à¸™ secret à¸™à¸µà¹‰; à¸•à¸£à¸§à¸ˆ path à¹€à¸„à¸£à¸·à¸­à¸‚à¹ˆà¸²à¸¢à¸ˆà¸²à¸ B2 à¸à¹ˆà¸­à¸™
3. Glue Console â†’ Connections â†’ Create connection â†’ à¹€à¸¥à¸·à¸­à¸ Redshift/JDBC à¸•à¸²à¸¡ UI à¸—à¸µà¹ˆà¸£à¸­à¸‡à¸£à¸±à¸š
4. Connection name à¸•à¸±à¸§à¸­à¸¢à¹ˆà¸²à¸‡ `thelook-redshift-conn`
5. JDBC URL: `jdbc:redshift://REPLACE_ENDPOINT:5439/REPLACE_DATABASE`; à¹€à¸›à¸´à¸” SSL à¹à¸¥à¸°à¸•à¸±à¹‰à¸‡ authentication/secret à¸•à¸²à¸¡ UI
6. VPC à¹ƒà¸Šà¹‰ handoff; à¹€à¸¥à¸·à¸­à¸ private subnet A à¸«à¸£à¸·à¸­ B à¸—à¸µà¹ˆà¸¡à¸µ route à¸žà¸£à¹‰à¸­à¸¡; SG = Glue SG
7. Save â†’ Test connection à¹‚à¸”à¸¢à¹€à¸¥à¸·à¸­à¸ role à¸—à¸µà¹ˆà¸ˆà¸°à¹ƒà¸Šà¹‰à¸ˆà¸£à¸´à¸‡; à¹€à¸à¹‡à¸šà¸œà¸¥à¹à¸¥à¸° error à¸—à¸µà¹ˆà¹„à¸¡à¹ˆà¹€à¸œà¸¢ secret
8. à¸œà¸¹à¸ connection à¸™à¸µà¹‰à¸à¸±à¸š job à¹ƒà¸™ Job details â†’ Connections/Network configuration à¸”à¹‰à¸§à¸¢ à¸à¸²à¸£à¸ªà¸£à¹‰à¸²à¸‡ connection à¸­à¸¢à¹ˆà¸²à¸‡à¹€à¸”à¸µà¸¢à¸§à¹„à¸¡à¹ˆà¸—à¸³à¹ƒà¸«à¹‰ job à¹ƒà¸Šà¹‰ VPC à¸™à¸±à¹‰à¸™

à¸•à¸±à¸§à¸­à¸¢à¹ˆà¸²à¸‡ orchestrator à¹ƒà¸Šà¹‰ connection à¹€à¸žà¸·à¹ˆà¸­ network placement à¹à¸¥à¸°à¹ƒà¸Šà¹‰ secret ARN à¹€à¸žà¸·à¹ˆà¸­ authenticate à¸œà¹ˆà¸²à¸™ Python driver à¹€à¸­à¸‡ à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¸”à¸¶à¸‡ password à¸ˆà¸²à¸ Glue connection à¹à¸¥à¸°à¹„à¸¡à¹ˆà¹ƒà¸Šà¹‰ JDBC driver à¹ƒà¸™ Python

- [ ] Test connection à¸œà¹ˆà¸²à¸™ (à¸–à¹‰à¸² UI à¸£à¸­à¸‡à¸£à¸±à¸šà¸Šà¸™à¸´à¸” connection à¸™à¸µà¹‰)
- [ ] Smoke test à¸ˆà¸²à¸ job runtime à¸ˆà¸£à¸´à¸‡à¸œà¹ˆà¸²à¸™à¸­à¸µà¸à¸„à¸£à¸±à¹‰à¸‡ à¹€à¸žà¸£à¸²à¸° connection test à¹„à¸¡à¹ˆà¸žà¸´à¸ªà¸¹à¸ˆà¸™à¹Œà¸§à¹ˆà¸² runtime à¹€à¸‚à¹‰à¸²à¸–à¸¶à¸‡ Secrets Manager/dependencies à¹„à¸”à¹‰à¸„à¸£à¸š

## E. Data Catalog/Crawler â€” optional à¸ªà¸³à¸«à¸£à¸±à¸š loader à¸™à¸µà¹‰

à¸–à¹‰à¸²à¹‚à¸ˆà¸—à¸¢à¹Œà¸•à¹‰à¸­à¸‡à¸à¸²à¸£ Catalog à¹ƒà¸«à¹‰à¸—à¸³à¹„à¸”à¹‰à¸«à¸¥à¸±à¸‡à¸¡à¸µ curated S3 à¹‚à¸”à¸¢à¹„à¸¡à¹ˆà¸•à¹‰à¸­à¸‡à¸£à¸­ Redshift:

1. Glue â†’ Data Catalog â†’ Databases â†’ à¸ªà¸£à¹‰à¸²à¸‡ `thelook_curated`
2. à¸ªà¸£à¹‰à¸²à¸‡ crawler à¹ƒà¸Šà¹‰ role à¸—à¸µà¹ˆà¸­à¹ˆà¸²à¸™ S3/Catalog à¹„à¸”à¹‰ à¸•à¸±à¹‰à¸‡ schedule On demand
3. à¸£à¸°à¸šà¸¸ source à¸—à¸µà¸¥à¸° table prefix à¸‚à¸­à¸‡ batch à¸—à¸µà¹ˆà¸£à¸±à¸š à¹€à¸Šà¹ˆà¸™ `.../BATCH_ID/users/`; à¸—à¸³à¸„à¸£à¸š 7 tables à¸«à¸£à¸·à¸­à¹à¸¢à¸ crawler à¸•à¸²à¸¡à¸•à¸²à¸£à¸²à¸‡à¹€à¸žà¸·à¹ˆà¸­à¸¥à¸”à¸à¸²à¸£à¸£à¸§à¸¡ schema à¸œà¸´à¸”
4. à¸­à¸¢à¹ˆà¸² crawl bucket root à¸«à¸£à¸·à¸­à¸£à¸§à¸¡ raw/curated/manifests/reports/temp à¹ƒà¸™ source à¹€à¸”à¸µà¸¢à¸§
5. à¸£à¸±à¸™ crawler à¹à¸¥à¹‰à¸§à¸•à¸£à¸§à¸ˆ names, types, decimal precision/scale, locations à¹à¸¥à¸° partitions à¸à¸±à¸š curated_schema.json
6. à¸•à¸£à¸§à¸ˆ timestamp semantics à¸à¸±à¸š Parquet à¸ˆà¸£à¸´à¸‡; schema inference à¹„à¸¡à¹ˆà¸žà¸´à¸ªà¸¹à¸ˆà¸™à¹Œ timezone/business meaning
7. à¸–à¹‰à¸²à¹€à¸›à¸¥à¸µà¹ˆà¸¢à¸™ batch à¸•à¹‰à¸­à¸‡à¸à¸³à¸«à¸™à¸”à¸§à¹ˆà¸² Catalog à¸ˆà¸°à¸Šà¸µà¹‰ batch à¹„à¸«à¸™; à¸«à¹‰à¸²à¸¡à¸£à¸§à¸¡ full snapshots à¸«à¸¥à¸²à¸¢ batch à¹à¸¥à¹‰à¸§à¸™à¸±à¸šà¹€à¸›à¹‡à¸™à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸Šà¸¸à¸”à¹€à¸”à¸µà¸¢à¸§

- [ ] Catalog à¸–à¸¹à¸à¸•à¹‰à¸­à¸‡à¸„à¸£à¸š 7 à¸•à¸²à¸£à¸²à¸‡ à¹à¸¥à¸°à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¹€à¸žà¸´à¹ˆà¸¡ report JSON à¹€à¸›à¹‡à¸™ data table
- [ ] à¹„à¸¡à¹ˆà¸¡à¸µ schema drift à¸—à¸µà¹ˆà¹„à¸¡à¹ˆà¹„à¸”à¹‰ review
- [ ] à¸šà¸±à¸™à¸—à¸¶à¸à¸Šà¸±à¸”à¸§à¹ˆà¸² Catalog à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¸ªà¸£à¹‰à¸²à¸‡ stg/dw à¹à¸¥à¸°à¹„à¸¡à¹ˆà¹ƒà¸Šà¹ˆ prerequisite à¸‚à¸­à¸‡ manifest COPY

## F. à¸ªà¸£à¹‰à¸²à¸‡ orchestration job â€” parameters à¹à¸¥à¸° code

### F1. à¸•à¸±à¹‰à¸‡à¸„à¹ˆà¸² Job details

| à¸„à¹ˆà¸² | à¸•à¸±à¸§à¸­à¸¢à¹ˆà¸²à¸‡/à¹€à¸à¸“à¸‘à¹Œ |
|---|---|
| Name | thelook-load-batch |
| Job type | Python shell à¸«à¸²à¸ Lab à¸­à¸™à¸¸à¸à¸²à¸• |
| Python | 3.9 à¸•à¸²à¸¡ runtime Python shell à¸—à¸µà¹ˆà¸­à¹‰à¸²à¸‡à¸­à¸´à¸‡; à¸•à¸£à¸§à¸ˆà¹ƒà¸™ Console à¸­à¸µà¸à¸„à¸£à¸±à¹‰à¸‡ |
| IAM role | LabRole à¸—à¸µà¹ˆà¸•à¸£à¸§à¸ˆà¹à¸¥à¹‰à¸§ |
| Capacity | 0.0625 DPU à¸ªà¸³à¸«à¸£à¸±à¸šà¹€à¸£à¸´à¹ˆà¸¡à¸—à¸”à¸ªà¸­à¸š orchestrator à¸™à¸µà¹‰ à¸«à¸²à¸ Lab à¸­à¸™à¸¸à¸à¸²à¸•; à¹„à¸¡à¹ˆà¹ƒà¸Šà¹‰à¸„à¹ˆà¸²à¸™à¸µà¹‰à¹à¸—à¸™ Spark worker configuration |
| Max concurrent runs | 1 |
| Max retries | 0 à¸Šà¹ˆà¸§à¸‡à¸—à¸”à¸ªà¸­à¸š à¹€à¸žà¸·à¹ˆà¸­à¸”à¸¹ error à¸à¹ˆà¸­à¸™ retry |
| Timeout | à¸•à¸±à¸§à¸­à¸¢à¹ˆà¸²à¸‡ 30 à¸™à¸²à¸—à¸µ à¸›à¸£à¸±à¸šà¸•à¸²à¸¡ runtime à¸ˆà¸£à¸´à¸‡; timeout/cancel à¹„à¸¡à¹ˆà¸žà¸´à¸ªà¸¹à¸ˆà¸™à¹Œà¸§à¹ˆà¸² DB CALL à¸«à¸¢à¸¸à¸”à¹à¸¥à¹‰à¸§ à¸•à¹‰à¸­à¸‡à¸•à¸£à¸§à¸ˆ ledger/query history |
| Connections | thelook-redshift-conn |
| Schedule | On demand à¸ˆà¸™ tests à¸œà¹ˆà¸²à¸™ |
| Script | S3 URI à¸‚à¸­à¸‡ glue_load_batch.py à¸—à¸µà¹ˆ review à¹à¸¥à¹‰à¸§ |
| Libraries | boto3, redshift_connector à¹à¸¥à¸° sqlparse à¸—à¸µà¹ˆà¸—à¸”à¸ªà¸­à¸šà¸£à¹ˆà¸§à¸¡à¸à¸±à¸š runtime; à¹ƒà¸Šà¹‰ preinstalled à¸«à¸²à¸à¸•à¸£à¸§à¸ˆ version à¹à¸¥à¹‰à¸§ à¸«à¸£à¸·à¸­ wheels à¸šà¸™ S3 à¸žà¸£à¹‰à¸­à¸¡ dependencies |

à¸«à¸²à¸à¸•à¸´à¸”à¸•à¸±à¹‰à¸‡à¸ˆà¸²à¸ Internet à¹ƒà¸Šà¹‰ `--additional-python-modules` à¸žà¸£à¹‰à¸­à¸¡ versions à¸—à¸µà¹ˆà¸—à¸”à¸ªà¸­à¸šà¹à¸¥à¹‰à¸§; à¸«à¸²à¸à¹„à¸¡à¹ˆà¸¡à¸µ NAT à¹ƒà¸Šà¹‰ S3 wheel/library configuration à¸—à¸µà¹ˆ Python shell à¸£à¸­à¸‡à¸£à¸±à¸šà¹à¸¥à¸°à¸•à¸£à¸§à¸ˆ dependencies à¸„à¸£à¸š à¹„à¸¡à¹ˆà¹€à¸”à¸²à¸§à¹ˆà¸² pip à¹ƒà¸Šà¹‰à¸‡à¸²à¸™à¹„à¸”à¹‰à¸œà¹ˆà¸²à¸™ S3 endpoint

### F2. Job parameters

| Key | à¸•à¸±à¸§à¸­à¸¢à¹ˆà¸²à¸‡/à¸—à¸µà¹ˆà¸¡à¸² |
|---|---|
| --AWS_REGION | us-east-1 |
| --RS_HOST | endpoint hostname à¹„à¸¡à¹ˆà¸¡à¸µ jdbc:// à¸«à¸£à¸·à¸­ port |
| --RS_PORT | 5439 |
| --RS_DATABASE | thelook à¸«à¸£à¸·à¸­ DB à¸—à¸”à¸ªà¸­à¸š |
| --DB_SECRET_ARN | ARN à¸‚à¸­à¸‡ secret à¸—à¸µà¹ˆà¸¡à¸µ username/password |
| --RUN_SQL_S3_URI | s3://BUCKET/thelook/control/BATCH_ID/run_batch.sql |
| --RUN_SQL_SHA256 | hash à¸‚à¸­à¸‡ SQL à¸—à¸µà¹ˆà¸­à¸™à¸¸à¸¡à¸±à¸•à¸´ à¹„à¸¡à¹ˆà¹ƒà¸Šà¹ˆ package_hash |
| --BATCH_ID | à¸„à¹ˆà¸²à¸ˆà¸²à¸ package.json |
| --PACKAGE_HASH | à¸„à¹ˆà¸²à¸ˆà¸²à¸ package.json |
| --SMOKE_ONLY | true à¸ªà¸³à¸«à¸£à¸±à¸šà¸•à¸£à¸§à¸ˆ connection à¸à¹ˆà¸­à¸™; false à¹€à¸žà¸·à¹ˆà¸­à¹‚à¸«à¸¥à¸”à¸ˆà¸£à¸´à¸‡ |

à¸•à¸±à¸§à¸­à¸¢à¹ˆà¸²à¸‡à¹‚à¸„à¹‰à¸”à¸ªà¸³à¸«à¸£à¸±à¸šà¸™à¸³à¹„à¸›à¸ªà¸£à¹‰à¸²à¸‡ `glue_load_batch.py` â€” à¸¢à¸±à¸‡à¹„à¸¡à¹ˆà¹„à¸”à¹‰ execute à¸šà¸™ Glue à¸•à¹‰à¸­à¸‡ review/pin libraries à¹à¸¥à¸°à¸—à¸”à¸ªà¸­à¸šà¸à¹ˆà¸­à¸™à¹ƒà¸Šà¹‰à¸‡à¸²à¸™à¸ˆà¸£à¸´à¸‡ à¹‚à¸„à¹‰à¸”à¸™à¸µà¹‰à¸­à¹ˆà¸²à¸™à¹€à¸‰à¸žà¸²à¸° generated run_batch.sql à¸—à¸µà¹ˆà¹€à¸Šà¸·à¹ˆà¸­à¸–à¸·à¸­à¹„à¸”à¹‰ à¹„à¸¡à¹ˆà¹ƒà¸Šà¹‰à¸à¸±à¸šà¹„à¸Ÿà¸¥à¹Œ DDL 00â€“03 à¸«à¸£à¸·à¸­ SQL à¸ˆà¸²à¸à¹à¸«à¸¥à¹ˆà¸‡à¸—à¸µà¹ˆà¹„à¸¡à¹ˆà¸£à¸¹à¹‰à¸ˆà¸±à¸

```python
import argparse
import hashlib
import json
from urllib.parse import urlparse

import boto3
import redshift_connector
import sqlparse

parser = argparse.ArgumentParser()
for key in ["AWS_REGION", "RS_HOST", "RS_DATABASE", "DB_SECRET_ARN",
            "RUN_SQL_S3_URI", "RUN_SQL_SHA256", "BATCH_ID", "PACKAGE_HASH"]:
    parser.add_argument("--" + key, required=True)
parser.add_argument("--RS_PORT", type=int, default=5439)
parser.add_argument("--SMOKE_ONLY", choices=["true", "false"], default="true")
args, _ = parser.parse_known_args()  # Glue may supply additional runtime arguments

uri = urlparse(args.RUN_SQL_S3_URI)
if uri.scheme != "s3" or not uri.netloc or not uri.path.strip("/"):
    raise ValueError("Invalid SQL S3 URI")
s3 = boto3.client("s3", region_name=args.AWS_REGION)
body = s3.get_object(Bucket=uri.netloc, Key=uri.path.lstrip("/"))["Body"].read()
if hashlib.sha256(body).hexdigest() != args.RUN_SQL_SHA256.lower():
    raise ValueError("SQL hash differs from reviewed artifact")
statements = sqlparse.split(body.decode("utf-8-sig"))
if not statements:
    raise ValueError("Empty SQL artifact")

secrets = boto3.client("secretsmanager", region_name=args.AWS_REGION)
secret = json.loads(secrets.get_secret_value(SecretId=args.DB_SECRET_ARN)["SecretString"])
conn = redshift_connector.connect(
    host=args.RS_HOST, port=args.RS_PORT, database=args.RS_DATABASE,
    user=secret["username"], password=secret["password"],
    ssl=True, sslmode="verify-full", timeout=30,
)
try:
    # Keep one connection for TEMP controls and CALL. No explicit BEGIN.
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user")
        database, _ = cur.fetchone()
        if database != args.RS_DATABASE:
            raise RuntimeError("Unexpected database")
        if args.SMOKE_ONLY == "true":
            print("SMOKE_PASS: S3 SQL hash, secret access, TLS and database connection")
        else:
            for statement in statements:
                cur.execute(statement)
                if cur.description:
                    cur.fetchall()  # consume small control query results, do not print source data
            cur.execute(
                "SELECT status,package_hash FROM etl.batch_ledger WHERE batch_id=%s",
                (args.BATCH_ID,),
            )
            rows = cur.fetchall()
            if len(rows) != 1 or rows[0][0] != "SUCCEEDED" or rows[0][1] != args.PACKAGE_HASH:
                raise RuntimeError("Published batch does not match expected identity")
            print("LOAD_VERIFIED: expected batch exists in success ledger")
finally:
    conn.close()
```

à¹‚à¸„à¹‰à¸”à¹„à¸¡à¹ˆ catch à¹à¸¥à¹‰à¸§à¸à¸¥à¸·à¸™ exception: error à¸•à¹‰à¸­à¸‡à¸—à¸³à¹ƒà¸«à¹‰ job FAILED; à¸«à¹‰à¸²à¸¡à¹€à¸›à¸¥à¸µà¹ˆà¸¢à¸™à¹€à¸›à¹‡à¸™ print à¹à¸¥à¹‰à¸§à¸ˆà¸šà¸ªà¸³à¹€à¸£à¹‡à¸ˆ Hash à¸‚à¸­à¸‡ SQL à¸¢à¸·à¸™à¸¢à¸±à¸™à¹€à¸‰à¸žà¸²à¸° artifact à¸—à¸µà¹ˆ review à¹à¸¥à¹‰à¸§ à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¸•à¸£à¸§à¸ˆ Parquet upload à¸«à¸£à¸·à¸­à¸­à¸™à¸¸à¸¡à¸±à¸•à¸´à¹€à¸™à¸·à¹‰à¸­à¸«à¸² SQL à¹ƒà¸«à¹‰à¹€à¸­à¸‡ Parameter/SQL à¸ˆà¸¶à¸‡à¸•à¹‰à¸­à¸‡à¹€à¸›à¹‡à¸™à¸Šà¸¸à¸”à¹€à¸”à¸µà¸¢à¸§à¸à¸±à¸™à¹à¸¥à¸°à¸ˆà¸³à¸à¸±à¸”à¸œà¸¹à¹‰à¹à¸à¹‰à¹„à¸‚

`SMOKE_PASS` à¹„à¸¡à¹ˆà¸žà¸´à¸ªà¸¹à¸ˆà¸™à¹Œ COPY, SCD, Redshift S3 role à¸«à¸£à¸·à¸­à¸à¸²à¸£à¹‚à¸«à¸¥à¸”à¸„à¸£à¸š à¸•à¹‰à¸­à¸‡à¸—à¸³à¸‚à¸±à¹‰à¸™ H à¸­à¸µà¸à¸„à¸£à¸±à¹‰à¸‡ à¸›à¸±à¸ˆà¸ˆà¸¸à¸šà¸±à¸™ job à¸™à¸µà¹‰à¸ªà¸±à¹ˆà¸‡ SQL à¹€à¸”à¸´à¸¡ à¹„à¸¡à¹ˆà¸¡à¸µ Spark transformations à¹à¸¥à¸°à¹„à¸¡à¹ˆà¸•à¹‰à¸­à¸‡à¹€à¸žà¸´à¹ˆà¸¡ S3 temp à¸ªà¸³à¸«à¸£à¸±à¸š connector

### F3. Upload script/SQL à¹à¸¥à¸°à¹€à¸•à¸£à¸µà¸¢à¸¡ run arguments

à¸«à¸¥à¸±à¸‡à¸šà¸±à¸™à¸—à¸¶à¸/à¸—à¸”à¸ªà¸­à¸š script à¹ƒà¸™à¹€à¸„à¸£à¸·à¹ˆà¸­à¸‡à¹à¸¥à¹‰à¸§ (à¸„à¸³à¸ªà¸±à¹ˆà¸‡à¸™à¸µà¹‰ upload objects):

```powershell
$BucketName = 'REPLACE_BUCKET'
$BatchId = 'REPLACE_BATCH_ID'
$PackageDir = "outputs/aws/$BatchId"
$JobName = 'thelook-load-batch'
$SqlPath = Join-Path $PackageDir 'run_batch.sql'
$SqlHash = (Get-FileHash -LiteralPath $SqlPath -Algorithm SHA256).Hash.ToLowerInvariant()
aws s3 cp $SqlPath "s3://$BucketName/thelook/control/$BatchId/run_batch.sql" --region $AwsRegion
if ($LASTEXITCODE -ne 0) { throw 'SQL upload failed' }
# Replace the local path with the reviewed script you saved from F2.
aws s3 cp 'REPLACE_LOCAL_SCRIPT_PATH' "s3://$BucketName/thelook/scripts/glue_load_batch.py" --region $AwsRegion
if ($LASTEXITCODE -ne 0) { throw 'Script upload failed' }
```

à¸•à¸±à¹‰à¸‡ parameters à¹ƒà¸™ Console à¸•à¸²à¸¡ F2 à¹à¸¥à¹‰à¸§ Save; password à¸•à¹‰à¸­à¸‡à¸­à¸¢à¸¹à¹ˆà¹ƒà¸™ secret à¹€à¸—à¹ˆà¸²à¸™à¸±à¹‰à¸™ à¹„à¸¡à¹ˆà¸­à¸¢à¸¹à¹ˆà¹ƒà¸™ job arguments à¸‹à¸¶à¹ˆà¸‡à¸­à¹ˆà¸²à¸™à¹„à¸”à¹‰à¸ˆà¸²à¸ Console/logs/API

## G. Smoke test à¹à¸¥à¸° monitoring

- [ ] à¸•à¸±à¹‰à¸‡ SMOKE_ONLY=true à¹à¸¥à¹‰à¸§ Run job à¸œà¹ˆà¸²à¸™ Console
- [ ] à¸•à¸£à¸§à¸ˆ job run state SUCCEEDED à¹à¸¥à¸° log SMOKE_PASS
- [ ] à¸–à¹‰à¸² import error à¹ƒà¸«à¹‰à¹à¸à¹‰ runtime/dependencies à¹„à¸¡à¹ˆà¹ƒà¸Šà¹ˆà¹€à¸žà¸´à¹ˆà¸¡ DPU à¹à¸šà¸šà¹€à¸”à¸²
- [ ] à¸–à¹‰à¸² S3 AccessDenied à¸•à¸£à¸§à¸ˆ Glue role; à¸–à¹‰à¸² COPY AccessDenied à¸ à¸²à¸¢à¸«à¸¥à¸±à¸‡à¸•à¸£à¸§à¸ˆ Redshift role à¹à¸¢à¸à¸à¸±à¸™
- [ ] à¸–à¹‰à¸² Secrets Manager timeout à¹ƒà¸«à¹‰à¸•à¸£à¸§à¸ˆ endpoint/DNS/SG; à¸–à¹‰à¸² AccessDenied à¹ƒà¸«à¹‰à¸•à¸£à¸§à¸ˆ IAM/KMS
- [ ] à¸–à¹‰à¸² DB timeout à¸•à¸£à¸§à¸ˆ subnet/routes/SG/port; à¸–à¹‰à¸² auth failed à¸•à¸£à¸§à¸ˆ DB user/secret/TLS à¹‚à¸”à¸¢à¹„à¸¡à¹ˆà¸žà¸´à¸¡à¸žà¹Œà¸£à¸«à¸±à¸ª
- [ ] à¸”à¸¹ Python shell logs à¸—à¸µà¹ˆ `/aws-glue/python-jobs/output` à¹à¸¥à¸° `/aws-glue/python-jobs/error`; job à¹à¸šà¸šà¸­à¸·à¹ˆà¸™à¸­à¸²à¸ˆà¸¡à¸µ log groups à¸•à¹ˆà¸²à¸‡à¸à¸±à¸™

à¸­à¹ˆà¸²à¸™à¸ªà¸–à¸²à¸™à¸°à¸”à¹‰à¸§à¸¢ CLI (à¹ƒà¸Šà¹‰ run ID à¸ˆà¸²à¸ Console):

```powershell
$JobName = 'thelook-load-batch'
$RunId = 'jr_REPLACE_RUN_ID'
aws glue get-job-run --job-name $JobName --run-id $RunId --region $AwsRegion --query 'JobRun.{State:JobRunState,Error:ErrorMessage,Started:StartedOn,Ended:CompletedOn,Seconds:ExecutionTime}' --output json
```

## H. à¹‚à¸«à¸¥à¸”à¸ˆà¸£à¸´à¸‡à¹à¸¥à¸°à¹€à¸à¸“à¸‘à¹Œà¸•à¸£à¸§à¸ˆà¸£à¸±à¸š

1. à¸•à¸£à¸§à¸ˆ batch/SQL hash/target DB à¸­à¸µà¸à¸„à¸£à¸±à¹‰à¸‡à¹à¸¥à¸°à¸¢à¸·à¸™à¸¢à¸±à¸™à¹„à¸¡à¹ˆà¸¡à¸µ writer à¸­à¸·à¹ˆà¸™
2. à¹€à¸›à¸¥à¸µà¹ˆà¸¢à¸™ SMOKE_ONLY=false à¹à¸¥à¹‰à¸§ Run; à¹„à¸¡à¹ˆà¹€à¸›à¸¥à¸µà¹ˆà¸¢à¸™ batch ID/observed_at à¸£à¸°à¸«à¸§à¹ˆà¸²à¸‡ retry
3. à¸£à¸­ job à¸ªà¸³à¹€à¸£à¹‡à¸ˆ à¹à¸¥à¹‰à¸§à¸•à¸£à¸§à¸ˆ DB à¹‚à¸”à¸¢à¸­à¸´à¸ªà¸£à¸°:

```sql
SELECT * FROM etl.batch_ledger WHERE batch_id='REPLACE_BATCH_ID';
SELECT * FROM etl.batch_checks WHERE batch_id='REPLACE_BATCH_ID' ORDER BY check_name;
SELECT * FROM etl.batch_attempts WHERE batch_id='REPLACE_BATCH_ID' ORDER BY attempted_at;
SELECT COUNT(*) AS rows,COUNT(DISTINCT order_item_id) AS distinct_items FROM dw.fact_sales;
```

4. à¸£à¸±à¸™ `code/sql/04_post_load_checks.sql` à¹à¸¥à¸° checks à¹€à¸žà¸´à¹ˆà¸¡à¸•à¸²à¸¡ [Phase 2 checklist](phase2_deployment_checklist.md); à¸­à¸¢à¹ˆà¸²à¸–à¸·à¸­ `mismatched_products` à¹ƒà¸™ SQL 04 à¹€à¸›à¹‡à¸™ distinct mismatch count à¹‚à¸”à¸¢à¹„à¸¡à¹ˆà¸•à¸£à¸§à¸ˆ query
5. Run job à¹€à¸”à¸´à¸¡à¸‹à¹‰à¸³: job à¸­à¸²à¸ˆ SUCCEEDED à¹à¸•à¹ˆà¹ƒà¸™ DB à¸•à¹‰à¸­à¸‡à¸¡à¸µ NO_OP à¹à¸¥à¸° contents/keys/versions à¹„à¸¡à¹ˆà¹€à¸›à¸¥à¸µà¹ˆà¸¢à¸™
6. à¸—à¸”à¸ªà¸­à¸š invalid SQL hash à¹ƒà¸™ DB à¸—à¸”à¸ªà¸­à¸š: à¸•à¹‰à¸­à¸‡ fail à¸à¹ˆà¸­à¸™ CALL; à¸—à¸”à¸ªà¸­à¸š rollback/SCD à¹à¸¢à¸à¸•à¸²à¸¡ Phase 2 à¹„à¸¡à¹ˆà¹ƒà¸Šà¹‰à¹à¸„à¹ˆ hash failure à¹à¸—à¸™ rollback test
7. à¸–à¹‰à¸² job timeout/connection à¸«à¸¥à¸¸à¸” à¸­à¸¢à¹ˆà¸²à¸ªà¸±à¹ˆà¸‡ batch à¹ƒà¸«à¸¡à¹ˆà¸—à¸±à¸™à¸—à¸µ à¸•à¸£à¸§à¸ˆ DB query history/ledger à¸à¹ˆà¸­à¸™ à¹à¸¥à¹‰à¸§ retry identity à¹€à¸”à¸´à¸¡à¹€à¸¡à¸·à¹ˆà¸­à¸—à¸£à¸²à¸šà¸ªà¸–à¸²à¸™à¸°

- [ ] Glue run SUCCEEDED à¹à¸¥à¸° ledger SUCCEEDED à¸‚à¸­à¸‡ batch/hash à¸—à¸µà¹ˆà¸„à¸²à¸”
- [ ] staging 7 à¸•à¸²à¸£à¸²à¸‡à¸•à¸£à¸‡ package; fact count à¹€à¸—à¹ˆà¸²à¸à¸±à¸š order_items à¸‚à¸­à¸‡ batch
- [ ] à¹„à¸¡à¹ˆà¸¡à¸µ duplicate/orphan/SCD overlap/as-of mismatch
- [ ] à¹€à¸‡à¸´à¸™/à¸§à¸±à¸™à¸—à¸µà¹ˆ/flags à¸•à¸£à¸‡ mapping à¹à¸¥à¸° known issues à¸¡à¸µà¸„à¸³à¸­à¸˜à¸´à¸šà¸²à¸¢
- [ ] NO_OP à¹„à¸¡à¹ˆà¹€à¸›à¸¥à¸µà¹ˆà¸¢à¸™ contents/keys/versions
- [ ] failure à¸—à¸³à¹ƒà¸«à¹‰ job FAILED à¹à¸¥à¸° rollback/no partial publish à¸œà¹ˆà¸²à¸™à¸à¸²à¸£à¸—à¸”à¸ªà¸­à¸šà¸ˆà¸£à¸´à¸‡
- [ ] à¹€à¸à¹‡à¸š run ID, query ID, commit, batch, SQL hash, package hash, results à¹à¸¥à¸°à¸‡à¸šà¸—à¸µà¹ˆà¹ƒà¸Šà¹‰
- [ ] à¹€à¸›à¸´à¸” trigger/schedule à¹€à¸‰à¸žà¸²à¸°à¹€à¸¡à¸·à¹ˆà¸­à¸œà¹ˆà¸²à¸™à¹à¸¥à¹‰à¸§; job concurrency 1 à¹à¸¥à¸°à¹„à¸¡à¹ˆà¸Šà¸™ manual loader

## I. à¸«à¸²à¸à¸•à¹‰à¸­à¸‡à¹ƒà¸Šà¹‰ Spark Redshift connector à¹€à¸žà¸´à¹ˆà¸¡à¹€à¸•à¸´à¸¡

à¸™à¸µà¹ˆà¹€à¸›à¹‡à¸™à¸­à¸µà¸à¹€à¸ªà¹‰à¸™à¸—à¸²à¸‡à¸«à¸™à¸¶à¹ˆà¸‡ à¹„à¸¡à¹ˆà¹ƒà¸Šà¹ˆà¹‚à¸„à¹‰à¸”à¹à¸—à¸™ F2 à¹‚à¸”à¸¢à¸•à¸£à¸‡:

- [ ] à¹€à¸¥à¸·à¸­à¸ Glue Spark version à¹à¸¥à¸° worker type/count à¸—à¸µà¹ˆ Lab à¸­à¸™à¸¸à¸à¸²à¸•; Python shell DPU à¹„à¸¡à¹ˆà¹ƒà¸Šà¹ˆà¸„à¹ˆà¸² worker à¸‚à¸­à¸‡ Spark
- [ ] à¸œà¸¹à¸ Redshift connection à¸à¸±à¸š job à¹à¸¥à¸°à¹ƒà¸Šà¹‰ Glue SG self-reference
- [ ] à¸à¸³à¸«à¸™à¸” `redshift_tmp_dir`/`redshiftTmpDir` à¹ƒà¸«à¹‰ connector à¸•à¸²à¸¡ API à¸—à¸µà¹ˆà¹ƒà¸Šà¹‰; Glue role à¹à¸¥à¸° Redshift role à¸•à¹‰à¸­à¸‡à¹€à¸‚à¹‰à¸²à¸–à¸¶à¸‡ temp prefix à¸ªà¸³à¸«à¸£à¸±à¸š COPY/UNLOAD
- [ ] à¹ƒà¸Šà¹‰ IAM role à¸—à¸µà¹ˆà¹€à¸«à¸¡à¸²à¸°à¸ªà¸¡à¸à¸±à¸š S3 à¹„à¸¡à¹ˆà¸žà¸¶à¹ˆà¸‡ temporary credentials à¹à¸šà¸šà¹„à¸¡à¹ˆà¸•à¸£à¸§à¸ˆà¸­à¸²à¸¢à¸¸
- [ ] à¸ªà¸³à¸«à¸£à¸±à¸š smoke test à¹€à¸¥à¸·à¸­à¸à¸•à¸²à¸£à¸²à¸‡à¹€à¸¥à¹‡à¸ à¹€à¸Šà¹ˆà¸™ distribution centers; à¸«à¹‰à¸²à¸¡ connector à¹€à¸‚à¸µà¸¢à¸™ production stg/dw à¹€à¸žà¸·à¹ˆà¸­à¸—à¸”à¸ªà¸­à¸š

à¸•à¸±à¸§à¸­à¸¢à¹ˆà¸²à¸‡à¸­à¹ˆà¸²à¸™à¸•à¸²à¸£à¸²à¸‡à¹€à¸¥à¹‡à¸à¸œà¹ˆà¸²à¸™ connection à¹ƒà¸™ Spark runtime (à¸•à¹‰à¸­à¸‡à¸•à¸´à¸”à¸•à¸±à¹‰à¸‡ DW à¹à¸¥à¸°à¸¡à¸µà¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¹à¸¥à¹‰à¸§):

```python
import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["CONNECTION_NAME", "REDSHIFT_TMP_DIR", "REDSHIFT_S3_ROLE"])
glue = GlueContext(SparkContext.getOrCreate())
frame = glue.create_dynamic_frame.from_options(
    connection_type="redshift",
    connection_options={
        "useConnectionProperties": "true",
        "connectionName": args["CONNECTION_NAME"],
        "dbtable": "dw.dim_distribution_centers",
        "redshiftTmpDir": args["REDSHIFT_TMP_DIR"],
        "aws_iam_role": args["REDSHIFT_S3_ROLE"],
    },
)
print("distribution_center_rows=", frame.count())
```

Parameters: --CONNECTION_NAME=à¸Šà¸·à¹ˆà¸­ connection, --REDSHIFT_TMP_DIR=s3://BUCKET/thelook/glue-temp/UNIQUE_RUN/, --REDSHIFT_S3_ROLE=ARN à¸—à¸µà¹ˆà¸œà¸¹à¸ Redshift à¸•à¸£à¸§à¸ˆ connector options à¸à¸±à¸š Glue version à¸—à¸µà¹ˆà¹€à¸¥à¸·à¸­à¸à¹à¸¥à¸°à¸£à¸±à¸™ smoke à¸à¹ˆà¸­à¸™à¹ƒà¸Šà¹‰à¸ˆà¸£à¸´à¸‡

à¸«à¸²à¸à¸•à¹‰à¸­à¸‡à¹à¸›à¸¥à¸‡ raw à¸šà¸™ Spark à¸•à¹‰à¸­à¸‡à¸­à¸­à¸à¹à¸šà¸š schema à¹à¸šà¸š explicit, Decimal(18,6)/ROUND_HALF_UP, UTC timestamps, null tokens, FK/DQ/quarantine à¹à¸¥à¸° Parquet column order à¸•à¸²à¸¡à¸ªà¸±à¸à¸à¸²à¹€à¸”à¸´à¸¡ à¸žà¸£à¹‰à¸­à¸¡ reconciliation à¸à¸±à¸šà¸œà¸¥ local à¹„à¸¡à¹ˆà¹ƒà¸«à¹‰ crawler inference à¹€à¸›à¸¥à¸µà¹ˆà¸¢à¸™à¸ªà¸±à¸à¸à¸²à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¹€à¸­à¸‡

## J. Checklist à¸ªà¹ˆà¸‡à¸¡à¸­à¸šà¹à¸¥à¸°à¸„à¹ˆà¸²à¹ƒà¸Šà¹‰à¸ˆà¹ˆà¸²à¸¢

- [ ] à¸£à¸°à¸šà¸¸à¸Šà¸±à¸”à¸§à¹ˆà¸²à¸—à¸³ Catalog, orchestration à¸«à¸£à¸·à¸­ Spark ETL à¸ªà¹ˆà¸§à¸™à¹ƒà¸”à¹€à¸ªà¸£à¹‡à¸ˆ/à¸¢à¸±à¸‡à¹„à¸¡à¹ˆà¸—à¸³
- [ ] à¸šà¸±à¸™à¸—à¸¶à¸ connection/job/script URI/dependency versions à¹à¸¥à¸° network endpoints à¸—à¸µà¹ˆà¹ƒà¸Šà¹‰
- [ ] à¸šà¸±à¸™à¸—à¸¶à¸ runtime role/Redshift role/secret ARN à¹‚à¸”à¸¢à¹„à¸¡à¹ˆà¸ªà¹ˆà¸‡à¸„à¹ˆà¸²à¸‚à¸­à¸‡ secret
- [ ] Export à¸«à¸¥à¸±à¸à¸à¸²à¸™ run/checks à¹à¸¥à¸°à¸£à¸²à¸¢à¸à¸²à¸£ NOT TESTED
- [ ] à¸›à¸´à¸” schedules/triggers à¸—à¸µà¹ˆà¹„à¸¡à¹ˆà¹ƒà¸Šà¹‰; à¸à¸³à¸«à¸™à¸” log retention à¹à¸¥à¸° temp lifecycle
- [ ] à¸•à¸£à¸§à¸ˆ jobs/crawlers/S3/Redshift/logs/Secrets Manager/interface endpoints/NAT à¸—à¸µà¹ˆà¸¢à¸±à¸‡à¸¡à¸µà¸„à¹ˆà¸²à¹ƒà¸Šà¹‰à¸ˆà¹ˆà¸²à¸¢ à¹„à¸¡à¹ˆà¸„à¸´à¸”à¹€à¸‰à¸žà¸²à¸° Glue DPU
- [ ] à¸­à¸¢à¹ˆà¸²à¸¥à¸š temp à¸—à¸µà¹ˆ job à¹ƒà¸Šà¹‰à¸­à¸¢à¸¹à¹ˆ à¹à¸¥à¸°à¸­à¸¢à¹ˆà¸²à¸¥à¸š curated/control package à¸—à¸µà¹ˆà¸¢à¸±à¸‡à¸•à¹‰à¸­à¸‡ retry à¸«à¸£à¸·à¸­à¸ªà¹ˆà¸‡à¹ƒà¸«à¹‰à¸—à¸µà¸¡ BI

## à¸­à¹‰à¸²à¸‡à¸­à¸´à¸‡

- [Project handoff](handoff1.md) â€” à¸ªà¸–à¸²à¸™à¸°à¹‚à¸„à¸£à¸‡à¸‚à¹ˆà¸²à¸¢à¸—à¸µà¹ˆà¹„à¸”à¹‰à¸£à¸±à¸š à¹„à¸¡à¹ˆà¹ƒà¸Šà¹ˆ live verification
- [Project SQL runbook](../code/sql/README.md)
- [AWS Academy Educator Guide](https://d1.awsstatic.com/AWS%20Academy%20Learner%20Lab%20Educator%20Guide.pdf) â€” à¸­à¸˜à¸´à¸šà¸²à¸¢à¹€à¸„à¸£à¸”à¸´à¸•/à¸šà¸£à¸´à¸à¸²à¸£à¸ˆà¸³à¸à¸±à¸”; à¹€à¸­à¸à¸ªà¸²à¸£à¹€à¸à¹ˆà¸² à¹„à¸¡à¹ˆà¹ƒà¸Šà¹‰à¸¢à¸·à¸™à¸¢à¸±à¸™à¸ˆà¸³à¸™à¸§à¸™à¹€à¸„à¸£à¸”à¸´à¸•à¸«à¸£à¸·à¸­à¸šà¸£à¸´à¸à¸²à¸£à¸‚à¸­à¸‡ Lab à¸›à¸±à¸ˆà¸ˆà¸¸à¸šà¸±à¸™
- [Glue Python shell runtime/capacity/libraries/logs](https://docs.aws.amazon.com/glue/latest/dg/add-job-python.html)
- [Glue Redshift connector à¹à¸¥à¸° S3 temporary directory](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-etl-connect-redshift-home.html)
- [Glue connection properties](https://docs.aws.amazon.com/glue/latest/dg/connection-properties.html)
- [Glue IAM setup](https://docs.aws.amazon.com/glue/latest/dg/set-up-iam.html)
- [Crawler include paths](https://docs.aws.amazon.com/glue/latest/dg/define-crawler-choose-data-sources.html)
- [Redshift Python connector configuration](https://docs.aws.amazon.com/redshift/latest/mgmt/python-configuration-options.html)
