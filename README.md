# Hermes × DFSC 飞书工程桥

主人的插件仓库：**[7oMB2006/hermes-engineering-bridge](https://github.com/7oMB2006/hermes-engineering-bridge)**。

让 Hermes 智能体接收飞书工程委托，通过 DFSC 的真实原生会话派工、观察执行证据、处理审批并验收；主人可以在桌面查看和接管同一会话。

本仓库提供 **DFSC 市场资源插件与 Hermes companion**。完整工程派工还需要已经具备 Agent Bridge 的 DFSC Hermes 宿主；本次没有把宿主应用源码、运行时或安装器迁入此仓库。普通 DFSC 安装资源插件后只获得技能、命令和说明。

## 组件与兼容

| 组件 | 版本 | 目录 |
| --- | --- | --- |
| DFSC 市场资源插件 | 0.1.0 | `plugins/hermes-engineering-bridge/` |
| Hermes companion | 0.2.0 | `companion/` |
| 配套 DFSC Hermes 宿主 | 0.6.0，Bridge 协议 v1 | 单独安装，本仓库不包含 |

目标平台为 macOS Apple Silicon 与 Windows x64。仓库不包含 Hermes/Python 环境、账号、连接凭据、真实 profile、工程任务账本或会话。

## 安装

这是原生市场仓库根目录，`.step-plugin/marketplace.json` 已位于根目录。DFSC 的「插件 → 市场来源 → 添加市场」可填写本仓库 Git 地址：

```text
https://github.com/7oMB2006/hermes-engineering-bridge.git
```

私有仓库需要 DFSC 所调用的 Git 已有有效认证；不要把 token 放入 URL 或配置文件提交。也可以用自己的 GitHub 账号下载或克隆到本机，然后在市场中添加含 `.step-plugin/marketplace.json` 的本地目录绝对路径。选择 `hermes-engineering-bridge` 安装资源插件。

Hermes 侧仍须使用已有 Python/Hermes 环境安装 `companion/`，为每个智能体使用独立身份、授权目录和 profile，再通过可信管理入口完成配对与重载。安装、升级、停用及卸载步骤见 [INSTALL.txt](INSTALL.txt)，companion 说明见 [companion/README.md](companion/README.md)。只安装市场资源不会自动连接飞书、创建任务或授予工程权限。

## 已验证的离线安装包

[下载 EngineeringBridge 0.6.0 ZIP](dist/DFSC.Hermes.EngineeringBridge.0.6.0.zip)；对应 [SHA256](dist/DFSC.Hermes.EngineeringBridge.0.6.0.zip.sha256) 与 [文件清单](dist/DFSC.Hermes.EngineeringBridge.0.6.0.manifest.json) 同目录提供。这是先前已验证交付包的原始字节，包内来源提交和逐文件清单描述该 ZIP；仓库文档已另按独立仓库调整。

## 验证与来源

初始实现提取自已验证的工程桥交付包，对应源码提交 `0a42819e3acf7b429e488e770fca5e8126d873a2`。运行代码保持一致，文档按独立仓库调整，来源与许可见 [ORIGIN.md](ORIGIN.md) 和 [LICENSE](LICENSE)。本仓库是独立插件仓库，不改变既有架构规划仓库。

既有验证包括插件包完整性、临时 profile 的独立安装与升级、中文路径及数据保留、缺文件拒绝，以及 macOS 原生市场发现、安装、技能/命令加载、卸载和重装。宿主另有 Windows/macOS 原生 CI 验收；这些结果不表示主人的 Windows 机器已完成安装，也不替代真实飞书新委托或连续过夜运行。

本仓库 companion 测试从仓库根目录运行：

```sh
python -B -m unittest discover -s companion -p 'test_*.py'
```

测试使用临时目录、受控事件及本地连接，不修改真实 profile、不发飞书消息、不调用模型或派真实工程。新增机器仍需分别记录实际宿主安装、独立配对、只读身份/目录核对与真实业务闭环结果。
