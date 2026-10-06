# GUI 与宿主协议

GUI 使用宿主交互可视化片段，在对话内渲染，不使用远程服务。

## 资源

`templates/questionnaire.html` 是 HTML 片段（没有 html/head/body/doctype）。用当前轮 JSON 替换唯一 `__GRILL_CONFIG_JSON__`，通过宿主认可的方式输出；有 Python 时可用 `scripts/render_round.py input.json --output <宿主可读取的绝对路径>`。脚本只在宿主执行环境使用，不在用户电脑部署。

输出标记以当前宿主说明为准。支持该协议的 ChatGPT/Codex 宿主使用独立一行：

`visualize{"path":"<片段的实际绝对路径>"}`

路径必须实际生成、可供宿主读取；这个标记不能单独赋予账号 GUI 能力。仅在最终回复呈现片段引用。不要展示 HTML 源码冒充交互内容。

## 配置形状

```json
{"session_id":"session-unique","batch_id":"round-unique","round":1,"questions":[{"id":"q1","type":"single","title":"决定什么？","recommendation":"建议与理由","options":[{"id":"a","label":"方案 A"},{"id":"b","label":"方案 B"}]}]}
```

`render_round.py` 自动添加配置内容摘要 `schema_id`。single/multi 题 options 至少 2 个且 ID 唯一；text 不含选项。最多 7 题；候选选择总数每题最多 8 个。配置不包含整个聊天历史、密钥或不必要个人信息。

单选/多选允许其他补充，文本允许“尚不确定”。不默认选择推荐答案。提交时先验证本轮全部题目，防止空答案冒充已答。

## 消息桥

主操作使用 `await window.openai.sendFollowUpMessage({prompt,title})`，发送 `GRILL_LITE_ANSWERS_V1` 加 JSON。用户按下按钮是明确提交，可能经过宿主确认弹窗。UI 显示“提交中”，防止并发重复。

消息包含 session_id、batch_id、schema_id、submission_id 与 answers；模型收到后自行按权威台账校验。相同 payload 的重试复用 submission_id；改答案产生新 submission_id。UI 不自动启动第三方调用、不发网络请求。

桥不存在或调用失败时保留答案，显示可复制消息与“复制答案”按钮，用户可贴进当前聊天。不伪造已送达。剪贴板失败时保留可选文本。按钮成功后锁住该轮；没有确认到达聊天时仍可复制该消息。

## 草稿

可选使用 widgetState/setWidgetState 与 openai:set_globals 恢复同一配置的草稿。按 session_id + batch_id + schema_id 绑定，不接收另一题目的草稿。存储失败不妨碍提交。保存每轮答案和必要标识，不保存秘密；小于 16KiB。modelContent 为 null，答案只由明确提交送入模型。此状态既不是独立服务存储，也不保证跨设备或长期恢复。

## 安全与移动端

配置内 JSON 必须转义 `<`、`>`、`&` 及 Unicode 行分隔符，用户文案用 textContent 和原生表单节点，不用 innerHTML。问卷不执行来自问题/答案的代码。

使用宿主 form-check/form-control/btn 类与主题变量，不覆盖控件样式。320px 堆叠，无固定外宽、内部滚动或 viewport-height。有效触屏目标约 44px，textarea 宿主保证手机字号。保留键盘焦点，fieldset/legend 和 live status；没有 hover 才能使用的功能。

宿主样式和接口变化时保留协议语义，适配其当前 API；模板只是当前接口实现，不能推断所有账号已支持。
