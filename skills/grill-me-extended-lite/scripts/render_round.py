"""Build a host visualization fragment; standard library only, no server."""
import argparse
import hashlib
import json
from pathlib import Path


def normalize(config):
    result = {k: config[k] for k in ('session_id', 'batch_id', 'round', 'questions')}
    for key in ('session_id', 'batch_id'):
        if not isinstance(result[key], str) or not 1 <= len(result[key]) <= 100:
            raise ValueError(f'Invalid {key}')
    if type(result['round']) is not int or result['round'] < 1:
        raise ValueError('Invalid round')
    questions = result['questions']
    if not isinstance(questions, list) or not 1 <= len(questions) <= 7:
        raise ValueError('Expected 1–7 questions')
    ids = set()
    cleaned = []
    for q in questions:
        item = {k: q[k] for k in ('id', 'type', 'title', 'recommendation')}
        for key in ('id', 'title', 'recommendation'):
            if not isinstance(item[key], str) or not 1 <= len(item[key]) <= (100 if key == 'id' else 600):
                raise ValueError(f'Invalid question {key}')
        if item['id'] in ids or item['type'] not in ('single', 'multi', 'text'):
            raise ValueError('Duplicate question ID or invalid type')
        ids.add(item['id'])
        if item['type'] != 'text':
            options = q.get('options')
            if not isinstance(options, list) or not 2 <= len(options) <= 8:
                raise ValueError('Expected 2–8 options')
            option_ids = set()
            item['options'] = []
            for option in options:
                oid, label = option['id'], option['label']
                if not isinstance(oid, str) or not 1 <= len(oid) <= 100 or oid in option_ids:
                    raise ValueError('Invalid option ID')
                if not isinstance(label, str) or not 1 <= len(label) <= 600:
                    raise ValueError('Invalid option label')
                option_ids.add(oid)
                item['options'].append({'id': oid, 'label': label})
        cleaned.append(item)
    result['questions'] = cleaned
    canonical = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    if len(canonical.encode('utf-8')) > 30000:
        raise ValueError('Split this oversized batch')
    result['schema_id'] = hashlib.sha256(canonical.encode()).hexdigest()[:20]
    return result


def render(config):
    snapshot, draft = config.get('session_snapshot'), config.get('draft')
    if config.get('state_view') is True and snapshot:
        config = dict(session_id=config['session_id'], batch_id='state-view', round=config['round'], schema_id='state-view', questions=[], state_view=True)
    else:
        config = normalize(config)
    if snapshot is not None:
        config['session_snapshot'] = snapshot
    if draft is not None:
        config['draft'] = draft
    template = (Path(__file__).parent.parent / 'templates/questionnaire.html').read_text(encoding='utf-8')
    data = json.dumps(config, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    return template.replace('__GRILL_CONFIG_JSON__', data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    fragment = render(json.loads(args.input.read_text(encoding='utf-8-sig')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(fragment, encoding='utf-8')
