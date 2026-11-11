# Hermes x DFSC

主人的插件仓库：**[7oMB2006/hermes-engineering-bridge](https://github.com/7oMB2006/hermes-engineering-bridge)**。

让 Hermes 理解工程委托、核对交付，让 DFSC 在明确授权的目录执行，
保留原生会话、审批和执行证据；你可以在桌面查看和停止任务。
安装资源与只读检查无需飞书。新增通用本机模式不依赖飞书，
旧 DFSC Hermes 专版的逐委托真人授权与回调继续使用原飞书通道。

本仓库提供 **DFSC 市场资源插件与 Hermes companion**。完整工程派工需要实际支持
所选协议的 DFSC 宿主；本仓库没有包含宿主应用源码、运行时或安装器。
只安装市场资源获得技能、命令和指南，不会自动安装连接服务或授予工程权限。

## 两种连接模式

**新增通用本机模式是源码路径，尚未发布。** 需要明确实现 `dfsc-external-v1` 的构建，
不是任意已发布的 DFSC 0.6.0。用户在「远程访问 → 外部 Agent」显式启用接入、
选择授权项目并创建连接，复制非秘密 `configPath`，再把 companion 安装到独立 profile：

```text
python -X utf8 -B companion/install_profile.py --profile-home PROFILE --desktop-connector HOST_CONFIG
```

安装器保留备份，不重启或重载 Hermes；由用户启用、重载对应 profile。
已有另一连接的 profile 不会被静默覆盖，确认切换才用 `--replace-connection`。
本模式仅创建、单轮派工、查询和停止自己的任务，审批只在 DFSC 本机处理。
没有预算、自动修正、事件唤醒或验收 API。`completed` 仅说明原生轮次结束，
不等于测试通过或用户已验收。本机进程获准接入也不证明后续聊天来自真人。
详情见 [通用本机接入](companion/EXTERNAL.md)。

**旧 DFSC Hermes 专版** 保留原有独立配对、逐委托飞书真人授权、预算及事件能力。
只有该旧路径使用 `--pair` 和原有人工凭据。没有显式 protocol 的配置保持旧模式，
不因能力缺失自动降级，不把新接口冒充旧专版的完整工程协议。

## 组件与兼容

| 组件 | 版本 | 目录 |
| --- | --- | --- |
| DFSC 市场资源插件 | 0.3.0；客户端版本下限 `>=0.6.0` | `plugins/hermes-engineering-bridge/` |
| 本项目维护的 Hermes companion | 0.2.0，不是 Hermes 官方桥 | `companion/` |
| 新增通用 DFSC 宿主 | `dfsc-external-v1`，源码尚未发布 | 需明确支持协议的构建，本仓库不包含 |
| 配套 DFSC Hermes 宿主 | 0.6.0，Bridge 协议 v1 | 单独安装，本仓库不包含 |

目标平台为 macOS Apple Silicon 与 Windows x64。仓库不包含 Hermes/Python 环境、账号、连接凭据、真实 profile、工程任务账本或会话。
客户端版本号达标不证明构建包含 `agent-bridge-v1`、本轮引导或 Agent Bridge 服务；
这些能力须分别确认，不能仅据版本下限或资源安装成功判断可以派工。

## 安装

这是原生市场仓库根目录，`.step-plugin/marketplace.json` 已位于根目录。DFSC 的「插件 → 市场来源 → 添加市场」可填写本仓库 Git 地址：

```text
https://github.com/7oMB2006/hermes-engineering-bridge.git
```

这是公开仓库，不需要为了安装资源向维护者索取仓库权限。也可下载或克隆到本机，
在市场中添加含 `.step-plugin/marketplace.json` 的本地目录绝对路径。
选择 `hermes-engineering-bridge` 安装资源插件，不在 URL 或配置文件中附带 token。

Hermes 侧仍须使用已有 Python/Hermes 环境安装 `companion/`，为每个智能体使用独立身份、授权目录和 profile，再通过可信管理入口完成配对与重载。安装、升级、停用及卸载步骤见 [INSTALL.txt](INSTALL.txt)，companion 说明见 [companion/README.md](companion/README.md)。只安装市场资源不会安装 Hermes、连接消息渠道、创建任务或授予工程权限。

首次使用先读随资源提供的 [开始使用](plugins/hermes-engineering-bridge/docs/START.md)。
新工作台需要支持 `agent-bridge-v1` 及对应引导的客户端。顶栏图标先展开状态小面板，
不切换当前聊天；从「打开完整工作台」进入默认选中的只读连接页。
用户主动选择本机 profile 后，按身份目录、companion 配置、Bridge 配对连接、
授权目录四项查看本次检查证据及下一步。令牌不进入页面，检查不会安装、配对或授权。
这不会给旧普通 DFSC 补装服务，也不证明 companion 已加载或可以派工。
不代表所有已发布 DFSC 安装包都支持；
旧宿主仍可从插件详情阅读本地指南。

## 历史离线资源包

[EngineeringBridge 0.6.0 ZIP](dist/DFSC.Hermes.EngineeringBridge.0.6.0.zip)、
[SHA256](dist/DFSC.Hermes.EngineeringBridge.0.6.0.zip.sha256) 与
[文件清单](dist/DFSC.Hermes.EngineeringBridge.0.6.0.manifest.json) 保留先前交付包的原始字节。
这是历史资源与 companion 包，不是 DFSC 宿主应用安装器，也不代表包含当前资源版本。
尚未取得配套 Bridge 宿主时，联系维护者确认受支持构建，不以下载这个 ZIP 代替。

## 验证与来源

初始实现提取自已验证的工程桥交付包，对应源码提交 `0a42819e3acf7b429e488e770fca5e8126d873a2`。
后续源码新增了显式通用适配，不能把旧交付包的验收直接套用到新模式。
来源与许可见 [ORIGIN.md](ORIGIN.md) 和 [LICENSE](LICENSE)。本仓库是独立插件仓库，不改变既有架构规划仓库。

既有验证包括插件包完整性、临时 profile 的独立安装与升级、中文路径及数据保留、缺文件拒绝，以及 macOS 原生市场发现、安装、技能/命令加载、卸载和重装。宿主另有 Windows/macOS 原生 CI 验收；这些结果不表示主人的 Windows 机器已完成安装，也不替代真实飞书新委托或连续过夜运行。

本仓库 companion 测试从仓库根目录运行：

```sh
python -X utf8 -B -m unittest discover -s companion -p 'test_*.py'
```

测试使用临时目录、受控事件及本地连接，不修改真实 profile、不发飞书消息、不调用模型或派真实工程。新增机器仍需分别记录实际宿主安装、独立配对、只读身份/目录核对与真实业务闭环结果。
