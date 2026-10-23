import unittest
from run_validation_replay import DataSession,check_results

class Fake:
    def __init__(self,status='FINISHED'): self.calls=[];self.status=status
    def execute_statement(self,**kw):self.calls.append(kw);return {'Id':'statement1','SessionId':'session1'}
    def describe_statement(self,**kw):return {'Status':self.status,'HasResultSet':True,'SessionId':'session1','Error':'synthetic error'}
    def get_statement_result(self,**kw):return {'ColumnMetadata':[{'name':'new_no_op_attempt'}],'Records':[[{'stringValue':'PASS'}]]}

class RunnerTests(unittest.TestCase):
    def test_same_session_and_stable_token(self):
        f=Fake();events=[];s=DataSession(f,events.append,'run1')
        self.assertEqual(s.execute('SELECT 1'),(['new_no_op_attempt'],[['PASS']]))
        s.execute('SELECT 2')
        self.assertEqual(f.calls[0]['Database'],'thelook_glue_validation')
        self.assertEqual(f.calls[1]['SessionId'],'session1')
        self.assertNotIn('Database',f.calls[1])
        self.assertNotEqual(f.calls[0]['ClientToken'],f.calls[1]['ClientToken'])
        self.assertEqual(len(events),4)
    def test_error_stops(self):
        with self.assertRaisesRegex(RuntimeError,'FAILED'):DataSession(Fake('FAILED'),lambda x:None,'run1').execute('SELECT 1')
    def test_fail_result_not_accepted(self):
        with self.assertRaises(RuntimeError):check_results(['new_no_op_attempt'],[['FAIL']])
        with self.assertRaises(RuntimeError):check_results(['table_name','status'],[['dw.dim_users','PASS']])
        self.assertEqual(check_results(['new_no_op_attempt'],[['PASS']]),'audit')

if __name__=='__main__':unittest.main()
