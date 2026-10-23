"""Relational fixture tests in SQLite; not Redshift SQL/decimal integration tests."""
import re
import sqlite3
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        for filename in ('02_warehouse.sql','00_control.sql'):
            text=(ROOT/'code/sql'/filename).read_text()
            for name,body in re.findall(r'CREATE TABLE (\w+\.\w+)\s*\((.*?)\)\s*DISTSTYLE',text,re.S):
                cols=[part.strip().split()[0] for part in re.split(r',\s*(?![^()]*\))',body) if part.strip()]
                self.db.execute('CREATE TABLE '+name.replace('.','_')+' ('+','.join('"'+c+'"' for c in cols)+')')
        self.add('dw_dim_date',date_key=20260101,full_date='2026-01-01',year=2026,month=1)
        self.add('dw_dim_users',user_key=10,user_id=1,country='Historical',age_group='26-35',is_current=0)
        self.add('dw_dim_users',user_key=11,user_id=1,country='Current',age_group='26-35',is_current=1)
        for pid in (1,2):self.add('dw_dim_products',product_key=pid,product_id=pid,product_name=f'P{pid}',category='C')
        for did in (1,2):self.add('dw_dim_distribution_centers',distribution_center_key=did,distribution_center_id=did,dc_name=f'D{did}')
        for iid,oid,status,pid,did,money in [(1,1,'Complete',1,1,10),(2,1,'Returned',2,2,20),(3,2,'Complete',1,1,30)]:
            self.add('dw_fact_sales',order_item_id=iid,order_id=oid,order_date_key=20260101,user_key=10,product_key=pid,distribution_center_key=did,status=status,quantity=1,sale_price=money,product_cost=4,gross_profit=money-4,reference_retail_price=money+2,source_batch_id='b',rule_version='provisional-v1',item_dates_comparable=1,item_shipped_before_created=(iid==1))
        self.add('etl_batch_ledger',batch_id='b',status='SUCCEEDED',fact_rows=3)
        self.add('etl_batch_attempts',batch_id='b',status='SUCCEEDED')
        self.add('etl_batch_attempts',batch_id='b',status='NO_OP')
        self.add('etl_batch_attempts',batch_id='failed_only',status='FAILED')
        sql=(ROOT/'code/sql/10_reporting_views.sql').read_text()
        sql=sql.replace('CREATE OR REPLACE VIEW','CREATE VIEW')
        sql=re.sub(r'\b(dw|etl|reporting)\.',r'\1_',sql)
        self.db.executescript(sql)

    def tearDown(self):self.db.close()

    def add(self,table,**values):
        self.db.execute(f'INSERT INTO {table} ({",".join(values)}) VALUES ({",".join("?" for _ in values)})',list(values.values()))

    def test_grain_money_and_rollups(self):
        self.assertEqual(self.db.execute('SELECT COUNT(*),SUM(item_sale_amount) FROM reporting_v_sales_item').fetchone(),(3,60))
        for view in ('daily_status','product_daily_status','dc_daily_status'):
            self.assertEqual(self.db.execute(f'SELECT SUM(item_count),SUM(sale_amount),SUM(cost_amount) FROM reporting_v_sales_{view}').fetchone(),(3,60,12))

    def test_historical_key_and_no_direct_pii(self):
        self.assertEqual(self.db.execute('SELECT DISTINCT country FROM reporting_v_sales_item').fetchall(),[('Historical',)])
        cols={r[1] for r in self.db.execute('PRAGMA table_info(reporting_v_sales_item)')}
        self.assertFalse(cols & {'email','full_name','street_address','postal_code','ip_address'})

    def test_distinct_orders_are_not_additive(self):
        self.assertEqual(self.db.execute('SELECT COUNT(DISTINCT order_id) FROM reporting_v_sales_item').fetchone()[0],2)
        self.assertEqual(self.db.execute('SELECT SUM(distinct_order_count) FROM reporting_v_sales_daily_status').fetchone()[0],3)

    def test_missing_dimension_keeps_fact_visible(self):
        self.db.execute('DELETE FROM dw_dim_products WHERE product_key=2')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM reporting_v_sales_item').fetchone()[0],3)
        self.assertEqual(self.db.execute('SELECT missing_dimension_item_count FROM reporting_v_sales_quality').fetchone()[0],1)

    def test_audit_aggregation_and_failed_only_visibility(self):
        self.assertEqual(self.db.execute('SELECT COUNT(*),MAX(attempt_count),MAX(no_op_count) FROM reporting_v_batch_history').fetchone(),(1,2,1))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM reporting_v_batch_attempt_history WHERE batch_id='failed_only'").fetchone()[0],1)

if __name__=='__main__':unittest.main()
