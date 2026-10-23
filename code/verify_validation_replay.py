"""CloudShell read-only S3 gate; emit NO_OP-only SQL, never execute SQL."""
import hashlib
import json
import tempfile
from pathlib import Path

from finalize_glue_warehouse_package import finalize, digest

BATCH='20261023T151247118967Z_f8a02155'
HASH='d897e3ee9663b725c6a226b99712094cc5d536346c9577fe14a634e3cc2ac7d7'
OBS='2026-10-22T18:59:01.935624+00:00'
ROLE='arn:aws:iam::006816724683:role/LabRole'


def replay_sql(package,before,after):
    if package['batch_id']!=BATCH or package['package_hash']!=HASH:
        raise ValueError('Verified package differs from approved replay identity')
    if package['target_database']!='thelook_glue_validation' or package['observed_at']!=OBS:
        raise ValueError('Database/observation differs')
    raw={k:v for k,v in package.items() if k!='package_hash'}
    if digest(raw)!=HASH: raise ValueError('Package content digest mismatch')
    # Lock and existence gate are in the SAME atomic CALL as the loader.
    gate=f"""-- Install this entire block; then run remaining statements separately in one session.
CREATE OR REPLACE PROCEDURE etl.replay_approved_glue_batch()
AS $$
DECLARE v_n BIGINT; v_before BIGINT; v_after BIGINT;
BEGIN
 CALL etl.assert_glue_validation_database();
 LOCK TABLE etl.batch_ledger;
 SELECT COUNT(*) INTO v_n FROM etl.batch_ledger WHERE batch_id='{BATCH}';
 IF v_n<>1 THEN RAISE EXCEPTION 'Replay requires exactly one existing batch; loading new data is prohibited'; END IF;
 SELECT COUNT(*) INTO v_n FROM etl.batch_ledger
 WHERE batch_id='{BATCH}' AND package_hash='{HASH}' AND observed_at='{OBS}'::TIMESTAMPTZ
 AND status='SUCCEEDED' AND schema_version='dw-v1' AND rule_version='provisional-v1';
 IF v_n<>1 THEN RAISE EXCEPTION 'Replay ledger identity mismatch'; END IF;
 SELECT COUNT(*) INTO v_before FROM etl.batch_attempts WHERE batch_id='{BATCH}' AND status='NO_OP';
 CALL etl.load_batch('{BATCH}','{HASH}','{OBS}'::TIMESTAMPTZ,'{ROLE}','dw-v1','provisional-v1');
 SELECT COUNT(*) INTO v_after FROM etl.batch_attempts WHERE batch_id='{BATCH}' AND status='NO_OP';
 IF v_after<>v_before+1 THEN RAISE EXCEPTION 'Replay did not produce exactly one NO_OP'; END IF;
END;
$$ LANGUAGE plpgsql;
"""
    return gate+'\n'+before+'\nCALL etl.replay_approved_glue_batch();\n'+after


def main():
    import boto3
    root=Path(__file__).resolve().parent
    output=root/'verified_replay.sql'
    if output.exists(): raise RuntimeError('verified_replay.sql already exists; preserve previous results and use a fresh extracted directory')
    hashes=json.loads((root/'bundle_sha256.json').read_text())
    for name,expected in hashes.items():
        p=(root/name).resolve()
        if not p.is_relative_to(root.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
            raise RuntimeError('Bundle checksum mismatch: '+name)
    session=boto3.Session(region_name='us-east-1')
    account=session.client('sts').get_caller_identity()['Account']
    with tempfile.TemporaryDirectory(prefix='thelook-replay-') as tmp:
        package,_=finalize(root,Path(tmp)/'verified',session.client('s3'),account)
        sql=replay_sql(package,(root/'noop_before.sql').read_text(),(root/'noop_after.sql').read_text())
    output.write_text(sql,encoding='utf-8')
    result={'status':'S3_GATE_PASSED_SQL_NOT_EXECUTED','batch_id':BATCH,'database':'thelook_glue_validation','package_hash':HASH,'sql_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'expected_result':'NO_OP'}
    (root/'replay_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    print('DOWNLOAD='+str(output))
    print('No AWS writes or Redshift SQL executed. Run only the generated verified_replay.sql in Query Editor.')


if __name__=='__main__':main()
