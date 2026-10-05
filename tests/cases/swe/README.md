# 真实 SWE 任务：候选与环境预检

pytest 和 packaging 已接入 [统一执行与评价入口](../../protocol.md)，并通过受控链路检查。[pytest 首轮真实对照](../../reports/pytest-pilot-2026-10-05.md)已完成；packaging 尚未试跑。DSPy 和 SDK 保留为未启用候选。

| 定义 | 来源与任务 | 当前判断 |
| --- | --- | --- |
| [pytest.json](pytest.json) | SWE-bench Verified，日志清空后的状态一致性 | 两轮环境与指定测试预检通过。 |
| [packaging.json](packaging.json) | FeatureBench fast / Level 1，包元数据与依赖解析 | 两轮环境与指定测试预检通过。 |
| [dspy.json](dspy.json) | 社区 FeatBench-Verified，异步 ReAct 与同步工具兼容 | 用户选定的替代候选。目标测试可区分起始／参考状态，但本机回归出现服务启动与耗时断言波动，尚未通过稳定性预检。 |
| [agents-sdk.json](agents-sdk.json) | 社区 FeatBench-Verified，extra_args 跨后端透传 | 用户决定暂缓。保留其需求／参考行为冲突的证据，不进入首批对照。 |

这些任务均属于开发／校准样本，不是保留集。当前首批候选是 pytest、packaging、DSPy，其中仅前两项通过预检。结果与限制见 [预检报告](../../reports/swe-preflight-2026-10-05.md)。

## 输入与验收分离

定义文件记录 dataset、split、定位行、任务 ID、base commit、冻结数据与源码归档哈希。行号只用于定位，身份仍以 instance ID 和哈希核对。完整原始数据、源码归档、补丁、容器日志及测试 XML 留在忽略的 `tests/runs/swe-preflight-20261005/`，不向执行 Agent 提供。

`preflight_swe.py` 从已准备的冻结输入生成三个目录：

- `learner/`：未来执行 Agent 的起始代码，不包含新增／恢复的隐藏测试或参考补丁文件。
- `control/`：起始代码加评分测试，用于确认未修复时确实失败。
- `reference/`：参考实现加相同评分测试，用于检查验收可通过。

FeatureBench 的 patch 用于遮蔽实现、test_patch 用于删除隐藏测试；验收时恢复测试，参考实现反向应用遮蔽补丁。SWE-bench／FeatBench 的 patch 则正向提供修复，test_patch 正向加入评分测试。这两种语义不能混用。

## 本地预检

需要已经启动的 Docker 和本仓库 uv 环境。当前适配使用 Linux ARM64 容器，pytest／packaging 使用 Python 3.10，DSPy 使用其声明支持的 Python 3.12，SDK 使用 Python 3.13；不是官方镜像结果。安装依赖时联网，测试时默认禁网；DSPy 的原始回归需要下载公开图片和 PDF，明确使用 bridge 网络。所有测试均不传入宿主凭据，相关模型测试使用 mock／容器内模拟服务。依赖通过容器内 uv 管理；SDK／DSPy 受各自 uv.lock 约束。镜像 ID、安装包清单和实际命令均记录在证据目录。

对本机已有的冻结输入，可重新运行：

```sh
uv run --locked python tests/preflight_swe.py tests/cases/swe/pytest.json \
  --inputs tests/runs/swe-preflight-20261005 \
  --output tests/runs/pytest-recheck
```

输出目录必须尚不存在。每次预检计划在独立副本上运行 control／reference 各两轮，每轮分别运行 F2P、P2P，最多 8 次测试命令；出现非预期结果时停止后续重复，先检查证据。每次测试最多 180 秒；单容器限制 2 CPU、3 GB，结束后清理容器。依赖镜像与原始证据保留供复查。来源下载仍需先准备冻结输入；已有输入可以由统一入口直接适配、执行和验收。

结果汇总判断运行矩阵是否完整、control 是否暴露失败、reference 和回归是否符合预期、两轮逐项结果是否一致。原测试的 xfail 单独记录，不算通过或普通跳过；目标测试不能靠 xfail 满足要求，回归中的预期失败也不得因参考补丁而增加或变化。它不能证明测试覆盖了全部文字需求。[SDK 诊断脚本](agents_sdk_none_probe.py)用于单独检查已发现的语义缺口，不混入原 benchmark 分数。
