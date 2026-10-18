"""Boundary checks for transformations; run with python -m unittest test_curated_pipeline."""
import unittest
from decimal import Decimal
import curated_pipeline as cp

class CuratedConversionTests(unittest.TestCase):
    def setUp(self):
        self.spec={'columns':[
            {'name':'id','type':'BIGINT','nullable':False},
            {'name':'city','type':'VARCHAR(20)','nullable':False},
            {'name':'price','type':'DECIMAL(18,6)','nullable':False},
            {'name':'created_at','type':'TIMESTAMPTZ','nullable':False},
        ]}

    def test_exact_id_rounding_and_reversible_city(self):
        raw=cp.pd.DataFrame({'id':['9007199254740993.0'],'city':[' NULL '],
                            'price':['1.0000005'],'created_at':['2024-01-01T07:00:00.123456+07:00']},dtype='string')
        before=raw.copy(deep=True)
        table,rejected,controls,_=cp.convert_chunk(raw,self.spec,'users')
        self.assertEqual(len(rejected),0)
        self.assertEqual(table['id'][0].as_py(),9007199254740993)
        self.assertEqual(table['price'][0].as_py(),Decimal('1.000001'))
        self.assertEqual(controls['price']['rounding_delta'],Decimal('0.0000005'))
        self.assertEqual(table['city'][0].as_py(),' NULL ')
        self.assertIsNone(table['city_clean'][0].as_py())
        self.assertTrue(table['city_missing_token'][0].as_py())
        self.assertEqual(table['created_at'][0].as_py().hour,0)
        self.assertEqual(table['created_at'][0].as_py().microsecond,123456)
        cp.pd.testing.assert_frame_equal(raw,before)

    def test_rejects_overflow_missing_timezone_and_utf8_length(self):
        raw=cp.pd.DataFrame({
            'id':['9223372036854775808','2','3','4','5'],
            'city':['Bangkok','Bangkok','ก'*7,'Bangkok','Bangkok'],
            'price':['1','1','1','1000000000000','1'],
            'created_at':['2024-01-01T00:00:00Z','2024-01-01','2024-01-01T00:00:00Z',
                          '2024-01-01T00:00:00Z','2024-01-01T00:00:00.123456789Z'],
        },dtype='string')
        table,rejected,_,_=cp.convert_chunk(raw,self.spec,'users')
        self.assertEqual(len(table),0)
        self.assertEqual(len(rejected),5)
        self.assertTrue(rejected['rejection_rules'].str.len().gt(0).all())

    def test_uncomparable_item_dates_are_null(self):
        spec={'columns':[{'name':'id','type':'BIGINT','nullable':False},
                         {'name':'created_at','type':'TIMESTAMPTZ','nullable':False},
                         {'name':'shipped_at','type':'TIMESTAMPTZ','nullable':True}]}
        raw=cp.pd.DataFrame({'id':['1','2'],'created_at':['2024-01-02T00:00:00Z']*2,
                            'shipped_at':['','2024-01-01T00:00:00Z']},dtype='string')
        table,rejected,_,_=cp.convert_chunk(raw,spec,'order_items')
        self.assertEqual(table['item_shipped_before_created'].to_pylist(),[None,True])
        self.assertEqual(table['item_dates_comparable'].to_pylist(),[False,True])
        self.assertEqual(len(rejected),0)

if __name__=='__main__': unittest.main()
