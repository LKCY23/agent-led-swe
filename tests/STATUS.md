# 当前测试状态

更新：2026-10-07。本页维护当前任务选择；过往预算与实验见 [历史索引](history.md)，不作为新的执行指令。

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
| SWE-Interact 适配 | cattrs 优先，TOMLKit、HTTPX 后续候选 | 第二次已进入反馈，两组最终被用户内部步数限制中断。已修正用户限制和搜索工具，修复后未重跑真实模型。见[第二次结果](reports/cattrs-retry-2026-10-07.md) |

当前没有默认运行的完整 SWE benchmark 套件。真实模型测试仍需明确任务、版本、模型、比较方式与预算。

## 保留能力与边界

保留 Codex／Claude Code、Flash／Pro 配置、原生 skill 安装调用、Docker 与模型网关隔离、完整事件和文件快照、独立 verifier。功能结果与流程分析分开，不自动调用 LLM judge。

既有 `run_evaluation.py` 仍用于单次请求；`run_collaboration.py` 提供独立多轮入口。`cattrs-user-cc-flash.json` 对应旧参数，仅作历史证据，不再作为运行门槛；旧直连 API 资格只作历史记录。实现约定见 [协议](protocol.md)。

solver 限时与依赖已修正并完成第二次试跑；发现的用户内部步数限制与搜索能力问题也已修正。旧试跑均保留，尚无完整闭环结果。两次轨迹都没有实现前的项目设计记录；本轮 skill 未读取参考指导，不能沿用前一轮的读取结论。

当前清理：已去掉额外轮数／单轮时限、输出与重试限制、工具裁剪和项目指导屏蔽，验收不再依赖会话完成。91 项回归与两种原生 CLI 的四组模拟 API 检查均通过；尚未重跑真实模型。检查范围与结果见[限制清理记录](reports/runtime-restrictions-2026-10-07.md)。

当前配置已按逐项审查再次修正：恢复 DeepSeek 1M 客户端声明、明确资源条件、确认容器停止后导出、补齐 CC 子 Agent 记录和用量增量。97 项本地回归、CC 子 Agent／用户接续、Codex 接续、bind／copy 停止与快照检查均通过；未追加真实模型运行。见[配置修正记录](reports/runtime-correction-2026-10-07.md)。


最新真实对照：单开发 Agent（模拟用户保留），CC＋Flash high，正式 skill 不变；baseline／skill 均完成三轮并被用户接受，独立 verifier 为基础 7/7、功能分别 64/69 与 66/69，均未完全通过。记录器的 Bash 心跳误报在运行结束后独立修正复核，原始记录保留。详见[本轮结果](reports/cattrs-single-agent-2026-10-07.md)。


待审阅 skill 候选：`42fc6f9`，调整 Process 适配、指导入口和记录衔接，正式 skill `1c65c00` 未动。结构与引用检查通过，四类情境仅完成静态核对，尚未进行候选模型试跑。见[候选说明](reports/process-adaptation-candidate-2026-10-07.md)。


四类情境小规模对照已完成：D15／D16／D18 两版均完成功能验收，D17 两版均超时；候选的指导使用与记录时序未表现出稳定改善，探索计划出现提前标记完成的问题。候选仍未合并，暂未追加完整 cattrs。见[情境对照报告](reports/adaptation-scenarios-2026-10-07.md)。
