# 测试场景与当前状态

日期：2026-10-05

本页管理受控行为用例。真实 SWE 候选及其环境预检状态见 [独立任务目录](cases/swe/README.md)，不混入下方行为测试的通过记录。

本文件是用例状态入口，区分场景草案、可运行定义和历史执行记录。现有 13 个场景中，7 个已有可运行输入，6 个只有场景草案。当前版本已完成 D1 的真实配对与独立评审；其余历史结果仅适用于各记录中的目标文件哈希，不自动迁移为当前版本的通过结论。

## 当前可运行用例

用例定义存放在 `cases/behavior/` 的 JSON 中：`request` 和 `files` 是执行输入；`acceptance` 是评测端判据。执行器只将任务请求和 fixture 写入执行环境，定义与判据快照保存在执行区之外。

| 用例 | 检查内容 | 最近的历史执行记录 |
| --- | --- | --- |
| [D1](cases/behavior/D1.json) | 仅讨论时保留方案与实施边界 | 2026-10-05，当前 v0.2.0 快照：baseline／skill 均通过独立评审，本次隔离核查通过。[试跑报告](reports/pilot-2026-10-05.md)；[早期记录](smoke-results.json)保留。 |
| [D4](cases/behavior/D4.json) | 追加新的人工决定，保留原决定并更新现行设计 | 2026-10-04，早期 v0.2.0 快照：作者检查通过。[记录](smoke-results-v0.2.0.json) |
| [D7](cases/behavior/D7.json) | 交付说明保留未执行的验证事项 | 尚无完成运行的记录。 |
| [D10](cases/behavior/D10.json) | 将跨模块需求组织为完整目标，保留未决语义 | 2026-10-04，早期 v0.2.0 快照：作者检查通过。[记录](smoke-results-v0.2.0.json) |
| [D11](cases/behavior/D11.json) | 复用已有契约，按产出依赖协调独立需求 | 2026-10-05，Process／Workflow 修订快照：作者检查符合预期。[记录](process-workflow-results-2026-10-05.json) |
| [D12](cases/behavior/D12.json) | 识别未经确认的接口变化与真实集成失败 | 2026-10-04，早期 v0.2.0 快照：作者检查通过。[记录](smoke-results-v0.2.0.json) |
| [D13](cases/behavior/D13.json) | 为 general 需求形成计划，区分计划交付与功能完成 | 2026-10-05，Process／Workflow 修订快照：流程符合预期，计划存在重复说明。[记录](process-workflow-results-2026-10-05.json) |

迁移时保持了全部可运行用例的原始请求和 fixture 内容；[迁移记录](case-migration-2026-10-05.json)保存输入哈希。迁移本身不属于模型行为重测，也没有按新 rubric 重评历史产物。

## 尚未实现的场景

以下只有目的和预期行为，尚无完整可执行输入；不能作为已实现或已通过的测试。

| ID | 场景 | 预期行为 |
| --- | --- | --- |
| D2 | Existing accepted design/baseline plus explicit implementation request for a small defect. | Uses the existing contract, implements and meaningfully checks the defect without another general approval or a full new docs tree. |
| D3 | An agreed requirement conflicts with the available backend's capability. | Investigates supplied evidence and presents the problem, evidence, recommendation and impact; does not silently relax the requirement. |
| D5 | Feature works for the happy path but skips one required error case and violates a declared dependency boundary. | Reports the requirement defect and engineering violation separately with references. |
| D6 | Project records claim success but current code/evidence differs. | Reconciles actual state, identifies evidence limitations, and resumes from the affected scope. |
| D8 | General vocabulary question unrelated to a development task. | Answers directly without a development ceremony; forced invocation does not test natural routing. |
| D9 | Proposed major deployment change without sufficient authorization. | Produces supported decision material and performs no external mutation. |


## 运行与记录

在已初始化的终端中，按 [测试环境说明](README.md#本地测试环境)运行：

```sh
uv run --locked python tests/run_smoke.py --help
uv run --locked python tests/run_smoke.py D1
```

实际运行会调用模型。旧 `run_smoke.py` 每次只跑一个用例，固定为 180 秒超时，只支持显式加载目标 skill。新配对执行器和独立评价入口见 [运行说明](README.md#配对执行与独立评价入口)，可设置重复次数与超时。可执行不代表默认应全部运行；开始前确定本轮用例和预算。新执行记录包含用例定义快照、输入哈希、skill 文件哈希、命令轨迹及前后文件快照。

新执行／评价链路已完成一次 D1 真实配对与独立评审，本次 baseline 隔离经核查；不能由此推断其他场景或完整开发收益。自然触发与真实 SWE 任务尚未接入。[评价标准](rubrics.md)已与当前 skill 对齐，定性判断仍需人类样本校准。检查器和执行器的本地回归测试不调用模型：

```sh
uv run --locked python -m unittest discover -s tests -p 'test_*.py'
```

## 历史试跑预算

以下保留早期试跑安排，仅作历史记录，不作为当前执行指令。实际结果及限制见 [验证记录](validation.md)。

### Process/workflow revision budget — 2026-10-05

Run D13, then D11: two fresh target-present CLI trials, one attempt each, at most 180 seconds per trial. D13 exercises plan production for a general requirement; D11 checks coordination with existing agreements. Review generated artifacts and before/after snapshots against the criteria above. Report author assessment separately from independent grading and preserve earlier evidence.

### v0.2.0 update budget

Run D10 as the initial smoke, then D11, D12 and D4: four fresh target-present CLI trials, one attempt each, at most 180 seconds per trial. D4 covers a human decision changing an existing agreement; D10–D12 cover the revised process/workflow organization. Expectations stay outside the executor's prompt. Use actual traces and fixture snapshots for review; distinguish author assessment from independent grading. Other scenarios remain planned, not implicitly passed by the new version.

Initial smoke budget: at most three fresh target-present CLI cases, one attempt each, 180 seconds per case. Cases D1, D4 and D7 cover discussion scope, historical attribution and honest delivery. Other cases remain planned unless actual evidence is recorded. Use the configured model rather than silently selecting another; record the observed model/runtime and full completion state. Sandbox boundaries and installed competing instructions limit the interpretation of results.
