# Hermes 工程桥资源包

这是 DFSC Hermes 0.6 的市场配套插件。它提供 `hermes-engineering-evidence` 技能、`hermes-bridge-help` 命令和插件图标；没有 MCP 调度工具或可执行 entry。

完整闭环需要两个组件：DFSC Hermes 宿主中的 Agent Bridge，以及装入对应 Hermes profile 的 companion。资源包安装不会复制账号、注册飞书或自动启用工程权限。

完整安装说明见仓库根目录 `INSTALL.txt`；安装器位于同层的
`companion/install_profile.py`，不在本资源插件内部。本仓库 companion 位于根目录
`companion/`。每个智能体独立配对、独立存储状态；不把 profile 凭据放入本插件。

从仓库根目录运行（使用 Hermes 的 Python 环境）：

```
python -X utf8 companion/install_profile.py --profile-home PROFILE --config companion.json --pair
```

参数路径按当前主机填写，使用 Hermes 已配置的 Python；使用独立 Python 时可补
`--hermes-source HERMES_SOURCE_ROOT`。配置格式见仓库根目录 `INSTALL.txt` 或
`companion/README.md`。安装器会备份现有插件；安装完成后按 companion 指引重载
对应 profile。普通市场资源包不能自行调用配对或人工管理能力。

## 兼容

- DFSC Hermes 0.6.0，Bridge 协议 v1。
- macOS Apple Silicon、Windows x64。
- 标准 DFSC 0.6.0 也可以安装本资源包，但没有 Agent Bridge 宿主能力时，安装仅提供文档与技能，不能派工。

## 升级与卸载

市场管理沿用 DFSC 的原生安装/卸载操作。先查看版本与来源；更新资源包时卸载旧包再安装新包，宿主任务/原生会话和 Hermes profile 数据不在此插件目录内。运行中的会话可能保留已加载技能，配置变化遵循原生会话生命周期。

停用整个工程桥请在 DFSC 面板关闭接入；卸载资源包不会自动停止正在执行的工程，
也不会撤销 Hermes companion。Hermes 侧通过其插件管理独立停用或卸载；单个智能体
的宿主权限由可信管理通道调整登记。当前 companion 安装器仅提供安装与配对，
没有卸载或解除配对参数。完整流程见仓库根目录 `INSTALL.txt`。
