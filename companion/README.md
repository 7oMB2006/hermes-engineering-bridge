# Hermes 工程桥 companion 0.2

## 通用 DFSC 接入

本源码新增显式 `dfsc-external-v1` 适配，使用
`--desktop-connector HOST_CONFIG` 安装到独立 profile。它不依赖飞书，
只支持创建、单轮派工、查询和停止，审批仍在 DFSC 本机完成。
详见 [通用本机接入说明](EXTERNAL.md)。需要确实包含该协议的宿主构建，
不能仅据 DFSC 版本号或资源安装成功判断支持。当前没有新增发行验收声明。

缺省配置继续使用下文旧 DFSC Hermes 专版，绝不自动切换协议或借用旧凭据。
旧专版到通用模式的切换需显式 `--replace-connection`，备份与旧投递状态保留。

## 旧专版模式

同一份插件安装到各自的 Hermes profile；名称、任务范围和连接位置由各 profile
的 `dfsc-bridge/config.json` 指定。原有 `delivery.json`、会话记忆、`.env` 与飞书身份保留。
本插件运行于 Hermes 生命周期，不作为 Step Code 的 MCP 工具暴露工程调度或人工审批。

## 配置与配对

配置格式（路径按当前主机填写，不包含凭据）：

```json
{
  "schemaVersion": 1,
  "agentId": "my-engineer",
  "displayName": "工程助手",
  "bridgeRoot": "/absolute/path/to/DFSC Hermes/agent-bridge",
  "workspaceRoots": ["/absolute/path/to/project"],
  "roleInstructions": "按照主人的工程委托，通过 DFSC 执行修改并核对验收证据。",
  "titlePrefix": true
}
```

首次安装通过管理终端运行，使用 Hermes 已配置的 Python 环境：

```
python install_profile.py --profile-home PROFILE --config companion.json --pair
# 若直接使用独立 Python，可再指定 --hermes-source HERMES_SOURCE_ROOT
```

`--pair` 是可信人工管理入口：合并宿主现有 agent 登记，读取根 human 凭据，创建
独立 `agents/<agentId>/model.json` 和 `human.json`。两者分别用于模型派工和已核验
飞书真人回调；模型工具和薄 CLI 均无配对及人工管理能力。配置范围为空时，首次
配对取当前 DFSC 已授权目录；后来新增目录需再次明确配对，不能由模型扩大范围。
不传 `--pair` 只更新插件和非秘密配置。安装器先创建唯一备份，不重载或重启网关；
宿主切换完成后再调用 Hermes 官方插件重载接口。

macOS 使用 Unix socket；Windows x64 使用带独立凭据的 `127.0.0.1` TCP。
连接地址来自宿主描述符，客户端拒绝非 loopback TCP、错误 agentId 和错误角色。
这是应用层权限边界，不是同用户 shell 的操作系统沙箱。

## 现有角色迁移

- 小刻：`agentId=h-keke`；设置主人原有通用工程授权目录与原职责说明。
  旧记录只有精确 `agent:h-keke:` sessionKey 前缀时可识别归属，未标记记录不猜测。
- 小蟹：`agentId=h-xiexie`；设置现有 XDJ 根目录和允许独立研究脚本的原职责说明。
- 两个 profile 使用同一插件代码，分别保留配置、delivery 游标、机器人凭据与卡片记录。
- 不把插件内部旧固定 actor 文案当成真实归属；以授权身份与任务 origin 为准。

从 0.5.1 的根连接描述符迁移时，按下面顺序处理：

1. 记录已授权工程根目录、两份旧插件中的职责和范围，独立备份应用数据、两份插件与各 profile 的 `config.yaml`、`dfsc-bridge/`。不复制飞书或模型凭据到市场包。
2. 在现有工程允许切换时安装并启动 0.6 宿主，保持应用身份和数据目录，核对原任务及自主审批开关。宿主启动不代表允许重派或继续任务。
3. 为各 profile 准备非秘密配置 JSON。小刻使用已授权工程范围；小蟹保留原 XDJ 根目录，`roleInstructions` 保留其金融研究、模拟仓、可自行编写研究脚本、应用工程修改交给 DFSC 的分工。不要为方便安装扩大范围。
4. 对两份 profile 分别运行安装器并传 `--pair`。安装器合并其他 agent 登记并检查版本，宿主生成专属描述符；不能把根 `model.json` / `human.json` 复制进 agent 目录冒充配对。只有宿主与配置都就绪后，才分别重载对应 Hermes profile 的插件。
5. 使用各自的 `dfsc-bridge --profile-home PROFILE system.capabilities` 与 `task.list` 核对身份、根目录及历史任务；恢复会话只查询已有记录，不发起实际工程。旧的指向 profile 插件目录的 CLI 符号链接可继续使用，但现在只返回该 profile 的任务，不能当作全局管理查询。

必须同步 `__init__.py`、`configuration.py`、`scope.py`、`client.py`、`plugin.yaml`、`dfsc-bridge` 和 `skills/SKILL.md`；由安装器创建 `dfsc-bridge/config.json` 并保留原 `delivery.json`。缺少显式配置时插件不会注册工具，单独复制新 `__init__.py` 后重载不足以完成迁移。独立 agent 描述符由宿主负责，companion 不保存或复制 token。

重载后首次订阅会按宿主当前归属核对缓存，清除旧消费者可能看见的其他角色卡片和唤醒记录，保留原事件游标。旧卡片仍需匹配当前真实请求、任务归属与操作者才可生效；迁移不延长额度、不改变验收状态、不生成新主人授权。

## 验证

`python -m unittest discover -s . -p 'test_*.py'` 包含真实 socket 取消与 loopback
连接测试，以及身份/角色校验、跨 agent 范围、真实飞书回调形状、审批竞争语义和
重连保留历史的受控测试。测试不发送飞书消息、不调用模型、不派真实工程。
描述符与投递状态始终使用 UTF-8；受控测试覆盖非 UTF-8 系统文本编码下的中文与 emoji 读写恢复。
