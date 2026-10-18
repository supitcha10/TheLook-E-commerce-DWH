"""Local contract tests only: these do not execute Redshift SQL or contact AWS."""
import json
import re
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / '.runtime_dependencies'))
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
from prepare_aws_batch import prepare, digest_file

BATCH = ROOT / 'outputs/curated/20261018T070120429459Z'

class WarehouseContracts(unittest.TestCase):
    def test_staging_matches_actual_parquet_order_types_and_nulls(self):
        ddl = (ROOT/'code/sql/01_staging.sql').read_text()
        report = json.loads((BATCH/'validation_report.json').read_text())
        for name, info in report['tables'].items():
            with self.subTest(table=name):
                block = re.search(r'CREATE TABLE stg\.'+name+r' \(\n(.*?)\n\)', ddl, re.S)[1]
                cols = [line.strip().rstrip(',').split(' ', 1) for line in block.splitlines()]
                table = pq.read_table(BATCH/f'{name}.parquet')
                self.assertEqual([c[0] for c in cols], table.column_names)
                self.assertEqual(table.num_rows, info['curated_rows'])
                for (col, spec), field in zip(cols, table.schema):
                    typ = field.type
                    if spec.startswith('BIGINT'): self.assertEqual(typ, pa.int64())
                    elif spec.startswith('SMALLINT'): self.assertEqual(typ, pa.int16())
                    elif spec.startswith('INTEGER'): self.assertEqual(typ, pa.int32())
                    elif spec.startswith('VARCHAR'): self.assertTrue(pa.types.is_string(typ))
                    elif spec.startswith('DOUBLE'): self.assertEqual(typ, pa.float64())
                    elif spec.startswith('BOOLEAN'): self.assertEqual(typ, pa.bool_())
                    elif spec.startswith('DECIMAL'): self.assertEqual(typ, pa.decimal128(18,6))
                    elif spec.startswith('TIMESTAMPTZ'): self.assertEqual(typ, pa.timestamp('us', tz='UTC'))
                    else: self.fail(spec)
                    if 'NOT NULL' in spec: self.assertEqual(table[col].null_count, 0)

    def test_package_manifest_and_repeatable_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'outputs') as tmp:
            tmp = Path(tmp)
            cfg = json.loads((ROOT/'code/aws_batch_config.example.json').read_text())
            cfg.update(bucket='local-test-not-a-deployment', iam_role='arn:aws:iam::123456789012:role/local-test-only')
            path = tmp/'config.json'; path.write_text(json.dumps(cfg))
            a = prepare(path, tmp/'a'); b = prepare(path, tmp/'b')
            p = json.loads((a/'package.json').read_text())
            self.assertEqual(p, json.loads((b/'package.json').read_text()))
            self.assertEqual(len(p['files']),7)
            self.assertEqual(len(p['money']),5)
            for f in p['files']:
                entry = json.loads((a/'manifests'/f"{f['table_name']}.json").read_text())['entries'][0]
                local = BATCH/f"{f['table_name']}.parquet"
                self.assertEqual(entry['meta']['content_length'],local.stat().st_size)
                self.assertEqual(f['sha256'],digest_file(local))
                self.assertTrue(entry['mandatory'])
                self.assertEqual(entry['url'],f['data_url'])
            self.assertIn('CALL etl.load_batch(', (a/'run_batch.sql').read_text())

    def test_placeholder_and_failed_batch_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'outputs') as tmp:
            tmp = Path(tmp)
            with self.assertRaises(ValueError): prepare(ROOT/'code/aws_batch_config.example.json', tmp/'out')
            cfg=json.loads((ROOT/'code/aws_batch_config.example.json').read_text())
            cfg.update(bucket='local-test-not-a-deployment',iam_role='arn:aws:iam::123456789012:role/local-test-only',curated_dir='outputs/curated/20261018T065840511275Z')
            path=tmp/'config.json'; path.write_text(json.dumps(cfg))
            with self.assertRaises(ValueError): prepare(path,tmp/'out')

    def test_bootstrap_joins_grain_money_and_calendar(self):
        def read(name): return pq.read_table(BATCH/f'{name}.parquet').to_pandas()
        items=read('order_items'); orders=read('orders'); inv=read('inventory_items')
        joined=items[['id','order_id','user_id','product_id','inventory_item_id','sale_price']].merge(
            orders[['order_id','created_at']],on='order_id',validate='many_to_one').merge(
            inv[['id','cost','product_retail_price','product_distribution_center_id']].rename(columns={'id':'inventory_item_id'}),
            on='inventory_item_id',validate='many_to_one')
        for table,fk,pk in [('users','user_id','id'),('products','product_id','id'),('distribution_centers','product_distribution_center_id','id')]:
            keys=read(table)[[pk]].rename(columns={pk:fk})
            joined=joined.merge(keys,on=fk,validate='many_to_one')
        self.assertEqual(len(joined),181759)
        self.assertTrue(joined.id.is_unique)
        self.assertEqual(sum(joined.sale_price),sum(items.sale_price))
        self.assertEqual(sum(joined.sale_price-joined.cost),sum(joined.sale_price)-sum(joined.cost))
        dates=pd.concat([orders[c].dropna() for c in ['created_at','shipped_at','delivered_at','returned_at']])
        self.assertLessEqual((dates.max().date()-dates.min().date()).days,99999)
        elapsed=(orders.delivered_at-orders.shipped_at).dropna()
        self.assertTrue((elapsed>=pd.Timedelta(0)).all())
        for delta in elapsed.unique():
            micros=int(delta / pd.Timedelta(microseconds=1))
            formula=Decimal((micros+43200)//86400)/Decimal(1000000)
            expected=(Decimal(micros)/Decimal(86400000000)).quantize(Decimal('.000001'), rounding='ROUND_HALF_UP')
            self.assertEqual(formula,expected)

if __name__=='__main__': unittest.main(verbosity=2)
