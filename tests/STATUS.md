# 当前测试状态

更新：2026-10-06。本页维护当前任务选择；过往预算与实验见 [历史索引](history.md)，不作为新的执行指令。

## 版本与工作区

- 正式 skill：`/Users/liyao/agent-led-swe`，接受提交 `1c65c00`。
- 测试工作区：`/Users/liyao/agent-led-swe-worktrees/verifier-and-environment-20261006`，分支 `chore/test-baseline-cleanup-20261006`。skill 文件已恢复到接受版本，测试工具改进保留。
- 未接受候选由 Git 分支与实验快照保留。运行时仍显式指定被测 skill 路径。

## 任务状态

| 类别 | 用途 | 状态 |
| --- | --- | --- |
| 本地工具测试、原生协议检查 | 检查基础设施，不评价 skill 效果 | 保留 |
| [D14](cases/behavior/D14.json) 与短诊断 skill | 检查直接请求／原生 skill 的明确步骤执行 | 保留快速诊断；不是完整 skill 的验收 |
| D1、D4、D7、D10–D13 | 早期需求、协作与文档场景 | 保留专项回归；限制见 [场景说明](scenarios.md) |
| smolagents、xarray、NodeBB、Navidrome、packaging | 旧单次请求 SWE 校准任务 | 退出当前推荐组合；适配器、输入和资格记录保留，可按名称显式调用 |
| Agents SDK、DSPy | 未采用的早期候选 | 不启用；定义和结论保留追溯 |
| SWE-Interact 等多轮任务 | 下一阶段候选 | 尚未接入、预检或执行 |

当前没有默认运行的完整 SWE benchmark 套件。真实模型测试仍需明确任务、版本、模型、比较方式与预算。

## 保留能力与边界

保留 Codex／Claude Code、Flash／Pro 配置、原生 skill 安装调用、Docker 与模型网关隔离、完整事件和文件快照、独立 verifier。功能结果与流程分析分开，不自动调用 LLM judge。

当前执行器主要用于无持续用户介入的任务；六个文件／Shell 工具、关闭 hooks 与自动记忆的配置不等于完整交互式宿主。接多轮任务前，单独明确用户模拟、交互入口、信息隔离和最终验收。实现约定见 [协议](protocol.md)。

先检查少量 SWE-Interact 任务与交互协议，再决定接入方式。新任务预检通过后，才评估删除旧 benchmark 专属适配代码与镜像。
