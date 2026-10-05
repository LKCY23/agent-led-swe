# 首轮真实 SWE 配对：pytest

结论：执行、独立功能验收和定性评审已完整跑通。两组功能均通过；baseline 的共同工程要求通过，skill 组因漏读明确要求阅读的贡献规范而未通过。本轮只有一个开发集任务、每组一次，不能据此判断 skill 的总体增益。

## 配置与任务

- 任务：SWE-bench Verified `pytest-dev__pytest-10051`，修复 `caplog.clear()` 后 `get_records()` 与当前记录不同步。沿用已通过预检的本地任务与可信测试。
- Executor：容器内 Claude Code 2.1.278，`deepseek-flash`（当前 DeepSeek V4.1 Flash），effort high，CC 1M context 设置。baseline／skill 各一次、每次 300 秒上限，无额外 attempt。
- Judge：本机 Codex 0.160.0，`gpt-6.1-sol`／high，每组新的只读评审，180 秒上限。
- 两组起始文件哈希完全一致，模型、运行环境、共同要求和预算相同。只有 skill 组获得目标指导；两组 discovery 检查均通过。
- 不强制 tokens／费用上限；cost 未知。运行顺序为 baseline → skill，未做多次重复或顺序平衡。

## 结果

| 项目 | baseline | skill |
| --- | --- | --- |
| 执行状态 | completed | completed |
| 可信目标测试 | 1/1 通过 | 1/1 通过 |
| 可信回归测试 | 15/15 通过 | 15/15 通过 |
| A1：仓库规范、范围、职责及兼容性 | pass | fail：未阅读 CONTRIBUTING.rst |
| A2：设计依据、实际验证与交付说明 | pass | pass |
| 按现有必需项汇总 | pass | fail |
| Executor 耗时 | 129.08 秒 | 60.68 秒 |
| input tokens（含缓存读写） | 762,288 | 358,997 |
| 其中 cache-read tokens | 742,272 | 343,168 |
| output tokens | 18,162 | 8,995 |
| 工具调用 | 44 | 31 |

上述 usage 为多次模型请求累计，不是单次上下文长度；费用未按 CC 客户端估价推算。Judge 耗时分别为 97.04／93.97 秒，其用量单独保存在评审结果中，不混入 Executor 指标。

## 人工核对与解释

两组都新增了保留列表引用的 handler `clear()`，保留按阶段重置的 `reset()`，并修改 caplog 调用、新增回归测试和 changelog。可信测试在独立副本中恢复后执行，未采用 Agent 自己宣称的通过数作为评分结果。

skill 组确实读取了 `SKILL.md` 和 `references/phases/implementation.md`。但完整工具记录中没有阅读 CONTRIBUTING.rst 的操作；它读取了 changelog README，不能替代任务明确点名的贡献指南。baseline 则检索了 CONTRIBUTING.rst 的 changelog 指导并读取相关段落。作者复核支持 judge 指出的遗漏，不修改原始判分或重跑来消除失败。

两组没有为这个小修复新增独立设计文档；执行记录及最终 handoff 解释了设计选择、实际测试与限制，A2 均通过。这里验证的是记录是否足以理解和接续工作，不是是否生成固定数量的文档。任务不涉及人类决策、多 process 协调或长期维护，不能代表这些能力已经验证。

还有两个需要后续审阅的观察：

1. 两组都猜测了 changelog issue 编号，并在 handoff 中披露不确定性；skill 组还把猜测编号写入测试 docstring。现有 judge 没将其判为失败。这是后续校准工程验收标准的样例，不在本轮事后增加判据。
2. skill 组更快、用量更少，但也漏掉一项明确要求；baseline 的额外验证更多。不能将时间差直接归因于 skill 的有效性，更不能只看速度忽略完成质量。

## 证据与后续

运行：`tests/runs/pair-pytest-20261005T151031497355Z/`。其中 `plan.json` 固定输入与配置，两个 trial 目录保留 prompt、原始事件、完整工具记录、前后文件快照和变更清单。

独立评价：`review-20261005T151439437302Z/`，包含可信测试日志、两个 judge 的输入与输出，以及 `summary.json`。所有运行和判分均保留；测试容器已退出并清理。

下一步先审阅这次流程遗漏及判分是否符合人类预期，再决定是否调整 skill 或评测规则。若调整，应保存新版本并重新验证；本次失败仍保留。更复杂的 packaging 任务及重复实验尚未开展。
