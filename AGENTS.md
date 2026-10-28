# 仓库范围

- 唯一 canonical 插件仓库是 `7oMB2006/hermes-engineering-bridge`。外部操作使用主人已连接的 GitHub 账号；不要沿用其他账号的 GH_CONFIG_DIR 或 CLI 凭据。对来源实现的记录不构成使用来源仓库账号的授权。
- 本仓库只有原生市场资源和 Hermes companion；DFSC Hermes 宿主源码、运行时和应用安装器未迁入。
- 保留 `.step-plugin/marketplace.json` 在仓库根目录，保持每个智能体的独立身份与授权目录；不扩大权限，不通过模型提供配对或人工管理能力。
- 不提交真实 profile、配置、`.env`、token、连接描述符、任务账本、原生会话、运行日志或个人绝对路径。
- 测试使用临时 profile 和本地受控传输；不发真实消息、调用模型或派真实工程。宿主 CI、插件测试与真实飞书/过夜验收分别报告。
- 从根目录运行：`python -B -m unittest discover -s companion -p 'test_*.py'`。保留 MIT LICENSE 及 ORIGIN.md 的来源归属。
