"""Render an App Block HTML fragment. Host must supply its actual App Block emission API."""
import argparse
import json
from pathlib import Path
from render_round import normalize


def render(config):
    if config.get('state_view'):
        data=dict(session_id=config['session_id'],batch_id='state-view',schema_id='state-view',round=config['round'],questions=[],state_view=True)
    else:
        data=normalize(config)
        if config.get('schema_id')!=data['schema_id']:
            raise ValueError('App Block requires the unchanged runner batch and schema_id')
    if config.get('draft') is not None: data['draft']=config['draft']
    template=(Path(__file__).parent.parent/'templates/questionnaire-app-block.html').read_text(encoding='utf-8')
    raw=json.dumps(data,ensure_ascii=False).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    return template.replace('__GRILL_CONFIG_JSON__',raw)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();fragment=render(json.loads(args.input.read_text(encoding='utf-8-sig')))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(fragment,encoding='utf-8')

