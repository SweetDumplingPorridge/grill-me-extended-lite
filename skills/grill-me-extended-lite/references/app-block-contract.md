# App Block：首选交互组件

依据用户提供的 Android 实测交接：radio、checkbox、textarea、button 与本地 JS 可用。此版本采用手动回传，没有自动 callback 依赖。宿主的 App Block 输出封装必须以当前宿主实际提供的协议为准；仓库中的 HTML 是组件内容，不是协议本身，不要发明工具名或输出标记。

## 输出

### GenUI Direct Mode 能力发现

用户在 Android 同一 Chat 会话的实际反馈：App Block 已成功显示，首轮的错误降级源于普通工具列表未出现 app_block。Direct Mode widget 不注册为普通函数，因此 **ALL_TOOLS 缺失 != App Block 缺失**。

检查当前宿主正式注入的 GenUI/widget metadata，例如 genui_search_tool_results → direct_mode → direct_mode_tools → app_block。这是能力描述的层级示例，不是要求调用一个假设存在的同名函数。声明 app_block 就选择 Direct Mode；按其当次 invocation contract 输出 GenUI content reference。若明确禁止 genui_run，则不得使用 genui_run，也不得寻找 MCP app_block 或通过 functions.exec 假调用。

交接文档中的 content reference 示例为空，不能从中恢复具体语法。不要自行补造；使用当前宿主正式 contract 或同会话已成功使用的协议。不把普通 HTML code block 冒充 App Block。

选择顺序：Direct Mode App Block → 其他正式 App Block surface → Visualize → 文本。只有正式能力确认 App Block 各入口都不存在后才能 fallback；信息缺失只是未知，先继续查宿主说明，不能因普通函数列表为空就降级。Direct Mode 存在时，无论 ALL_TOOLS 内容如何均选择 App Block。

### 创建或重新展示

1. 新业务轮次才通过 runner batch 生成当前轮；重新展示已有问卷则先 get 现有活动分支，再 runner render。render 默认输出 App Block 片段，不修改 state。
2. 使用当前 Chat 的真实 App Block 组件能力输出该片段。若只有宿主专用工具/内置输出语法，使用它当前的正式说明；不把普通 HTML 代码块或下载链接当作组件。
3. App Block 不可用时使用 runner render --renderer visualize 与 GUI 协议；两者都不可用时明确告知并使用聊天文本问卷。没有 Python 执行时说明 runner 未运行，不能宣称正式状态已持久化。

App Block 只能复制 runner 的 session_id、batch_id、schema_id、round；不能重绑定身份或创建新的业务批次。包含三种问题类型，推荐不预选，补充文本最多 1000 字，支持 320px 和触屏。

修复错误 fallback 不能重新 init 或 batch；重新渲染前后的 session_id、batch_id、schema_id、round、revision 和 answer_rounds 必须完全不变。若已 import，则沿用 import 后的新分支，不退回原分支。组件打开/草稿填写不触发 answers；只有用户发送协议消息并由 runner answers 校验成功才推进状态。

## 手动回传

“生成提交消息”产生 GRILL_LITE_ANSWERS_V1 换行加 JSON，用户复制完整消息到当前聊天。聊天读取最新 revision，调用 runner answers --expected-revision，成功才确认“已记录答案，revision N”。同一组答案复用 submission_id，改答案生成新 ID。旧组件不映射到新批次；runner 拒绝旧会话或旧 schema。

组件不访问网络、存储、文件、剪贴板 API，也不调用 window.openai。全选只是方便系统复制，不代表复制或提交成功。

## 草稿与完整存档

- 查看当前填写内容／导出当前草稿：中文纯文本草稿，只包含当前问卷与未提交填写。组件状态不代表 runner 最新状态，不包含完整历史。
- 导入草稿：恢复同一 session/batch/schema 的控件，先验证全部答案，错误时原填写不变。兼容旧 grill-lite-app-draft JSON 格式；中文草稿可以交给聊天修复。
- 导入存档：识别完整 Markdown 或 JSON，生成 GRILL_LITE_IMPORT_V1 加原文。用户发送到聊天，runner import 到新路径创建恢复分支。组件本身不恢复 runner。
- 完整存档：在聊天请求“导出最新状态”，runner export --output 存档.md。要包含未发送草稿，先把组件草稿发给聊天，由模型按当前批次校验并调用 runner draft，再 export。

切换设备或重新渲染不保证保留未发送草稿。需要存档时手动复制草稿或发送到聊天，正式存档下载到自己设备保存。

## 验收

0.2.1 定向回归清单（客户端由用户验证）：A. Direct Mode 声明 app_block、ALL_TOOLS 无 app_block，仍直接出组件；B. App Block 正式确认不可用但有 Visualize，选旧 renderer；C. 两者确实不可用，明确说明后用文本且 runner 继续；D. 重绘不改变身份、round/revision；E. 320px 三题型、按钮、读取、reset 可用；F. 未发送草稿不改变 revision/answer_rounds；G. 正式 answers 后 revision +1、current_batch 清空、answer_rounds +1、SYNTHESIZING；H. get/export Markdown/repair/import 新分支保持业务资料、原文件保留。

本地测试覆盖三题型、320/390/1280、未预选、相同答案幂等 ID、修改 ID、草稿恢复、错误草稿保持原填写、存档回传。真实 Android/网页 App Block 封装仍由用户验收，浏览器渲染通过不等于 ChatGPT 客户端通过。
