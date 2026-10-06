"""Offline JSON state machine. No sockets, service, or third-party dependencies."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid
from datetime import datetime, timezone
from render_round import normalize, render

STATUSES = {'COLLECTING', 'AWAITING_USER', 'SYNTHESIZING', 'REVIEW_PENDING', 'NEEDS_MORE', 'APPROVED', 'MATERIALIZED', 'PAUSED', 'CANCELLED'}
RUBRIC = ['consistent_scope', 'decided_tradeoffs', 'implementable_interfaces', 'recovery_permissions', 'executable_acceptance', 'handoff', 'no_undecided_high_impact']


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    raw = Path(path).read_bytes()
    if len(raw) > 5_000_000:
        raise ValueError('Snapshot exceeds 5 MB; split attachments from state')
    return json.loads(raw.decode('utf-8-sig'))


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate(state):
    required = {'schema_version', 'session_id', 'goal', 'status', 'revision', 'round', 'max_rounds', 'risk_accepted', 'current_batch', 'answer_rounds', 'decisions', 'remaining_areas', 'candidate', 'reviews', 'idempotency', 'events', 'created_at', 'updated_at', 'draft'}
    if not isinstance(state, dict) or not required <= state.keys() or state.get('schema_version') != 1:
        raise ValueError('Incomplete or unsupported state schema')
    if state['status'] not in STATUSES:
        raise ValueError('Unknown status')
    for key in ('session_id', 'goal', 'created_at', 'updated_at'):
        if not isinstance(state[key], str) or not state[key].strip():
            raise ValueError(f'Invalid {key}')
    for key in ('revision', 'round', 'max_rounds'):
        if type(state[key]) is not int or state[key] < (0 if key == 'round' else 1):
            raise ValueError(f'Invalid {key}')
    if state['round'] > state['max_rounds'] or type(state['risk_accepted']) is not bool:
        raise ValueError('Invalid round limit or risk acceptance')
    for key in ('answer_rounds', 'decisions', 'remaining_areas', 'reviews', 'events'):
        if not isinstance(state[key], list):
            raise ValueError(f'Expected list: {key}')
    if any(not isinstance(x, str) for key in ('decisions', 'remaining_areas') for x in state[key]):
        raise ValueError('Decisions and remaining areas must be strings')
    if not isinstance(state['idempotency'], dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in state['idempotency'].items()):
        raise ValueError('Invalid idempotency records')
    if state['candidate'] is not None and not isinstance(state['candidate'], str):
        raise ValueError('Candidate must be text or null')
    batch = state['current_batch']
    if batch is not None:
        normalized = normalize(batch)
        if normalized != batch or batch['session_id'] != state['session_id'] or batch['round'] != state['round']:
            raise ValueError('Current batch schema/identity mismatch; remove schema_id to recalculate in import')
    active = state.get('resume_status') if state['status'] == 'PAUSED' else state['status']
    if state['status'] == 'PAUSED' and state.get('resume_status') not in STATUSES - {'PAUSED','CANCELLED'}:
        raise ValueError('Invalid paused resume status')
    if active == 'AWAITING_USER' and batch is None:
        raise ValueError('Awaiting user requires a batch')
    if active in {'REVIEW_PENDING','APPROVED','MATERIALIZED'} and not state['candidate']:
        raise ValueError('This status requires candidate text')
    draft = state['draft']
    if draft is not None:
        if not isinstance(draft, dict) or not isinstance(draft.get('answers'),list) or batch is None:
            raise ValueError('Invalid draft')
        if draft.get('key') != ':'.join(batch[k] for k in ('session_id','batch_id','schema_id')):
            raise ValueError('Draft belongs to a different batch')
        check_answers(batch, draft['answers'], partial=True)
    for entry in state['answer_rounds']:
        if not isinstance(entry,dict) or not isinstance(entry.get('batch'),dict):
            raise ValueError('Invalid answer history')
        normalize(entry['batch'])
        check_answers(entry['batch'], entry.get('answers'))
    for record in state['reviews']:
        if not isinstance(record,dict) or record.get('decision') not in ('approve','return') or not isinstance(record.get('checks'),dict):
            raise ValueError('Invalid review history')
    return state


def check_answers(batch, answers, partial=False):
    if not isinstance(answers,list):
        raise ValueError('Answers must be a list')
    ids = [a.get('question_id') for a in answers if isinstance(a,dict)]
    questions = {q['id']:q for q in batch['questions']}
    if len(ids) != len(answers) or len(set(ids)) != len(ids) or set(ids) != set(questions):
        raise ValueError('Answers must match exactly the current questions')
    for a in answers:
        q=questions[a['question_id']]
        selected=a.get('selected',[]); text=a.get('text','')
        if not isinstance(text,str) or len(text)>1000 or not isinstance(selected,list) or any(not isinstance(x,str) for x in selected):
            raise ValueError('Invalid answer value')
        if len(set(selected))!=len(selected) or any(x not in {o['id'] for o in q.get('options',[])} for x in selected):
            raise ValueError('Invalid or duplicate selected option')
        if q['type']=='single' and len(selected)>1:
            raise ValueError('Single choice has multiple answers')
        if not partial and not selected and not text.strip():
            raise ValueError('Missing answer; explicitly say unknown if necessary')


def envelope(state):
    return {'format':'grill-me-extended-lite-checkpoint','format_version':1,'session':copy.deepcopy(state)}


def init(goal):
    if not isinstance(goal,str) or not goal.strip():
        raise ValueError('Goal required')
    return dict(schema_version=1,session_id=str(uuid.uuid4()),goal=goal,status='COLLECTING',revision=1,round=0,max_rounds=12,risk_accepted=False,current_batch=None,answer_rounds=[],decisions=[],remaining_areas=[],candidate=None,reviews=[],idempotency={},events=[{'type':'init','at':now()}],created_at=now(),updated_at=now(),draft=None)


def transition(state, action, data):
    s=copy.deepcopy(state)
    allowed={'batch':{'COLLECTING','SYNTHESIZING','NEEDS_MORE'},'answers':{'AWAITING_USER'},'candidate':{'SYNTHESIZING','COLLECTING','NEEDS_MORE'},'review':{'REVIEW_PENDING'},'resume':{'PAUSED'},'materialize':{'APPROVED'}}
    # Successful retries return the same state even when its status/revision advanced.
    if action=='answers':
        identifier=data.get('submission_id')
        digest=hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        if identifier in s['idempotency']:
            if s['idempotency'][identifier]!=digest: raise ValueError('Submission ID reused with changed answers')
            return s
    if action in allowed and s['status'] not in allowed[action]:
        raise ValueError(f"{action} cannot run in {s['status']}")
    if s['status']=='CANCELLED': raise ValueError('Session cancelled; import as a new branch if needed')
    if action=='batch':
        if s['round']>=s['max_rounds']: raise ValueError('Round limit: use limit with explicit user choice')
        s['round']+=1
        config=dict(data,session_id=s['session_id'],round=s['round'],batch_id=data.get('batch_id') or str(uuid.uuid4()))
        s['current_batch']=normalize(config);s['draft']=None;s['status']='AWAITING_USER'
    elif action=='answers':
        if not isinstance(identifier,str) or not 1<=len(identifier)<=100: raise ValueError('Submission ID required')
        batch=s['current_batch']
        if any(data.get(k)!=batch[k] for k in ('session_id','batch_id','schema_id')): raise ValueError('Stale or unrelated batch')
        check_answers(batch,data.get('answers'))
        s['answer_rounds'].append({'batch':copy.deepcopy(batch),'answers':data['answers'],'submission_id':identifier,'at':now()})
        s['idempotency'][identifier]=digest;s['current_batch']=None;s['draft']=None;s['status']='SYNTHESIZING'
    elif action=='decisions':
        if s['status'] in {'PAUSED','APPROVED','MATERIALIZED'}: raise ValueError('Cannot edit decisions in this status')
        s['decisions']=data['decisions'];s['remaining_areas']=data['remaining_areas']
    elif action=='candidate':
        if not isinstance(data.get('markdown'),str) or not data['markdown'].strip(): raise ValueError('Candidate text required')
        s['candidate']=data['markdown'];s['status']='REVIEW_PENDING'
    elif action=='review':
        checks=data.get('checks',{})
        if set(checks)!=set(RUBRIC) or any(type(v)is not bool for v in checks.values()): raise ValueError('Seven boolean review checks required')
        decision=data.get('decision'); reasons=data.get('reasons')
        if decision not in ('approve','return') or not isinstance(reasons,str) or not reasons.strip(): raise ValueError('Review decision and reasons required')
        if decision=='approve' and not all(checks.values()) and not s['risk_accepted']: raise ValueError('Failed review cannot approve without explicit risk acceptance')
        s['reviews'].append(dict(data,at=now()));s['status']='APPROVED' if decision=='approve' else 'NEEDS_MORE'
    elif action=='limit':
        if s['status'] not in {'NEEDS_MORE','SYNTHESIZING','COLLECTING'} or s['round']<s['max_rounds']: raise ValueError('Round limit choice not due')
        if data.get('choice')=='continue':s['max_rounds']+=12
        elif data.get('choice')=='finish_with_known_risks' and isinstance(data.get('risks'),str) and data['risks'].strip():
            s['risk_accepted']=True;s['remaining_areas'].append(data['risks'])
        else:raise ValueError('Explicit continue or finish_with_known_risks plus risk text required')
    elif action=='pause':
        if s['status']=='PAUSED':raise ValueError('Already paused')
        s['resume_status']=s['status'];s['status']='PAUSED'
    elif action=='resume':s['status']=s.pop('resume_status')
    elif action=='cancel':s['status']='CANCELLED'
    elif action=='draft':
        if s['status']!='AWAITING_USER':raise ValueError('Draft requires current questionnaire')
        s['draft']=data
    elif action=='materialize':s['status']='MATERIALIZED'
    else:raise ValueError('Unknown action')
    s['revision']+=1;s['updated_at']=now();s['events'].append({'type':action,'revision':s['revision'],'at':now()})
    return validate(s)


def restore(checkpoint):
    if not isinstance(checkpoint,dict) or checkpoint.get('format')!='grill-me-extended-lite-checkpoint' or checkpoint.get('format_version')!=1:
        raise ValueError('Unsupported checkpoint envelope')
    s=copy.deepcopy(checkpoint['session'])
    if s.get('current_batch') is not None:
        # Manual edits recalculate the batch signature; invalid selections still fail validation.
        s['current_batch']=normalize(s['current_batch'])
        if s.get('draft'):
            s['draft']['key']=':'.join(s['current_batch'][k] for k in ('session_id','batch_id','schema_id'))
    validate(s)
    previous=s['session_id'];s['session_id']=str(uuid.uuid4())
    if s['current_batch']:
        s['current_batch']['session_id']=s['session_id'];s['current_batch']=normalize(s['current_batch'])
        if s['draft']:s['draft']['key']=':'.join(s['current_batch'][k] for k in ('session_id','batch_id','schema_id'))
    s['revision']+=1;s['updated_at']=now();s['events'].append({'type':'import_branch','from_session':previous,'at':now(),'note':'User-supplied snapshot; historical review is not independently verified'})
    return validate(s)


def persist(path,state):
    validate(state)
    history=path.parent/(path.name+'.history')
    atomic(history/f"{state['revision']:06}-{uuid.uuid4().hex}.json",envelope(state))
    atomic(path,state)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['init','get','validate','export','import','render','batch','answers','decisions','candidate','review','limit','pause','resume','cancel','draft','materialize'])
    parser.add_argument('--state',required=True,type=Path)
    parser.add_argument('--input',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--expected-revision',type=int)
    args=parser.parse_args()
    action=args.action;path=args.state.resolve()
    data=read(args.input) if args.input else {}
    if action in {'get','validate','export','render'}:
        state=validate(read(path))
        if action=='export':
            if not args.output:raise ValueError('--output required')
            if args.output.resolve()==path:raise ValueError('Export cannot overwrite working state')
            atomic(args.output,envelope(state));return envelope(state)
        if action=='render':
            if not args.output:raise ValueError('--output required')
            if args.output.resolve()==path:raise ValueError('Render cannot overwrite working state')
            config=dict(state['current_batch'] or dict(session_id=state['session_id'],round=state['round'],state_view=True),session_snapshot=envelope(state),draft=state['draft'])
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(render(config),encoding='utf-8')
            return {'path':str(args.output.resolve()),'revision':state['revision']}
        return state
    path.parent.mkdir(parents=True,exist_ok=True)
    lock=path.with_name(path.name+'.lock')
    descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        if action in {'init','import'}:
            if path.exists():raise ValueError('Use a new state path; existing state is preserved')
            state=init(data.get('goal')) if action=='init' else restore(data)
        else:
            state=validate(read(path))
            if args.expected_revision!=state['revision']:
                # Permit exact answer retry; never permit a different mutation on stale revision.
                if action!='answers' or data.get('submission_id') not in state['idempotency']:
                    raise ValueError(f"Revision conflict: current {state['revision']}")
            state=transition(state,action,data)
        persist(path,state)
        return state
    finally:
        os.close(descriptor);lock.unlink()


if __name__=='__main__':
    try:print(json.dumps({'ok':True,'result':main()},ensure_ascii=False))
    except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError) as error:
        print(json.dumps({'ok':False,'error':str(error)},ensure_ascii=False));sys.exit(1)
