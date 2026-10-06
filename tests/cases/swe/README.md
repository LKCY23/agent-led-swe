# 真实 SWE 任务：选择与接入

本轮先审阅任务是否适合检验 skill，再决定效果试跑。可执行资格与评测适用性分别判断。

| 任务 | 当前状态 | 适用范围与限制 |
| --- | --- | --- |
| [packaging](packaging.json) | 已通过环境预检，统一入口可用；暂未启动新对照 | 多文件实现、需求覆盖、兼容性与交付；接口已经给定，不能充分检验自主接口设计。 |
| [DSPy](dspy.json) | 未启用，等待稳定性处理与审阅 | 同步／异步 ReAct 与工具协作较接近模块变更；回归存在模拟服务启动、耗时断言和联网资源问题。 |
| [Agents SDK](agents-sdk.json) | 按用户决定暂缓 | 文字需求与参考实现的 None 过滤行为冲突。 |

任务选择理由和建议见 [候选审阅](../../reports/task-selection-2026-10-06.md)。现有候选均为开发／校准用例，不是未见验证集。小型修复不足以检验设计、文档和项目管理能力；已退出的 pytest 任务及专属运行历史按用户决定清理。

## 输入与验收分离

定义文件记录 dataset、split、任务 ID、base commit、冻结数据与源码归档哈希。完整数据、补丁和隐藏测试仅留在评测端；执行 Agent 只获得 learner 工作区。

- learner：任务起始代码，不含参考补丁或隐藏测试。
- control：起始代码加可信评分测试，确认未实现时失败。
- reference：参考实现加同一组评分测试，确认验收可通过。

FeatureBench 的 patch 遮蔽实现，参考状态需要反向恢复；其他修复型来源的 patch 正向应用。适配器保留这个差异，不改变统一 verifier 的职责。

## 环境与预检

依赖在准备镜像时安装。正式 Agent worker 使用内部网络，仅能访问固定模型网关；公开资源应事先冻结准备，不能依赖执行时联网下载。DSPy 旧预检的 bridge 网络是未解决的限制，不是新版 executor 的例外。

packaging 使用独立的精简 executor 镜像与完整 verifier 镜像，并审计本地实现副本。[资格记录](../../reports/packaging-execution-environment-2026-10-06.json)锁定任务和镜像。预检结果见 [报告](../../reports/swe-preflight-2026-10-05.md)。

已有冻结输入可复验：

```sh
uv run --locked python tests/preflight_swe.py tests/cases/swe/packaging.json \
  --inputs '<冻结输入目录>' --output '<新输出目录>'
```

每轮 control/reference 各两次，每次分目标与回归组，最多 8 次测试命令、每次 180 秒、2 CPU、3 GB。首次非预期结果即停止排查，不删除失败测试、不放宽断言、不以重跑替代归因。预检通过只证明既定验收能够稳定运行，不证明覆盖全部文字需求。
