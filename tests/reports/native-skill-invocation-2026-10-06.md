# 原生 skill 安装与调用修复

状态：Codex 和 Claude Code 均已支持原生安装与主动调用，使用当前基准 skill 验证；本次只修评测接入，没有继续修改 skill 指导，也没有重跑 benchmark。改动位于 `fix/native-skill-invocation-20261006` 分支，主工作区保持基准。

## 安装和调用

| Agent | 安装位置 | 提示词开头 | 实际加载证据 |
| --- | --- | --- | --- |
| Codex 0.160.0 | 隔离 HOME 下 `.agents/skills/agent-led-swe/` | `$agent-led-swe` 后接任务正文 | 原生 session 中的 user input 包含 `<skill>`、名称、安装路径及完整冻结正文。 |
| CC 2.1.278 | 容器 HOME 下 `.claude/skills/agent-led-swe/` | `/agent-led-swe` 后接任务正文 | init 发现目标；CLI replay 输出解析后的 command-name；模拟 API 确认首个请求包含完整 skill 正文。 |

路径与调用依据：[Codex skills](https://learn.chatgpt.com/docs/build-skills)、[Claude Code skills](https://code.claude.com/docs/en/skills)。Codex 字面量 `$` 通过文件传入，不经 shell 展开；CC 将同一提示词编码成 stream-json，以获得原生命令回放。

只安装 skill 正文与资源，不将 `.claude-plugin` 包装再加载为插件。Docker 安装是只读原生目录挂载；本地 Codex 使用临时 HOME／CODEX_HOME及临时认证副本，清理时删除，不修改本机配置。Codex executor 保留原生 session 供验证，judge 继续 ephemeral。

CC 移除了阻止目标发现的 bare／disable-slash-commands。新 HOME 只安装目标用户 skill；固定 CLI 自带的 skills／命令在两组相同保留，拒绝其他自定义 skills、插件、MCP 和委派工具。baseline 不安装目标且没有主动调用前缀，不能通过“关闭所有 skills”构造与目标组不同的 CLI 模式。

## 验证

- 47 项本地测试通过，包括安装但未调用、只有普通读取、注入正文不匹配、baseline 意外加载目标等拒绝路径，以及配对／三组执行和独立评审回归。
- 使用真实 CLI + 本地模拟 API，分别验证 Codex 本地、Codex Docker、CC Docker。每种均包含 baseline／skill：目标组的首个模型请求已含完整 skill 正文，baseline 没有。不是由 mock 要求模型去 Read SKILL.md 再冒充原生调用。
- 两次真实模型冒烟：Codex/gpt-6.1-sol/high 与 CC/DeepSeek Flash/high，各 120 秒上限。原生激活均确认，最终回答均与读取的随机标记一致，工作区不变；耗时分别约 12.13／2.35 秒。
- Codex 冒烟最初的文本检查把中间 commentary 和最终消息拼接，标记为 failed。原始结果保留；`author-review.json` 确认最后一条回复匹配标记，且原生激活检查从始至终通过。没有为此追加模型调用或覆盖失败记录。

每次正式执行保存 `skill-installation.json`、`skill-activation.json` 和相关原生证据哈希；加载无法确认时拒绝将完成状态作为有效 skill trial。Codex 比较注入正文与冻结源，CC 检查发现及原生命令回放；模型自述或普通文件读取不能代替这些证据。

## 证据位置

以下均在主工作区被 Git 忽略的 `tests/runs/` 中：

- `native-codex-local-20261006-v2/report.json`：本地隔离 HOME 与完整正文注入。
- `native-codex-docker-20261006/report.json`：容器安装及原生 session 导出。
- `native-cc-real-skill-20261006/report.json`：使用完整基准 skill 的 CC 命令解析和首次请求检查。
- `native-live-20261006/`：两次真实模型运行；Codex 的人工核对为 `codex/author-review.json`。

早期探测也保留：CC 在 bare 模式下提示命令不可用，去掉 bare 后原生展开成功；Codex 首个检查脚本的冻结目录与 trial 目录重名，修复后换新输出目录执行。均为接入检查，不用于效果比较。

## 旧结果与后续

此前 D1 和早期候选比较采用路径提示加普通 Read／Bash 的 **document-reading** 模式。保留的记录不能作为 native skill 的效果验收，也不能与新模式混合汇总。候选内容的效果仍待原生模式重新验证。

接入修复不自动解决 packaging 的替代实现暴露或 judge 一致性问题。先保持这些限制可见；后续原生对照另建冻结计划和新证据目录，不能覆盖旧结果或直接接受上一轮候选。
