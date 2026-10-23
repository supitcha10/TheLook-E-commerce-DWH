"""Manual CloudShell runner: S3 verification -> Data API replay -> PASS checks.
Default verify mode requires no running cluster. Never resumes/pauses or schedules.
"""
import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

from finalize_glue_warehouse_package import finalize
from verify_validation_replay import replay_sql, BATCH, HASH

CLUSTER='thelook-redshift-cluster-1'
DATABASE='thelook_glue_validation'
DBUSER='thelook-admin'


class DataSession:
    def __init__(self, client, save, run_id, timeout=600):
        self.client=client;self.save=save;self.run_id=run_id
        self.timeout=timeout;self.session=None;self.index=0

    def execute(self,sql):
        self.index+=1
        args={'Sql':sql,'SessionKeepAliveSeconds':600,
              'ClientToken':hashlib.sha256(f'{self.run_id}:{self.index}'.encode()).hexdigest()}
        if self.session: args['SessionId']=self.session
        else: args.update(ClusterIdentifier=CLUSTER,Database=DATABASE,DbUser=DBUSER)
        result=self.client.execute_statement(**args)
        sid=result['Id'];self.session=result.get('SessionId',self.session)
        self.save({'index':self.index,'statement_id':sid,'sql_sha256':hashlib.sha256(sql.encode()).hexdigest(),'status':'SUBMITTED'})
        deadline=time.monotonic()+self.timeout
        while True:
            state=self.client.describe_statement(Id=sid)
            self.session=state.get('SessionId',self.session)
            status=state['Status']
            if status in ('FINISHED','FAILED','ABORTED'):break
            if time.monotonic()>deadline:
                raise RuntimeError(f'Statement outcome uncertain; inspect {sid} before any retry. Runner stopped, query may still be running.')
            time.sleep(2)
        if status!='FINISHED':
            self.save({'index':self.index,'statement_id':sid,'status':status,'error':state.get('Error')})
            raise RuntimeError(f"Statement {sid} {status}: {state.get('Error','')}")
        if not self.session:raise RuntimeError('Data API did not return SessionId; stop before replay')
        rows=[];columns=[]
        if state.get('HasResultSet'):
            kwargs={'Id':sid}
            while True:
                page=self.client.get_statement_result(**kwargs)
                columns=[c['name'] for c in page['ColumnMetadata']]
                for row in page['Records']:
                    rows.append([None if cell.get('isNull') else next(iter(cell.values())) for cell in row])
                token=page.get('NextToken')
                if not token:break
                kwargs={'Id':sid,'NextToken':token}
        self.save({'index':self.index,'statement_id':sid,'status':'FINISHED','columns':columns,'rows':rows})
        return columns,rows


def check_results(columns,rows):
    if columns==['table_name','status']:
        expected={'dw.dim_date','dw.dim_users','dw.dim_products','dw.dim_distribution_centers','dw.fact_sales','etl.batch_ledger','etl.batch_inputs','etl.batch_checks'}
        if len(rows)!=8 or {r[0] for r in rows}!=expected or any(r[1]!='PASS' for r in rows):
            raise RuntimeError('Eight-table unchanged check failed')
        return 'tables'
    if columns==['new_no_op_attempt']:
        if rows!=[['PASS']]:raise RuntimeError('NO_OP increment check failed')
        return 'audit'
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['verify','run'],default='verify')
    args=parser.parse_args()
    import boto3
    root=Path(__file__).resolve().parent
    for name,expected in json.loads((root/'bundle_sha256.json').read_text()).items():
        p=(root/name).resolve()
        if not p.is_relative_to(root.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
            raise RuntimeError('Bundle integrity failure: '+name)
    run_id=str(uuid.uuid4())
    out=root/'runs'/run_id;out.mkdir(parents=True)
    print('RUN_DIRECTORY='+str(out),flush=True)
    report={'run_id':run_id,'mode':args.mode,'batch_id':BATCH,'package_hash':HASH,'database':DATABASE,'status':'STARTED'}
    def save_report(): (out/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    def journal(event):
        with (out/'statements.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
    save_report()
    try:
        session=boto3.Session(region_name='us-east-1')
        account=session.client('sts').get_caller_identity()['Account']
        if account!='006816724683':raise RuntimeError('Wrong AWS account')
        # Fail fast on paused/unavailable cluster without changing its state.
        if args.mode=='run':
            status=session.client('redshift').describe_clusters(ClusterIdentifier=CLUSTER)['Clusters'][0]['ClusterStatus']
            if status!='available':raise RuntimeError('Cluster must be available; current status='+status)
        with TemporaryDirectory(prefix='verified-replay-') as tmp:
            package,_=finalize(root,Path(tmp)/'verified',session.client('s3'),account)
            sql=replay_sql(package,(root/'noop_before.sql').read_text(),(root/'noop_after.sql').read_text())
        (out/'verified_replay.sql').write_text(sql,encoding='utf-8')
        report['sql_sha256']=hashlib.sha256(sql.encode()).hexdigest()
        report['status']='S3_GATE_PASSED';save_report()
        if args.mode=='verify':
            print('VERIFY_PASSED: no Redshift calls, no AWS writes.');return
        import sqlparse
        data=DataSession(session.client('redshift-data'),journal,run_id)
        _,rows=data.execute('SELECT current_database() AS database_name, current_user AS user_name')
        if len(rows)!=1 or rows[0][0]!=DATABASE:raise RuntimeError('Wrong database')
        seen=set()
        for stmt in sqlparse.split(sql):
            columns,rows=data.execute(stmt)
            marker=check_results(columns,rows)
            if marker:seen.add(marker)
        if seen!={'tables','audit'}:raise RuntimeError('Required result checks were not returned')
        report['status']='REPLAY_PASSED';save_report()
        print('REPLAY_PASSED: eight tables unchanged; one new NO_OP. No Glue job or schedule started.')
    except Exception as exc:
        report['status']='STOPPED_REVIEW_REQUIRED'
        report['error']=str(exc);save_report()
        raise


if __name__=='__main__':main()
