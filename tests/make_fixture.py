import json
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'skills/grill-me-extended-lite/scripts'))
import runner
from render_round import render
s=runner.transition(runner.init('仅测试用示例'),'batch',json.loads((root/'examples/round.json').read_text(encoding='utf-8')))
config=dict(s['current_batch'],session_snapshot=runner.envelope(s))
(root/'artifacts').mkdir(exist_ok=True)
(root/'artifacts/round.html').write_text(render(config),encoding='utf-8')
