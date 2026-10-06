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

待执行。保留全部失败与超时，结束后补充结果；本页不预判 skill 收益。
