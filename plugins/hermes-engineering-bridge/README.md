# Hermes x DFSC

资源版本 **0.3.0**。让 Hermes 理解委托、核对交付，让 DFSC 在授权目录执行工程，
保留原生会话、审批和执行证据。

自动执行或长期委托前，请阅读 [风险说明](docs/RISKS.md)。
新版通用 companion 要求宿主风险确认接口及显式插件关联；
缺少时只保留查询、停止，不继续派工或代审批。

## 这次安装得到什么

本地指南、帮助命令与工程证据规范。支持 `agent-bridge-v1` 及本轮引导的客户端
还提供连接工作台。DFSC `>=0.6.0` 是版本下限，不证明构建包含协议或 Bridge 服务。

顶栏图标先展开状态小面板，不切换当前聊天；再次点击、Escape 或点击外部收起。
点击「打开完整工作台」，选择目标 Hermes 身份目录（profile），再重新检查。
完整页按身份目录、companion 配置、Bridge 配对连接、授权目录显示证据及下一步。
小面板只显示本次核验身份和首批最多 5 项任务，不是实时在线状态。

## 还要准备什么

- 你自己的 Hermes Agent、模型和独立 profile。安装资源与只读检查无需飞书。
- 本项目维护的 Hermes x DFSC companion 0.2.0，单独安装、启用并重载目标 profile。
- 实际支持所选协议的 DFSC 宿主，以及独立配对和明确目录授权。

有两条不同路径：

- **新增通用本机模式，源码尚未发布：** 需要明确提供 `dfsc-external-v1` 的构建。
  在「远程访问 → 外部 Agent」人工打开开关、选择授权项目并创建连接，
  复制非秘密 `configPath`，用 `--desktop-connector HOST_CONFIG` 安装到独立 profile，
  再由你启用、重载。此模式不依赖飞书；一任务只派一轮，审批仅在 DFSC 本机完成。
- **旧 DFSC Hermes 专版：** 保留原配对与逐委托飞书真人授权，
  旧配置缺省不切换。只有旧路径使用 `--pair` 和既有预算、事件及审批回调。

两种模式都不能仅凭版本号判断支持，不能混用凭据或因为连接失败自动降级。
通用模式配对允许本机进程派工，不验证后续聊天是否来自真人；
没有旧专版的预算、事件唤醒或验收 API。`completed` 不等于测试或验收通过。

companion 不是 Hermes 官方提供的桥。市场资源不包含 Hermes/Python 环境、
companion 安装器、宿主应用安装器、MCP 调度服务或可执行前端脚本。
配套代码及管理说明在 [项目仓库](https://github.com/7oMB2006/hermes-engineering-bridge)
的 `companion/`、`INSTALL.txt`；新增通用路径详见源码的 `companion/EXTERNAL.md`。
尚未取得对应构建时，先确认宿主实际支持，不把历史资源 ZIP 当宿主安装器。

## 下一步

- [开始使用](docs/START.md)：安装得到什么，接下来做什么。
- [连接准备](docs/SETUP.md)：四项检查分别说明什么，缺项如何处理。
- [第一项任务](docs/FIRST_TASK.md)：由你发起空目录练习，核对真实交付。
- [排查问题](docs/TROUBLESHOOTING.md)：入口、连接、任务和移除。
- [更新记录](CHANGELOG.md)。

检查不会自动安装、配对、授权或派工；目录通过不证明 Hermes 正在运行，
配置通过不证明 companion 已加载，只读连接通过不证明可以派工。
`hermes-bridge-help` 只提供帮助，`hermes-engineering-evidence` 规范工程证据。
更新市场后还需更新已安装副本；资源更新后需重新选择 profile。
卸载资源不会停止工程，也不会撤销 companion 或宿主权限。
