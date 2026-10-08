# ofetch B 场景接入与本轮计划

已接入现有多轮执行器，保留原生模拟用户、网络隔离、轨迹和独立 verifier；未修改被测 skill。A、C、D 本轮不运行。

## 接入与验证

- `run_collaboration.py --task ofetch` 选择任务与场景，默认 cattrs 行为保留。
- `ofetch_task.py` 冻结源码、任务要求、独立测试与参考补丁；只有公共源码进入 solver，参考与验收材料不挂载给开发 Agent 或模拟用户。
- 镜像只提供工具及固定依赖，Node 通过父目录 `/node_modules` 解析依赖；项目使用绑定目录，使每轮用户快照包含最新修改，依赖不进入项目快照。镜像不含应用源码或参考实现。
- 新镜像与实际验收器预检通过：起始新增测试 7/54、参考 54/54，三组 base 筛选均通过。原项目公网测试与参考格式问题仍按 [前次预检](ofetch-preflight-2026-10-08.md)单列，未修改断言。
- 105 项本地回归通过。真实 Claude Code CLI 对接模拟 API 的 baseline / skill 两组检查均通过，涵盖两轮接续、原生调用、项目指导与 hooks、只读模拟用户和隔离。此处 baseline 只用于链路检查，不是新增的真实无 skill 对照。

材料：`/Users/liyao/agent-led-swe/tests/runs/ofetch-integration-20261008`。首次 `inputs/`、`preflight/`、`native-probe/` 保留；修正后的输入与检查见 `inputs-v2/`、`preflight-v2/`、`native-probe-v2/`。

首次真实试跑暴露接入缺陷：Agent 将预装依赖链接为项目 node_modules 后，快照规则将依赖链接判为越界，current 在用户审阅前中断，candidate 随后被主动停止。该次记录在 `ofetch-versions-20261008`，另存 `invalid-comparison.json`，不作为 skill 效果证据。

修正后由环境启动阶段提供 node_modules 链接，并在每轮、初始和最终快照中排除明确声明的依赖目录；代码、文档仍保留，其他越界链接仍拒绝。107 项本地回归和两组原生用户协议检查通过，实际 verifier 再次预检通过。执行错误不再仅因原生调用成功而标为有效对照。新真实试跑使用独立目录 `ofetch-versions-20261008-v2`，不修改首次原始结果。

## 真实对照计划

| 项目 | 设置 |
| --- | --- |
| 任务 | ofetch per-origin circuit breaker，B：持续协作开发 |
| skill | current 为已接受的 1c65c00；candidate 内容为 42fc6f9；实际文件分别冻结 |
| Agent / 模型 | Claude Code 2.1.278 + DeepSeek Flash high，独立原生 CC 用户使用同一模型与 high |
| 开发并行性 | 单开发 Agent，模拟用户独立；不启用开发子 Agent |
| 预算 | 每组 solver 与用户共享 3600 秒，双方获知；无单轮或轮数限制，完成即结束 |
| 次数 | 每组一次，current 先运行，无自动重试 |
| 功能判断 | 独立 canonical verifier；用户接受不代替功能正确性 |
| 主要分析 | 是否适配仓库规范；重要设计能否及时审阅；约定、进展、验证与限制是否形成有用的项目记录；过程负担是否适当 |

相较前次 cattrs 的 30 分钟预算，本题增加到 60 分钟，以容纳状态、重试与 hooks 的联合设计、验证和用户审阅。预算是上限，不要求消耗完，也不在看到结果后为某一组延长。

初始请求见 [request.md](../cases/collaboration/ofetch/request.md)，用户角色见 [user.md](../cases/collaboration/ofetch/user.md)。不预设反馈或返工，不要求固定文件名。此题已被用于选题和预检，作为开发集，不声称是未见验证。
