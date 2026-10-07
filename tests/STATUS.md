# 当前测试状态

更新：2026-10-07。当前只推进一项真实开发任务、两个 skill 版本、一次完整对照。

## 当前实验

| 项目 | 设置 |
| --- | --- |
| 任务 | SWE-Interact 适配的 cattrs partial structuring，多轮需求澄清、开发、审阅与修订 |
| 当前版本 | 已接受 skill：1c65c00，主工作区保持不变 |
| 候选版本 | skill 内容：42fc6f9，独立 worktree 中保留；未合并 |
| 比较组 | current / candidate，各一次；本轮不运行无 skill baseline |
| Agent / 模型 | Claude Code + DeepSeek Flash high；单个开发 Agent，独立原生模拟用户 |
| 预算 | 每组开发 Agent 与模拟用户共享 1800 秒，双方均获知；不另设轮数或单轮时限 |
| 判定 | 独立 verifier 判功能；执行后分析轨迹和文档，不自动调用 LLM judge |
| 当前进度 | 补齐多轮版本对照入口后运行；不自动重试 |

重点检查：是否按任务需要使用 skill、流程是否顺畅、实现依据是否及时记录、验证与交付记录是否真实、文档是否准确精炼且便于人类审阅。文件数量或读取指导本身不能证明 skill 有效。cattrs 已用于分析和优化，属于开发集；单次对照不能证明普遍效果。

## 保留测试的定位

- 本地单元测试、原生协议及环境检查：保障评测工具可靠，不作为 skill 效果证据。
- D 系列：只保留专项诊断与回归能力，本轮不再扩展或重跑，包括 D17。
- 其他旧 SWE 任务：保留输入、适配器及历史材料，不在本轮执行范围。

## 已有证据

- [cattrs 单开发 Agent 对照](reports/cattrs-single-agent-2026-10-07.md)：无 skill / 已接受 skill 均完成三轮并获用户接受；独立 verifier 基础均 7/7，新增功能分别 64/69、66/69，均未完全通过。
- [候选修改](reports/process-adaptation-candidate-2026-10-07.md)：调整指导入口、Process 适配与记录衔接，尚未接受。
- [D15–D18 情境对照](reports/adaptation-scenarios-2026-10-07.md)：三项功能两版均通过，探索原型两版超时；未显示稳定流程改善，并发现计划提前标记完成。历史预算与结果保持原样。

运行原始材料保存在独立目录。工具与 skill 分开提交；用户审阅后再决定是否接受候选。入口见 [README](README.md)，执行约定见 [协议](protocol.md)，过往实验见 [历史索引](history.md)。
