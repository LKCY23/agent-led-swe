# agent-led-swe 测试机制

更新：2026-10-06。测试负责执行、保存完整历史和调用 verifier；后续过程分析独立进行，不决定任务是否通过。先看 [当前状态](STATUS.md)，实现约定见 [协议](protocol.md)，既往实验见 [历史索引](history.md)。

## 职责与结果

| 部分 | 职责 |
| --- | --- |
| Executor | 按冻结配置运行 Agent，保留原始事件、用量、原生 skill 调用、文件前后快照和变化清单。 |
| Verifier | 根据任务的可信测试检查提交产物，给出功能结果和原始证据。 |
| 历史分析 | 人类与 Agent 按需检查机制、推进、文档和交付，形成观察、归因与优化建议；不自动调用 LLM judge、不修改分数。 |

结果分别记录：
- `run_status`：是否启动、完成、超时或执行出错。
- `comparison_validity`：配置、原生调用等是否支持本次对照；无效不等于代码失败。
- `task_status`：只由 verifier 给出 pass／fail／unknown。未配置 verifier、缺少完整提交或验证受阻时不能虚构通过／失败。

本仓库使用 benchmark 原始测试与本地 Docker 验证适配；不是原 benchmark 官方镜像的榜单成绩。原始计数、xfail、skip、错误与日志均保留。

## 本地测试环境

使用 uv、Python 3.11 和锁定依赖，不修改全局 Python：

```sh
uv sync --locked
uv run --locked python -m unittest discover -s tests -p 'test_*.py'
uv run --locked python tests/check_package.py
uv run --locked python tests/check_hosts.py
```

自动化工具使用已初始化的终端，如 `zsh -lic 'uv run --locked python tests/check_hosts.py'`。真实 SWE executor 在容器内按 `configs/agents.json` 安装固定版本，不依赖本机 CC Switch；本地行为用例使用本机 Codex。

## 配对执行与独立评价入口

开始前固定任务、版本、模型、预算和比较组。下面的执行命令调用模型，验证命令不调用模型：

```sh
uv run --locked python tests/run_evaluation.py D14 \
  --agent claude-code --model-profile tests/configs/models/deepseek-v4.1-flash.json \
  --credentials '<本地凭据文件>' \
  --skill-path tests/fixtures/instruction-delivery \
  --direct-guidance tests/fixtures/instruction-delivery/guidance.md \
  --output-root '<独立运行目录>' --effort high --timeout 180
uv run --locked python tests/evaluate_results.py '<上一步运行目录>'
```

Codex 使用 `--agent codex --model-profile tests/configs/models/codex-gpt-6.1-sol.json`。支持 baseline／skill 两组；加 `--reference-skill-path` 则比较 baseline／current／candidate。每组每轮新建工作区与会话，默认每组一次、不自动重跑；`--repetitions` 和 `--reverse-order` 控制已记录的重复与顺序。

仅比较两个 skill 版本时，同时使用 `--reference-skill-path` 和 `--without-baseline`，执行 current／candidate 两组；计划以 current 为初始文件一致性检查的参照，不运行无 skill 组。

`--direct-guidance <文件>` 用于诊断指令提供方式：同一正文直接放入请求，或通过原生 skill 提供，组别为 direct／skill。正文必须与所选 skill 的完整正文一致，且不能同时使用版本对照选项。`D14` 是这一诊断的小型 Docker 任务，使用 `tests/fixtures/instruction-delivery/` 的三步指令；它不代表完整 agent-led-swe 的效果。

Codex 将 skill 安装到隔离 HOME 的 `.agents/skills/agent-led-swe/`，提示词以 `$agent-led-swe` 开头；CC 安装到 `.claude/skills/agent-led-swe/`，以 `/agent-led-swe` 开头。baseline 不安装目标。发现与原生调用均核查，不以普通 Read 或模型自述代替。[原生接入验证](reports/native-skill-invocation-2026-10-06.md)。

DeepSeek 凭据填在被 Git 忽略的 `tests/configs/credentials.local.json`，可从 `credentials.example.json` 创建；环境变量优先，`--credentials` 可指定其他文件。直接 API 检查使用 `check_model_connection.py`；受限容器的真实连通检查使用 `check_worker_network.py`（每次一个 Agent 会话、90 秒）。两者都不改变本机日常配置。

## 任务与环境

- D14 保留快速诊断。旧 SWE 任务退出当前推荐组合，适配器、输入和资格记录保留供显式回归；见 [状态](STATUS.md)与[旧任务目录](cases/swe/README.md)。多轮 benchmark 尚未接入。
- packaging 的 verifier 镜像保留完整测试依赖，Agent 使用单独精简的 execution image。已知安装／vendored／缓存副本清除后，需要重复起始／参考检查；实际 worker 安装项目后和执行结束时还会审计。
- 行为场景见 [场景与状态](scenarios.md)。它们可以执行和分析，但没有程序 verifier 的场景，task_status 保持 unknown。
- 不挂载私有参考补丁、验收材料或宿主 Docker socket。正式 Docker worker 只通过固定模型网关出站；直接外网与非许可代理路径被阻止，本地来源审计继续保留。

## 保存与后续分析

每个新运行目录保留：
- plan、case、来源版本与输入／skill 哈希、模型和预算；
- prompt、原始 stdout／stderr、工具轨迹、实际原生安装与调用、环境审计；
- 全部文件前后快照、变化清单、用量及失败／超时记录；
- verifier 的测试副本、安装与运行日志、XML、原始计数、结果与汇总。

重新验证使用新目录，不覆盖原记录。分析按 [测试历史分析](analysis.md)进行，单独保存观察、证据、归因假设、反证和建议。小任务不要求完整文档套件；涉及人类决策或长期维护时，用实际协作记录分析，不虚构 simulated user。

旧 [rubric](rubrics.md)、judge 判分和文档读取模式结果保留为历史材料，不进入新成绩，也不与 native 模式混合比较。不能凭单个任务、单轮通过或耗时下降认定 skill 有效。

## 隔离优化与检查

按仓库 AGENTS.md：基准提交 → 独立 worktree → 工具与 skill 分开修改 → 冻结版本 → 有限测试 → 审阅后决定是否合并。当前版本不被候选覆盖；已用于调优的任务不再称为未见验证集。

`check_swe_pipeline.py` 使用未修复／参考产物检查验收链路，不调用模型。`check_codex_worker.py`、`check_claude_worker.py` 以模拟 API 检查真实 CLI 原生接入，不能证明模型或 skill 效果。原始记录索引见 [验证记录](validation.md)。

当前任务选择以 [STATUS](STATUS.md) 为准。示例命令只说明接口，不表示已授权新的模型运行。旧四题的准备、预检与 worker 检查入口继续保留，相关历史不作为当前默认测试安排。
