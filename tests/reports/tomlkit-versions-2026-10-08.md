# A 场景：TOMLKit 运行结果

两版各运行一次，均完成两轮协作、获得模拟用户接受，并通过独立功能验收。本记录只保存运行结果与证据入口；流程适配、文档质量和差异归因待各场景完成后统一分析，不据此修改 skill。

## 配置与有效性

- 任务与准备见 [A 接入计划](tomlkit-integration-2026-10-08.md)。执行工具提交 `862b42e`；current 为已接受 skill `1c65c00`，candidate 的 skill 内容为 `42fc6f9`，实际文件分别冻结。
- Claude Code 2.1.278 + DeepSeek Flash high；单开发 Agent，独立原生模拟用户；两组各共享 3600 秒，current 先运行，无追加重试。
- 两组原生 skill 调用、隔离与单开发 Agent 核查均有效。两组验收用例身份与结果指纹均匹配已预检的参考实现；验收未改动提交成果。
- 未修改、合并或重新安装被测 skill。测试产物保存在独立运行目录。

## 结果

| 项目 | current | candidate |
| --- | --- | --- |
| 开发回合 / 用户回复 | 2 / 2 | 2 / 2 |
| 用户接受 | 是 | 是 |
| 独立 base 测试 | 964/964 | 964/964 |
| 独立新增测试 | 60/60 | 60/60 |
| 验收中的失败、错误、跳过 | 均为 0 | 均为 0 |
| 开发 Agent capture 时间 | 1955.64 秒 | 885.90 秒 |
| 模拟用户 capture 时间 | 41.79 秒 | 36.73 秒 |
| 开发输入 / 其中缓存输入 tokens | 30,815,286 / 30,695,424 | 21,589,633 / 21,487,232 |
| 开发输出 tokens | 212,541 | 172,081 |

时间为 capture 累计，不含环境准备和独立验收；tokens 是累计用量，不是上下文长度或费用。两组自然交互及开发选择可能不同，单次耗时差异不直接证明 skill 收益。测试通过也不等于全部语义、文档及流程要求已获确认。

## 已保存材料

运行目录：`/Users/liyao/agent-led-swe/tests/runs/tomlkit-versions-20261008`。

| 材料 | 相对路径 |
| --- | --- |
| 冻结配置、来源、版本与哈希 | `plan.json`、`task-inputs/`、`scenario/`、`reference-skill/`、`frozen-skill/` |
| 运行结果与计数摘要 | `results.json`、`execution-summary.json` |
| 各轮请求、原生输出与工具轨迹 | `<variant>/conversation/turn-*/` |
| 用户回复及只读审阅轨迹 | `<variant>/user/reply-*/` |
| 初始与最终成果 | `<variant>/before/`、`<variant>/after/` |
| 独立验收日志、JUnit 与结果 | `<variant>/verifier/`、`<variant>/verifier-result.json` |

两组均修改 `CHANGELOG.md` 和 `docs/quickstart.rst`；current 另修改 `docs/api.rst`。这些是文件差异清单，不是文档质量评价；生成时序、内容准确性、可读性和是否满足相应场景要求，统一审阅时再核对原始轨迹。

A、B 已完成本轮对照；C、D 尚未运行。后续继续完成剩余场景，再汇总证据、归因并讨论优化。
