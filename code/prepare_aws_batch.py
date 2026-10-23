"""Prepare SQL and S3 manifests locally. Does not connect to or modify AWS."""
import argparse
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def digest_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def sql_literal(value):
    return "'"+str(value).replace("'","''")+"'"

def prepare(config_path,output_path):
    cfg=json.loads(Path(config_path).read_text(encoding='utf-8'))
    bucket=cfg['bucket']; prefix=cfg['prefix'].strip('/'); role=cfg['iam_role']
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',bucket) or 'replace' in bucket.lower():
        raise ValueError('Set a real S3 bucket name in config (availability not checked locally).')
    if not re.fullmatch(r'[A-Za-z0-9/_=-]+',prefix): raise ValueError('Use a nonempty S3 prefix with letters/numbers / _ = - only.')
    if not re.fullmatch(r'arn:aws:iam::\d{12}:role/[A-Za-z0-9+=,.@_/-]+',role) or 'REPLACE' in role:
        raise ValueError('Set the actual Redshift IAM role ARN; do not put access keys in this file.')
    folder=(ROOT/cfg['curated_dir']).resolve()
    report=json.loads((folder/'validation_report.json').read_text(encoding='utf-8'))
    if report['status']!='PASS_WITH_KNOWN_ISSUES' or any(c['status']!='PASS' for c in report['checks']):
        raise ValueError('Only an accepted curated batch can be packaged.')
    if any(i['status']!='KNOWN_ISSUE' for i in report['known_issues']): raise ValueError('Known issue drift requires review first.')
    expected_tables=json.loads((ROOT/'code/curated_schema.json').read_text(encoding='utf-8'))['tables']
    if set(report['tables'])!=set(expected_tables): raise ValueError('Expected all seven curated tables.')
    if report['schema_version']!='curated-v1' or report['rule_version']!='provisional-v1':
        raise ValueError('Unsupported curated/rule version.')
    # A deployment may use a different S3 batch ID for the same validated files.
    batch=cfg.get('batch_id',report['batch_id'])
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',batch): raise ValueError('Invalid batch ID')
    observed=cfg['observed_at']
    if datetime.fromisoformat(observed).tzinfo is None: raise ValueError('observed_at must include timezone.')
    s3root=f's3://{bucket}/{prefix}/{batch}'
    items=[]; manifests={}; money=[]
    known={i['issue_id']:i for i in report['known_issues']}
    for name,info in report['tables'].items():
        file=folder/f'{name}.parquet'
        if info['quarantined_rows']!=0 or info['raw_rows']!=info['curated_rows']: raise ValueError('Rejected/partial data cannot be published automatically.')
        city=known['CITY-01-'+name]['actual_rows'] if name in ('users','events') else None
        dates=known['DATE-01-items'] if name=='order_items' else None
        entry={'table_name':name,'local_file':str(file),'rows':info['curated_rows'],'sha256':digest_file(file),
               'content_length':file.stat().st_size,'data_url':f'{s3root}/{name}/data.parquet',
               'manifest_url':f'{s3root}/_manifests/{name}.json','city_tokens':city,
               'date_flags':dates['actual_rows'] if dates else None,'comparable':dates['comparable_rows'] if dates else None}
        items.append(entry)
        manifests[name]={'entries':[{'url':entry['data_url'],'mandatory':True,'meta':{'content_length':entry['content_length']}}]}
        for column,metrics in info['money'].items():
            if Decimal(metrics['expected_curated_sum'])!=Decimal(metrics['readback_sum']): raise ValueError('Money report mismatch')
            money.append((name,column,metrics['readback_sum']))
    # Absolute paths do not participate in input identity; files can be relocated without changing a batch.
    package={'batch_id':batch,'observed_at':observed,'dw_schema':'dw-v1','curated_schema':'curated-v1',
             'rule_version':'provisional-v1','s3_root':s3root,'iam_role':role,
             'files':[{k:v for k,v in i.items() if k!='local_file'} for i in items], 'money':money}
    if batch != report['batch_id']:
        package['source_curated_batch_id']=report['batch_id']
    package_hash=hashlib.sha256(json.dumps(package,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    package['package_hash']=package_hash
    out=Path(output_path).resolve()
    out.mkdir(parents=True,exist_ok=False)
    (out/'manifests').mkdir()
    for name,manifest in manifests.items():
        (out/'manifests'/f'{name}.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (out/'package.json').write_text(json.dumps(package,indent=2)+'\n',encoding='utf-8')
    sql=["-- Run this whole file in ONE persistent session, autocommit ON, after installing sql/00..03.",
         "-- Do not wrap CALL in an explicit BEGIN. This does not upload files.",
         "SET timezone TO 'UTC';",
         'DROP TABLE IF EXISTS expected_inputs;',
         'CREATE TEMP TABLE expected_inputs (table_name VARCHAR(64) NOT NULL,expected_rows BIGINT NOT NULL,manifest_url VARCHAR(2048) NOT NULL,file_sha256 VARCHAR(64) NOT NULL,expected_city_tokens BIGINT,expected_date_flags BIGINT,expected_comparable BIGINT);',
         'DROP TABLE IF EXISTS expected_money;',
         'CREATE TEMP TABLE expected_money (table_name VARCHAR(64) NOT NULL,column_name VARCHAR(64) NOT NULL,expected_sum DECIMAL(38,6) NOT NULL);']
    for i in items:
        optional=['NULL' if i[k] is None else str(i[k]) for k in ['city_tokens','date_flags','comparable']]
        sql.append('INSERT INTO expected_inputs VALUES ('+', '.join([sql_literal(i['table_name']),str(i['rows']),sql_literal(i['manifest_url']),sql_literal(i['sha256'])]+optional)+');')
    for table,column,total in money:
        sql.append(f'INSERT INTO expected_money VALUES ({sql_literal(table)}, {sql_literal(column)}, {sql_literal(total)}::DECIMAL(38,6));')
    sql.append('CALL etl.load_batch('+', '.join([sql_literal(batch),sql_literal(package_hash),sql_literal(observed)+'::TIMESTAMPTZ',sql_literal(role),"'dw-v1'","'provisional-v1'"])+');')
    sql += [f'SELECT * FROM etl.batch_ledger WHERE batch_id={sql_literal(batch)};',f'SELECT * FROM etl.batch_checks WHERE batch_id={sql_literal(batch)} ORDER BY check_name;']
    (out/'run_batch.sql').write_text('\n'.join(sql)+'\n',encoding='utf-8')
    def ps(value): return "'"+str(value).replace("'","''")+"'"
    uploads=['# Review paths/account/region before running. Generated only; no uploads have been performed.',
             "$ErrorActionPreference = 'Stop'"]
    for i in items:
        uploads += [f"aws s3 cp {ps(i['local_file'])} {ps(i['data_url'])} --region us-east-1 --only-show-errors",
                    "if ($LASTEXITCODE -ne 0) { throw 'Data upload failed' }",
                    f"aws s3 cp {ps(out/'manifests'/(i['table_name']+'.json'))} {ps(i['manifest_url'])} --region us-east-1 --only-show-errors",
                    "if ($LASTEXITCODE -ne 0) { throw 'Manifest upload failed' }"]
    (out/'upload.ps1').write_text('\n'.join(uploads)+'\n',encoding='utf-8')
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',required=True); p.add_argument('--output',required=True)
    args=p.parse_args(); print(prepare(args.config,args.output))
