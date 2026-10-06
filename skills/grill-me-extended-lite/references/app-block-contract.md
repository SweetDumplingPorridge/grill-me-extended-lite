# App Block：首选交互组件

依据用户提供的 Android 实测交接：radio、checkbox、textarea、button 与本地 JS 可用。此版本采用手动回传，没有自动 callback 依赖。宿主的 App Block 输出封装必须以当前宿主实际提供的协议为准；仓库中的 HTML 是组件内容，不是协议本身，不要发明工具名或输出标记。

## 输出

1. 通过 runner batch 生成当前轮，runner render 默认输出 App Block 片段。
2. 使用当前 Chat 的真实 App Block 组件能力输出该片段。若只有宿主专用工具/内置输出语法，使用它当前的正式说明；不把普通 HTML 代码块或下载链接当作组件。
3. App Block 不可用时使用 runner render --renderer visualize 与 GUI 协议；两者都不可用时明确告知并使用聊天文本问卷。没有 Python 执行时说明 runner 未运行，不能宣称正式状态已持久化。

App Block 只能复制 runner 的 session_id、batch_id、schema_id、round；不能重绑定身份或创建新的业务批次。包含三种问题类型，推荐不预选，补充文本最多 1000 字，支持 320px 和触屏。

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

本地测试覆盖三题型、320/390/1280、未预选、相同答案幂等 ID、修改 ID、草稿恢复、错误草稿保持原填写、存档回传。真实 Android/网页 App Block 封装仍由用户验收，浏览器渲染通过不等于 ChatGPT 客户端通过。
