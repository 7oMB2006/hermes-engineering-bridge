# 通用 DFSC 本机接入

此路径用于明确包含 `dfsc-external-v1` 的 DFSC 构建，与旧 DFSC Hermes
专版分开。本轮是源码适配，不代表市场、发行安装器或真实 Hermes gateway 已完成验收。
仅匹配 `>=0.6.0` 不能证明宿主实现了此协议。

新 companion 还要求 `pluginConfirmations.version=1`，且此连接明确关联
`hermes-engineering-bridge`。接口或关联缺失时阻止创建、提交及代审批，
保留查询和停止；不会静默跳过风险确认或切换旧协议。

## 安装后得到什么

DFSC 负责连接身份、项目目录授权和原生会话。Hermes companion 只负责把
受限方法提供给当前 profile，不依赖飞书、不读取 `.env`。
支持的宿主可由 companion 后台线程接收审批通知，定向唤醒原 Hermes 会话。
模型和 Hermes 本体仍需自行安装配置。DFSC 必须运行，本机入口必须启用。

本模式一任务只派一轮。支持创建、提交、查询和停止自己的任务；
审批默认在 DFSC 本机处理。新宿主可按任务或身份与项目长期委托，
普通命令、文件修改、高风险工具、提问与回答独立选择。
没有个人实验模式的预算、自动跟进、修正或验收能力，也不会因为能力缺失而回退到旧凭据。

## 配对和安装

1. 在受支持 DFSC 的「远程访问 → 外部 Agent」启用本机接入。
2. 安装本项目资源插件后填写连接名称，只选择此次确实允许操作的项目根目录，
   在「关联插件」选择 Hermes x DFSC，确认创建。
   已有普通连接可在无进行中任务和长期策略时明确关联；关联不是自动授予审批权。
   这允许该本机进程发起任务，不证明它接收到的后续聊天来自真人。
3. 复制界面提供的 `config.json` 路径。它是非秘密连接配置，
   实际 token 只在宿主的专属 `agents/<agentId>/model.json` 中；
   不复制、发送或手工修改 model/human 描述符。
4. 用已安装 Hermes 的 Python 环境运行安装器，指定已存在且有 `config.yaml`
   的独立 profile。若该 Python 缺少 `hermes_yaml`，沿用旧安装器的
   `--hermes-source` 参数指向 Hermes 源码。

从仓库根目录运行：

```sh
python -X utf8 -B companion/install_profile.py --profile-home PROFILE --desktop-connector HOST_CONFIG
```

`HOST_CONFIG` 是上一步复制的绝对路径，不是 `model.json`，也不是旧专版配置。
此命令不能与 `--pair` 同用，不读取人工凭据，不修改 DFSC 的授权。
如果目标 profile 已配置另一协议、身份、宿主或目录，安装会拒绝覆盖；
确认确实需要切换后才追加 `--replace-connection`。首次安装更建议新建独立 profile。

安装器先备份原配置和插件，结果报告 `backup`、`protocol`、
`reloadRequired`；旧 `delivery.json`、`.env`、旧宿主凭据和其他模型设置保留。
`paired:false` 表示安装器未实施配对，配对已经在 DFSC 完成，不代表当前连通性。
安装器不重启或重载 Hermes。按该 profile 原有方式激活或重载后，在新会话确认
`dfsc_engineering` 方法枚举与宿主实际能力匹配，不能仅据文件安装成功判断已加载。

## 独立连通性检查

无需 Hermes Python 库，也可从仓库根目录直接检查宿主：

```sh
python -X utf8 -B companion/external.py --config HOST_CONFIG system.capabilities
python -X utf8 -B companion/external.py --config HOST_CONFIG task.list
```

CLI 通过真实 loopback socket 连接。每次读取当前 model 描述符，并先核对
capabilities 的协议、身份、授权目录和支持方法。错误时输出固定代码，退出非零；
不会读取 `human.json`、自动配对或重新派工。

安装后的诊断入口也会根据 profile 中的显式 protocol 选择模式：

```sh
python -X utf8 -B PROFILE/plugins/hermes-dfsc/dfsc-bridge --profile-home PROFILE system.capabilities
```

公开配置固定包含六个字段，不含 token。路径使用 DFSC 实际生成的值，不猜个人配置目录：

```json
{
  "schemaVersion": 1,
  "protocol": "dfsc-external-v1",
  "agentId": "assigned-identity",
  "displayName": "工程助手",
  "bridgeRoot": "/absolute/host/connector-root",
  "workspaceRoots": ["/absolute/authorized/project"]
}
```

## 最小首次任务

先在空白测试项目验证，勿直接用重要工程。请 Hermes：

> 查询 DFSC 连接能力，在已授权的测试项目创建一个任务，要求只回复
> `DFSC 连接成功`，不要改文件或运行命令。提交后告诉我任务 id，不要反复轮询。

工具调用顺序：

```text
system.capabilities {}
task.create {"key":"first-create-1","cwd":"授权根目录","title":"首次连接检查"}
run.submit {"taskId":"返回的id","key":"first-submit-1","message":"只回复 DFSC 连接成功，不改文件、不运行命令。"}
task.get {"taskId":"返回的id"}
```

`task.get` 在用户询问时调用，不是循环。每个逻辑操作固定 key/内容，
超时先 `task.list` 或 `task.get` 核对，不能更换 key 或重复建单。
在 DFSC 原生会话核对真实回复、目录与审批状态，查询摘要只能作为导航信息。
`completed` 只代表原生轮次结束，不等于测试通过、用户接受或工程验收。

CLI 的派工方法也有实际副作用，仅在人工明确委托的测试项目使用，例如：

```sh
python -X utf8 -B companion/external.py --config HOST_CONFIG task.create --params '{"key":"first-create-1","cwd":"/absolute/authorized/project","title":"首次连接检查"}'
python -X utf8 -B companion/external.py --config HOST_CONFIG run.submit --params '{"taskId":"返回的id","key":"first-submit-1","message":"只回复 DFSC 连接成功，不改文件、不运行命令。"}'
```

Windows PowerShell 可将参数以哈希表序列化，避免路径反斜杠和中文转义错误：

```powershell
$Params = @{key='first-create-1'; cwd='C:\Projects\authorized-project'; title='首次连接检查'} | ConvertTo-Json -Compress
python -X utf8 -B companion/external.py --config $HostConfig task.create --params $Params
```

## 支持的方法

| 方法 | 参数 | 语义 |
| --- | --- | --- |
| `system.capabilities` | `{}` | 当前协议、身份、实际根目录及可用方法 |
| `task.create` | `key,cwd,title` | 幂等创建专属原生会话，默认 Ask，可按本机长期策略选「代我批准」 |
| `run.submit` | `taskId,key,message` | 每任务只提交一轮，重复相同 key/内容复用回执 |
| `task.list` | `{}` | 当前适配器读取首批至多 20 条本身份任务状态，不含回答摘要 |
| `task.get` | `taskId` | 有界状态与当前 DFSC 进程已捕获的回答摘要 |
| `task.stop` | `taskId` | 撤回未发输入，或停止已开始的本身份原生任务 |
| `approval.list` | `taskId` | 当前显式委托、完整可审阅的审批 |
| `approval.respond` | `taskId,requestId,decision,reason`，可选 `answers` | 单次允许、拒绝、问题回答或转交人工 |

只允许所选项目根目录本身，不允许将 cwd 改为任意子目录或其他路径。
目录授权是路由权限，不是操作系统文件沙箱。原生 Ask 和项目信任继续独立生效。
`awaitingLocalApproval:true` 不代表已授权代审批。宿主声明支持时，可在 DFSC 的
「远程访问 → 接入渠道 → 外部 Agent」中刷新，为具体任务选择范围和
本次任务或 15/30/60 分钟有效期，确认后开启。临时委托在任务结束或重启后失效。
长期委托按此 Agent 和此项目保存，可选 1/7/30 天或直到手动撤销，跨任务和正常重启有效；
凭据或目录身份改变不能借用旧策略，关闭接入或撤销连接删除相关策略。
新任务可选 Ask 或「代我批准」，后者常规操作由原生策略自动执行，不是 Hermes 审核；
风险请求仍需单独选择。替换、到期或撤销长期策略会中止使用旧自动权限的任务并降回 Ask。
自动任务结束时也先降回 Ask 再释放原生会话，长期策略仍保留给后续新任务；
权限清理不改变已完成结果，也不重新附着之后由用户本地使用的会话。
不尝试旧凭据，也不把风险确认当作新的审批授权。

新的相关授权动作由宿主展示插件风险和实际范围，取消不改变已有授权。
可自行勾选记住当前包、风险和精确范围；内容、包、身份凭据或范围变化需重新确认。
这只是知情确认，不代替本机授权，也不保证模型审核安全。详情见资源包的
`docs/RISKS.md`。未升级宿主只能查询和停止现有任务，不能用新版 companion 继续派工或代审批。

`approval.list {taskId}` 只导出已委托且完整的当前请求，包含不透明 `requestId`、
完整 `input`、可选 `otherParameters` 和 `verificationCommand`。模型需独立审阅用户目标，
调用 `approval.respond {taskId,requestId,decision,reason}`，decision 为 `allow/deny/escalate`，
理由必填。允许只作用于当前一次确认，不改变权限档位。不能判断就转交人工，不换 ID 重答。
风险和问题需分别授权；结构化问题的 `input` 是问题数组，回答需额外传完整
`answers:[{id,value,wasCustom}]`，选项、顺序与自定义许可由宿主验证。
缺失/脱敏参数、无法分析、未知请求、信任项目和权限切换仍在本机处理。
文件修改附带验证命令时，必须同时勾选命令类。审批记录只在本机管理页查看，最多最近 200 条。

## 审批提醒

支持 `events.wait` 的宿主由 companion 后台长轮询，不让模型循环等待。
只将当前有效审批的提醒注入发起任务的 Hermes 会话，再由模型读取并审阅完整请求；
提醒不会执行 allow/deny。保持 Hermes 运行，不是延迟几秒后无条件批准，也不承诺离线审批。

Hermes TUI/desktop/gateway 需提供可信的 turn-local session key，并自行允许
`plugins.entries.hermes-dfsc.allow_gateway_injection: true`。安装器保持默认关闭，
不会代用户改许可；在目标独立 profile 明确启用后按 Hermes 自身方式重载。
未提供可信 session key 的旧 CLI 需手动查询审批，不回退到环境变量或其他最近聊天。
任务的 `approvalWakeup` 表示会话路由已登记或不可用，不证明 Hermes 已接受消息注入。
拒绝注入会有界退避重试；卸载会停止线程；重载不猜测恢复旧会话映射。
旧宿主无事件能力时只保留手动流程，模型侧不暴露 `events.wait` 工具。

目录范围不是文件系统沙箱，
委托 Agent 也可能判断错误。配对不等于委托，模型不能授予、续期或扩大自己的权限。
摘要缺失或截断时，去关联原生会话查看详细工具输出和测试证据，不猜测通过。
`taskId` 使用 `task.create` 返回对象的 `id`，不是 `sessionId` 或 `runtimeId`。

回答摘要只在当前 DFSC 进程内保存，不写入桥接任务账本。DFSC 重启后，
已完成任务仍可能保留 `completed`、`submitted:true` 和交付回执，但
`resultAvailable:false` 且没有 `summary`。这不代表原生回复被删除或没有执行。
不要因此重建任务、重新派工、补造回答或验收结果，也不要读取整个原生会话历史
来补齐摘要；请用户在 DFSC 中打开关联原生会话核对。

## 本机信任边界

此版本假定可信的本机单用户环境，不是共享主机的强隔离接口。
Loopback TCP 与 bearer 只校验客户端凭据，不提供服务端身份认证。
尤其在宿主异常退出留下陈旧端口时，其他本机进程若抢占该端口，
可能收到客户端发送的 token。描述符的私有文件权限不能解决服务端冒充；
不要在存在不可信本机用户或进程的环境使用此入口。
本轮没有增加自动凭据轮换或强服务端认证。

宿主任务列表按 20 条分页；当前最小适配器只暴露空参数查询，
没有开放 `offset`，所以空列表或当前批次都不代表全部历史。
原生会话历史仍在 DFSC 中查看。

## 撤销和恢复

- 在 DFSC 撤销单个连接，或关闭整个入口后，不再接受该连接的新请求。
- 仍可撤回的待发输入会撤回；长期自动权限的任务会中止并降回 Ask，
  其他任务保留 DFSC 本机停止和查看。
- DFSC 重启后不重放旧任务、消息或审批。未完成任务按宿主恢复记录显示中断，
  不自行再提交。原生历史仍在桌面保留。
- 不把 `--replace-connection` 当作失效凭据的修复方式。先查清是宿主关闭、
  授权撤销、目录失效还是版本不支持，再由用户决定重新授权。

## 验证边界

自动化测试覆盖 loopback 真实客户端、模式隔离、安装备份、受限方法、范围、
有界摘要和协议失败，不调用真实模型、不发送聊天消息。
隔离 Electron 与可控模型端点的宿主验收应另行记录；
不能由这些测试推断真实 Hermes gateway、账号、飞书或干净机器已完成验收。
