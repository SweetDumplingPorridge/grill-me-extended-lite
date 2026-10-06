# 离线 runner 和 JSON 存档

脚本：skills/grill-me-extended-lite/scripts/runner.py。仅 Python 3.10+ 标准库，宿主执行工具调用；不启动进程服务，不监听端口，不需 npm、Docker、MCP 或模型 API。

## 一次安装后的使用

技能/资源应由插件携带，或由 Plugin Creator 创建时固定嵌入。每次访谈从已安装资源读取，不访问 GitHub。宿主没有资源访问或执行能力时不能运行 runner，必须明确报出该条件；安装包本身不授予额外执行权限。

通用形式：

```text
python <插件资源>/scripts/runner.py <action> --state <当前宿主任务目录>/state.json [--input input.json] [--expected-revision N] [--output output.json或html]
```

普通操作输入为 JSON；import/repair 同时接受中文 Markdown、文本或旧 JSON 存档，命令行不嵌入用户文本。输出为 JSON ok/result 或 ok:false/error；失败退出码为 1。任何报错后 get 读取真实状态，不把失败命令当成功。

## 命令与输入

| action | 输入与效果 |
|---|---|
| init | `{ "goal": "用户目标" }`；只写新 state 路径 |
| get / validate | 全状态读取/校验，不修改 |
| batch | 题目配置 questions，自动补 session_id、轮次、batch_id、schema_id |
| answers | GUI 的 GRILL_LITE_ANSWERS_V1 后面的 JSON，校验后进入 SYNTHESIZING |
| decisions | decisions 字符串列表、remaining_areas 字符串列表 |
| candidate | markdown：完整计划文本，进入 REVIEW_PENDING |
| review | decision approve/return、checks 七个布尔值、reasons 文本 |
| limit | 到轮次门槛后用户明确 choice continue，或 finish_with_known_risks 加 risks 文本 |
| pause / resume / cancel | 不需要 input；保留全状态 |
| draft | `{key,answers}`；允许部分空答案，不计为提交 |
| export | 默认 --output 存档.md；指定 .json 保留旧格式；任意状态可执行 |
| repair | --input 存档.md --output 新修复文件.md；确定性格式修复、验证并写回新副本，不修改 state |
| import | --input 存档.md 或 checkpoint.json；--state 指向新路径，保留原存档，恢复成新 session_id |
| render | --output questionnaire.html 默认 App Block；--renderer visualize 为旧 GUI；无问卷时提供状态操作说明 |
| materialize | 宿主已实际生成三份文档后才标记 MATERIALIZED；此命令自身不写文档 |

修改动作（init/import 除外）必须带最新 revision；完全相同的答案重试允许旧 revision，不能变更 payload。读写锁已有时退出 BUSY/文件存在错误，不抢占；崩溃残留锁要核实执行已停止后人工处理。

review checks 必须逐项覆盖：consistent_scope、decided_tradeoffs、implementable_interfaces、recovery_permissions、executable_acceptance、handoff、no_undecided_high_impact。所有 true 才正常 approve；有失败项且明确 risk_accepted 时必须保留风险交付标签。该检查记录模型自审，不证明事实已验证。

## 文件与随时存档

state.json：完整 UTF-8 JSON，可读取。每次成功操作旁边产生 state.json.history/<revision>-<unique>.json，含相同完整状态。checkpoint 外壳：

```json
{"format":"grill-me-extended-lite-checkpoint","format_version":1,"session":{"schema_version":1,"...":"完整状态字段"}}
```

session 包含 goal、status、revision、round/max_rounds、risk_accepted、current_batch、answer_rounds（完整题目和答案）、decisions、remaining_areas、candidate、reviews、idempotency、events、时间和 draft。不是整个聊天记录；聊天中尚未整理进状态的背景可由用户补充，不能宣称恢复全部对话。

手动修改可使用任意文本编辑器。保留外壳和必需字段；题目修改自动重算 schema_id；删除选项时同步调整 draft 或已记录答案，错误会拒绝导入。导入记录为用户提供快照，原审核记录不能被当作独立已验证证据。没有加密或签名；用户可以编辑，不能用于防篡改审计。

App Block 导出只含本轮草稿，正式完整存档必须聊天执行 export。旧 Visualize 导出来自该界面渲染时快照，可能过时。草稿不会被当作已提交答案。格式修复与正文修改详见 readable-state.md。
