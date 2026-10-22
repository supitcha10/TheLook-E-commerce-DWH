"""Build typed local Parquet datasets and reconcile them against immutable CSV input."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if importlib.util.find_spec('pyarrow') is None and (ROOT / '.runtime_dependencies').is_dir():
    sys.path.insert(0, str(ROOT / '.runtime_dependencies'))

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

RELATIONS = [
    ('products','distribution_center_id','distribution_centers','id'),
    ('inventory_items','product_id','products','id'),
    ('inventory_items','product_distribution_center_id','distribution_centers','id'),
    ('orders','user_id','users','id'),
    ('order_items','order_id','orders','order_id'),
    ('order_items','user_id','users','id'),
    ('order_items','product_id','products','id'),
    ('order_items','inventory_item_id','inventory_items','id'),
    ('events','user_id','users','id'),
]

def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def arrow_type(kind):
    if kind.startswith('VARCHAR'): return pa.string()
    return {'BIGINT':pa.int64(), 'INTEGER':pa.int32(), 'SMALLINT':pa.int16(),
            'DOUBLE PRECISION':pa.float64(), 'TIMESTAMPTZ':pa.timestamp('us', tz='UTC'),
            'DECIMAL(18,6)':pa.decimal128(18,6)}[kind]

def convert_chunk(raw, spec, name):
    """Never mutate raw. Return accepted typed rows, row-level rejection reasons, and controls."""
    converted, errors, money, column_stats = {}, {}, {}, {}
    for col in spec['columns']:
        key, kind = col['name'], col['type']
        source = raw[key].astype('string')
        trimmed = source.str.strip()
        missing = source.isna() | trimmed.eq('').fillna(False)
        values = source.mask(missing)
        bad = pd.Series(False, index=raw.index)
        stats = {'raw_missing':int(missing.sum()), 'max_utf8_bytes':None}
        if not col['nullable']:
            errors[key + ':required'] = missing
        if kind.startswith('VARCHAR'):
            lengths = source.str.encode('utf-8').str.len()
            limit = int(re.search(r'\d+',kind).group())
            bad = ~missing & lengths.gt(limit)
            stats['max_utf8_bytes'] = int(lengths.max()) if len(source) else 0
            # Preserve case/spacing of nonblank source text; no speculative normalization.
        elif kind in ('BIGINT','INTEGER','SMALLINT'):
            limits = {'BIGINT':(-2**63,2**63-1), 'INTEGER':(-2**31,2**31-1), 'SMALLINT':(-2**15,2**15-1)}
            lo, hi = limits[kind]
            cache = {}
            for v in trimmed.loc[~missing].unique():
                if not re.fullmatch(r'[+-]?\d+(?:\.0+)?', v):
                    cache[v] = None
                else:
                    n = int(v.split('.')[0])
                    cache[v] = n if lo <= n <= hi else None
            # Explicit nullable integer construction prevents float conversion of large IDs.
            values = pd.Series(pd.array([cache.get(v) if not m else None for v,m in zip(trimmed,missing)],
                                        dtype={'BIGINT':'Int64','INTEGER':'Int32','SMALLINT':'Int16'}[kind]),index=raw.index)
            bad = ~missing & values.isna()
            if key == 'id' or key.endswith('_id') or key == 'num_of_item':
                bad |= values.le(0).fillna(False)
        elif kind == 'DOUBLE PRECISION':
            values = pd.to_numeric(trimmed.mask(missing), errors='coerce').astype('Float64')
            bad = ~missing & (values.isna() | ~np.isfinite(values))
            if key in ('latitude','longitude'):
                limit = 90 if key == 'latitude' else 180
                bad |= values.abs().gt(limit).fillna(False)
        elif kind == 'TIMESTAMPTZ':
            has_zone = trimmed.str.contains(r'(?:Z|[+-]\d{2}:?\d{2})$',case=False,regex=True,na=False)
            values = pd.to_datetime(trimmed.mask(missing),format='mixed',utc=True,errors='coerce')
            # Reject sub-microsecond precision rather than silently truncating it.
            precision_loss = values.notna() & values.ne(values.dt.floor('us'))
            bad = ~missing & (~has_zone | values.isna() | precision_loss)
        elif kind == 'DECIMAL(18,6)':
            original, rounded = {}, {}
            for text in trimmed.loc[~missing].unique():
                try:
                    number = Decimal(text)
                    target = number.quantize(Decimal('0.000001'),rounding=ROUND_HALF_UP)
                    if not number.is_finite() or abs(target) >= Decimal('1000000000000'):
                        raise InvalidOperation
                    original[text], rounded[text] = number,target
                except (InvalidOperation, ValueError):
                    original[text], rounded[text] = None,None
            values = trimmed.map(rounded).astype(object).where(~missing, None)
            bad = ~missing & values.isna()
            money[key] = (trimmed.map(original),values)
        errors[key + ':invalid_type_or_range'] = bad.fillna(False)
        converted[key] = values
        column_stats[key] = stats

    rejected = pd.Series(False,index=raw.index)
    for mask in errors.values(): rejected |= mask
    good = ~rejected
    error_rows = {}
    for rule,mask in errors.items():
        for idx in mask[mask].index:
            error_rows.setdefault(idx,[]).append(rule)
    quarantine = raw.loc[rejected].copy()
    quarantine.insert(0,'source_record',quarantine.index + 2)
    quarantine['rejection_rules'] = [';'.join(error_rows[idx]) for idx in quarantine.index]

    arrays, fields = [], []
    for col in spec['columns']:
        key = col['name']
        arrays.append(pa.array(converted[key].loc[good],type=arrow_type(col['type']),from_pandas=True))
        fields.append(pa.field(key,arrow_type(col['type']),nullable=col['nullable']))
        column_stats[key]['curated_nulls'] = arrays[-1].null_count
    extras = {}
    if name in ('users','events'):
        flag = raw['city'].astype('string').str.strip().str.casefold().eq('null').fillna(False)
        clean = raw['city'].astype('string').mask(flag | raw['city'].astype('string').str.strip().eq(''))
        extras = {'city_clean':(clean,pa.string()),'city_missing_token':(flag,pa.bool_())}
    if name == 'order_items':
        comparable = converted['created_at'].notna() & converted['shipped_at'].notna()
        flag = converted['shipped_at'].lt(converted['created_at']).astype('boolean').where(comparable,pd.NA)
        extras = {'item_shipped_before_created':(flag,pa.bool_()),'item_dates_comparable':(comparable,pa.bool_())}
    for key,(series,kind) in extras.items():
        arrays.append(pa.array(series.loc[good],type=kind,from_pandas=True))
        fields.append(pa.field(key,kind,nullable=key not in ('city_missing_token','item_dates_comparable')))
    table = pa.Table.from_arrays(arrays,schema=pa.schema(fields))
    controls = {}
    for key,(before,after) in money.items():
        pairs = [(a,b) for a,b in zip(before.loc[good],after.loc[good]) if a is not None and not pd.isna(a)]
        controls[key] = {
            'source_accepted_sum':sum((a for a,b in pairs),Decimal(0)),
            'expected_curated_sum':sum((b for a,b in pairs),Decimal(0)),
            'rounding_delta':sum((b-a for a,b in pairs),Decimal(0)),
            'sum_absolute_rounding':sum((abs(b-a) for a,b in pairs),Decimal(0)),
            'rounded_rows':sum(a!=b for a,b in pairs),
        }
    return table,quarantine,controls,column_stats

def run_curated(project_dir=ROOT, chunk_size=250_000, batch_id=None):
    project_dir = Path(project_dir).resolve()
    schema = json.loads((project_dir/'code/curated_schema.json').read_text(encoding='utf-8'))
    baseline = json.loads((project_dir/'code/dq_known_issues_baseline.json').read_text(encoding='utf-8'))
    batch_id = batch_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = project_dir/'outputs'/'curated'/batch_id
    output.mkdir(parents=True,exist_ok=False)
    report = {'batch_id':batch_id,'schema_version':schema['version'],'rule_version':'provisional-v1',
              'status':'RUNNING','source_confirmation':'pending','tables':{},'checks':[], 'known_issues':[]}
    def check(name,passed,detail):
        report['checks'].append({'check':name,'status':'PASS' if passed else 'FAIL','detail':detail})
    try:
        for name,spec in schema['tables'].items():
            source = project_dir/'dataset'/f'{name}.csv'
            source_hash = file_hash(source)
            with source.open(encoding='utf-8-sig',newline='') as stream:
                header = next(csv.reader(stream))
            if header != [c['name'] for c in spec['columns']]:
                raise ValueError(f'{name}: CSV header does not match curated_schema.json')
            target = output/f'{name}.parquet'
            details = {'source_sha256':source_hash,'raw_rows':0,'curated_rows':0,'quarantined_rows':0,
                       'money':{},'columns':{},'parquet':str(target),'expected_row_groups':0}
            writer = None
            try:
                for raw in pd.read_csv(source,dtype='string',keep_default_na=False,na_filter=False,
                                       encoding='utf-8-sig',chunksize=chunk_size):
                    table,rejects,controls,stats = convert_chunk(raw,spec,name)
                    if writer is None: writer = pq.ParquetWriter(target,table.schema,compression='snappy')
                    if len(table):
                        writer.write_table(table,row_group_size=len(table))
                        details['expected_row_groups'] += 1
                    details['raw_rows'] += len(raw)
                    details['curated_rows'] += len(table)
                    details['quarantined_rows'] += len(rejects)
                    if len(rejects):
                        reject_path = output/f'{name}_quarantine.csv'
                        rejects.to_csv(reject_path,index=False,mode='a',header=not reject_path.exists())
                    for key,metrics in controls.items():
                        dest = details['money'].setdefault(key,{k:0 if k=='rounded_rows' else Decimal(0) for k in metrics})
                        for metric,value in metrics.items(): dest[metric] += value
                    for key,metrics in stats.items():
                        dest = details['columns'].setdefault(key,{'raw_missing':0,'curated_nulls':0,'max_utf8_bytes':None})
                        for metric in ['raw_missing','curated_nulls']: dest[metric] += metrics[metric]
                        if metrics['max_utf8_bytes'] is not None:
                            dest['max_utf8_bytes'] = max(dest['max_utf8_bytes'] or 0,metrics['max_utf8_bytes'])
            finally:
                if writer is not None: writer.close()
            report['tables'][name] = details
            parquet = pq.ParquetFile(target)
            readback_sums = {key:Decimal(0) for key in details['money']}
            readback_rows, values_equal = 0,True
            # Compare logical Arrow values/schema, not serialized bytes: null buffers can
            # differ across writers even when every logical value is exactly equal.
            expected_groups = (convert_chunk(raw,spec,name)[0] for raw in pd.read_csv(
                source,dtype='string',keep_default_na=False,na_filter=False,
                encoding='utf-8-sig',chunksize=chunk_size))
            expected_groups = (group for group in expected_groups if len(group))
            for i in range(parquet.num_row_groups):
                group = parquet.read_row_group(i)
                readback_rows += len(group)
                expected_group = next(expected_groups,None)
                values_equal &= expected_group is not None and expected_group.equals(group)
                for key in readback_sums:
                    readback_sums[key] += sum((v for v in group[key].to_pylist() if v is not None),Decimal(0))
            check(f'{name}:row_reconciliation',details['raw_rows']==readback_rows+details['quarantined_rows'],
                  f"raw={details['raw_rows']}, readback={readback_rows}, quarantine={details['quarantined_rows']}")
            check(f'{name}:no_rejected_rows',details['quarantined_rows']==0,str(details['quarantined_rows']))
            values_equal &= next(expected_groups,None) is None and parquet.num_row_groups==details['expected_row_groups']
            check(f'{name}:typed_values_readback',values_equal,'Exact Arrow values and schema vs conversion of source CSV, including NULL positions and row order')
            check(f'{name}:source_unchanged',source_hash==file_hash(source),'CSV SHA-256 before/after')
            for key,total in readback_sums.items():
                controls = details['money'][key]
                controls['readback_sum'] = total
                check(f'{name}.{key}:amount_reconciliation',total==controls['expected_curated_sum'] and total-controls['source_accepted_sum']==controls['rounding_delta'],
                      f'Exact decimal comparison; rounding delta={controls["rounding_delta"]}')
            print(f'{name}: {readback_rows:,} curated rows, {details["quarantined_rows"]:,} quarantined',flush=True)

        # Read only join keys/controls for integrity checks; avoid loading events strings again.
        keys = {}
        for name,spec in schema['tables'].items():
            selected = [c['name'] for c in spec['columns'] if c['name']=='id' or c['name'].endswith('_id') and c['name']!='session_id']
            selected += [c for c in ['num_of_item','status'] if c in [v['name'] for v in spec['columns']]]
            keys[name] = pq.read_table(output/f'{name}.parquet',columns=selected).to_pandas()
            primary = keys[name][spec['primary_key']]
            check(f'{name}:primary_key',not primary.isna().any() and not primary.duplicated().any(),'non-null and unique after conversion')
        for child,fk,parent,pk in RELATIONS:
            vals = keys[child][fk]
            orphan = vals.notna() & ~vals.isin(keys[parent][pk])
            check(f'{child}.{fk}:foreign_key',not orphan.any(),f'orphan rows={int(orphan.sum())}')
        items,orders,inventory = keys['order_items'],keys['orders'],keys['inventory_items']
        counts = items.groupby('order_id').size()
        check('orders:item_counts',orders['num_of_item'].eq(orders['order_id'].map(counts).fillna(0)).all(),'num_of_item vs COUNT(order_items)')
        for parent,parent_key,fk,field in [(orders,'order_id','order_id','user_id'),(inventory,'id','inventory_item_id','product_id')]:
            if parent[parent_key].duplicated().any():
                check(f'order_items:{field}_matches_parent',False,'parent PK is not unique')
            else:
                lookup = parent.set_index(parent_key)[field]
                check(f'order_items:{field}_matches_parent',items[field].eq(items[fk].map(lookup)).all(),'compare mapped parent value')

        for issue in baseline['issues']:
            name=issue['table']
            column='item_shipped_before_created' if name=='order_items' else 'city_missing_token'
            flags=pq.read_table(output/f'{name}.parquet',columns=[column])[column].to_pylist()
            actual=sum(v is True for v in flags)
            denominator=sum(v is not None for v in flags)
            info=report['tables'][name]
            expected_snapshot=baseline['tables'][name]
            same=(actual==issue['expected_count'] and denominator==issue['expected_checked_rows']
                  and info['source_sha256']==expected_snapshot['sha256'] and info['raw_rows']==expected_snapshot['rows'])
            report['known_issues'].append({'issue_id':issue['id'],'status':'KNOWN_ISSUE' if same else 'WARN',
                                          'actual_rows':actual,'expected_rows':issue['expected_count'],
                                          'comparable_rows':denominator,'source_confirmation':'pending'})
        report['status'] = ('FAIL' if any(c['status']=='FAIL' for c in report['checks']) else
                            'REVIEW_REQUIRED' if any(i['status']=='WARN' for i in report['known_issues']) else 'PASS_WITH_KNOWN_ISSUES')
    except Exception as exc:
        report['status']='FAILED_INCOMPLETE'
        report['error']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        (output/'validation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
        summary=['# Curated validation report','',f"Batch: `{batch_id}`",f"Status: **{report['status']}**",'',
                 '| Table | Raw rows | Curated rows | Quarantine |','|---|---:|---:|---:|']
        for name,info in report['tables'].items():
            summary.append(f"| {name} | {info['raw_rows']:,} | {info['curated_rows']:,} | {info['quarantined_rows']:,} |")
        summary += ['', '## Decimal reconciliation', '',
                    'All source rows/statuses are included. These controls are not a definition of sales revenue.', '',
                    '| Table.column | Source accepted sum | Parquet sum | Rounding delta | Rounded rows |',
                    '|---|---:|---:|---:|---:|']
        for name,info in report['tables'].items():
            for key,metrics in info['money'].items():
                summary.append(f"| {name}.{key} | {metrics['source_accepted_sum']} | {metrics.get('readback_sum','not checked')} | {metrics['rounding_delta']} | {metrics['rounded_rows']} |")
        summary += ['', '## Known issues pending source confirmation', '',
                    '| Issue | Status | Rows | Comparable rows |','|---|---|---:|---:|']
        summary.extend(f"| {issue['issue_id']} | {issue['status']} | {issue['actual_rows']} | {issue['comparable_rows']} |" for issue in report['known_issues'])
        summary += ['', 'Source confirmation is pending. KNOWN_ISSUE is not proof that the source is correct.',
                    'Money is Decimal(18,6), ROUND_HALF_UP; exact rounding deltas are recorded in validation_report.json.',
                    'Raw CSV is unchanged. Every exported typed value is checked after reading Parquet back.', '',
                    '| Check | Status | Detail |','|---|---|---|']
        summary.extend(f"| {c['check']} | {c['status']} | {c['detail']} |" for c in report['checks'])
        (output/'validation_report.md').write_text('\n'.join(summary)+'\n',encoding='utf-8')
    if report['status'] != 'PASS_WITH_KNOWN_ISSUES':
        raise RuntimeError(f"Curated output requires review: {report['status']}. See {output}")
    return output,report

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--batch-id', help='Custom batch ID (default: auto timestamp)')
    args = p.parse_args()
    folder, result = run_curated(batch_id=args.batch_id)
    print(f"RESULT_PATH={folder}")
    print(f"STATUS={result['status']}")
