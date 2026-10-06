"""Lossless readable checkpoint overlay and conservative syntax repair. No model calls."""
import copy
import json
import re

FORMAT = 'grill-me-extended-lite-checkpoint'
LABELS = {'goal':'目标','decisions':'已确认决定','remaining_areas':'未决事项与风险','candidate':'候选计划',
          'current_batch':'当前问卷','answer_rounds':'历史问答','questions':'问题','title':'题目','recommendation':'建议与理由',
          'options':'选项','label':'选项文字','answers':'回答','selected':'已选选项','text':'补充回答',
          'draft':'未提交草稿','reviews':'审核记录','reasons':'审核理由'}


def unique(pairs):
    result = {}
    for k,v in pairs:
        if k in result: raise ValueError(f'重复 JSON 字段 {k}，不能确认取哪一个')
        result[k] = v
    return result


def trailing_commas(raw):
    # Scan string tokens intact, so text such as ",}" is never changed.
    tokens = re.compile(r'"(?:[^"\\]|\\.)*"|,(?=\s*[}\]])', re.S)
    return tokens.sub(lambda m: m[0] if m[0].startswith('"') else '', raw)


def parse_json(raw, repairs):
    try: return json.loads(raw, object_pairs_hook=unique)
    except json.JSONDecodeError:
        fixed = trailing_commas(raw)
        if fixed == raw: raise ValueError('JSON 结构有误，需要 agent 根据上下文修复；不能猜测答案或删除字段')
        try: result = json.loads(fixed, object_pairs_hook=unique)
        except json.JSONDecodeError as exc: raise ValueError(f'JSON 无法明确修复：{exc}') from exc
        repairs.append('移除字符串外的末尾逗号')
        return result


def fields(state):
    """Expose business text, preserving machine IDs, transitions and evidence in the baseline."""
    def walk(value, path, title):
        if isinstance(value, str) or value is None:
            yield path, title, value, 'text'
        elif isinstance(value, list):
            if all(isinstance(x,str) for x in value):
                yield path,title,value,'list'
            else:
                for i,item in enumerate(value):
                    yield from walk(item, f'{path}/{i}', f'{title} · {i+1}')
        elif isinstance(value, dict):
            for key,item in value.items():
                if key in {'goal','title','recommendation','label','text','selected','reasons'} or isinstance(item,(dict,list)):
                    yield from walk(item, f'{path}/{key}', f'{title} / {LABELS.get(key,key)}')
    for key in ('goal','decisions','remaining_areas','current_batch','draft','answer_rounds','candidate','reviews'):
        value=state[key]
        if value is None and key not in {'candidate'}: continue
        yield from walk(value,key,LABELS[key])


def encode(value,kind):
    if kind=='list':
        # Multiline entries use a visible continuation indent; empty line is preserved.
        text='\n'.join('- '+x.replace('\n','\n  ') for x in value)
    else: text=value or ''
    # These escapes prevent user content impersonating a field marker. Ordinary Markdown is left alone.
    return text.replace('&','&amp;').replace('<!--','&lt;!--')


def decode(body, kind):
    body=body.replace('&lt;!--','<!--').replace('&amp;','&')
    if kind=='text': return body
    if not body: return []
    items=[]
    for line in body.split('\n'):
        if line.startswith(('- ','* ','• ')): items.append(line[2:])
        elif re.match(r'^\d+[.、)] ',line): items.append(re.sub(r'^\d+[.、)] ','',line))
        elif line.startswith('  ') and items: items[-1]+='\n'+line[2:]
        else: raise ValueError('列表项边界不明确：请由 agent 修复为每项一行，勿合并或丢失内容')
    return items


def assign(state,path,value):
    parts=path.split('/');node=state
    for part in parts[:-1]: node=node[int(part)] if isinstance(node,list) else node[part]
    if isinstance(node,list): node[int(parts[-1])]=value
    else: node[parts[-1]]=value


def dumps(checkpoint):
    state=checkpoint['session']
    parts=['# Grill Me Lite 存档\n\n这是完整访谈存档。直接修改各节正文；列表每项一行。文末机器记录用于无损恢复，通常无需编辑。\n',
           f"会话：{state['session_id']}　版本：{state['revision']}　轮次：{state['round']}　状态：{state['status']}\n"]
    for path,title,value,kind in fields(state):
        parts.append(f'\n## {title}\n<!-- grill:{path} -->\n{encode(value,kind)}\n<!-- /grill:{path} -->\n')
    raw=json.dumps(checkpoint,ensure_ascii=False,separators=(',',':'))
    parts.append('\n<details>\n<summary>机器记录（保留即可，不需手改；人类正文优先）</summary>\n\n<!-- grill:machine -->\n```json\n'+raw+'\n```\n<!-- /grill:machine -->\n</details>\n')
    return ''.join(parts)


def loads(raw):
    if not isinstance(raw,str) or len(raw.encode('utf-8'))>5_000_000: raise ValueError('存档文本过大或不是文本')
    repairs=[]
    if raw.startswith('\ufeff'): raw=raw[1:];repairs.append('移除 UTF-8 BOM')
    if '\r' in raw: raw=raw.replace('\r\n','\n').replace('\r','\n');repairs.append('统一换行')
    raw=raw.strip()
    fence=re.fullmatch(r'```(?:json|markdown|md)?\s*\n(.*?)\n```',raw,re.S)
    if fence: raw=fence[1];repairs.append('移除粘贴的外层代码围栏')
    if raw.startswith('{'): return parse_json(raw,repairs),repairs
    # Only repair punctuation in known technical markers, never globally in human text.
    fixed=re.sub(r'(<!--\s*/?grill)\s*：',r'\1:',raw)
    if fixed!=raw:repairs.append('修复字段标记的全角冒号');raw=fixed
    machine=re.findall(r'<!--\s*grill:machine\s*-->\s*```json\s*\n(.*?)\n```\s*<!--\s*/grill:machine\s*-->',raw,re.S)
    if len(machine)!=1: raise ValueError('机器记录缺失或重复；需要 agent 结合原存档恢复，不能新建空历史')
    checkpoint=parse_json(machine[0],repairs)
    if not isinstance(checkpoint,dict) or checkpoint.get('format')!=FORMAT or checkpoint.get('format_version')!=1:
        raise ValueError('不支持的存档类型')
    original=checkpoint['session'];state=copy.deepcopy(original)
    front=raw.split('<!-- grill:machine -->')[0]
    pattern=r'<!--\s*grill:([a-z_0-9/]+)\s*-->\n(.*?)\n<!--\s*/grill:\1\s*-->'
    records=re.findall(pattern,front,re.S)
    if len({p for p,b in records})!=len(records): raise ValueError('重复正文区域：需要确认哪个版本有效')
    blocks=dict(records);expected={p for p,t,v,k in fields(original)}
    if set(blocks)!=expected: raise ValueError(f'正文区域缺失或多出：{sorted(expected.symmetric_difference(blocks))}；先修复再导入')
    for path,title,value,kind in fields(original):
        body=blocks[path]
        if body!=encode(value,kind): assign(state,path,decode(body,kind))
    # Editing the candidate invalidates prior approval; old reviews remain historical evidence.
    if state!=original and state['status'] in {'APPROVED','MATERIALIZED'}:
        state['status']='REVIEW_PENDING';repairs.append('已审核计划的正文已修改，回到待审核')
    checkpoint['session']=state
    return checkpoint,repairs

