# 真实 SWE 候选的环境与验收预检

日期：2026-10-05。结论：pytest、packaging 可进入下一步接入；按用户决定暂缓 SDK，改做 DSPy 预检，但 DSPy 的本机回归尚不稳定。没有调用模型，也没有运行 skill／baseline 对照。

## 实际结果

最初三个候选的每个条件在独立代码副本中运行两次，下表两轮结果完全一致。F2P 是需要从失败变为通过的目标测试，P2P 是不应退化的回归测试。后续 DSPy 的不同结果单列在下一节。

| 任务 | 起始代码的目标测试 | 参考实现的目标测试 | 回归测试：起始／参考 | 判断 |
| --- | --- | --- | --- | --- |
| pytest 日志状态修复 | 1 项失败 | 1 项通过 | 各 15 项通过 | 指定验收预检通过。 |
| packaging 元数据处理 | 294 项中 284 项失败 | 294 项全部通过 | 各 3,508 项通过 | 指定验收预检通过。 |
| Agents SDK extra_args | 8 项全部失败 | 8 项全部通过 | 各 349 项通过 | 测试链路通过，但任务描述与参考实现存在冲突。 |

共完成 24 次测试命令，没有超时、collection error 或 skip。SDK 的 331 个 P2P 节点在参数化展开后产生 349 项实际测试；FeatureBench 按文件列出测试，因此不是“只有 1 项目标测试”。两轮一致只支持本次短期复现，不证明长期无波动。

## SDK 为什么暂缓

冻结的任务描述要求从 extra_args 字典中滤掉值为 None 的项。参考实现的 ChatCompletions 路径直接展开该字典；指定测试覆盖了整个 extra_args 为 None、空字典和普通透传，没有验证字典内部的 None 值。

额外的 [最小诊断](../cases/swe/agents_sdk_none_probe.py)在参考代码上将模型客户端替换为本地 mock，传入一个 None 项和一个普通值，实际得到：

```json
{"reference_null_filtered": false, "reference_non_null_forwarded": true}
```

诊断在禁网容器中执行，没有访问真实模型服务。它证实了文字要求与参考行为的冲突，因此不能仅凭 benchmark 测试全过就把该任务判为完整满足需求。没有修改原需求、参考实现或评分测试。

用户已决定暂缓 SDK，改选 DSPy 并另做预检。SDK 的原始需求与测试均保持不变，保留诊断作为排除依据。

## DSPy 替代候选的结果

固定社区 FeatBench-Verified 中的 `stanfordnlp__dspy-8139`，base commit 为 `cefe8db85bca3a520bd82c7d9fdbde7efff44214`。该版本声明 Python <3.13，使用 Python 3.12.14；依赖由原始 uv.lock 约束，并补齐原项目 dev 配置声明的 LiteLLM proxy 测试依赖。

完整的第 3 次尝试中，起始状态的两个目标测试两轮均失败，参考实现两轮均通过；回归的 256 个选择器展开为 305 项：

| 条件 | 实际回归结果 |
| --- | --- |
| control 第 1 轮 | 302 passed、2 xfailed、1 setup error：模拟服务未在原测试规定的 10 秒内启动。 |
| control 第 2 轮 | 303 passed、2 xfailed。 |
| reference 第 1 轮 | 303 passed、2 xfailed。 |
| reference 第 2 轮 | 302 passed、2 xfailed、1 failed：`test_asyncify` 触发耗时断言。 |

两项 xfail 是原测试主动标注的 PIL 输入支持限制，不代表新功能通过，也不是被本次评测删掉的失败项。汇总器已区分 xfail 与普通 skipped，并比较逐项结果指纹，避免仅凭失败数量相同就声称重复稳定。

前两次准备分别发现 proxy 测试依赖缺失、全断网与公开图片／PDF 下载不兼容，保留日志后停止了无效重复。第 3 次使用 bridge 网络完成上表；没有传入宿主凭据。第 4 次改用 LiteLLM 包内固定的模型价格表，避免启动时获取在线价格数据，但 setup error 再次出现，已停止后续重复。没有修改测试超时、耗时断言或待测实现。

因此 DSPy 的目标功能具有可执行验收，但**本机完整回归稳定性尚未通过**。暂不把它作为干净的 skill 对照样本；后续需要单独稳定其测试服务／资源环境，或重新选题。不能用该问题判断 Agent 或 skill 的能力。

## 环境与过程

- 固定到各任务的 base commit；冻结完整数据行、源码归档及其 SHA256，保留参考材料。
- 本机 Docker 启动后，使用自建 Linux ARM64 依赖镜像。pytest／packaging 为 Python 3.10.20，SDK 为 Python 3.13.14。未使用官方预构建镜像，因此不声称复现官方榜单环境。
- 依赖通过容器内 uv 安装，原三个任务测试时关闭网络，DSPy 的例外见上节；每次容器限制 2 CPU、3 GB。SDK／DSPy 使用原仓库 uv.lock 约束依赖版本。
- pytest 的源码归档没有 Git 版本标签，安装时显式提供 setuptools-scm 的开发版本；这属于环境适配，未修改待测源码。
- SDK 第一次准备遇到适配脚本读取 TOML 层级错误，第二次遇到离线 editable 构建缺少 editables。修复的是适配器与构建依赖，第三次完成全部测试；前两次记录保留，未算作 Agent 或任务失败。
- FeatureBench 正向 patch 是遮蔽操作，参考实现需要反向恢复；已按官方运行逻辑区分。见 [FeatureBench runtime](https://github.com/LiberCoders/FeatureBench/blob/main/featurebench/harness/runtime.py)。

## 证据与下一步

可审阅的结构化结果见 [预检记录](swe-preflight-2026-10-05.json)，任务定位见 [任务目录](../cases/swe/README.md)。原始材料在本机忽略目录：

```text
tests/runs/swe-preflight-20261005/
├── pytest-attempt-1/
├── packaging-attempt-1/
├── agents-sdk-attempt-1/       # 适配器准备失败
├── agents-sdk-attempt-2/       # 离线构建缺少依赖
├── agents-sdk-attempt-3/       # 全部指定测试完成
└── agents-sdk-none-probe/      # 单独的需求一致性诊断
```

DSPy 的完整结果位于同目录下 `dspy-attempt-3/`；其余 `dspy-attempt-1/`、`dspy-attempt-2/`、`dspy-attempt-4/` 保留未完成尝试及中止证据。结构化记录包含这些状态，不将其丢弃或统计为通过。

所有测试容器均已清理，依赖镜像和原始证据保留。当前行为用例 runner 尚不能直接运行这些真实仓库；后续需要连接隔离的 learner 工作区、补丁提取、独立功能验收及工程／文档评审。不能把此次环境预检算作 skill 效果评测，或把第 4 步整体标为完成。
