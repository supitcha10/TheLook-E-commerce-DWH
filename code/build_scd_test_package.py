"""Build offline synthetic COPY/SCD/rollback integration fixtures. No AWS calls."""
import copy
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/aws/scd-test-fixtures-v1'
PREFIX = 'thelook/tests/scd-rollback/fixtures-v1'
BUCKET = 'thelook-dwh-20241022'
ROLE = 'arn:aws:iam::006816724683:role/LabRole'
BASE = f's3://{BUCKET}/{PREFIX}'
CONTRACT = json.loads((ROOT/'code/curated_schema.json').read_text())['tables']
MONEY = [('products','cost'),('products','retail_price'),('inventory_items','cost'),('inventory_items','product_retail_price'),('order_items','sale_price')]


def stamp(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def schema(name):
    fields = []
    types = {'BIGINT':pa.int64(), 'INTEGER':pa.int32(), 'SMALLINT':pa.int16(), 'DOUBLE PRECISION':pa.float64(), 'TIMESTAMPTZ':pa.timestamp('us',tz='UTC')}
    for c in CONTRACT[name]['columns']:
        t=c['type']
        typ=pa.string() if t.startswith('VARCHAR') else pa.decimal128(18,6) if t.startswith('DECIMAL') else types[t]
        fields.append(pa.field(c['name'],typ,nullable=c['nullable']))
    if name in ('users','events'):
        fields += [pa.field('city_clean',pa.string()),pa.field('city_missing_token',pa.bool_())]
    if name=='order_items':
        fields += [pa.field('item_shipped_before_created',pa.bool_()),pa.field('item_dates_comparable',pa.bool_())]
    return pa.schema(fields)


def user(uid,city):
    return dict(id=uid,first_name=f'Test{uid}',last_name='Synthetic',email=f'user{uid}@example.invalid',age=30,gender='F',state='Test',street_address='Synthetic only',postal_code='00100',city=city,country='Test',latitude=0.,longitude=0.,traffic_source='Organic',created_at=stamp('2026-01-01'),city_clean=None if city=='null' else city,city_missing_token=city=='null')


def add_sale(d,oid,uid,when):
    dt=stamp(when)
    d['orders'].append(dict(order_id=oid,user_id=uid,status='Processing',gender='F',created_at=dt,returned_at=None,shipped_at=None,delivered_at=None,num_of_item=1))
    d['inventory_items'].append(dict(id=oid,product_id=1,created_at=stamp('2025-12-01'),sold_at=dt,cost=Decimal('4.123456'),product_category='Test',product_name='Synthetic product',product_brand='Test',product_retail_price=Decimal('12.000000'),product_department='Test',product_sku='TEST-1',product_distribution_center_id=1))
    d['order_items'].append(dict(id=oid,order_id=oid,user_id=uid,product_id=1,inventory_item_id=oid,status='Processing',created_at=dt,shipped_at=None,delivered_at=None,returned_at=None,sale_price=Decimal('10.123456'),item_shipped_before_created=None,item_dates_comparable=False))


def fixtures():
    d={t:[] for t in CONTRACT}
    d['distribution_centers']=[dict(id=1,name='Synthetic DC',latitude=0.,longitude=0.)]
    d['products']=[dict(id=1,cost=Decimal('4.123456'),category='Test',name='Synthetic product',brand='Test',retail_price=Decimal('12.000000'),department='Test',sku='TEST-1',distribution_center_id=1)]
    d['users']=[user(1,'Alpha'),user(2,'null'),user(3,'Gamma')]
    for uid in (1,2,3): add_sale(d,uid,uid,'2026-01-15')
    d['events']=[dict(id=1,user_id=1,sequence_number=1,session_id='synthetic-session',created_at=stamp('2026-01-15'),ip_address='192.0.2.1',city='Alpha',state='Test',postal_code='00100',browser='Test',traffic_source='Organic',uri='/synthetic',event_type='home',city_clean='Alpha',city_missing_token=False)]
    changed=copy.deepcopy(d)
    changed['users'][0]=user(1,'null')
    changed['users'][1]=user(2,'Beta')
    changed['users'].append(user(4,'Delta'))
    add_sale(changed,4,1,'2026-02-01')
    add_sale(changed,5,4,'2026-02-02')
    dup=copy.deepcopy(changed);dup['products'].append(copy.deepcopy(dup['products'][0]))
    fk=copy.deepcopy(changed);fk['orders'][0]['user_id']=999
    late=copy.deepcopy(changed);late['users'][2]['age']=31
    return {'bootstrap':d,'changes':changed,'unchanged':copy.deepcopy(changed),'bad_pk':dup,'bad_fk':fk,'bad_money':copy.deepcopy(changed),'late_retry':late}


def quote(v):
    return 'NULL' if v is None else "'"+str(v).replace("'","''")+"'"


def assertion(condition,label):
    return f'CALL etl.scd_test_assert({quote(condition)},{quote(label)});\n'


def write(name,s):
    (OUT/'sql'/name).write_text(s,encoding='utf-8')


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'sql').mkdir(exist_ok=True)
    table_names=[]
    for filename in ('00_control.sql','01_staging.sql','02_warehouse.sql'):
        table_names += re.findall(r'CREATE TABLE\s+([\w.]+)',(ROOT/'code/sql'/filename).read_text())
    protected=[t for t in table_names if t!='etl.batch_attempts']
    source=(ROOT/'outputs/aws/scd-test-install/04_install_procedures.sql').read_text()
    marker='    INSERT INTO dw.fact_sales SELECT * FROM tmp_fact_work;'
    assert source.count(marker)==1
    clone=source[source.index('CREATE OR REPLACE PROCEDURE etl.load_batch('):].replace('PROCEDURE etl.load_batch(', 'PROCEDURE etl.load_batch_test_fail_after_publish(',1)
    clone=clone.replace(marker,marker+"\n    RAISE EXCEPTION 'SCD_TEST_INJECTED_AFTER_FACT_WRITE';")
    helper="""-- Test-only helpers. Run CREATE PROCEDURE blocks separately, then CALLs.
CREATE OR REPLACE PROCEDURE etl.scd_test_assert(p_query VARCHAR(65535),p_label VARCHAR(1024))
AS $$ DECLARE v_ok BOOLEAN; BEGIN
 IF current_database()<>'thelook_scd_test' THEN RAISE EXCEPTION 'Wrong test database'; END IF;
 EXECUTE p_query INTO v_ok;
 IF v_ok IS NULL OR NOT v_ok THEN RAISE EXCEPTION 'TEST_FAILED: %',p_label; END IF;
 RAISE INFO 'PASS: %',p_label;
END; $$ LANGUAGE plpgsql;
CALL etl.assert_scd_test_database();
"""
    helper += ''.join(assertion(f'SELECT COUNT(*)=0 FROM {t}',f'empty {t}') for t in table_names)
    write('00_helpers_and_empty_gate.sql',helper)
    write('01_install_test_only_failure_procedure.sql',clone)
    write('repair_50_atomic_handlers.sql', '-- Run each complete CREATE PROCEDURE block separately in thelook_scd_test. No load or table reset.\n'+source+'\n'+clone)
    package={'target_database':'thelook_scd_test','s3_prefix':BASE,'synthetic':True,'loader_sha256':hashlib.sha256(source.encode()).hexdigest(),'injection':'Clone only: RAISE immediately after fact insert; production load_batch unchanged','cases':{}}
    data=fixtures()
    for label,d in data.items():
        info={'tables':{},'money':{},'synthetic':True}
        for t,rows in d.items():
            p=OUT/'s3'/label/t/'data.parquet';p.parent.mkdir(parents=True,exist_ok=True)
            typed=pa.Table.from_pylist(rows,schema=schema(t))
            pq.write_table(typed,p,compression='snappy',version='1.0',coerce_timestamps='us')
            assert pq.read_table(p).equals(typed), (label,t)
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            manifest={'entries':[{'url':f'{BASE}/{label}/{t}/data.parquet','mandatory':True,'meta':{'content_length':p.stat().st_size}}]}
            mp=OUT/'s3'/label/'manifests'/f'{t}.json';mp.parent.mkdir(exist_ok=True)
            mp.write_text(json.dumps(manifest,indent=2))
            info['tables'][t]={'rows':len(rows),'sha256':digest,'manifest':f'{BASE}/{label}/manifests/{t}.json','city':sum(r['city_missing_token'] for r in rows) if t in ('users','events') else None,'flags':0 if t=='order_items' else None,'comparable':0 if t=='order_items' else None}
        for t,c in MONEY:
            info['money'][f'{t}.{c}']=str(sum((r[c] for r in d[t]),Decimal('0.000000')))
        if label=='bad_money': info['money']['order_items.sale_price']=str(Decimal(info['money']['order_items.sale_price'])+1)
        info['package_hash']=hashlib.sha256(json.dumps(info,sort_keys=True).encode()).hexdigest()
        package['cases'][label]=info

    def controls(label):
        info=package['cases'][label]
        s="""CALL etl.assert_scd_test_database();
SET timezone TO 'UTC';
CREATE TEMP TABLE IF NOT EXISTS expected_inputs (table_name VARCHAR(64) NOT NULL,expected_rows BIGINT NOT NULL,manifest_url VARCHAR(2048) NOT NULL,file_sha256 VARCHAR(64) NOT NULL,expected_city_tokens BIGINT,expected_date_flags BIGINT,expected_comparable BIGINT);
CREATE TEMP TABLE IF NOT EXISTS expected_money (table_name VARCHAR(64) NOT NULL,column_name VARCHAR(64) NOT NULL,expected_sum DECIMAL(38,6) NOT NULL);
DELETE FROM expected_inputs;
DELETE FROM expected_money;
"""
        for t,v in info['tables'].items():
            vals=[t,v['rows'],v['manifest'],v['sha256'],v['city'],v['flags'],v['comparable']]
            s+='INSERT INTO expected_inputs VALUES ('+','.join(quote(v) for v in vals)+');\n'
        for key,val in info['money'].items():
            t,c=key.split('.');s+=f'INSERT INTO expected_money VALUES ({quote(t)},{quote(c)},{quote(val)});\n'
        return s

    def call(label,observed,proc='load_batch'):
        return f"CALL etl.{proc}('scd_v1_{label}','{package['cases'][label]['package_hash']}','{observed}'::TIMESTAMPTZ,'{ROLE}','dw-v1','provisional-v1');\n"

    def snapshot(tag):
        s='CALL etl.assert_scd_test_database();\n'
        for t in protected:
            s+=f'CREATE TEMP TABLE snap_{tag}_{t.replace(".","_")} AS SELECT * FROM {t};\n'
        s+=f'CREATE TEMP TABLE attempts_{tag} AS SELECT COUNT(*) AS n FROM etl.batch_attempts;\n'
        return s

    def unchanged(tag):
        s=''
        for t in protected:
            snap=f'snap_{tag}_{t.replace(".","_")}'
            condition=f'SELECT (SELECT COUNT(*) FROM {t})=(SELECT COUNT(*) FROM {snap}) AND NOT EXISTS(SELECT * FROM {t} EXCEPT SELECT * FROM {snap}) AND NOT EXISTS(SELECT * FROM {snap} EXCEPT SELECT * FROM {t})'
            s+=assertion(condition,f'{tag}: unchanged {t}')
        return s

    def success(label,total,current,facts,ledger):
        s=assertion(f"SELECT COUNT(*)=1 FROM etl.batch_ledger WHERE batch_id='scd_v1_{label}' AND status='SUCCEEDED'",label+' ledger')
        for t,n in [('dw.dim_users',total),('dw.fact_sales',facts),('etl.batch_ledger',ledger)]:
            s+=assertion(f'SELECT COUNT(*)={n} FROM {t}',label+' '+t)
        s+=assertion(f'SELECT COUNT(*)={current} FROM dw.dim_users WHERE is_current',label+' current users')
        s+=assertion('SELECT NOT EXISTS(SELECT user_id FROM dw.dim_users GROUP BY user_id HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END)<>1)','one current per user')
        s+=assertion('SELECT NOT EXISTS(SELECT 1 FROM dw.dim_users a JOIN dw.dim_users b ON a.user_id=b.user_id AND a.user_key<b.user_key WHERE (a.valid_from IS NULL OR b.valid_to IS NULL OR a.valid_from<b.valid_to) AND (b.valid_from IS NULL OR a.valid_to IS NULL OR b.valid_from<a.valid_to))','no overlapping user history')
        s+=assertion('SELECT (SELECT SUM(sale_price) FROM dw.fact_sales)=(SELECT SUM(sale_price) FROM stg.order_items)','fact money matches staging')
        s+="SELECT user_id,user_key,city,age,version_origin,valid_from,valid_to,is_current FROM dw.dim_users ORDER BY user_id,observed_at;\n"
        return s

    write('10_bootstrap.sql',controls('bootstrap')+call('bootstrap','2026-01-01T00:00:00Z')+success('bootstrap',3,3,3,1)+assertion("SELECT COUNT(*)=3 FROM dw.dim_users WHERE version_origin='BOOTSTRAP_SNAPSHOT' AND valid_from IS NULL",'bootstrap origin')+'CREATE TEMP TABLE original_users AS SELECT * FROM dw.dim_users;\n')
    # Recovery after the original helper truncated a >256-character query argument.
    recovery=helper[:helper.index('CALL etl.assert_scd_test_database();')]
    recovery+='CALL etl.assert_scd_test_database();\n'
    recovery+=success('bootstrap',3,3,3,1)
    recovery+=assertion("SELECT COUNT(*)=1 FROM etl.batch_attempts WHERE batch_id='scd_v1_bootstrap' AND status='SUCCEEDED'",'bootstrap succeeded once')
    recovery+=assertion("SELECT COUNT(*)=1 FROM etl.batch_attempts",'no extra test attempts before recovery')
    recovery+=assertion("SELECT COUNT(*)=3 FROM dw.dim_users WHERE version_origin='BOOTSTRAP_SNAPSHOT' AND valid_from IS NULL",'bootstrap origin')
    recovery+='-- Run once in this session. If original_users already exists, stop and verify it; do not overwrite it.\n'
    recovery+='CREATE TEMP TABLE original_users AS SELECT * FROM dw.dim_users;\n'
    recovery+=assertion('SELECT (SELECT COUNT(*) FROM original_users)=3 AND NOT EXISTS(SELECT * FROM original_users EXCEPT SELECT * FROM dw.dim_users) AND NOT EXISTS(SELECT * FROM dw.dim_users EXCEPT SELECT * FROM original_users)','original_users snapshot ready')
    write('repair_bootstrap_assert_only.sql',recovery)
    changechecks=success('changes',6,4,5,2)
    changechecks+=assertion("SELECT COUNT(*)=2 FROM dw.dim_users WHERE user_id IN (1,2) AND NOT is_current AND valid_to='2026-02-01'::TIMESTAMPTZ",'closed versions at boundary')
    changechecks+=assertion("SELECT COUNT(*)=2 FROM dw.dim_users WHERE user_id IN (1,2) AND is_current AND version_origin='OBSERVED_CHANGE' AND valid_from='2026-02-01'::TIMESTAMPTZ",'new change versions')
    changechecks+=assertion("SELECT COUNT(*)=1 FROM dw.dim_users WHERE user_id=1 AND is_current AND city IS NULL AND city_missing_token",'value to NULL')
    changechecks+=assertion("SELECT COUNT(*)=1 FROM dw.dim_users WHERE user_id=2 AND is_current AND city='Beta' AND NOT city_missing_token",'NULL to value')
    changechecks+=assertion("SELECT COUNT(*)=1 FROM dw.dim_users WHERE user_id=4 AND is_current AND valid_from IS NULL AND version_origin='OBSERVED_NEW'",'new user')
    changechecks+=assertion('SELECT NOT EXISTS(SELECT * FROM dw.dim_users WHERE user_id=3 EXCEPT SELECT * FROM original_users WHERE user_id=3) AND NOT EXISTS(SELECT * FROM original_users WHERE user_id=3 EXCEPT SELECT * FROM dw.dim_users WHERE user_id=3)','unchanged user key and attributes')
    changechecks+=assertion('SELECT COUNT(*)=3 FROM dw.fact_sales f JOIN original_users u ON f.user_key=u.user_key WHERE f.order_item_id IN (1,2,3)','old facts retain historical keys')
    changechecks+=assertion("SELECT COUNT(*)=1 FROM dw.fact_sales f JOIN dw.dim_users u ON f.user_key=u.user_key WHERE f.order_item_id=4 AND u.user_id=1 AND u.valid_from='2026-02-01'::TIMESTAMPTZ",'boundary fact uses new key')
    write('20_changes.sql',controls('changes')+call('changes','2026-02-01T00:00:00Z')+changechecks+'CREATE TEMP TABLE changed_users AS SELECT * FROM dw.dim_users;\n')
    write('30_unchanged_new_batch.sql',controls('unchanged')+call('unchanged','2026-03-01T00:00:00Z')+success('unchanged',6,4,5,3)+assertion('SELECT NOT EXISTS(SELECT * FROM dw.dim_users EXCEPT SELECT * FROM changed_users) AND NOT EXISTS(SELECT * FROM changed_users EXCEPT SELECT * FROM dw.dim_users)','no versions on unchanged snapshot'))
    write('40_replay.sql',snapshot('replay')+controls('unchanged')+call('unchanged','2026-03-01T00:00:00Z')+unchanged('replay')+assertion("SELECT (SELECT COUNT(*) FROM etl.batch_attempts)=(SELECT n+1 FROM attempts_replay) AND (SELECT COUNT(*) FROM etl.batch_attempts WHERE batch_id='scd_v1_unchanged' AND status='NO_OP')=1",'one new NO_OP audit'))
    for number,label,message in [(50,'bad_pk','products: invalid primary key'),(60,'bad_fk','orders.user_id: orphan key'),(70,'bad_money','Staging monetary reconciliation failed'),(80,'late_retry','SCD_TEST_INJECTED_AFTER_FACT_WRITE')]:
        write(f'{number}a_prepare_{label}.sql',snapshot(label)+controls(label))
        proc='load_batch_test_fail_after_publish' if label=='late_retry' else 'load_batch'
        write(f'{number}b_EXPECT_ERROR_{label}.sql',f'-- Expected error contains: {message}. Run this CALL ALONE, autocommit ON.\n'+call(label,'2026-04-01T00:00:00Z',proc))
        checks=unchanged(label)+assertion(f"SELECT (SELECT COUNT(*) FROM etl.batch_attempts)=(SELECT n+1 FROM attempts_{label}) AND (SELECT COUNT(*) FROM etl.batch_attempts WHERE batch_id='scd_v1_{label}' AND status='FAILED' AND detail LIKE '%{message}%')=1",label+' FAILED audit matches expected reason')
        write(f'{number}c_verify_rollback_{label}.sql',checks)
    write('90_retry_real_loader.sql',controls('late_retry')+call('late_retry','2026-04-01T00:00:00Z')+success('late_retry',7,4,5,4)+assertion("SELECT COUNT(*)=1 FROM dw.dim_users WHERE user_id=3 AND is_current AND age=31 AND version_origin='OBSERVED_CHANGE' AND valid_from='2026-04-01'::TIMESTAMPTZ",'retry publishes one changed user version')+assertion("SELECT COUNT(*)=1 FROM etl.batch_attempts WHERE batch_id='scd_v1_late_retry' AND status='SUCCEEDED'",'retry success once'))
    summary="CALL etl.assert_scd_test_database();\n"
    summary+=assertion("SELECT COUNT(*)=9 AND SUM(CASE WHEN status='SUCCEEDED' THEN 1 ELSE 0 END)=4 AND SUM(CASE WHEN status='NO_OP' THEN 1 ELSE 0 END)=1 AND SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END)=4 FROM etl.batch_attempts",'final audit totals')
    summary+=assertion("SELECT COUNT(*)=4 FROM etl.batch_ledger WHERE status='SUCCEEDED'",'four published test batches')
    summary+=assertion('SELECT COUNT(*)=7 AND SUM(CASE WHEN is_current THEN 1 ELSE 0 END)=4 FROM dw.dim_users','final user history')
    summary+="SELECT batch_id,status,detail FROM etl.batch_attempts ORDER BY attempted_at;\nSELECT batch_id,status,fact_rows FROM etl.batch_ledger ORDER BY observed_at;\nSELECT user_id,COUNT(*) AS versions,SUM(CASE WHEN is_current THEN 1 ELSE 0 END) AS current_versions FROM dw.dim_users GROUP BY user_id ORDER BY user_id;\n"
    write('99_summary.sql',summary)
    (OUT/'package.json').write_text(json.dumps(package,indent=2),encoding='utf-8')
    (OUT/'loader_installed_reference.sql').write_text(source,encoding='utf-8')
    # Copies are included for review only, never auto-install the existing schemas again.
    (OUT/'README_TH.md').write_text(README,encoding='utf-8')
    (OUT/'upload_fixtures.py').write_text((ROOT/'code/upload_scd_fixtures.py').read_text(encoding='utf-8'),encoding='utf-8')
    hashes={str(p.relative_to(OUT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file() and p.name!='sha256.json'}
    (OUT/'sha256.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    with zipfile.ZipFile(OUT.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():z.write(p,str(p.relative_to(OUT)))
    print(f'Built {OUT.with_suffix(".zip")} ({len(data)*7} Parquet files). AWS tests NOT RUN.')


README = '''# SCD / rollback fixtures v1 — synthetic only
ฐานที่อนุญาต: thelook_scd_test ซึ่งติดตั้งตารางว่างและ loader แล้ว
ชุดนี้สร้างในเครื่อง ไม่ได้ upload หรือ execute บน AWS
## Upload ใน CloudShell
Upload zip แล้วแตกในโฟลเดอร์ใหม่:
```bash
mkdir scd-test-fixtures-v1
unzip scd-test-fixtures-v1.zip -d scd-test-fixtures-v1
cd scd-test-fixtures-v1
python3 upload_fixtures.py
```
Uploader ตรวจ account และ local SHA แล้ว upload เฉพาะ s3/ ไป prefix ทดสอบ และอ่านกลับตรวจ SHA ไม่ execute SQL
## Query Editor v2
เลือก thelook_scd_test ทุกครั้ง ใช้แท็บ/session เดียวตลอดชุดเพราะมี TEMP snapshots อย่าเปลี่ยน connection หรือเปิด session ใหม่ระหว่างไฟล์
Autocommit ON; ไม่ครอบ BEGIN / COMMIT. รัน statements ต่อกันใน session เดิม; หากเครื่องมือรันหลาย statements เป็น transaction เดียว ให้รันทีละ statement โดย CREATE PROCEDURE ต้องเป็นบล็อกครบ $$
00_helpers_and_empty_gate: รัน helper CREATE PROCEDURE ทั้งบล็อก จากนั้น CALL ทีละคำสั่ง ต้อง PASS ตารางว่าง16ตาราง
01_install_test_only_failure_procedure: ติดตั้งสำเนา loader ที่มีจุดจำลอง error หลัง INSERT facts ตัว etl.load_batch จริงไม่ถูกแก้
10_bootstrap → 20_changes → 30_unchanged_new_batch → 40_replay ตามลำดับ ทุก assertion ต้อง PASS
50a → 50b → 50c; ทำแบบเดียวกันกับ 60,70,80
ไฟล์ b ชื่อ EXPECT_ERROR ต้องรัน CALL แยกเดี่ยว คาด error ตาม comment เท่านั้น แล้วรัน c ใน session เดิมเพื่อตรวจ rollback/audit
ถ้า CALL ไม่ error หรือ error ข้อความอื่น เช่น AccessDenied/COPY/schema ให้หยุด ไม่ถือว่าผ่าน negative test
หลัง negative tests ทั้ง4ผ่าน: 90_retry_real_loader → 99_summary
ห้ามกด Run ทั้งชุด zip ครั้งเดียว; ห้ามรันขั้นที่ผ่านแล้วซ้ำเอง เพราะ expected attempt counts และ TEMP snapshots จะเปลี่ยน
ถ้า session หลุด/ผลผิด ให้เก็บ error และส่งกลับ ห้าม DROP/ล้างฐานเพื่อเริ่มใหม่โดยไม่ตรวจสาเหตุ
## Expected
10: users3/current3/facts3/ledger1
20: users6/current4/facts5/ledger2, users1/2 เปลี่ยน city ข้าม NULL, user4ใหม่, user3คงเดิม
30: users6/current4/facts5/ledger3; ทุก user row คงเดิม
40: NO_OP และ15ตารางคงเดิม (7stg+5dw+3etl); auditเพิ่ม1
50/60/70: duplicatePK/badFK/money mismatch ต้อง FAILED และ15ตารางคงเดิม
80: สำเนา loader เขียน SCD และ facts แล้ว raise;15ตาราง rollback, FAILED audit
90: retry batchเดียวกับ80ด้วย loaderจริง: users7/current4/facts5/ledger4
99: audit9แถว (SUCCEEDED4, NO_OP1, FAILED4); user versions 1=2,2=2,3=2,4=1
Observation timestamps ปี2026ใน fixtures เป็นเวลาสมมติ ไม่เกี่ยวกับ observation time ของข้อมูลจริง
file_sha256 เป็น SHA256 ของ Parquet ไฟล์เดียวต่อตาราง ส่วน package_hash คือ SHA256 ของ metadata fixture ก่อนเพิ่ม field package_hash
assertions เทียบค่าทุกคอลัมน์สองทิศทางร่วมกับ counts; baseline PKs ของตารางที่ตรวจมี unique key ส่วน batch_checks มีหนึ่งแถวต่อ batch/check
ตรวจทั้ง history overlap, historical fact key, boundary fact key, known flags, exact money และ audit
Catalog ไม่เกี่ยวกับ COPY test นี้ ไม่รัน Glue ETL/crawlerใหม่
หลังชุดผ่าน ยังไม่ครอบคลุม cancellation/concurrency และยังไม่ใช่ production deployment
อ้างอิง transaction/exception semantics:
https://docs.aws.amazon.com/redshift/latest/dg/stored-procedure-transaction-management.html
https://docs.aws.amazon.com/redshift/latest/dg/stored-procedure-trapping-errors.html
'''

if __name__=='__main__':
    build()
