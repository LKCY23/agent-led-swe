# 当前测试状态

更新：2026-10-08。A、B 场景的接入与真实版本对照已完成，C、D 待运行。

TOMLKit [A 运行结果](reports/tomlkit-versions-2026-10-08.md)：两版均两轮完成，用户接受，独立 base 964/964、新增 60/60。原生调用、隔离与单 Agent 核查有效，未追加重试。本轮只保存结果与证据，待剩余场景完成后统一归因和讨论优化。

ofetch [B 有效对照结果](reports/ofetch-versions-2026-10-08.md)：current 四轮、candidate 两轮，均通过新增 54/54 和原 base 筛选。首次依赖快照故障及此前的分析原样保留，见[接入记录](reports/ofetch-integration-2026-10-08.md)。主 skill 未合并。

## 当前实验

| 项目 | 设置 |
| --- | --- |
| 任务 | A：SWE-Interact 适配的 TOMLKit table converters，成熟仓库普通功能开发 |
| 当前版本 | 已接受 skill：1c65c00，主工作区保持不变 |
| 候选版本 | skill 内容：42fc6f9，独立 worktree 中保留；未合并 |
| 比较组 | current / candidate，各一次；本轮不运行无 skill baseline |
| Agent / 模型 | Claude Code + DeepSeek Flash high；单个开发 Agent，独立原生模拟用户 |
| 预算 | 每组开发 Agent 与模拟用户共享 3600 秒，双方均获知；不另设轮数或单轮时限 |
| 判定 | 独立 verifier 判功能；执行后分析轨迹和文档，不自动调用 LLM judge |
| 当前进度 | 已完成：两版均基础 964/964、新功能 60/60；未重试 |

统一分析时重点检查：是否按任务需要使用 skill、流程是否顺畅、实现依据是否及时记录、验证与交付记录是否真实、文档是否准确精炼且便于人类审阅。文件数量或读取指导本身不能证明 skill 有效。这些任务已用于选题、预检或调优，属于开发集；单次对照不能证明普遍效果。

## 保留测试的定位

多场景评估遵循 [评估设计规范](evaluation-design.md)。[四场景方案](reports/multi-scenario-design-2026-10-08.md)包含 TOMLKit A、ofetch B、空目录 gRPC 服务 C、真实 cattrs 成果接续 D。A、B 已完成本轮对照；C、D 尚未接入运行。A 的环境与原生协议预检见 [接入计划](reports/tomlkit-integration-2026-10-08.md)。

B 的[本机与 Linux 断网容器预检](reports/ofetch-preflight-2026-10-08.md)为起始新增测试 7/54、参考 54/54，构建通过。容器完整原项目测试均为 27/28，同一项公网调用因断网受阻；参考有两处 Prettier 格式问题。该环境基线与后续模型结果分开保留。

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
