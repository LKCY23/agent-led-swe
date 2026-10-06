# 新 benchmark 接入前的清理

## 当前结果

旧单次请求 SWE 任务退出当前推荐组合；通用执行与评测能力、D14 快速诊断和核心历史证据保留。多轮 benchmark 尚未接入或执行。

当前状态由 [STATUS](../STATUS.md) 维护，证据入口见 [history](../history.md)。测试 README、协议、场景与旧任务说明已同步，不再将此前四题称为当前主组合。CLI 按名称显式调用旧任务的能力保留，不新增运行审批选项。

## 工具与 skill 基线

清理前测试工具提交为 `9c3fb4c`。当前测试工作区继承的四份未接受 skill 修改已恢复至 `1c65c00`，提交 `01832f5`；测试工具改进保留。工作分支为 `chore/test-baseline-cleanup-20261006`。

正式主工作区 `/Users/liyao/agent-led-swe` 未修改，仍保留接受版本。未合并任何内容候选。清理后的工具与接受 skill 组合以本轮提交和 `test-baseline-2026-10-06` 标签固定，供后续接入工作引用。

## 实际删除

删除 45 个可重建源码目录，135,363 个文件，删除前文件分配空间合计约 1,627 MiB（约 1.59 GiB；不等同于 APFS 最终物理可用空间增量）：

- `four-task-inputs-20261006/{smolagents,xarray,nodebb,navidrome}/public/`：4 个旧展开副本；对应 `public.tar.gz`、元数据与准备日志保留。
- `swe-preflight-20261005/*-attempt-*/` 下的 `learner`、`control`、`reference` 及编号源码副本：41 个目录；原始任务压缩包、元数据、补丁、构建配方、manifest、测试日志和评分保留。

没有删除正式模型执行的轨迹、前后快照、失败记录、可信测试或当前规范输入。旧日志中的某些展开路径已不存在；可通过保留压缩包和准备流程重建，不能把旧路径当作当前工作目录。

完整删除清单与逐目录恢复依据：`/Users/liyao/agent-led-swe/tests/runs/cleanup-20261006/deletion-manifest.json`。该清单先于删除保存，每项删除后更新状态。

## Worktree 整理

确认无未提交或未跟踪工作后，移除以下 checkout。分支仍指向原提交，可恢复：

| Checkout | 保留分支 | 提交 |
| --- | --- | --- |
| `action-sequence-20261006` | `diagnostic/action-sequence-20261006` | `dbdf29b` |
| `inline-guidance-20261006` | `diagnostic/inline-guidance-20261006` | `ee58579` |
| `requirements-coverage-20261005` | `fix/native-skill-invocation-20261006` | `d608a2a` |

第三个 checkout 的忽略文件仅为可重建虚拟环境和 Python 缓存，随 checkout 清理。明细在同目录 `worktrees.json`。主工作区与当前测试工作区保留。

## 验证与保留项

清理前后核对 30,846 个核心证据文件，哈希一致。覆盖近期效果试跑、两个候选诊断、短流程的有缺陷样例与修复后运行、四题规范冻结输入、资格预检和 worker 检查。清理没有通过删除失败来改变成绩。

保留任务专属适配代码、环境配方及镜像；它们尚可能用于重建与回归，待新 benchmark 预检通过后再评估退出。没有运行 Docker 全局清理，没有修改凭据或宿主 Agent 配置。

本轮不调用真实模型，不改功能判据。最终本地测试、包引用、接受 skill 一致性与规范输入检查的结果记录在 validation 的本轮条目中。
