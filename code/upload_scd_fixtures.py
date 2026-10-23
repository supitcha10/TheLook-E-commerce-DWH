"""Run only from extracted test package in CloudShell. Upload immutable test objects, no SQL."""
import hashlib
import json
from pathlib import Path

BUCKET='thelook-dwh-20241022'
PREFIX='thelook/tests/scd-rollback/fixtures-v1/'
ACCOUNT='006816724683'


def main():
    import boto3
    from botocore.exceptions import ClientError
    root=Path(__file__).resolve().parent
    hashes=json.loads((root/'sha256.json').read_text())
    for name,digest in hashes.items():
        p=(root/name).resolve()
        if not p.is_relative_to(root.resolve()): raise RuntimeError('Unsafe package path')
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest: raise RuntimeError('Local file hash differs: '+name)
    session=boto3.Session(region_name='us-east-1')
    if session.client('sts').get_caller_identity()['Account']!=ACCOUNT: raise RuntimeError('Wrong account')
    s3=session.client('s3')
    pending=[]
    files=sorted(p for p in (root/'s3').rglob('*') if p.is_file())
    if len(files)!=98: raise RuntimeError('Expected 49 Parquet files and 49 manifests')
    def remote(key):
        try:
            obj=s3.get_object(Bucket=BUCKET,Key=key)
            with obj['Body'] as stream: return hashlib.sha256(stream.read()).hexdigest()
        except ClientError as e:
            if e.response['Error']['Code'] in ('NoSuchKey','404'): return None
            raise
    # Preflight every destination: never replace different content under this immutable prefix.
    for p in files:
        relative=p.relative_to(root/'s3').as_posix()
        key=PREFIX+relative
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        old=remote(key)
        if old is not None and old!=digest: raise RuntimeError('Existing S3 content differs: '+key)
        if old is None: pending.append((p,key))
    for p,key in pending:
        s3.put_object(Bucket=BUCKET,Key=key,Body=p.read_bytes(),IfNoneMatch='*')
    for p in files:
        key=PREFIX+p.relative_to(root/'s3').as_posix()
        if remote(key)!=hashlib.sha256(p.read_bytes()).hexdigest(): raise RuntimeError('Remote verification failed: '+key)
    print('UPLOAD_VERIFIED: 98 objects; synthetic test prefix only. No SQL executed.')


if __name__=='__main__':main()
