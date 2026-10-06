# 网络限制与任务清理：本轮结果

本轮只修改测试系统。工作分支为 `fix/network-and-task-scope-20261006`，基于 `aa6d267`；主工作区及 skill 正文未修改、未合并。没有启动新的 benchmark 效果对照。

## 已完成

1. **Docker worker 只能连接模型网关。** 每次运行创建独立 internal 网络。网关只转发固定上游的指定模型接口，拒绝 CONNECT、任意目标、非许可路径及重定向。Worker 移除默认 capabilities，仅保留准备目录所需 CHOWN，并启用 no-new-privileges。安装当前任务时也使用离线模式。
2. **真实凭据留在网关。** Codex 从现有认证读取访问凭据，CC 从指定文件／环境变量读取密钥；只向独立网关挂载临时认证文件，worker 获得占位值。网关转发到原模型服务，退出后清理凭据，不刷新或改写宿主登录。
3. **网络证据纳入实验有效性检查。** 保存网络策略、实际探测和网关路由状态，冻结其哈希。缺少新版网络边界的历史 Docker 对照标记 unknown，新运行缺少网络核查则 invalid；这些状态不改变 verifier 的功能成绩。
4. **移除 pytest benchmark。** 删除任务定义、专属报告、运行轨迹、产物及验证历史，清理混合报告与引用。共删除 13 个明确定位的路径、26,331 个文件，约 247 MB；未清理其他任务、通用原生接入记录或 pytest 测试工具，也未进行全局 Docker prune 或 Git 历史重写。
5. **重新整理任务用途。** packaging 保留为实现完整性候选；DSPy 待环境稳定性处理与审阅；SDK 继续暂缓。具体理由见 [候选审阅](task-selection-2026-10-06.md)。

## 验证

| 检查 | 结果 |
| --- | --- |
| 本地回归 | 53 项通过，包含网关路由限制、认证头替换、流式转发、拒绝重定向、Codex 参数位置和网络有效性与成绩分离。 |
| 实际网络边界 | 两种 worker 均阻止公网 IP、GitHub、PyPI、宿主 80／443 端口及非许可网关路径；确认只加入一个 internal 网络且不具备网络管理／原始套接字 capabilities。 |
| 原生协议 | 实际 Codex／CC CLI 的 baseline 与 skill 检查通过；模拟 API 确认首次请求包含完整原生 skill，baseline 无目标注入。 |
| 真实 Codex | gpt-6.1-sol/high 完成，14.75 秒；原生加载已确认，实际读取并准确返回随机 marker，工作区未改动。 |
| 真实 CC | DeepSeek Flash/high 完成，2.94 秒；原生加载已确认，实际读取并返回 marker，工作区未改动。该次输出核查另存记录，没有修改原 result。 |
| packaging 实际 worker | 两种 CLI 的离线任务注册、本地来源审计、网络审计与 pytest 启动均通过。 |
| packaging 独立 verifier | 未实现产物的目标测试失败、回归通过；参考产物目标与回归均通过。伪造测试不能覆盖可信测试，提交快照保持不变。 |
| 文件与凭据 | 包检查通过；测试文档本地链接无缺失；diff 格式检查通过；新证据未包含现有真实密钥或令牌。 |

这里的真实模型调用仅检查连接、原生 skill 和文件读取，不代表开发效果。

## 调试发现与保留范围

Codex 0.160.0 不允许覆盖内置 provider；并且 `exec` 的配置覆盖需要放在子命令后。最初的模拟检查自行追加 provider，未暴露正式参数位置问题。现在模拟检查复用正式 Docker 参数，另有回归测试约束参数位置。

最终使用独立的 `evaluation-gateway` provider，通过 Responses SSE 发送原模型与 effort；上游认证由网关提供，避免 worker 自行发现外部服务地址。配置依据参见 [OpenAI 配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)，固定版本的实际行为以本轮 CLI 证据为准。

另外修复了 Docker inspect 将 CHOWN 表示为 CAP_CHOWN 导致的审计误报，以及通用验收自检错误地从 worktree 推导外部预检输入位置的问题。所有本轮失败检查保留在新证据目录，没有用通过结果覆盖；pytest 的清理是用户明确决定退出该任务后的独立清理。

## 证据与下一步

证据根目录：`/Users/liyao/agent-led-swe/tests/runs/network-repair-20261006/`。

- `codex-runtime-protocol/`、`claude-runtime-protocol/`：最终原生协议检查。
- `live-codex-v6/`、`live-claude-code-v3/`、`live-output-check.json`：真实模型连接与输出核查。
- `packaging-workers/`：实际任务的离线准备、来源及网络审计。
- `packaging-verifier-v2/`：独立验收链路复查。
- 其他带版本的目录：排查期间的失败或早期检查，不作为效果样本。

后续先审阅候选任务，再固定任务、模型和合理预算开展当前 skill 对照。DSPy 的回归波动及资源供给尚未解决；本轮没有修改其测试或宣称预检通过。模块／接口设计、人类决策及多 process 协调仍需适合的任务覆盖。

网络机制用于 Docker 真实任务；本地行为用例不具备相同边界。网关不处理令牌刷新或模型服务不可用；检查失败时停止，不恢复 worker 通用联网。当前验证针对代码／软件包获取渠道，不宣称能防御任意恶意沙箱逃逸。
