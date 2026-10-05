# Verifier 解耦与 packaging 环境修复结果

两项修改已完成。测试成绩只由任务 verifier 决定，过程分析独立进行；packaging 的已知本地实现副本已清理并通过重新预检。主工作区未修改、未合并。本轮没有更改 skill 内容，没有新增自动 LLM 分析系统。

工作区：`/Users/liyao/agent-led-swe-worktrees/verifier-and-environment-20261006`，分支 `fix/verifier-and-environment-20261006`，基于原生接入提交 `d608a2a`。核心修复冻结于 `84e4adf` 后执行原生 pytest 对照；随后补充了可重复运行的 packaging 资格检查命令与本报告。

## 1. 成绩与分析解耦

- `evaluate_results.py` 只校验证据并运行冻结的 verifier，不导入或调用模型判分流程，CLI 不再接受 judge 的模型配置。
- `task_status` 只由 verifier checks 汇总。历史 judge 的 checks／task_status 不导入新结果；没有 verifier 时保持 unknown。
- `run_status`、`comparison_validity` 与任务成绩分别保存。skill 加载、模型或来源审计异常影响实验有效性，不替 verifier 把代码判失败。
- 测试保留完整配置、原生调用、原始事件、文件变化与 verifier 证据。后续按 [分析指导](../analysis.md)记录观察、证据、归因与建议，不修改成绩。
- 在新目录中对旧 pytest 三组产物复算，verifier 均通过；旧 judge 判分及原始目录没有覆盖。这不把旧 document-reading 实验变成原生 skill 对照。

## 2. packaging 本地来源清理

完整 verifier 镜像仍为 `sha256:163233746275d789db7ea225d50c87f872681d1193d091df71ef7f78b0fa95f4`。Agent 使用独立 execution image，登记在 [资格记录](packaging-execution-environment-2026-10-06.json)。

清理范围包括全局与 venv 的其他 packaging 安装、pip／setuptools／wheel vendored 副本、uv／pip 缓存及 wheel；保留任务源码导入和所需工具。精简环境使用 uv 与 flit_core，不保留依赖已删除副本的全局 pip／setuptools。

首个 worker 审计又发现 npm/node-gyp 携带的 packaging。构建已改为仅复制 Agent 自己的 npm namespace，修复后两种 worker 均通过。该失败及此前发现保留，没有通过删除审计规则绕过。

`packaging_environment.py --inputs ...` 可重复执行清理、两轮 control/reference 和两种 worker 检查。每轮结果如下：

| 阶段 | 目标测试 | 回归测试 |
| --- | --- | --- |
| control（缺失实现） | 294 项，其中 284 失败，符合原始预期 | 3508 通过 |
| reference（参考实现） | 294 通过 | 3508 通过 |

两轮均一致，测试身份／结果指纹与原预检匹配。初次检查和脚本化复验各执行同一套 8 次无模型测试。Codex 0.160.0、CC 2.1.278 的实际 worker 均确认 CLI 可用、任务能安装、pytest 8.3.5 能启动，前后审计无替代实现目录或 wheel，Python 从 `/testbed` 导入任务包。

正式 rollout 启动前再次审计；不满足条件则不启动 Agent。结束后再次审计，新出现的本地副本标记实验无效，任务成绩仍单独保留。

**范围限制：** 处理的是本次发现的本地安装／vendored／缓存来源，不是完整网络访问控制或抗恶意绕过的沙箱。模型网络沿用现有设置；不宣称无法从任何远端获取代码。清理后的 packaging 尚未重新做真实 Agent 效果试跑。

## 3. 新原生 pytest 对照

使用当前基准 skill `/Users/liyao/agent-led-swe`，没有使用上一轮候选正文。CC 2.1.278 + DeepSeek Flash/high，baseline／skill 各一次，300 秒上限；原生安装／调用已确认，起始文件哈希相同。

| 结果 | baseline | skill |
| --- | --- | --- |
| Agent 状态 | completed | completed |
| 目标 verifier | 1/1 通过 | 1/1 通过 |
| 回归 verifier | 15/15 通过 | 15/15 通过 |
| task_status | pass | pass |
| 原生目标加载／缺席核查 | verified | verified |
| Executor 耗时 | 273.76 秒 | 189.66 秒 |
| 累计 input tokens（含缓存） | 591,701 | 770,194 |
| 其中 cache-read tokens | 572,416 | 746,624 |
| output tokens | 13,689 | 20,173 |

本轮启动 2 次 Agent，0 次 LLM judge，没有额外尝试。这里验证测试流程及原生调用正常，不对 skill 效果作因果结论；文档、推进、额外动作和归因留待后续历史分析。

## 4. 证据与检查

证据均在 `/Users/liyao/agent-led-swe/tests/runs/`：

- `packaging-environment-20261006-v1/`：初次清理和重复测试。
- `packaging-worker-preflight-20261006/`：npm/node-gyp 来源被拦截的失败。
- `packaging-worker-preflight-20261006-v2/`：修复后的两种 worker。
- `packaging-environment-20261006-repro/`：可重复命令的完整资格验证，作为登记依据。
- `verifier-only-history-check-20261006/`：旧产物新目录复算。
- `verifier-environment-20261006/pair-pytest-20261005T175022137274Z/`：新原生对照；`verification-20261005T180020698416Z/summary.json` 保存 verifier-only 汇总。

49 项本地测试通过，覆盖 verifier 独立决定结果、历史分数不干扰、无 verifier／未完成状态、原生有效性不改变任务成绩、证据篡改检查和环境资格拒绝。包检查与 diff 格式检查通过；测试容器已清理。

本分支继承了此前 worktree 历史，但本轮相对 `d608a2a` 只修改测试系统。后续采用修复时应只接收评测工具相关提交，不能顺带接受未经审阅的 skill 候选正文。
