# Grill Me Extended Lite

面向 ChatGPT **Chat 对话**的决策访谈：当前模型采访、生成 GUI 问卷、整理计划并自审。状态机在 ChatGPT 执行环境离线运行，不启动 localhost MCP，不部署服务器。GitHub 用于一次获取、分享和改造。

## 你要获得的体验

一次创建/安装插件，之后在新 Chat 对话里选择 `@Grill Me Extended Lite`，让它根据当前对话生成单选、多选和补充问卷。点击提交把答案交给同一对话，由离线 runner 校验、保存，再继续采访。最终交付计划.md、进度.md、AGENTS.md。

任意阶段都能说“读取状态”“导出存档”“暂停”“导入这个 JSON 继续”。问卷内也有状态读取、导出草稿、粘贴 JSON 读档入口。JSON 可人工编辑；导入创建恢复分支，原档保留。

## 一次创建和安装

下载 Release 中的 `Grill-Me-Extended-Lite-Setup.md`。在网页 Chat 中选择 **Plugin Creator**，附上安装套件，并发送：

> 请根据附件创建私人插件 Grill Me Extended Lite，将技能、GUI 模板和 Python runner 固定保存为插件资源。我需要在 Chat 模式随时调用，不要创建 MCP 服务、不要要求部署 GitHub。请核验执行工具和 Visualize，创建后帮我做一次 GUI 提交、存档和新聊天读档测试。

按 Plugin Creator 的实际提示完成创建与安装，然后开新聊天选择插件。没有 Plugin Creator、资源执行能力或 Visualize 时，这个账号尚不能满足完整目标；不要把普通附件对话当作一次安装成功。此仓库不能自行授予账号能力。

ZIP 是 Agent Plugins 格式源码/资源包。开发者平台上传会创建草稿并做检查；公开目录还需对应审核发布。GitHub 上传不等于插件全账号可安装。团队可使用自身允许的 GitHub marketplace；个人创建优先用账号提供的 Plugin Creator。

## 条件与当前验证边界

- 需要当前 Chat 有 Python 执行工具、可访问固定插件资源、交互可视化以及发送继续消息的桥。
- GUI 不能执行 Python；点击后模型收到消息，再调用 runner。
- 若桥缺失/失败，答案保留且可复制；不宣称已保存。
- 沙箱文件不是永久存储；请下载 JSON。widget 草稿恢复不保证跨设备。
- 网页/手机支持取决于账号与版本；本项目不宣称你的实际安装已验证。
- 本地 runner 和浏览器模拟验证见 docs/verification.md；真实账号安装与模型行为另需验收。

## 存档、迁移和手工修改

完整状态与历史快照都为 UTF-8 JSON。每次正式操作自动存档；GUI 导出可附未提交草稿。在新聊天附上 JSON，让已安装插件导入并渲染恢复问卷即可。旧界面快照可能较旧，最新状态让模型通过 runner export 获取。

可编辑目标、决定、风险、题目、答案、候选计划与审核记录。格式或状态不一致时导入拒绝，并报告字段；不覆盖原档。存档没有签名，导入历史标为用户提供内容，不能当作独立已验证证据。

## 分享与改造

源资源在 skills/grill-me-extended-lite/。其他用户/agent 可 fork，修改技能与领域模板，重新打包、创建自己的插件。每轮问题基于自身对话，示例只是测试数据。不要把真实会话、个人信息或存档提交公开仓库。

原 MCP 版保留在 [grill-me-extended-cloud](https://github.com/SweetDumplingPorridge/grill-me-extended-cloud)，部署与持久化能力另行保留，不依赖本 Lite。

## 开发验证与打包

```text
python -m unittest discover -s tests -p "test_*.py" -v
npm ci
npx playwright install chromium
npm run test:ui
python scripts/package.py
```

Windows 可通过 CHROME_PATH 指向已安装的 Chrome，PYTHON 指向 Python。npm 只用于开发 UI 测试，用户运行 runner 不需 npm。

官方依据：[对话创建插件](https://learn.chatgpt.com/docs/build-plugins)、[可视化能力](https://learn.chatgpt.com/docs/visualizations)、[插件打包](https://developers.openai.com/plugins/build/plugins)。能力存在仍需在具体账号验证。
