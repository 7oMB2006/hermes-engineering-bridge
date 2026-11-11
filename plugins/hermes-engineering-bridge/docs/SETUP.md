# 连接准备

先在完整工作台的「连接」页选择目标 Hermes 身份目录（profile），再检查。
不知道目录在哪时，先从你启动 Hermes 时使用的 profile 确认，不猜默认身份，
不把模型 Key、令牌或消息渠道凭据发进聊天。

## 身份目录

选择包含 `config.yaml` 的本机 profile，不是 Hermes 源码、Python 环境或市场资源目录。
此项只验证目录和标记文件，不读取配置内容，不证明 Hermes 已安装完整或正在运行。

还没安装 Hermes 时，先按 [Hermes Agent 项目](https://github.com/NousResearch/hermes-agent)
准备自己的环境、模型和独立 profile，并确认它能正常回复普通消息。
安装资源与只读检查无需飞书。当前 companion 0.2.0 发起新工程所需的人工授权、
控制命令和回调在旧专版模式仍使用已配置飞书；
新增通用本机模式不依赖飞书，但没有旧模式的人工授权回调和事件唤醒。

## Companion 配置

Hermes x DFSC companion 是本项目维护的 Hermes 侧桥接插件，不是 Hermes 官方组件。
市场资源包不会把它装进你的 profile。

从 [Hermes x DFSC 项目](https://github.com/7oMB2006/hermes-engineering-bridge)
取得 `companion/`，由你或管理员阅读根目录 `INSTALL.txt` 和 `companion/README.md`。
使用 Hermes 自己的 Python 环境安装到刚才选择的 profile，保留安装器报告的备份。
该目录下应有 `dfsc-bridge/config.json`，其中明确指定身份和 `bridgeRoot`。

配置有效不证明 companion 已启用或加载。安装器不会重载网关；
仍需按 Hermes 的可信管理入口启用、重载目标 profile，并核对成功应答。
可以请 Agent 解释非秘密配置和步骤；配对及权限确认由你或管理员完成，
不要让工程会话搜索凭据或替你批准。

## Bridge 配对与连接

已发布的普通 DFSC 不应仅凭版本号推断可用，资源工作台也不能补装服务。
新增通用本机接入目前是源码路径，尚未发布；
旧普通构建不内置 Agent Bridge 服务时，需要升级到明确支持对应协议的构建。
本仓库不提供宿主应用安装器；尚未取得时，先联系项目维护者确认受支持构建，
不要把历史资源 ZIP 当作宿主安装包。

DFSC `>=0.6.0` 是版本下限，不证明同号安装包已包含连接协议或本轮引导。
工作台的 `agent-bridge-v1` 只读展示协议，也不等于完整旧专版或通用派工协议。

### 新增通用本机模式

明确支持 `dfsc-external-v1` 的构建才可使用，不能套用到任意 0.6.0：

1. 在 DFSC「远程访问 → 外部 Agent」打开「允许本机 Agent 接入」。
2. 填写连接名称，选择一个空练习项目的根目录，核对确认页面后授权。
   这是允许本机进程派工，不会验证后续聊天是否来自真人；审批仍只在本机处理。
3. 复制界面给出的非秘密连接配置路径 `configPath`，不是 model/human 描述符。
4. 在同一份项目源码根目录，用已有 Hermes 环境运行：

```text
python -X utf8 -B companion/install_profile.py --profile-home PROFILE --desktop-connector HOST_CONFIG
```

`PROFILE` 是有 `config.yaml` 的独立 profile，`HOST_CONFIG` 是刚复制的绝对路径。
不加 `--pair`，不手写 token，不猜个人 Step Code 或旧专版的数据目录。
若已有连接不同，安装器拒绝覆盖；确认切换才显式加 `--replace-connection`。
保留备份和旧投递状态，由你启用并重载目标 profile，不会自动重启网关。

可先检查六方法协议，不发工程：

```text
python -X utf8 -B companion/external.py --config HOST_CONFIG system.capabilities
```

应看到 `protocol=dfsc-external-v1`、本身份和实际授权根目录，
支持创建、单轮提交、查询和停止；没有 `human.*`、审批回调、预算或自动验收。
详细安装与错误说明见项目源码的 `companion/EXTERNAL.md`。

### 旧 DFSC Hermes 专版模式

使用实际包含旧 Bridge 协议 v1 的专版宿主，按原管理入口独立配对，
保留原 profile、飞书身份及逐委托真人授权。只有这条旧路径使用安装器 `--pair`。
缺省旧配置继续旧模式，能力缺失不会自动降级或借用其他凭据。

两种模式都不复制其他智能体的 `model.json` / `human.json` 来跳过配对。

回到连接页重新检查。宿主仅使用所选身份的 `model.json` 进行固定只读查询，
页面不接收令牌。通过表示本次查询成功，不证明 companion 已加载或可以派工。

## 授权目录

第一次仅选择一个空的练习目录，由你在所选模式的宿主可信入口明确授权。
连接页展示宿主授权与 companion 配置范围的实际交集，不增加任何权限。
没有可见目录时，核对两侧范围及目录是否存在，不要改成全盘授权来跳过问题。

完整页最多显示首批 50 条中符合身份和目录范围的 20 项任务。
空列表不证明全部历史没有任务，任务摘要不包含对话、工具输出或审批操作。
通用宿主当前每页最多 20 项；最小适配器只取首批状态，不含回答摘要，
也没有开放翻页参数，不能据这批记录或空列表推断全部历史。
通用模式 cwd 只允许所选根目录本身，目录授权不是文件系统沙箱。
其 `completed` 仅表示原生轮次结束，摘要不代替完整工具输出、测试或用户验收。

四项检查后，仍需核对目标 Hermes 已加载 companion 及当前支持的工程授权通道，再由你发起
[第一项任务](FIRST_TASK.md)。异常时看 [排查问题](TROUBLESHOOTING.md)。
「忘记此选择」不修改原 profile、配对文件或授权。
