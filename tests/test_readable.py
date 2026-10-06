import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/grill-me-extended-lite/scripts'
sys.path.insert(0, str(SCRIPTS))
import runner
import checkpoint_text
from render_app_block import render


class ReadableTests(unittest.TestCase):
    def setUp(self):
        self.s = runner.transition(runner.init('周末读书会'), 'batch', json.loads((ROOT/'examples/round.json').read_text(encoding='utf-8')))
        b = self.s['current_batch']
        self.s = runner.transition(self.s, 'draft', dict(key=':'.join(b[k] for k in ('session_id','batch_id','schema_id')), answers=[dict(question_id=q['id'],selected=[],text='尚不确定' if i==2 else '') for i,q in enumerate(b['questions'])]))
        self.s['decisions'] = ['不要收费', '允许迟到']

    def test_full_lossless_roundtrip_and_unicode(self):
        doc = checkpoint_text.dumps(runner.envelope(self.s))
        self.assertIn('## 目标', doc)
        self.assertIn('<details>', doc)
        self.assertEqual(checkpoint_text.loads(doc)[0], runner.envelope(self.s))

    def test_edit_goal_decisions_question_and_draft_without_json(self):
        doc = checkpoint_text.dumps(runner.envelope(self.s))
        # Only edit readable part; leave embedded machine record unchanged.
        front, back = doc.split('<details>', 1)
        front = front.replace('周末读书会','周日科幻读书会').replace('不要收费','每人十元').replace('尚不确定','预算一百元')
        result, _ = checkpoint_text.loads(front+'<details>'+back)
        restored = runner.restore(result)
        self.assertEqual(restored['goal'], '周日科幻读书会')
        self.assertEqual(restored['decisions'][0], '每人十元')
        self.assertEqual(restored['draft']['answers'][2]['text'], '预算一百元')
        self.assertNotEqual(restored['session_id'], self.s['session_id'])

    def test_safe_repairs_bom_crlf_trailing_comma_and_fullwidth_marker(self):
        value = json.dumps(runner.envelope(self.s), ensure_ascii=False)
        result, report = checkpoint_text.loads('\ufeff```json\r\n'+value[:-1]+',}\r\n```')
        self.assertEqual(result, runner.envelope(self.s))
        self.assertTrue(report)
        doc = checkpoint_text.dumps(runner.envelope(self.s)).replace('grill:goal', 'grill：goal')
        result, report = checkpoint_text.loads(doc)
        self.assertEqual(result, runner.envelope(self.s))
        self.assertTrue(report)

    def test_ambiguous_damage_duplicate_fields_and_json_keys_rejected(self):
        doc = checkpoint_text.dumps(runner.envelope(self.s))
        with self.assertRaises(ValueError): checkpoint_text.loads(doc.replace('<!-- grill:goal -->', '<!-- removed -->'))
        with self.assertRaises(ValueError): checkpoint_text.loads(doc.replace('<!-- /grill:goal -->','<!-- /grill:goal -->\n<!-- grill:goal -->\n矛盾目标\n<!-- /grill:goal -->'))
        with self.assertRaises(ValueError): checkpoint_text.loads('{"format":1,"format":2}')

    def test_multiline_markdown_and_reserved_markers_are_lossless(self):
        self.s['candidate'] = '# 候选\n\n- 项目\n<!-- grill:goal -->\n```json\n{}\n```\n\n'
        doc = checkpoint_text.dumps(runner.envelope(self.s))
        self.assertEqual(checkpoint_text.loads(doc)[0]['session'], self.s)

    def test_history_and_review_edit_preserved(self):
        s = copy.deepcopy(self.s); b = s['current_batch']
        answers = [dict(question_id=q['id'],selected=[],text='历史回答') for q in b['questions']]
        s = runner.transition(s, 'answers',dict(session_id=b['session_id'],batch_id=b['batch_id'],schema_id=b['schema_id'],submission_id='test',answers=answers))
        s = runner.transition(s,'candidate',{'markdown':'# 候选计划'})
        s = runner.transition(s,'review',dict(decision='return',checks={k:False for k in runner.RUBRIC},reasons='缺少安排'))
        doc = checkpoint_text.dumps(runner.envelope(s)); front,back=doc.split('<details>',1)
        result,_=checkpoint_text.loads(front.replace('历史回答','修订回答').replace('缺少安排','补全时间')+'<details>'+back)
        restored=runner.restore(result)
        self.assertEqual(restored['answer_rounds'][0]['answers'][0]['text'],'修订回答')
        self.assertEqual(restored['reviews'][0]['reasons'],'补全时间')

    def test_app_renderer_does_not_rebind_or_allow_script_injection(self):
        b=copy.deepcopy(self.s['current_batch']); b['questions'][0]['title']='</script><script>evil()</script>'
        with self.assertRaises(ValueError):render(b)  # schema is now inconsistent
        b.pop('schema_id'); b=__import__('render_round').normalize(b)
        html=render(b)
        self.assertNotIn('</script><script>evil()',html)
        self.assertIn('生成提交消息',html)
        for forbidden in ('navigator.clipboard','localStorage','sessionStorage','window.openai','fetch(', 'innerHTML'):
            self.assertNotIn(forbidden,html)

    def test_cli_readable_export_repair_writeback_and_branch_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); state=tmp/'original.json';runner.persist(state,self.s)
            doc=tmp/'archive.md';fixed=tmp/'fixed.md'; branch=tmp/'branch.json'
            def cli(action,path,inp=None,out=None):
                args=[sys.executable,str(SCRIPTS/'runner.py'),action,'--state',str(path)]
                if inp:args+=['--input',str(inp)]
                if out:args+=['--output',str(out)]
                return subprocess.run(args,capture_output=True,text=True,encoding='utf-8',env=dict(__import__('os').environ,PYTHONIOENCODING='utf-8'))
            self.assertEqual(cli('export',state,out=doc).returncode,0)
            doc.write_text(doc.read_text(encoding='utf-8').replace('grill:goal','grill：goal'),encoding='utf-8')
            self.assertEqual(cli('repair',state,inp=doc,out=fixed).returncode,0)
            self.assertIn('grill:goal',fixed.read_text(encoding='utf-8'))
            self.assertEqual(cli('import',branch,inp=fixed).returncode,0)
            self.assertEqual(runner.read(state),self.s)
            self.assertNotEqual(runner.read(branch)['session_id'],self.s['session_id'])

