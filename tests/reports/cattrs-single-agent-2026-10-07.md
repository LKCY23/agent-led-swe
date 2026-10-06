# cattrs 单开发 Agent 对照

## 冻结条件

- 被测 skill：主工作区接受版本 `1c65c00`；本轮不修改 skill。
- 执行代码：`bba5a67`；明确 `allow_subagents=false`，模拟用户保留。
- 任务：此前冻结并预检的 cattrs partial structuring / recovery；属于开发用例。
- Solver／用户：CC 2.1.278 + deepseek-flash，high；CC 上下文声明 1M。
- baseline／skill 各一次，顺序执行；每组协作总时长 1200 秒，无额外单轮／回复次数限制。不自动重试。
- worker 2 CPU／3 GiB，模型专用网络；独立 verifier，流程与文档通过轨迹另行分析。
- 原始结果目录：`/Users/liyao/agent-led-swe/tests/runs/cattrs-single-agent-20261007/`。

## 执行前检查

98 项本地测试通过；两种原生 CLI 的 baseline／skill 四组模拟 API 检查通过，并核对委派工具不再曝光、原生 skill 安装调用和用户接续正常。

## 真实试跑

两组均完成三轮 Solver／用户交互，最终得到模拟用户接受；没有超时或需要追加模型试跑的执行故障。独立 verifier 均未全通过。

| 组别 | 基础测试 | 新功能测试 | 用户接受 | 采集到的 Solver＋用户执行时间 |
| --- | --- | --- | --- | --- |
| baseline | 7/7 | 64/69 | 是，3 次回应 | 843 秒 |
| skill | 7/7 | 66/69 | 是，3 次回应 | 785 秒 |

时间来自各次 capture，不包括镜像准备和 verifier，不能据此做普遍效率结论。两组的功能结论均为 fail，不能将用户接受或多数测试通过改写为成功。

### 功能缺口

- 两组共有：`refine` 覆盖了已成功结构化的字段；`test_complete_result_unchanged` 和 `test_preserves_successful_fields` 失败。
- baseline 另有 3 项：字段转换失败时，`errors` 没有按要求提供汇总异常。
- skill 另有 1 项：TypedDict 的必填字段失败时仍返回部分 dict，而测试要求 `value=None`。

### 流程与文档的直接观察

- 两组都在实现前提出接口问题，收到要求后继续开发；模拟用户分别进行了代码／文档审阅，随后继续同一原生会话。
- baseline 的实现前草案在对话中，项目内 `docs/partial.md` 在实现之后写入。
- skill 先阅读 Human Collaboration、Design、Requirements 指导，再在第一轮把设计草案写入 `docs/partial.md`，尚未修改源码。这是本轮明确观察到的文档时机差异。
- skill 第二轮先开始实现，再把第一轮草案修订为符合反馈的说明；因此不能称为“所有设计与需求都已先更新再实现”。这个衔接仍需进一步分析。
- skill 没有盲从用户的一条错误审阅：核查源码并实测后，指出 `init=False` 的既有行为，用户复核后撤回意见。证据位于第三轮公开对话。
- 最终使用文档 baseline 178 行、skill 114 行。skill 按 API／成员／语义／限制组织，阅读路径明确，但文档也明确写入了与验收要求不符的 TypedDict 和 refine 语义；结构清楚不能替代内容正确。
- 模拟用户接受了两份仍有功能缺陷的实现，并曾提出一条错误审阅。其接受只表示该模拟协作结束，不承担功能判分。

这是一个已用于开发的任务、每组一次；不能据此证明 skill 普遍优于 baseline，也不能将所有变化归因于关闭子 Agent。

## 单 Agent 记录误报与独立复核

原始 `result.json` 把两组的 `single_agent_verified` 标为 false、comparison_validity 标为 invalid。原因是解析器把 Bash 长命令的 `tool_progress` 心跳中的 `parent_tool_use_id` 当作子 Agent 消息；该字段本身不能证明存在子 Agent。

两组跑完后在 `c55e93e` 修正分类：只将带父调用标识的 assistant／user 消息或明确的子 Agent 启动事件计入；保留真正子 Agent 检测。回归增至 99 项，全部通过。

复核原始日志确认：

- 每轮委派工具 Task／Agent／Workflow 均未曝光。
- 更正后无子 Agent 消息，且每组只导出一个主会话文件，没有 subagents 文件。
- 原生 skill 的调用／缺席检查通过。

新的复核结果及原始文件哈希保存在：
`/Users/liyao/agent-led-swe/tests/runs/cattrs-single-agent-20261007/single-agent-recheck/result.json`。

原始结果、日志、verifier 成绩均未覆盖，没有重跑模型或更改功能判据。复核后的单 Agent 检查与对照有效性为 valid；报告引用的是这份修正后的记录，功能仍为 fail。
