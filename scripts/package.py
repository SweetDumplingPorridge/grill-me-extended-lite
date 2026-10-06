"""Create installable-resource ZIP and a one-time Plugin Creator attachment."""
import hashlib
import json
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'plugin.json').read_text(encoding='utf-8'))
paths=[root/'plugin.json',root/'README.md']
for folder in ('skills','assets'):
    paths.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
names=[p.relative_to(root).as_posix() for p in paths]
assert len(names)==len(set(names))
assert 'mcp.json' not in names and '.mcp.json' not in names
for field in ('composerIcon','logo'):
    assert manifest['extensions']['com.openai']['interface'][field].removeprefix('./') in names
for p in paths:
    p.read_text(encoding='utf-8')
output=root/'releases';output.mkdir(exist_ok=True)
name=f"grill-me-extended-lite-{manifest['version']}.zip"
with zipfile.ZipFile(output/name,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(paths):z.write(p,p.relative_to(root).as_posix())
with zipfile.ZipFile(output/name) as z:
    assert z.testzip() is None and 'plugin.json' in z.namelist()
digest=hashlib.sha256((output/name).read_bytes()).hexdigest()
(output/(name+'.sha256')).write_text(f'{digest}  {name}\n',encoding='utf-8')
intro='''# Grill Me Extended Lite：一次创建安装套件

这是提供给 Plugin Creator 的源资源，不是已安装证明。请创建私人插件，并将以下各个带路径的资源固定保存在插件中，之后调用不再读取 GitHub、不要求用户重新上传或部署。

运行方式：当前 ChatGPT 采访、自审；Python 标准库 runner 在宿主执行环境维护 JSON 状态；可视化显示问卷；明确提交后模型调用 runner。不要启动 localhost MCP 或远程服务。

先确认此账号 Chat 的插件资源访问、Python 执行工具、Visualize 和消息桥。如果缺少关键能力，应明确报告，不能将文本版声称为 GUI 完成。按当前宿主的输出协议适配，而非仅打印 HTML。安装后的新聊天必须能直接调用该技能并读取所有资源，不能只把文件留在创建对话的临时沙箱。

测试：在一个新 Chat 中显式选择插件，生成三种题型，点击提交并由 runner 确认；导出带未提交草稿的完整 JSON；再开新 Chat 导入，恢复题目、答案、决定和自审记录。只在实际观察后声称通过。完成后提供宿主真实插件入口，保留下面的来源版本信息。

'''
chunks=[intro]
for p in sorted(paths):
    lang={'.json':'json','.py':'python','.html':'html','.svg':'xml','.md':'markdown'}.get(p.suffix,'text')
    text=p.read_text(encoding='utf-8')
    fence='`'*(max([len(x) for x in __import__('re').findall(r'`+',text)]+[2])+1)
    chunks.append(f"\n## 资源：{p.relative_to(root).as_posix()}\n\n{fence}{lang}\n{text.rstrip()}\n{fence}\n")
(output/'Grill-Me-Extended-Lite-Setup.md').write_text(''.join(chunks),encoding='utf-8')
print(f'Validated {len(paths)} packaged UTF-8 resources; {name}; SHA256 {digest}')
