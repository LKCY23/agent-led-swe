# 要求覆盖候选：结果与处理决定

2026-10-06 方法更正：本报告的三组试验使用 document-reading 模式，没有原生安装／调用 skill。本报告现保留 packaging 结果，不能作为 native skill 效果验收。接入修复和新模式证据见 [原生调用报告](native-skill-invocation-2026-10-06.md)。

结论：候选 `8b706d2` 没有证明改进，不合并。主工作区保持基准 `1c65c00`。本轮建立并验证了 worktree／冻结版本／独立证据的优化方式，同时发现迁移任务环境需要先处理的问题。

## 版本与隔离

| 内容 | 提交／位置 |
| --- | --- |
| 已接受内容的基准快照 | `1c65c00`；主工作区 `/Users/liyao/agent-led-swe`，基准分支 `baseline/20261005-pre-requirements-coverage` |
| 评测工具改造 | `462e38a`；支持显式 skill 路径、baseline／current／candidate、冻结来源与文件哈希、三组汇总及冻结副本校验 |
| 候选 skill 与事前计划 | `8b706d2`；分支 `candidate/requirements-coverage-20261005`，worktree `/Users/liyao/agent-led-swe-worktrees/requirements-coverage-20261005` |

基准提交包含此前实际评测过的未提交文件，未将旧 HEAD 误当基准。凭据、原始运行和虚拟环境被 Git 忽略；worktree 没有复制凭据。主工作区的 `AGENTS.md` 已记录以后沿用的隔离规则。候选与工具分开提交，未合并、安装或发布。

候选只修改 SKILL.md、implementation、engineering-baseline、verification 四份指导，强化要求保留、准备依据和完成核对。没有增加审批点、固定文档数量或 benchmark 专属文件名。44 项本地测试、包检查及 skill 元数据检查通过；worktree 暴露的目录名检查问题也已修正，包身份按元数据判断，不要求 worktree 目录恰好叫 agent-led-swe。

执行遵循 [事前计划](requirements-coverage-plan-2026-10-05.md)：相同 CC 2.1.278／DeepSeek Flash/high、相同任务和 rubric，每组 300 秒上限；独立 Codex／gpt-6.1-sol/high judge 上限 180 秒。全部三组使用候选 worktree 中的同一套评测器。运行中没有修改候选或判据。

## packaging：环境暴露其他实现，暂停迁移验证

按计划反序执行。candidate 在 300 秒达到超时；current 运行到约 289 秒时被人工停止；baseline 未启动。原始结果分别为 timeout、error、not_started；current 的 error 来自停止 runner，不是 Agent 自行报错。`control-stop.json` 记录原因与 SIGINT，采集器保留原始日志、结束记录及已有文件快照，容器已删除。

停止依据：两个已启动的 Agent 都读取了容器中的其他 packaging 实现；current 还用脚本从这些副本提取实现。只读、无网络的镜像检查确认，**依赖基础镜像已经包含**：

- `/usr/local/lib/python3.10/site-packages/packaging`，版本 26.2；
- `/usr/local/lib/python3.10/site-packages/setuptools/_vendor/packaging`，版本 24.2。

这些副本包含 metadata、requirements、parser 的完整实现；扩展为 CC worker 后文件哈希不变。暴露发生在容器依赖环境，未发现它来自主机配置导入，也没有把私有参考补丁或验收目录挂给 Agent。

其他版本不是已证明逐字相同的参考答案，但能够直接参考被遮蔽功能的实现，与本轮预期的迁移验证条件不一致。先前预检验证了测试和参考实现可运行，未检查 Agent 可读环境是否还暴露替代实现。此次 functional-only 汇总将三组保留为 unknown，没有执行额外功能测试或模型判分，也没有把超时解释为候选效果。

## 实际预算与证据


证据根目录：`/Users/liyao/agent-led-swe/tests/runs/requirements-coverage-20261005/`。

| 材料 | 相对该根目录的位置 |
| --- | --- |
| packaging 部分运行及停止原因 | `pair-packaging-20261005T154545173077Z/`、其中的 `control-stop.json` |
| 基础／worker 镜像实现副本核查 | packaging 目录的 `environment-source-audit.json` |
| packaging 未完成状态汇总 | packaging 目录的 `review-20261005T155712684445Z/summary.json` |

## 后续建议

先保持当前版，保留候选供审阅。下一轮应将两个问题分开：修复或重新限定 packaging 的可读环境并重新预检；过程分析改为独立读取轨迹，再决定是否设计下一版 skill 候选。不能在此次记录上替换环境、改分或补跑后宣称原候选通过。

packaging 的执行结果现已用于诊断，后续若据此调优，应归入开发用例，另选新的迁移任务。本轮没有证明长期协作、多 process 或复杂设计能力，也没有要求人类接受这个候选。
