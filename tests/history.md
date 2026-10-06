# 测试历史索引

当前选择见 [STATUS](STATUS.md)。历史报告中的“当前”“下一轮”和预算只适用于其记录时点。

| 主题 | 记录 | 结论或用途 |
| --- | --- | --- |
| 短流程提供方式／模型对照 | [指令诊断](reports/instruction-delivery-probe-2026-10-06.md) | 四组有效执行顺序正确；两次样例错误误启动保留 |
| 入口推进顺序候选 | [结果](reports/action-sequence-results-2026-10-06.md) | 未达到实施前记录目标；未接受 |
| 指导内联候选 | [结果](reports/inline-guidance-results-2026-10-06.md) | 仍先实现后记录；原版有连接错误；未接受 |
| 两题首次效果对照 | [结果](reports/paired-pilot-2026-10-06.md) | verifier 与流程观察分开；xarray 有任务／验收歧义 |
| 四题接入与资格 | [报告](reports/four-task-integration-results-2026-10-06.md)、[旧任务](cases/swe/README.md) | 环境与参考预检，不代表 skill 有效 |
| 网络与本地副本隔离 | [网络](reports/network-and-task-scope-2026-10-06.md)、[环境](reports/verifier-environment-results-2026-10-06.md) | 隔离修复与验证依据 |
| 原生安装与展开 | [检查](reports/native-skill-invocation-2026-10-06.md) | 区分原生调用与早期文档读取模式 |
| 早期候选与预检 | [需求覆盖](reports/requirements-coverage-results-2026-10-05.md)、[预检](reports/swe-preflight-2026-10-05.md) | 保留未接受结果与限制 |
| 本轮清理 | [记录](reports/test-cleanup-2026-10-06.md) | 删除清单、保留材料与恢复依据 |

完整时间记录见 [validation](validation.md)。历史报告不移动，已有引用保留。

## 原始材料

根目录为 `/Users/liyao/agent-led-swe/tests/runs/`，不进入 Git。以下核心材料完整保留：

- `paired-pilot-20261006`：首轮真实任务对照。
- `inline-guidance-diagnostic-20261006`、`action-sequence-diagnostic-20261006`：两次候选诊断与准备失败。
- `instruction-delivery-probe-20261006`、`instruction-delivery-probe-v2-20261006`：有缺陷样例与修复后的四组对照。
- `four-task-inputs-v2-20261006`：旧四题的规范冻结输入。
- `four-task-preflight-20261006`、`four-task-workers-20261006`：资格与 worker 检查。

清理只删除早期可重建展开目录和预检的重复源码副本。压缩包、元数据、补丁、环境配方、日志和评分保留。旧路径仍可能出现在历史日志中，不表示文件当前存在；具体路径与恢复依据见清理记录。

## 候选恢复

闲置 checkout 移除后，下列 Git 分支保留，可用 `git worktree add <新目录> <分支>` 恢复：

| 分支 | 提交 | 状态 |
| --- | --- | --- |
| `diagnostic/action-sequence-20261006` | `dbdf29b` | 未接受的入口顺序候选 |
| `diagnostic/inline-guidance-20261006` | `ee58579` | 未接受的内联诊断版 |
| `fix/native-skill-invocation-20261006` | `d608a2a` | 旧工具／候选工作区，不是当前基线 |

运行包中另有被测 skill 的文件快照与哈希。
