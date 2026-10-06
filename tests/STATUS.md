# 当前测试状态

更新：2026-10-06。本页维护当前任务选择；过往预算与实验见 [历史索引](history.md)，不作为新的执行指令。

## 版本与工作区

- 正式 skill：`/Users/liyao/agent-led-swe`，接受提交 `1c65c00`。
- 测试工作区：`/Users/liyao/agent-led-swe-worktrees/verifier-and-environment-20261006`，当前分支 `feat/cattrs-collaboration-20261006`。本轮从 `b7d308d` 开始；工具旧基线标签为 `test-baseline-2026-10-06`，skill 文件保持接受版本。
- 未接受候选由 Git 分支与实验快照保留。运行时仍显式指定被测 skill 路径。

## 任务状态

| 类别 | 用途 | 状态 |
| --- | --- | --- |
| 本地工具测试、原生协议检查 | 检查基础设施，不评价 skill 效果 | 保留 |
| [D14](cases/behavior/D14.json) 与短诊断 skill | 检查直接请求／原生 skill 的明确步骤执行 | 保留快速诊断；不是完整 skill 的验收 |
| D1、D4、D7、D10–D13 | 早期需求、协作与文档场景 | 保留专项回归；限制见 [场景说明](scenarios.md) |
| smolagents、xarray、NodeBB、Navidrome、packaging | 旧单次请求 SWE 校准任务 | 退出当前推荐组合；适配器、输入和资格记录保留，可按名称显式调用 |
| Agents SDK、DSPy | 未采用的早期候选 | 不启用；定义和结论保留追溯 |
| SWE-Interact 适配 | cattrs 优先，TOMLKit、HTTPX 后续候选 | 已执行一对真实试跑，但两组均被单轮 300 秒限制截断，用户回应为 0；完整多轮评测未完成。见[试跑结果](reports/cattrs-pair-native-2026-10-06.md) |

当前没有默认运行的完整 SWE benchmark 套件。真实模型测试仍需明确任务、版本、模型、比较方式与预算。

## 保留能力与边界

保留 Codex／Claude Code、Flash／Pro 配置、原生 skill 安装调用、Docker 与模型网关隔离、完整事件和文件快照、独立 verifier。功能结果与流程分析分开，不自动调用 LLM judge。

既有 `run_evaluation.py` 仍用于单次请求；`run_collaboration.py` 提供独立多轮入口。当前可用用户资格为 `cattrs-user-cc-flash.json`，旧直连 API 的失败资格只作历史记录。实现约定见 [协议](protocol.md)。

自写用户工具循环已移除。首次对照没有自动重跑；下一轮需先修正单轮限制与总预算的关系，并处理检查环境的缺口。现有轨迹能确认 skill 已加载／读指导但没有先形成设计记录，不能评价完整用户协作与最终文档。
