# 来源、许可与验证边界

本仓库初始插件实现提取自 `DFSC.Hermes.EngineeringBridge.0.6.0.zip`，交付包 SHA256：

```text
4ec8c675aa4039dae26b2dc6a1f5d148c601e2acbf03ab6a4cec74099b037f8b
```

该包对应 DFSC Hermes 工程树的已提交源码 `0a42819e3acf7b429e488e770fca5e8126d873a2`。提取范围是根市场清单、`plugins/` 市场资源、`companion/` 安装源及说明；另从相同工程树补入两个 `test_*.py`。运行代码、资源及测试保持原样；仓库 README、安装说明与维护规则按独立插件仓库调整。

原交付 ZIP 的 `PACKAGE.json` 记录的是原 ZIP 文件集及旧文档的哈希，因此没有原样复制到这个仓库。它也不能用作本仓库当前 tree 的校验清单。本仓库文件以 Git 提交记录为准。

原工程的 MIT 许可证及版权声明完整保留于 `LICENSE`。Copyright (c) 2026 Desktop for Step Code contributors。维护与后续交付使用主人的 canonical 仓库 `7oMB2006/hermes-engineering-bridge`。

本次是插件代码及市场目录的迁入，**不是 DFSC Hermes 宿主应用迁仓**。宿主内置 Agent Bridge、Step Code 运行时和操作系统安装器仍是独立组件。资源版本 0.1.0、companion 0.2.0 与配套宿主 0.6.0 是不同组件的版本。

已有交付验证包括 ZIP 内容哈希、独立临时 profile 安装/升级、中文路径、原有数据保留及缺文件拒绝；macOS 原生市场检查覆盖发现、安装、技能/命令加载、卸载与重装。配套宿主在此前双端原生 CI 中通过源码及包内验收，原宿主提交为 `c3a4b8ddb728065569100a13150b1a201975f457`；这些不是本仓库新增 CI 运行结果。

主人的 Windows 实机安装、新的真实飞书工程委托及连续过夜运行没有在本次迁仓中重新完成，不以受控测试代替。测试输出应另行记录，不打包真实账号、profile 或任务数据。
