# Agent 与模型接入验证

状态：Codex／Claude Code adapter 及独立模型配置已实现。真实 DeepSeek 服务与 CC 容器连通检查已通过；后续的 [pytest 首轮真实配对](pytest-pilot-2026-10-05.md)亦已完成。本报告记录接入验证，任务结果单独报告。

## 本次改动

- 原有 Codex 启动与上下文检查移入 `agent_adapters/codex.py`；CC 增加独立的启动、隔离核查及 stream-json 解析。公共 runtime 负责容器、采集与快照，任务适配和功能评分共用。
- 容器 CLI 版本由 `configs/agents.json` 决定，不依赖本机安装：Codex 0.160.0、CC 2.1.278。构建缓存依据完整 Dockerfile 哈希，实际镜像 ID 写入运行记录。
- 模型 profile 保存模型、provider、协议和凭据引用。首批支持原生 Codex／OpenAI，以及 CC／DeepSeek Flash；不接受尚未实现的交叉组合或隐式 effort 映射。
- `configs/credentials.local.json` 由用户本地填写、被 Git 忽略。CC 凭据只在运行时注入容器，不读取本机 CC Switch，不持久化到镜像或证据。
- 独立 judge 仍为 Codex；没有因为切换 executor 同时更换评价模型。

## 实际检查与证据

| 检查 | 结果与范围 |
| --- | --- |
| CC 容器 + 模拟 API | baseline／skill 各两次本地 HTTP 请求，真实执行 Read 并回传文件内容，完成事件及 usage 可解析；没有真实模型推理。 |
| 隔离与模型参数 | 没有加载 skills／plugins／MCP／自定义 Agent，没有委派工具；仅 skill 组读取目标指导。API 请求模型为 `deepseek-flash`，CC 的 `[1m]` 后缀设置了 1M context window。 |
| Codex 容器回归 | 提取 adapter 后，原生无模型 context 检查仍通过；没有加载额外指导。 |
| 本地回归 | 42 项测试通过；合成事件覆盖完成／失败、错误模型、缺失凭据、隔离异常、缓存统计；模拟配对执行继续由原有 Codex judge 接口消费。包检查及 diff 格式检查通过。 |

CC 通过记录：`tests/runs/claude-worker-check-20261005-v4/report.json`。镜像 ID：`sha256:9c7b6710ab14509bed128b17d42eca402a3573b831175e4ce1ff80336f6713ce`。Codex 回归：`tests/runs/codex-adapter-regression-20261005/report.json`。

早期失败保存在 `claude-worker-check-20261005`、`-v2`、`-v3`：固定版本的 CC npm 包入口为 `bin/claude.exe`，不能沿用旧版 `cli.js`；init 会报告内置 Agent 名称，但没有委派工具；usage 使用带 `[1m]` 的客户端名称。修复适配后重新验证，没有删除失败记录。

## 尚未证明的内容

模拟 API 检查只能证明 CLI／工具／采集链路。下述真实检查补充了当前 DeepSeek endpoint 的最小兼容性证据，但不能证明 SWE 推理表现或 skill 效果。CC 客户端对非 Claude 模型输出的费用属于估算，正式结果的 cost 保留 null。真实 endpoint 返回模型名也不能证明固定权重版本。

后续使用固定任务、同一 CC／DeepSeek 配置和有限超时开展 baseline／skill 配对。CC 暂只支持 Docker SWE 任务；本地行为 case 和独立 judge 沿用 Codex。

## 真实服务连通验证

2026-10-05，用户填入凭据后执行：

| 检查 | 结果 |
| --- | --- |
| 官方 Anthropic Messages endpoint | 两次请求完成 tool_use → tool_result → end_turn，均返回 `deepseek-flash`；非 thinking 模式，耗时 1.606 秒。 |
| CC 2.1.278 容器 + DeepSeek Flash/high | 一次 Agent 运行，120 秒上限，实际耗时 2.318 秒。真实 Read 读取随机标记文件，准确返回标记；无其他工具调用、无文件修改，隔离及模型标识检查通过。 |
| CC 原生 usage | 规范化 input_tokens 2680（含 cached_input_tokens 1152），output_tokens 70。cost 保留 null。 |

原始证据：`tests/runs/model-connection-20261005T150637947223Z/receipt.json` 与 `tests/runs/claude-live-connection-20261005T150752219611Z/result.json`。后者保留执行计划、原生事件、工具结果、文件快照和 adapter 哈希；容器已清理。该检查没有加载目标 skill，也不是 benchmark 对照实验。
