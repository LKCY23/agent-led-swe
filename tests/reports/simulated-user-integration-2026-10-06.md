# 模拟用户接入与真实 Flash 检查

当前实现已改为[原生 CC 用户](native-cc-user-2026-10-06.md)，本报告描述的是已停用的直连 API 路径。

后续：[Pro 小样本对照](simulated-user-pro-comparison-2026-10-06.md)也未通过。以下保留本轮 Flash 接入的原始结论与过程。

**接入代码已实现，但真实模拟用户尚未取得运行资格，因此没有开始 cattrs 的 skill 开发对照。** 本轮从 `3bab3c1` 继续，在原测试 worktree 内工作；正式 skill 不变。用户选择的模拟用户模型为 DeepSeek Flash。

## 实现范围

| 部分 | 当前职责 |
| --- | --- |
| [初始请求](../cases/collaboration/cattrs/request.md)、[用户规则](../cases/collaboration/cattrs/user.md) | 固定公开目标、授权及私有回应规则；原始功能要求从冻结任务输入读取。不给用户模型 skill、组别或 verifier。 |
| [simulated_user.py](../simulated_user.py) | 根据公开对话回应；只能列文件、读文件和对比初始快照。审阅未提交产物，不要求 Git 提交；不提供 shell、写入或任意目录访问。 |
| `chat_completion.py`（历史提交 `8b31874`；现已移除） | 当时使用独立的 Chat Completions HTTP 子进程。凭据通过 stdin 传递，不写进 argv 或证据；禁用重定向、限制响应大小、超时终止，不自动重试。 |
| [run_collaboration.py](../run_collaboration.py) | 冻结两组条件，运行同一原生会话的多轮协作，再独立验收；要求任务预检和模拟用户资格都通过。当前 Flash 资格为失败，真实配对入口会拒绝执行。 |

每次用户回应有模型调用上限，整组还有总调用上限；每个请求限制生成长度，用户与 solver 均有时间限制。solver 费用没有硬上限，不把时长控制说成费用控制。完整问答、HTTP 请求／响应、工具结果、逐轮产物与错误均保留在 solver 不可见的证据目录。

最终用户回复包含自然语言和 `accepted` 布尔值。确认设计或允许继续均不结束协作；`accepted=true` 只用于接受最终交付，且本轮必须实际读取产物。这个条件不能证明审阅充分，功能结果仍只由 verifier 给出。

## 已验证部分

- 本地工具测试 **95 项通过**，包括新增用户读取边界、错误响应、超时、调用预算、结束语义与失败资格阻止真实配对的检查。
- Codex／Claude Code 的 baseline／skill 四组模拟联测已通过：真实 CLI 的两轮接续连接了用户 HTTP／只读工具适配器。响应为模拟 API 生成，不能当作真实模型行为证据。
- 真实 Flash 检查使用两个问题：一次说明完整需求；审阅一份明确违反缺失字段与必填字段要求的提案。它们是模拟用户的开发检查，不是 skill 评测题目的实现尝试。

## 真实检查发现的问题

| 检查版本 | 结果与调整依据 |
| --- | --- |
| v1、v2 | 能说明主要需求，但自然语言 JSON 缺少 `accepted`，即使明确必填并使用 JSON 输出仍发生。按错误停止，没有默认同意。 |
| v3 | 提供结构化回复工具后仍输出普通文本；还把未明确给定的参数顺序说成要求。 |
| v4 | 强制工具调用后完成第一条回应；第二条回应反复检查文件并耗尽预算。第一条还附加了先审阅计划的条件。 |
| v5 | 第一条回应成功；最后一条回复使用了未声明的 `call(function=...)` 包装。依据实际响应增加了仅限已声明工具的格式转换，原始数据保留。 |
| v6 | 到限定发送最终答复的请求时，仍调用当前未提供的读取工具；两条回应未完整完成。现在这类越过当次工具列表的调用直接报错，不继续执行。 |

六次有界检查共取得 **24 个真实 API 响应**，原始 usage 合计 81,593 prompt tokens、4,762 completion tokens；未核对账单费用。每次调整在新目录运行，之前的失败没有被覆盖。提示词、输出协议和 thinking 设置曾改变，这不是重复同一条件的统计实验，不能据此估计模型的总体失败率。

目前不能断言单纯是模型能力问题：也可能涉及当前提示组织、工具调用协议或服务端兼容性。已观察到的偏离足以说明这套配置不能直接用于可靠的 skill 对照。若用户模型自行改变要求、添加审批或错误批准，会污染流程分析。

当前用非 thinking 模式配合 required／指定回复工具；这是因 [DeepSeek API](https://api-docs.deepseek.com/api/create-chat-completion/) 对 thinking 模式工具选择的约束作出的配置选择，并不意味着该组合在本次真实测试中已可靠。原始模型标签和所有请求配置保留。

## 当前状态与下一步

[Flash 模拟用户资格记录](qualifications/cattrs-user-flash.json)为 `qualified=false`。配对入口检查 profile、用户规则、需求与适配器哈希，拒绝失败或过期资格；环境和 verifier 已通过不会绕过这个条件。

已向用户提出两个后续选择：用 Pro 在相同协议下做少量对照，或保留 Flash 先继续分析接入。确定后只改变相应条件，先把模拟用户检查做可靠，再开展完整开发对照。不将本轮用户模型问题解释为 skill 的效果。

证据位于 `/Users/liyao/agent-led-swe/tests/runs/cattrs-user-integration-20261006/`：`live-user-smoke*`、`smoke-summary.json`、`protocol-cc/`、`protocol-codex/`、`unit-tests-gated.log`。这些路径不挂载给执行 Agent。
