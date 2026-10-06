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
| SWE-Interact 适配 | cattrs 优先，TOMLKit、HTTPX 后续候选 | 环境／verifier、双宿主模拟联测通过；真实 Flash 模拟用户未取得资格，尚未进行开发对照。见[用户接入与检查](reports/simulated-user-integration-2026-10-06.md) |

当前没有默认运行的完整 SWE benchmark 套件。真实模型测试仍需明确任务、版本、模型、比较方式与预算。

## 保留能力与边界

保留 Codex／Claude Code、Flash／Pro 配置、原生 skill 安装调用、Docker 与模型网关隔离、完整事件和文件快照、独立 verifier。功能结果与流程分析分开，不自动调用 LLM judge。

既有 `run_evaluation.py` 仍用于单次请求；`run_collaboration.py` 提供独立多轮入口，要求任务和用户模型均取得资格。Flash 模拟用户真实检查未通过，入口保持阻止运行。实现约定见 [协议](protocol.md)。

先诊断模拟用户的输出协议及回应规则偏离；已请求用户选择 Pro 小样本对照或继续改进 Flash 接入。当前没有可据此分析 skill 表现的真实多轮结果。暂不删除旧适配代码或镜像。
