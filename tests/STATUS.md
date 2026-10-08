# 当前测试状态

更新：2026-10-08。本轮新版模拟用户下的一项真实任务、两个 skill 版本对照已完成。

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
| 当前进度 | 已完成：current 基础 7/7、新功能 69/69；candidate 基础 7/7、新功能 67/69；未重试 |

重点检查：是否按任务需要使用 skill、流程是否顺畅、实现依据是否及时记录、验证与交付记录是否真实、文档是否准确精炼且便于人类审阅。文件数量或读取指导本身不能证明 skill 有效。cattrs 已用于分析和优化，属于开发集；单次对照不能证明普遍效果。

## 保留测试的定位

后续多场景评估遵循 [评估设计规范](evaluation-design.md)。已形成 [四场景任务与用户目标方案](reports/multi-scenario-design-2026-10-08.md)：TOMLKit A、ofetch B、空目录 gRPC 服务 C、真实 cattrs 成果接续 D。[B 的四题比较](reports/scenario-b-selection-2026-10-08.md)推荐 ofetch 熔断器。已静态核查来源、需求与验收代码；尚未接入或完成新环境预检，未修改当前任务请求或启动模型测试。

模拟用户已按自主协作规范更新并完成真实试跑。用户能够自主审阅和反馈，但 candidate 组仍批准了与既定要求不符的 TypedDict 行为；不能因两组对话不同就认定无效，也不能因原生运行核查通过就认为用户回答均正确。详见 [本轮报告](reports/cattrs-user-revision-2026-10-08.md)与[设计规范](protocol.md#agent-based-模拟用户)。

- 本地单元测试、原生协议及环境检查：保障评测工具可靠，不作为 skill 效果证据。
- D 系列：只保留专项诊断与回归能力，本轮不再扩展或重跑，包括 D17。
- 其他旧 SWE 任务：保留输入、适配器及历史材料，不在本轮执行范围。

## 已有证据

- [新版用户真实对照](reports/cattrs-user-revision-2026-10-08.md)：current 三轮完成并通过验收；candidate 两轮获接受但有两项功能失败。候选读取了四份补充指导，仍未形成实现前项目记录。功能差异受到用户反馈与需求解释影响，不直接归因于 skill。

- [当前版 / 候选版真实对照](reports/cattrs-versions-2026-10-07.md)：两组均两轮完成并通过独立验收；未观察到补充指导读取或记录时序的改善。模拟用户有额外要求，归因需保留这一限制。

- [cattrs 单开发 Agent 对照](reports/cattrs-single-agent-2026-10-07.md)：无 skill / 已接受 skill 均完成三轮并获用户接受；独立 verifier 基础均 7/7，新增功能分别 64/69、66/69，均未完全通过。
- [候选修改](reports/process-adaptation-candidate-2026-10-07.md)：调整指导入口、Process 适配与记录衔接，尚未接受。
- [D15–D18 情境对照](reports/adaptation-scenarios-2026-10-07.md)：三项功能两版均通过，探索原型两版超时；未显示稳定流程改善，并发现计划提前标记完成。历史预算与结果保持原样。

运行原始材料保存在独立目录。工具与 skill 分开提交；用户审阅后再决定是否接受候选。入口见 [README](README.md)，执行约定见 [协议](protocol.md)，过往实验见 [历史索引](history.md)。
