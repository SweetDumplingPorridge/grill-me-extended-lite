import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'skills/grill-me-extended-lite/scripts'
sys.path.insert(0,str(SCRIPTS))
import runner
from render_round import render


class StateTests(unittest.TestCase):
    def setUp(self):
        self.s=runner.init('中文访谈目标')
        self.batch=json.loads((ROOT/'examples/round.json').read_text(encoding='utf-8'))

    def awaiting(self):
        return runner.transition(self.s,'batch',self.batch)

    def payload(self,s):
        b=s['current_batch']
        return dict(session_id=s['session_id'],batch_id=b['batch_id'],schema_id=b['schema_id'],submission_id='submit-1',answers=[dict(question_id=q['id'],selected=[q['options'][0]['id']] if q['type']!='text' else [],text='预算待定' if q['type']=='text' else '') for q in b['questions']])

    def test_invalid_choices_and_missing_answers_rejected(self):
        s=self.awaiting();p=self.payload(s)
        p['answers'][0]['selected']=['not-an-option']
        with self.assertRaises(ValueError):runner.transition(s,'answers',p)
        p=self.payload(s);p['answers'].pop()
        with self.assertRaises(ValueError):runner.transition(s,'answers',p)

    def test_retry_is_idempotent_but_changed_payload_rejected(self):
        s=self.awaiting();p=self.payload(s);done=runner.transition(s,'answers',p)
        self.assertEqual(done,runner.transition(done,'answers',p))
        p['answers'][2]['text']='changed'
        with self.assertRaises(ValueError):runner.transition(done,'answers',p)

    def test_old_batch_is_rejected(self):
        s=self.awaiting();p=self.payload(s);p['batch_id']='old'
        with self.assertRaises(ValueError):runner.transition(s,'answers',p)

    def test_pause_export_import_resume_preserves_all_data_and_draft(self):
        s=self.awaiting();b=s['current_batch']
        s=runner.transition(s,'draft',dict(key=':'.join(b[k] for k in ('session_id','batch_id','schema_id')),answers=[dict(question_id=q['id'],selected=[],text='未提交' if i==0 else '') for i,q in enumerate(b['questions'])]))
        s=runner.transition(s,'pause',{})
        restored=runner.restore(runner.envelope(s))
        self.assertNotEqual(s['session_id'],restored['session_id'])
        self.assertEqual(restored['status'],'PAUSED')
        self.assertEqual(restored['draft']['answers'],s['draft']['answers'])
        self.assertEqual(runner.transition(restored,'resume',{})['status'],'AWAITING_USER')

    def test_manual_edit_rehashes_batch_and_preserves_original(self):
        s=self.awaiting();checkpoint=runner.envelope(s)
        checkpoint['session']['goal']='修改后的目标'
        checkpoint['session']['current_batch']['questions'][0]['title']='新的问题'
        restored=runner.restore(checkpoint)
        self.assertEqual(restored['goal'],'修改后的目标')
        self.assertNotEqual(s['current_batch']['schema_id'],restored['current_batch']['schema_id'])
        self.assertEqual(s['goal'],'中文访谈目标')

    def test_invalid_import_status_and_draft_rejected(self):
        snapshot=runner.envelope(self.s);snapshot['session']['status']='AWAITING_USER'
        with self.assertRaises(ValueError):runner.restore(snapshot)
        snapshot=runner.envelope(self.awaiting());snapshot['session']['draft']={'key':'old','answers':[]}
        with self.assertRaises(ValueError):runner.restore(snapshot)

    def test_review_roundtrip_and_history_are_full_text(self):
        s=self.awaiting();s=runner.transition(s,'answers',self.payload(s))
        s=runner.transition(s,'candidate',{'markdown':'# 计划\n中文候选'})
        checks={k:True for k in runner.RUBRIC};checks['handoff']=False
        with self.assertRaises(ValueError):runner.transition(s,'review',dict(decision='approve',checks=checks,reasons='仍缺交接'))
        s=runner.transition(s,'review',dict(decision='return',checks=checks,reasons='补交接'))
        r=runner.restore(runner.envelope(s))
        self.assertEqual(r['candidate'],s['candidate']);self.assertEqual(r['answer_rounds'],s['answer_rounds']);self.assertEqual(r['reviews'],s['reviews'])

    def test_round_limit_requires_explicit_valid_choice(self):
        s=self.s;s['round']=12
        with self.assertRaises(ValueError):runner.transition(s,'batch',self.batch)
        with self.assertRaises(ValueError):runner.transition(s,'limit',{})
        self.assertEqual(runner.transition(s,'limit',{'choice':'continue'})['max_rounds'],24)
        self.assertTrue(runner.transition(s,'limit',{'choice':'finish_with_known_risks','risks':'依赖未验证'})['risk_accepted'])

    def test_cancelled_state_can_export_but_cannot_mutate(self):
        s=runner.transition(self.s,'cancel',{})
        self.assertEqual(runner.restore(runner.envelope(s))['status'],'CANCELLED')
        with self.assertRaises(ValueError):runner.transition(s,'batch',self.batch)

    def test_atomic_snapshots_cli_revision_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory);state=directory/'state.json';inp=directory/'input.json'
            def cli(action,data=None,revision=None,output=None):
                command=[sys.executable,str(SCRIPTS/'runner.py'),action,'--state',str(state)]
                if data is not None:inp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');command+=['--input',str(inp)]
                if revision is not None:command+=['--expected-revision',str(revision)]
                if output:command+=['--output',str(output)]
                p=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',env=dict(__import__('os').environ,PYTHONIOENCODING='utf-8'))
                return p.returncode,json.loads(p.stdout)
            self.assertEqual(cli('init',{'goal':'中文目标'})[0],0)
            self.assertNotEqual(cli('init',{'goal':'覆盖'})[0],0)
            self.assertNotEqual(cli('pause',revision=99)[0],0)
            self.assertEqual(cli('pause',revision=1)[0],0)
            self.assertEqual(cli('export',output=directory/'checkpoint.json')[0],0)
            self.assertNotEqual(cli('export',output=state)[0],0)
            self.assertEqual(len(list((directory/'state.json.history').glob('*.json'))),2)
            self.assertEqual(cli('render',output=directory/'state-view.html')[0],0)

    def test_script_injection_is_data_and_unicode_is_readable(self):
        batch=copy.deepcopy(self.batch);batch['questions'][0]['title']='</script><script>evil()</script> 中文'
        fragment=render(batch)
        self.assertNotIn('</script><script>evil()',fragment)
        self.assertIn('中文',fragment)

    def test_every_status_has_exportable_full_snapshot(self):
        s=self.awaiting();s=runner.transition(s,'answers',self.payload(s));s=runner.transition(s,'candidate',{'markdown':'# 计划'})
        s=runner.transition(s,'review',dict(decision='approve',checks={k:True for k in runner.RUBRIC},reasons='逐项自审通过'))
        s=runner.transition(s,'materialize',{})
        self.assertEqual(runner.validate(runner.envelope(s)['session'])['status'],'MATERIALIZED')


if __name__=='__main__':unittest.main()
