"""Generate reviewable Redshift SQL from the versioned schema and load fragment."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'code' / 'sql'

def fail_if(query, message):
    return f"    IF EXISTS ({query}) THEN RAISE EXCEPTION '{message}'; END IF;\n"

def build():
    OUT.mkdir(exist_ok=True)
    schema = json.loads((ROOT/'code/curated_schema.json').read_text(encoding='utf-8'))['tables']
    stage = ['-- First-time installation only. Do not use this file as a schema migration.', 'CREATE SCHEMA IF NOT EXISTS stg;']
    for name,spec in schema.items():
        cols = [f"    {c['name']} {c['type']}" + ('' if c['nullable'] else ' NOT NULL') for c in spec['columns']]
        if name in ('users','events'):
            cols += ['    city_clean VARCHAR(256)', '    city_missing_token BOOLEAN NOT NULL']
        if name == 'order_items':
            cols += ['    item_shipped_before_created BOOLEAN', '    item_dates_comparable BOOLEAN NOT NULL']
        stage.append(f'CREATE TABLE stg.{name} (\n'+',\n'.join(cols)+'\n) DISTSTYLE AUTO SORTKEY AUTO ENCODE AUTO;')
    (OUT/'01_staging.sql').write_text('\n\n'.join(stage)+'\n',encoding='utf-8')
    doc = (ROOT/'docs/data_warehouse_schema_design.md').read_text(encoding='utf-8')
    ddl = next(b for b in re.findall(r'```sql\n(.*?)```',doc,re.S) if 'CREATE TABLE' in b)
    (OUT/'02_warehouse.sql').write_text('-- First-time installation; no DROP or automatic migration.\n'+ddl,encoding='utf-8')

    validation = ''
    for name,spec in schema.items():
        pk=spec['primary_key']
        validation += fail_if(f'SELECT {pk} FROM stg.{name} GROUP BY {pk} HAVING {pk} IS NULL OR COUNT(*)>1',f'{name}: invalid primary key')
        validation += f"""    SELECT COUNT(*) INTO v_n FROM stg.{name};
    SELECT expected_rows INTO v_expected FROM expected_inputs WHERE table_name='{name}';
    IF v_n <> v_expected THEN RAISE EXCEPTION '{name}: row count differs from approved package'; END IF;
"""
        for col in spec['columns']:
            key,typ=col['name'],col['type']
            if key=='id' or key.endswith('_id') and key!='session_id':
                validation += fail_if(f'SELECT 1 FROM stg.{name} WHERE {key}<=0',f'{name}.{key}: nonpositive key')
        if name in ('users','events'):
            validation += fail_if(f"SELECT 1 FROM stg.{name} WHERE city_missing_token <> (LOWER(TRIM(city))='null') OR (city_missing_token AND city_clean IS NOT NULL) OR (NOT city_missing_token AND (city_clean IS NULL OR city_clean<>city))",f'{name}: city transformation differs from provisional rule')
            validation += f"""    SELECT COUNT(*) INTO v_n FROM stg.{name} WHERE city_missing_token;
    SELECT expected_city_tokens INTO v_expected FROM expected_inputs WHERE table_name='{name}';
    IF v_expected IS NULL OR v_n <> v_expected THEN RAISE EXCEPTION '{name}: known city issue drift'; END IF;
"""
    relations=[('products','distribution_center_id','distribution_centers','id'),('inventory_items','product_id','products','id'),
               ('inventory_items','product_distribution_center_id','distribution_centers','id'),('orders','user_id','users','id'),
               ('order_items','order_id','orders','order_id'),('order_items','user_id','users','id'),
               ('order_items','product_id','products','id'),('order_items','inventory_item_id','inventory_items','id'),('events','user_id','users','id')]
    for child,fk,parent,pk in relations:
        validation += fail_if(f'SELECT 1 FROM stg.{child} c LEFT JOIN stg.{parent} p ON c.{fk}=p.{pk} WHERE c.{fk} IS NOT NULL AND p.{pk} IS NULL',f'{child}.{fk}: orphan key')

    # Generate null-safe equality without sentinel values (a literal sentinel could be real data).
    tracked=['full_name','email','age','gender','city','city_missing_token','state','country','postal_code','traffic_source']
    equal=' AND\n            '.join(f'(u.{c}=s.{c} OR (u.{c} IS NULL AND s.{c} IS NULL))' for c in tracked)
    # NOT of SQL UNKNOWN is UNKNOWN; use CASE to turn every comparison into a real boolean.
    changed=' OR\n            '.join(f'CASE WHEN u.{c}=s.{c} OR (u.{c} IS NULL AND s.{c} IS NULL) THEN FALSE ELSE TRUE END' for c in tracked)
    fragment=(OUT/'load_body.sql.inc').read_text(encoding='utf-8')
    fragment=fragment.replace('-- GENERATED_STAGE_CHECKS',validation).replace('-- GENERATED_USER_CHANGE',changed)
    header="""-- Default ATOMIC procedure. Install after 00/01/02. Call in autocommit mode.
-- expected_inputs and expected_money are session TEMP tables created by rendered run_batch.sql.
-- Only this procedure is the supported writer of stg/dw; do not call pieces independently.
CREATE OR REPLACE PROCEDURE etl.load_batch(
    p_batch_id VARCHAR, p_package_hash VARCHAR, p_observed_at TIMESTAMPTZ,
    p_iam_role VARCHAR, p_schema_version VARCHAR, p_rule_version VARCHAR)
AS $$
DECLARE
    r RECORD;
    v_n BIGINT;
    v_expected BIGINT;
    v_sum DECIMAL(38,6);
    v_old_hash VARCHAR;
    v_old_time TIMESTAMPTZ;
    v_bootstrap BOOLEAN;
    v_min_date DATE;
    v_max_date DATE;
    v_days INTEGER;
BEGIN
"""
    footer="""
EXCEPTION WHEN OTHERS THEN
    -- In default mode Redshift rolls back the failed transaction, logs in a new
    -- transaction, commits the handler, then automatically rethrows the error.
    -- Explicit RAISE ensures re-throw even if behavior changes.
    INSERT INTO etl.batch_attempts(batch_id, attempted_at, status, detail)
    VALUES (p_batch_id, GETDATE(), 'FAILED', LEFT(SQLERRM, 4000));
    RAISE;
END;
$$ LANGUAGE plpgsql;
"""
    (OUT/'03_load_batch.sql').write_text(header+fragment+footer,encoding='utf-8')

if __name__=='__main__':
    build()
    print('Generated sql/01_staging.sql, 02_warehouse.sql, 03_load_batch.sql')
