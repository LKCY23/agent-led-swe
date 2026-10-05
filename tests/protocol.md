# 统一任务、执行与评价协议

目标是比较 Agent 在相同开发任务下使用／不使用 skill 的结果。Benchmark 提供任务与验证资源；来源差异在适配时处理，执行和评价共用规则。

```text
行为 case / benchmark 数据
          ↓ task_adapters：准备并冻结任务
统一任务 → run_evaluation：配对执行与采集
          ↓ 不可变产物、轨迹、用量
evaluate_results → 功能验收 + 独立定性评审 → 逐项比较
```

## 1. 任务约定

适配器输出一个准备好的任务，包含以下内容：

| 内容 | 用途与可见范围 |
| --- | --- |
| `id`、`request` | 任务身份及双方共同获得的要求。 |
| `workspace` | 起始代码和项目资料；每次执行复制一份。 |
| `environment` | 运行环境；行为任务使用本地工作区，已接入的 SWE 任务使用固定 Docker 镜像。 |
| `validation` | 可信验证材料和检查方式，只交给评测端；行为任务可以不需要功能测试。 |
| `acceptance` | 定性评审判据，不放入执行者工作区。共同交付要求已明确写入 request。 |
| `provenance` | 来源、版本、输入哈希及改编说明，保留追溯依据。 |

FeatureBench 的遮蔽、隐藏测试恢复与其他 benchmark 的正向修复，均由适配器处理。执行器只消费准备好的任务，不解释原始 patch。

参考实现用于预检与测试框架自检，不保存在正式任务的公共工作区中。正式功能评价检查提交产物，不比较 Agent 是否复刻参考代码。

真实任务目前只开放已通过预检的 pytest 和 packaging。SDK 暂缓，DSPy 尚未满足本机稳定性要求。接入其他候选需要相匹配的预检证据，不能只将名字加入 CLI。

## 2. 执行与产物约定

每轮先冻结任务、skill、rubric、模型／预算和运行矩阵。Baseline 与 skill 使用相同的任务、环境、工程要求和权限；只有 skill 组获得目标指导。项目规范仍是双方共同任务输入，不因禁用全局 skills 而被取消。

真实任务在独立 Docker 容器中运行 Codex 或 CC。基础镜像提供项目依赖，Agent 安装层按 `configs/agents.json` 固定 CLI 版本，`--agent-version` 可显式覆盖并记录；不从本机 CLI 推断容器版本。只挂载公共工作区及 skill 组的只读指导，不挂载评分目录、参考实现或 Docker socket。Codex 使用 full-access；CC 以匹配工作区所有者的非 root 用户使用 bypassPermissions。二者均由容器提供边界，不额外授予内核 capability。

模型 profile 与 Agent 分开选择，运行前验证组合和 effort。Codex 沿用只读挂载的 auth.json；CC 从显式环境变量或被 Git 忽略的 `configs/credentials.local.json` 取密钥，通过临时 env 文件注入容器，容器启动后立即删除该临时文件。凭据不写入镜像、命令参数或证据；也不读取本机 CC／CC Switch 设置。

skill 组安装原生 skill 并显式调用，baseline 不安装。CC 禁用插件、MCP 和委派工具；固定 CLI 自带的 skills／命令在两组一致保留，额外用户 skill 只允许目标项。init 可以列出内置 Agent 名称，但不得加载自定义 Agent 或暴露委派工具。每次保存原生 init、工具事件、完成事件和 usage；未完成、模型标识不一致、隔离或原生调用未验证的运行不作为有效提交。`[1m]` 是 CC 的上下文设置后缀，规范化模型标识时去除，同时保留原始名称。CC usage 中普通输入与缓存读写合计为 input_tokens，并保留原始 usage；客户端费用估算不作为真实账单，cost 保留 null。

### 原生 skill 安装与调用

| Agent | 隔离环境中的安装位置 | 提示词首行 | 加载证据 |
| --- | --- | --- | --- |
| Codex | `$HOME/.agents/skills/agent-led-swe/` | `$agent-led-swe` | 发现目录中保留目标；原生 session 的 user input 包含匹配名称、路径和完整冻结正文的 `<skill>` 注入。 |
| Claude Code | `$HOME/.claude/skills/agent-led-swe/` | `/agent-led-swe` | init 识别目标，CLI replay 输出已解析的 `<command-name>/agent-led-swe</command-name>`；真实 CLI + 模拟 API 检查另验证首次请求已包含完整正文。 |

依据：[Codex 原生 skills](https://learn.chatgpt.com/docs/build-skills)、[CC skills](https://code.claude.com/docs/en/skills)。原生命令按原始字符串写入提示词，不经过 shell 展开；CC 再编码为 stream-json 输入，以保留 CLI 的命令解析回放。

安装复制完整 skill 正文和资源，不把独立的 `.claude-plugin` 包装元数据当作用户 skill 插件再次加载。容器将该 payload 只读挂到原生目录；本地 Codex 使用临时 HOME／CODEX_HOME，不修改本机安装。Codex executor 的原生 session 在清理环境前导出用于验证；judge 仍使用 ephemeral 模式。CC 不使用会阻止该安装方式的 bare／disable-slash-commands。

`skill-installation.json` 和 `skill-activation.json` 分别记录安装与原生调用；缺少调用证据不能以“Agent 读过 SKILL.md”替代。原生证据文件的哈希写入 result，评审前检查。baseline 同样需要证据证明没有目标注入。

此前 `Use the skill at …` 的记录属于 **document-reading** 模式，仍保留，但不能作为 native skill 效果验收或与新模式混合比较；新计划显式记录 `skill_loading_mode: native`。

执行结束或超时后先停止容器，再保存完整工作区快照、文件变化清单、原始事件及资源用量。新增文档、未跟踪文件和删除操作都必须保留，不能仅收集代码 patch。Git 内部状态不作为交付产物。

`run_status` 说明执行是否完成，不能代替任务是否满足要求。失败、缺失和超时的运行保留在计划矩阵中，不自动重试或丢弃。

## 3. 独立评价约定

评价只读取冻结后的执行结果，可以反复运行；不驱动 Agent 追加 attempts，也不修改提交产物。

| 检查 | 执行方式 |
| --- | --- |
| 功能和回归 | 复制提交快照，在独立副本中恢复可信测试材料，再运行固定检查。预检和正式评价复用同一个 Docker 测试入口。 |
| 工程、文档与开发过程 | 新的只读 judge 依据共同要求、rubric、原始产物、轨迹和功能证据评审，不修复代码。 |

恢复评分材料不覆盖原始提交记录：Agent 改动过的测试或文档仍保留供评审，但不能通过篡改评分测试取得功能通过。

功能与定性结果分别保存，使用 pass／fail／unknown、原因和证据。功能失败不能被定性通过覆盖；缺少必要评审不能宣称整个任务通过。缺失日志、超时、collection error 或环境问题保留 unknown 并给出诊断依据，不一律归因于 Agent。原测试的 xfail 单独记录，不算新增功能通过。

真实任务执行未完成时，不把起始代码当作已提交成果验收，也不因此判 Agent 功能失败；保留已有产物和错误证据，结果为 unknown。完成执行后，测试项目和结果指纹还应与预检的参考验收对应，缺项不能靠一个成功退出码变为通过。

定性评价检查实际用途，不要求统一文档数量、文件名或固定阶段。必要项来自任务约定，不能在看到结果后增加或放宽。原 benchmark 功能结果与附加工程要求分别报告；共享工程／交付要求构成的改编已记录在 provenance 中。

## 4. 代码职责与入口

| 文件 | 职责 |
| --- | --- |
| `task_adapters.py` | 来源加载、任务准备、补丁语义与验证材料整理。 |
| `agent_adapters/` | 各 Agent 的启动参数、上下文检查和原生事件解析。 |
| `model_config.py`、`configs/` | 独立的模型／Agent 配置、兼容性检查与本地凭据读取。 |
| `evaluation_runtime.py` | 容器构建与生命周期、进程采集及快照。 |
| `run_evaluation.py` | 冻结条件，组织 baseline／skill 的配对执行。 |
| `functional_checks.py` | 在独立副本运行可信检查，输出功能结果。 |
| `evaluate_results.py` | 组织功能验收、独立评审及结果比较。 |
| `preflight_swe.py` | 在正式实验前验证起始／参考状态和运行稳定性，复用准备与检查代码。 |

现有行为任务仍可直接运行。真实任务执行示例：

```sh
uv run --locked python tests/run_evaluation.py pytest \
  --swe-inputs tests/runs/swe-preflight-20261005 \
  --agent codex --model-profile tests/configs/models/codex-gpt-6.1-sol.json \
  --effort high --timeout 300
# CC + DeepSeek：先填写本地凭据，并完成连通检查
uv run --locked python tests/run_evaluation.py pytest \
  --swe-inputs tests/runs/swe-preflight-20261005 \
  --agent claude-code --model-profile tests/configs/models/deepseek-v4.1-flash.json \
  --effort high --timeout 300
uv run --locked python tests/evaluate_results.py '<运行目录>' \
  --model '<judge-model>' --effort high --timeout 180
```

只检查功能时使用 `evaluate_results.py '<运行目录>' --functional-only`，不调用 judge。即使功能全部通过，未完成的定性评审仍是 unknown。原运行目录不被覆盖，重评创建新的目录。

Docker 基础链路可用 `check_swe_pipeline.py --inputs tests/runs/swe-preflight-20261005 --output '<新目录>'` 验证。它使用未修复／参考产物，并模拟替换评分测试与新增文档，不调用模型；其结果不得当作 skill 的收益。

CC 适配可用 `check_claude_worker.py --base-image '<任务依赖镜像 ID>' --output '<新目录>'` 检查：真实容器 CLI 对接本地模拟 API，执行文件读取和 tool-result 回传，分别检查 baseline／skill。该检查不需要密钥，不调用 DeepSeek，也不能证明真实模型表现。

## 5. 隔离候选版本

按仓库 `AGENTS.md`，先固定包含实际修改的基准提交，再从该提交建立候选 worktree。评测器与被测 skill 独立选择：

```sh
# 在候选 worktree 中运行同一套评测器；路径替换为本轮实际位置
uv run --locked python tests/run_evaluation.py pytest \
  --swe-inputs '<冻结的 benchmark 输入目录>' \
  --agent claude-code --model-profile tests/configs/models/deepseek-v4.1-flash.json \
  --credentials '<主工作区本地凭据文件>' \
  --skill-path '<候选 worktree>' --reference-skill-path '<基准工作区>' \
  --output-root '<独立证据目录>' --effort high --timeout 300
```

只传 `--skill-path` 时仍为 baseline／skill 两组；同时传 `--reference-skill-path` 时为 baseline／current／candidate 三组，每组一份新工作区和会话。两种 skill 均冻结完整文件、哈希及源路径／Git 状态。原始文件后续变化不影响已冻结实验；评审拒绝被改动的冻结副本。相同容器路径 `/opt/target-skill` 不暴露新旧版本标签给执行者。

默认首轮按上述顺序，后续 repetition 反序；`--reverse-order` 可反转首轮。顺序记录在 plan 中，不声称单轮已经消除了顺序或服务波动。证据写入全新的输出目录，凭据与原始历史运行不复制进 worktree 或 Git。评测工具和候选内容分开提交，审阅接受前不合并候选。
