# 统一任务、执行与评价协议

目标是比较 Agent 在相同开发任务下使用／不使用 skill 的结果。Benchmark 提供任务与验证资源；来源差异在适配时处理，执行和评价共用规则。

```text
行为 case / benchmark 数据
          ↓ task_adapters：准备并冻结任务
统一任务 → run_evaluation：配对执行与采集
          ↓ 不可变产物、轨迹、用量
evaluate_results → 任务 verifier → 成绩与执行状态分别保存
          ↓ 按需读取完整历史
人类／Agent 后续分析 → 观察、证据、归因假设、优化建议
```

## 1. 任务约定

适配器输出一个准备好的任务，包含以下内容：

| 内容 | 用途与可见范围 |
| --- | --- |
| `id`、`request` | 任务身份及双方共同获得的要求。 |
| `workspace` | 起始代码和项目资料；每次执行复制一份。 |
| `environment` | 运行环境；行为任务使用本地工作区，已接入的 SWE 任务使用固定 Docker 镜像。 |
| `validation` | 可信验证材料和检查方式，只交给评测端；行为任务可以不需要功能测试。 |
| `acceptance` | 历史分析依据，保留但不由 LLM 自动判分。共同交付要求已写入 request。 |
| `provenance` | 来源、版本、输入哈希及改编说明，保留追溯依据。 |

FeatureBench 的遮蔽、隐藏测试恢复与其他 benchmark 的正向修复，均由适配器处理。执行器只消费准备好的任务，不解释原始 patch。

参考实现用于预检与测试框架自检，不保存在正式任务的公共工作区中。正式功能评价检查提交产物，不比较 Agent 是否复刻参考代码。

真实任务目前只开放已通过预检的 packaging。SDK 暂缓，DSPy 尚未满足本机稳定性要求。接入其他候选需要相匹配的预检证据，不能只将名字加入 CLI。

## 2. 执行与产物约定

每轮先冻结任务、skill、rubric、模型／预算和运行矩阵。Baseline 与 skill 使用相同的任务、环境、工程要求和权限；只有 skill 组获得目标指导。项目规范仍是双方共同任务输入，不因禁用全局 skills 而被取消。

真实任务在独立 Docker 容器中运行 Codex 或 CC。基础镜像提供项目依赖，Agent 安装层按 `configs/agents.json` 固定 CLI 版本，`--agent-version` 可显式覆盖并记录；不从本机 CLI 推断容器版本。只挂载公共工作区及 skill 组的只读指导，不挂载评分目录、参考实现或 Docker socket。Codex 使用 full-access；CC 以匹配工作区所有者的非 root 用户使用 bypassPermissions。二者均由容器提供边界：移除默认 capabilities，只保留准备 CC 用户目录所需的 CHOWN，启用 no-new-privileges；不授予 NET_ADMIN 或 NET_RAW。

模型 profile 与 Agent 分开选择，运行前验证组合和 effort。Codex 使用现有 auth.json 中的有效访问凭据；CC 从显式环境变量或被 Git 忽略的 `configs/credentials.local.json` 取密钥。真实凭据仅通过权限为 0600 的临时文件只读挂载给外部网关，worker 只获得无权限的占位值。网关按固定上游替换认证头，退出时删除临时文件。凭据不写入镜像、命令参数或证据，不修改宿主登录，也不读取本机 CC／CC Switch 设置。

skill 组安装原生 skill 并显式调用，baseline 不安装。CC 禁用插件、MCP 和委派工具；固定 CLI 自带的 skills／命令在两组一致保留，额外用户 skill 只允许目标项。init 可以列出内置 Agent 名称，但不得加载自定义 Agent 或暴露委派工具。每次保存原生 init、工具事件、完成事件和 usage；未完成、模型标识不一致、隔离或原生调用未验证的运行不作为有效提交。`[1m]` 是 CC 的上下文设置后缀，规范化模型标识时去除，同时保留原始名称。CC usage 中普通输入与缓存读写合计为 input_tokens，并保留原始 usage；客户端费用估算不作为真实账单，cost 保留 null。

### 正式执行的网络边界

每个 worker 独享 Docker internal 网络，只连接同轮的模型网关。网关同时接入外网，按固定 upstream 和 HTTP 路由转发模型请求；拒绝 CONNECT、任意目标、非许可路径和重定向。Worker 无法自行改路由或连接其他 Docker 网络。

Codex 使用独立的 evaluation-gateway provider 发送 Responses SSE，保留请求模型和 effort；认证由网关向原 OpenAI／ChatGPT 服务提交。CC 使用 Anthropic Messages SSE。Codex 的 provider 覆盖放在 exec 子命令后，模拟协议检查复用正式参数。网关不执行登录刷新，失效凭据会使连通检查失败。

镜像构建时准备依赖；挂载当前任务后的 editable 注册也使用离线模式。缺依赖时停止，不在 rollout 中恢复外网。容器内 loopback 模拟服务可以运行。独立 verifier 使用任务声明的测试网络，不能与 Agent 联网权限混为一谈。

启动 Agent 前保存网络探测结果；不通过则不执行。网关日志只记录路由与状态，不记录请求正文或认证头。检查涵盖公网 IP、GitHub、PyPI、宿主端口与非许可网关路径；模拟协议检查和真实模型连通检查分别报告。此机制适用于 Docker 真实任务，本地行为用例不宣称同等网络隔离。

### 原生 skill 安装与调用

| Agent | 隔离环境中的安装位置 | 提示词首行 | 加载证据 |
| --- | --- | --- | --- |
| Codex | `$HOME/.agents/skills/agent-led-swe/` | `$agent-led-swe` | 发现目录中保留目标；原生 session 的 user input 包含匹配名称、路径和完整冻结正文的 `<skill>` 注入。 |
| Claude Code | `$HOME/.claude/skills/agent-led-swe/` | `/agent-led-swe` | init 识别目标，CLI replay 输出已解析的 `<command-name>/agent-led-swe</command-name>`；真实 CLI + 模拟 API 检查另验证首次请求已包含完整正文。 |

依据：[Codex 原生 skills](https://learn.chatgpt.com/docs/build-skills)、[CC skills](https://code.claude.com/docs/en/skills)。原生命令按原始字符串写入提示词，不经过 shell 展开；CC 再编码为 stream-json 输入，以保留 CLI 的命令解析回放。

安装复制完整 skill 正文和资源，不把独立的 `.claude-plugin` 包装元数据当作用户 skill 插件再次加载。容器将该 payload 只读挂到原生目录；本地 Codex 使用临时 HOME／CODEX_HOME，不修改本机安装。Codex executor 的原生 session 在清理环境前导出用于验证。CC 不使用会阻止该安装方式的 bare／disable-slash-commands。

`skill-installation.json` 和 `skill-activation.json` 分别记录安装与原生调用；缺少调用证据不能以“Agent 读过 SKILL.md”替代。原生证据文件的哈希写入 result，评审前检查。baseline 同样需要证据证明没有目标注入。

此前 `Use the skill at …` 的记录属于 **document-reading** 模式，仍保留，但不能作为 native skill 效果验收或与新模式混合比较；新计划显式记录 `skill_loading_mode: native`。

执行结束或超时后先停止容器，再保存完整工作区快照、文件变化清单、原始事件及资源用量。新增文档、未跟踪文件和删除操作都必须保留，不能仅收集代码 patch。Git 内部状态不作为交付产物。

`run_status` 说明执行是否完成，不能代替任务是否满足要求。失败、缺失和超时的运行保留在计划矩阵中，不自动重试或丢弃。

## 3. 独立评价约定

评价只读取冻结后的执行结果，可以反复运行；不驱动 Agent 追加 attempts，也不修改提交产物。

| 检查 | 执行方式 |
| --- | --- |
| 功能和回归 | 复制提交快照，在独立副本中恢复可信测试材料，再运行固定检查。预检和正式评价复用同一个 Docker 测试入口。 |
| 工程、文档与开发过程 | 测试后按需分析完整历史，记录观察、证据和归因；不自动判分。 |

恢复评分材料不覆盖原始提交记录：Agent 改动过的测试或文档仍保留供评审，但不能通过篡改评分测试取得功能通过。

任务结果只来自冻结的 verifier，保留 pass／fail／unknown、原始计数、日志和证据；没有配置 verifier 时为 unknown，不能用 LLM 补上。执行状态与 comparison_validity 单独保存，原生调用失败会使实验无效，但不能替 verifier 把正确代码判为失败。缺失日志、超时、collection error 或环境问题保留 unknown 并提供诊断依据；原测试 xfail 单列。

真实任务执行未完成时，不把起始代码当作已提交成果验收，也不因此判 Agent 功能失败；保留已有产物和错误证据，结果为 unknown。完成执行后，测试项目和结果指纹还应与预检的参考验收对应，缺项不能靠一个成功退出码变为通过。

后续分析不要求统一文档数量、文件名或固定阶段，不改变任务分数。原 benchmark 功能结果与过程观察分别报告；共享工程／交付要求的改编保留在 provenance 中。详见 [分析指导](analysis.md)。历史 judge 判分不覆盖，新版验证始终创建新目录。

## 4. 代码职责与入口

| 文件 | 职责 |
| --- | --- |
| `task_adapters.py` | 来源加载、任务准备、补丁语义与验证材料整理。 |
| `agent_adapters/` | 各 Agent 的启动参数、上下文检查和原生事件解析。 |
| `model_config.py`、`configs/` | 独立的模型／Agent 配置、兼容性检查与本地凭据读取。 |
| `evaluation_runtime.py` | 容器构建与生命周期、进程采集及快照。 |
| `worker_network.py`、`model_gateway.py` | 独立内部网络、固定模型转发、网络探测与清理。 |
| `run_evaluation.py` | 冻结条件，组织 baseline／skill 的配对执行。 |
| `functional_checks.py` | 在独立副本运行可信检查，输出功能结果。 |
| `evaluate_results.py` | 校验历史证据，调用任务 verifier，分别汇总任务结果与实验有效性；不调用模型。 |
| `packaging_environment.py` | 构建精简执行镜像，清理并审计本地实现副本；验收镜像独立保留。 |
| `preflight_swe.py` | 在正式实验前验证起始／参考状态和运行稳定性，复用准备与检查代码。 |

现有行为任务仍可直接运行。真实任务执行示例：

```sh
uv run --locked python tests/run_evaluation.py packaging \
  --swe-inputs tests/runs/swe-preflight-20261005 \
  --agent codex --model-profile tests/configs/models/codex-gpt-6.1-sol.json \
  --effort high --timeout 300
# CC + DeepSeek：先填写本地凭据，并完成连通检查
uv run --locked python tests/run_evaluation.py packaging \
  --swe-inputs tests/runs/swe-preflight-20261005 \
  --agent claude-code --model-profile tests/configs/models/deepseek-v4.1-flash.json \
  --effort high --timeout 300
uv run --locked python tests/evaluate_results.py '<运行目录>'
```

评价默认仅使用 verifier，不需要模型参数。旧 `--functional-only` 保留为兼容参数，含义相同。没有后续分析不会使已通过的 verifier 结果变成 unknown。原运行目录不覆盖，重评创建新目录。

Docker 基础链路可用 `check_swe_pipeline.py --inputs tests/runs/swe-preflight-20261005 --output '<新目录>'` 验证。它使用未修复／参考产物，并模拟替换评分测试与新增文档，不调用模型；其结果不得当作 skill 的收益。

CC 适配可用 `check_claude_worker.py --base-image '<任务依赖镜像 ID>' --output '<新目录>'` 检查：真实容器 CLI 对接本地模拟 API，执行文件读取和 tool-result 回传，分别检查 baseline／skill。该检查不需要密钥，不调用 DeepSeek，也不能证明真实模型表现。

### packaging 执行环境

`environment.image` 仍是独立 verifier 镜像；`execution_image` 是清理后的 Agent 基础镜像。精简镜像移除其他 packaging 安装／vendored 目录、wheel 和 uv／pip 缓存，使用 uv 与 flit_core，不再提供依赖已被移除副本的全局 pip／setuptools。

任务准备要求匹配的数据版本与执行环境资格记录。启动 worker 并安装任务后，再扫描运行目录并确认 Python 导入来自 `/testbed`；不满足则不启动 Agent。执行后复查并保存记录，新出现的副本使实验有效性为 invalid，verifier 成绩仍独立。

检查覆盖本轮发现的本地可读实现来源，不是完整网络安全边界。本地来源检查与上述网络边界互补；不声称能防御所有恶意沙箱逃逸。任何新的来源暴露都应保留证据并重新审查任务资格，不能通过提示词或补分掩盖。

可用以下命令重建并完成资格检查（不调用模型）：

```sh
uv run --locked python tests/packaging_environment.py \
  --base-image '<原 verifier 镜像 ID>' --inputs '<冻结任务输入目录>' \
  --output '<新预检目录>'
```

只有生成报告的 qualified 为 true 时，才将它登记为 `tests/reports/packaging-execution-environment-2026-10-06.json`；任务准备会核对数据版本与 verifier 镜像。Agent 安装层只复制对应 Agent 的 npm namespace，避免把 npm/node-gyp 的 Python 实现再次带入环境。

## 5. 隔离候选版本

按仓库 `AGENTS.md`，先固定包含实际修改的基准提交，再从该提交建立候选 worktree。评测器与被测 skill 独立选择：

```sh
# 在候选 worktree 中运行同一套评测器；路径替换为本轮实际位置
uv run --locked python tests/run_evaluation.py packaging \
  --swe-inputs '<冻结的 benchmark 输入目录>' \
  --agent claude-code --model-profile tests/configs/models/deepseek-v4.1-flash.json \
  --credentials '<主工作区本地凭据文件>' \
  --skill-path '<候选 worktree>' --reference-skill-path '<基准工作区>' \
  --output-root '<独立证据目录>' --effort high --timeout 300
```

只传 `--skill-path` 时仍为 baseline／skill 两组；同时传 `--reference-skill-path` 时为 baseline／current／candidate 三组，每组一份新工作区和会话。两种 skill 均冻结完整文件、哈希及源路径／Git 状态。原始文件后续变化不影响已冻结实验；评审拒绝被改动的冻结副本。各 Agent 相同的原生安装路径 不暴露新旧版本标签给执行者。

默认首轮按上述顺序，后续 repetition 反序；`--reverse-order` 可反转首轮。顺序记录在 plan 中，不声称单轮已经消除了顺序或服务波动。证据写入全新的输出目录，凭据与原始历史运行不复制进 worktree 或 Git。评测工具和候选内容分开提交，审阅接受前不合并候选。
