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
args, _ = parser.parse_known_args()

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
                    cur.fetchall()
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