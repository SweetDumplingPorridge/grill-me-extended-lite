# Grill Me Extended Lite 0.2.0

在普通 Chat 对话里采访、生成问卷、整理计划并自审。Python 标准库 runner 离线保存权威状态，不部署服务器、不启动 localhost MCP。GitHub 用于一次安装、分享和改造。

## 安装与升级

下载 [Release](https://github.com/SweetDumplingPorridge/grill-me-extended-lite/releases) 中的最新 ZIP。在 ChatGPT 网页插件页面选择 **添加 → 上传插件压缩包**，上传后按页面提示添加/安装。已装 0.1.0 时，在旧插件的编辑/更新入口上传新版；若账号只提供新增入口，添加新版并确认版本 0.2.0 后选择新版调用。保留自己的存档。

之前已实际通过网页 ZIP 上传安装 0.1.0，页面识别技能并显示“在聊天中试用”；GUI 能力当时未通过。0.2.0 的真实网页/Android App Block 验收由用户完成。ZIP 不能给账号添加缺失的执行或组件能力。

安装后新建 Chat，选择 `@Grill Me Extended Lite`：

> 拷问我，用内置 App Block 问卷把这个对话里的想法收敛成计划。

## 交互方式

App Block 优先，不可用时尝试旧 Visualize，再到聊天文本问卷。单选、多选、自由文本；推荐不预选；适配 320px 触屏。当前 **手动回传**：填写 → 生成提交消息 → 全选/复制 → 发送到当前聊天 → runner 校验 → 聊天确认正式记录。没有自动回调依赖。

组件可查看填写、导出/恢复本轮草稿、生成存档读档消息、清空本轮。它不读取最新 runner 状态、不保存完整历史、不访问网络或剪贴板 API。换设备之前请复制草稿，或发给聊天录入后正式导出。

## 人类友好的完整存档

任意时刻说“读取状态”“导出最新状态”“暂停并存档”或“导入这份存档继续”。默认得到 **中文 Markdown**：目标、决定、风险、问题、选项、答案、草稿、候选计划、审核理由都是正文；完整机器记录折叠在文末。直接修改正文，列表每项一行，不需要手改 JSON 引号、括号和转义。

格式损坏时 agent **先尝试自动修复并返回修复后文件**，不覆盖原文。能唯一确定的标记、围栏、换行、末尾逗号等修复不额外打扰用户。冲突答案、缺失语义或无法确定字段才询问。修复后仍须 runner 校验，不伪造答案或审核成功。已审核计划的业务内容修改后重新进入审核。

旧 JSON 存档仍可读写。导入创建新恢复分支，原 state 保留；旧组件不能写入新分支。存档不带签名，历史作为用户提供资料。沙箱文件不是永久存储，请下载保存。

## 分享和开发

资源位于 skills/grill-me-extended-lite/。用户或 agent 可 fork 后修改领域、题目与计划模板，重新打包；每轮根据当前对话生成问题。不要把真实存档提交到公开仓库。

原 [MCP 版](https://github.com/SweetDumplingPorridge/grill-me-extended-cloud) 保留，独立于本 Lite。

```text
python -m unittest discover -s tests -p "test_*.py" -v
npm ci
npx playwright install chromium
npm run test:ui
python scripts/package.py
```

npm 仅用于开发测试；runner 仅需 Python 3.10+。Windows 可以通过 CHROME_PATH 指定 Chrome。

组件实现依据用户提供的 Android App Block 实测交接；官方公开文档暂未确认其通用输出语法，技能要求使用当前宿主实际协议，不发明工具。真实端到端支持需客户端验收。旧 Visualize 参见[官方可视化说明](https://learn.chatgpt.com/docs/visualizations)。
