import hashlib
import json
import unittest
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq
import build_scd_test_package as build


class FixtureTests(unittest.TestCase):
    def test_assert_helper_capacity_and_recovery_does_not_reload(self):
        sql=(build.OUT/'sql/00_helpers_and_empty_gate.sql').read_text()
        self.assertIn('p_query VARCHAR(65535)',sql)
        recovery=(build.OUT/'sql/repair_bootstrap_assert_only.sql').read_text()
        self.assertNotIn('CALL etl.load_batch(',recovery)
        self.assertNotIn('empty etl.',recovery)
        self.assertIn('CREATE TEMP TABLE original_users AS SELECT',recovery)
        self.assertNotIn('IF NOT EXISTS original_users AS',recovery)

    def test_positive_snapshots_keys_and_parent_consistency(self):
        for name in ('bootstrap','changes','unchanged','late_retry'):
            data=build.fixtures()[name]
            for t,rows in data.items():
                key=build.CONTRACT[t]['primary_key']
                self.assertEqual(len(rows),len({r[key] for r in rows}))
            users={r['id'] for r in data['users']}
            orders={r['order_id']:r for r in data['orders']}
            inventory={r['id']:r for r in data['inventory_items']}
            for item in data['order_items']:
                self.assertIn(item['user_id'],users)
                self.assertEqual(item['user_id'],orders[item['order_id']]['user_id'])
                self.assertEqual(item['product_id'],inventory[item['inventory_item_id']]['product_id'])
            self.assertEqual(len(orders),len(data['order_items']))

    def test_scd_scenarios_and_negative_fixtures(self):
        d=build.fixtures()
        self.assertEqual(d['bootstrap']['users'][0]['city_clean'],'Alpha')
        self.assertIsNone(d['changes']['users'][0]['city_clean'])
        self.assertIsNone(d['bootstrap']['users'][1]['city_clean'])
        self.assertEqual(d['changes']['users'][1]['city_clean'],'Beta')
        self.assertEqual(d['bootstrap']['users'][2],d['changes']['users'][2])
        self.assertEqual(d['unchanged'],d['changes'])
        self.assertEqual(d['late_retry']['users'][2]['age'],31)
        self.assertEqual(d['bad_pk']['products'][0],d['bad_pk']['products'][1])
        self.assertEqual(d['bad_fk']['orders'][0]['user_id'],999)

    def test_parquet_manifests_hashes_and_money(self):
        package=json.loads((build.OUT/'package.json').read_text())
        for label,case in package['cases'].items():
            unhashed={k:v for k,v in case.items() if k!='package_hash'}
            self.assertEqual(case['package_hash'],hashlib.sha256(json.dumps(unhashed,sort_keys=True).encode()).hexdigest())
            for t,info in case['tables'].items():
                path=build.OUT/'s3'/label/t/'data.parquet'
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),info['sha256'])
                table=pq.read_table(path)
                self.assertEqual(table.schema,build.schema(t))
                self.assertEqual(table.num_rows,info['rows'])
                manifest=json.loads((build.OUT/'s3'/label/'manifests'/f'{t}.json').read_text())['entries']
                self.assertEqual(len(manifest),1)
                self.assertEqual(manifest[0]['meta']['content_length'],path.stat().st_size)
                self.assertEqual(manifest[0]['url'],f'{build.BASE}/{label}/{t}/data.parquet')
                for mt,mc in build.MONEY:
                    if mt==t:
                        total=sum(table[mc].to_pylist(),Decimal(0))
                        if label=='bad_money' and mc=='sale_price':total+=1
                        self.assertEqual(total,Decimal(case['money'][f'{mt}.{mc}']))

    def test_injection_only_changes_clone_name_and_adds_raise(self):
        ref=(build.OUT/'loader_installed_reference.sql').read_text()
        expected=ref[ref.index('CREATE OR REPLACE PROCEDURE etl.load_batch('):]
        actual=(build.OUT/'sql/01_install_test_only_failure_procedure.sql').read_text()
        restored=actual.replace('PROCEDURE etl.load_batch_test_fail_after_publish(', 'PROCEDURE etl.load_batch(',1).replace("\n    RAISE EXCEPTION 'SCD_TEST_INJECTED_AFTER_FACT_WRITE';",'')
        self.assertEqual(expected,restored)
        self.assertIn("current_database() = 'thelook_scd_test'",actual)
        self.assertNotIn('thelook_glue_validation',actual)
        self.assertNotIn('\n    RAISE;',actual)
        self.assertNotIn('\n    RAISE;',expected)
        repair=(build.OUT/'sql/repair_50_atomic_handlers.sql').read_text()
        self.assertNotIn('CALL etl.load_batch(',repair)
        self.assertIn('PROCEDURE etl.load_batch(',repair)
        self.assertIn('PROCEDURE etl.load_batch_test_fail_after_publish(',repair)

    def test_rollback_coverage_and_file_integrity(self):
        for number,label in [(50,'bad_pk'),(60,'bad_fk'),(70,'bad_money'),(80,'late_retry')]:
            sql=(build.OUT/'sql'/f'{number}c_verify_rollback_{label}.sql').read_text()
            self.assertEqual(sql.count(': unchanged '),15)
            self.assertIn('FAILED audit matches expected reason',sql)
            call=(build.OUT/'sql'/f'{number}b_EXPECT_ERROR_{label}.sql').read_text()
            self.assertEqual(call.count('CALL etl.'),1)
        hashes=json.loads((build.OUT/'sha256.json').read_text())
        for name,checksum in hashes.items():
            self.assertEqual(hashlib.sha256((build.OUT/name).read_bytes()).hexdigest(),checksum)


if __name__=='__main__':unittest.main()
