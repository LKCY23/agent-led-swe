# 要求覆盖候选：结果与处理决定

结论：候选 `8b706d2` 没有证明改进，不合并。主工作区保持基准 `1c65c00`。本轮建立并验证了 worktree／冻结版本／独立证据的优化方式，同时发现候选仍未落实实现前的规范核查，以及迁移任务环境和定性判分需要先处理的问题。

## 版本与隔离

| 内容 | 提交／位置 |
| --- | --- |
| 已接受内容的基准快照 | `1c65c00`；主工作区 `/Users/liyao/agent-led-swe`，基准分支 `baseline/20261005-pre-requirements-coverage` |
| 评测工具改造 | `462e38a`；支持显式 skill 路径、baseline／current／candidate、冻结来源与文件哈希、三组汇总及冻结副本校验 |
| 候选 skill 与事前计划 | `8b706d2`；分支 `candidate/requirements-coverage-20261005`，worktree `/Users/liyao/agent-led-swe-worktrees/requirements-coverage-20261005` |

基准提交包含此前实际评测过的未提交文件，未将旧 HEAD 误当基准。凭据、原始运行和虚拟环境被 Git 忽略；worktree 没有复制凭据。主工作区的 `AGENTS.md` 已记录以后沿用的隔离规则。候选与工具分开提交，未合并、安装或发布。

候选只修改 SKILL.md、implementation、engineering-baseline、verification 四份指导，强化要求保留、准备依据和完成核对。没有增加审批点、固定文档数量或 benchmark 专属文件名。44 项本地测试、包检查及 skill 元数据检查通过；worktree 暴露的目录名检查问题也已修正，包身份按元数据判断，不要求 worktree 目录恰好叫 agent-led-swe。

执行遵循 [事前计划](requirements-coverage-plan-2026-10-05.md)：相同 CC 2.1.278／DeepSeek Flash/high、相同任务和 rubric，每组 300 秒上限；独立 Codex／gpt-6.1-sol/high judge 上限 180 秒。全部三组使用候选 worktree 中的同一套评测器。运行中没有修改候选或判据。

## pytest：三组均完成，候选仍有遗漏

| 结果 | baseline（无 skill） | current（当前版） | candidate（候选版） |
| --- | --- | --- | --- |
| 功能验收 | 目标 1/1、回归 15/15 | 目标 1/1、回归 15/15 | 目标 1/1、回归 15/15 |
| Judge A1：工程要求 | pass | pass | fail |
| Judge A2：依据、验证与交付说明 | pass | fail | pass |
| 原始总体判分 | pass | fail | fail |
| Executor 耗时 | 107.47 秒 | 278.77 秒 | 130.29 秒 |
| input tokens（含缓存） | 610,149 | 494,195 | 819,591 |
| 其中 cache-read tokens | 585,984 | 476,416 | 797,056 |
| output tokens | 17,610 | 13,543 | 23,327 |

起始文件哈希一致，三组均通过 discovery 检查。功能测试由独立环境恢复可信测试后执行；token 数为累计请求用量，cost 未知。

人工核对支持的事实：

- 上次 current 漏读贡献指南；本次检索了相关规范，表明这一遗漏存在运行波动。一次失败对一次通过不能单独建立因果。
- current 扩大测试范围后，将 10 个失败和 1 个错误整体称为原有／环境问题，但只在回退后复现了其中 9 个失败。Judge 因交付说明过度概括而将 A2 判为 fail。
- candidate 读取 Process、Design 和 Verification，但在修改代码后才读取 CONTRIBUTING.rst 的前 60 行，遗漏实际适用的修改与测试指导。因此，增加要求说明没有保证“核实适用依据 → 实现”的行为成立。读取更多 skill 文档不是成功依据。
- 三组都猜测了 changelog 编号；candidate 明确把编号称为占位。三个 judge 对此以及“测试失败是原有问题”的断言，严格程度不完全一致。尤其 candidate 的 A2 在承认该归因未证实时仍为 pass，而 current 的类似过度概括被判 fail。原始判分保留，需统一核对具体证据与措辞差异后校准，不能直接用总体 pass/fail 当可靠的质量排名。

因此，这轮支持“功能修复完成，流程要求仍不稳定”，不支持候选更优。候选输出用量也没有减少。单次、有限顺序的实验不用于总体效率或稳定性结论。

## packaging：环境暴露其他实现，暂停迁移验证

按计划反序执行。candidate 在 300 秒达到超时；current 运行到约 289 秒时被人工停止；baseline 未启动。原始结果分别为 timeout、error、not_started；current 的 error 来自停止 runner，不是 Agent 自行报错。`control-stop.json` 记录原因与 SIGINT，采集器保留原始日志、结束记录及已有文件快照，容器已删除。

停止依据：两个已启动的 Agent 都读取了容器中的其他 packaging 实现；current 还用脚本从这些副本提取实现。只读、无网络的镜像检查确认，**依赖基础镜像已经包含**：

- `/usr/local/lib/python3.10/site-packages/packaging`，版本 26.2；
- `/usr/local/lib/python3.10/site-packages/setuptools/_vendor/packaging`，版本 24.2。

这些副本包含 metadata、requirements、parser 的完整实现；扩展为 CC worker 后文件哈希不变。暴露发生在容器依赖环境，未发现它来自主机配置导入，也没有把私有参考补丁或验收目录挂给 Agent。

其他版本不是已证明逐字相同的参考答案，但能够直接参考被遮蔽功能的实现，与本轮预期的迁移验证条件不一致。先前预检验证了测试和参考实现可运行，未检查 Agent 可读环境是否还暴露替代实现。此次 functional-only 汇总将三组保留为 unknown，没有执行额外功能测试或模型判分，也没有把超时解释为候选效果。

## 实际预算与证据

原计划最多 6 次 Executor、6 次 judge。实际启动 5 次 Executor（pytest 3 次完成，packaging 1 次超时、1 次中止），运行 3 次 pytest judge；没有自动追加 attempts。packaging baseline 未运行的事实保留在冻结矩阵中。

证据根目录：`/Users/liyao/agent-led-swe/tests/runs/requirements-coverage-20261005/`。

| 材料 | 相对该根目录的位置 |
| --- | --- |
| pytest 执行及冻结版本 | `pair-pytest-20261005T153634391097Z/` |
| pytest 原始独立判分 | 上述目录的 `review-20261005T154545168442Z/summary.json` |
| packaging 部分运行及停止原因 | `pair-packaging-20261005T154545173077Z/`、其中的 `control-stop.json` |
| 基础／worker 镜像实现副本核查 | packaging 目录的 `environment-source-audit.json` |
| packaging 未完成状态汇总 | packaging 目录的 `review-20261005T155712684445Z/summary.json` |

## 后续建议

先保持当前版，保留候选供审阅。下一轮应将两个问题分开：修复或重新限定 packaging 的可读环境并重新预检；用本轮证据校准同一工程要求的判分口径，再决定是否设计下一版 skill 候选。不能在此次记录上替换环境、改分或补跑后宣称原候选通过。

packaging 的执行结果现已用于诊断，后续若据此调优，应归入开发用例，另选新的迁移任务。本轮没有证明长期协作、多 process 或复杂设计能力，也没有要求人类接受这个候选。
