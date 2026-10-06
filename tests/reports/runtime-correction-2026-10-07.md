# 配置逐项审查后的修正

基准 `7884e77`。仅修改测试 worktree；正式 skill `1c65c00` 未动。当前执行代码冻结于 `2de1595`，本轮真实模型调用为 0。

## 配置与依据

| 项目 | 当前处理 | 已验证范围 |
| --- | --- | --- |
| DeepSeek 上下文 | 主模型、Opus／Sonnet／Haiku／Fable 别名及子 Agent 默认模型统一声明 `[1m]`；API ID 不变 | 原生 CC 报告 1,000,000；主／子请求均为 deepseek-flash、high、32000 输出上限。未进行真实 1M 输入压力测试。 |
| 资源 | worker 2 CPU／3 GiB；gateway 256 MiB；集中在 configs/runtime.json，任务可声明 worker 需求 | Docker 实际额度、OOM 与 cgroup 峰值保存；当前 CC 模拟场景 Solver 约 154–161 MiB、用户约 126–127 MiB。短场景峰值不能代替长程开发容量测试。 |
| 构建 | Node 22 基础镜像固定 digest，Agent CLI 继续固定版本 | 两种原生 CLI 构建、启动和接续通过。模型别名仍不等于供应商固定版本。 |
| 总时长 | 计时器控制实际容器；到期停止 Solver、用户与网关，等待退出回执 | 真实 Docker 后台写入探针通过；失败会记录停止／导出错误，不能用旧快照判分。 |
| 快照 | 轮间复制时短暂暂停 worker；最终停止后导出 | bind／copy 均保留新增与删除、停止后台写入；copy 保持声明的依赖排除。 |
| 网关 | 64 KiB 分块上传，不把整份请求留在内存；连接建立最多 30 秒，生成阶段不设额外短限时 | 33 MiB 请求通过；客户端断开时，上游等待连接被取消。远端是否已产生计费用量由供应商决定。 |
| 原生子 Agent | 保留默认工具，转发子 Agent 文本，导出 CC projects 和子会话文件 | 真实 CC Task 调用及回传通过；同一进程产生多组正常 init/result 时可继续执行。Codex 本轮只检查普通两轮接续，未新增子 Agent 分支测试。 |
| 用量 | 保存原生 modelUsage；同一 session 累计量转为每轮增量，包含子 Agent | 模拟 API 五次 Solver 请求各 10 输入 tokens，总计 50；两轮记录为 40＋10，无漏计或重复累计。 |
| 项目配置／交互 | 保留项目指导和 hooks；文字问答后 resume | 项目指导、SessionStart hook、用户只读审阅和两轮接续通过。未接通原生 UI 回调，不宣称任意项目配置均已验证。 |

仍保留独立 HOME、原生 skill 安装调用、baseline 隔离、隐藏 verifier、模型专用网络、用户只读角色、总预算与基础设施故障保护。不恢复无依据的回复次数、单轮生成时间、4096 输出或一次结构化修复限制。

## 验证与保留的失败

原始记录均位于 `/Users/liyao/agent-led-swe/tests/runs/`，未覆盖旧结果。

| 记录目录 | 冻结版本／结果 |
| --- | --- |
| runtime-correction-20261007-cc | `e8f1416`：子 Agent 回传成功，但多组 init/result 被旧解析条件误判，两个比较组失败。 |
| runtime-correction-20261007-control | `e8f1416`：首轮停止观测断言未通过，保留完整 capture；之后增加明确退出等待和观测记录。 |
| runtime-correction-20261007-cc-v2 | `cca079b`：两组接续、子 Agent、项目指导及 hook 通过；进一步核查发现用量需要使用累计差值。 |
| runtime-correction-20261007-control-v2 | `cca079b`：bind 通过；copy 探针用 root 访问非 root 工作区而提前报权限错误，未进入超时路径。 |
| runtime-correction-20261007-codex | `cca079b`：baseline／skill 两组通过普通接续与原生调用检查。 |
| runtime-correction-20261007-control-v3 | `2de1595`：按实际 Agent UID 执行，bind／copy 的停止、稳定产物、资源检查均通过。 |
| runtime-correction-20261007-cc-v3 | `2de1595`：两组子 Agent 回传、1M 声明、用量增量、原生调用、用户接续全部通过。 |

本地回归 97 项通过，包含网关大请求／断开取消、子事件与主会话区分、重复结果、用量增量和原有行为回归。模拟 API 检查运行真实容器 CLI，但不证明真实模型会按 skill 完整执行开发流程；下一次真实对照应使用新的运行目录。

## 依据

- [DeepSeek 官方 CC 接入](https://github.com/deepseek-ai/awesome-deepseek-agent/blob/main/docs/claude_code.md)：长上下文声明与模型别名配置。
- [CC headless 文档](https://code.claude.com/docs/en/headless)：原生接续、子 Agent 消息转发；具体兼容性以固定 2.1.278 的帮助输出与原生探针为准。
- [Docker 资源约束](https://docs.docker.com/engine/containers/resource_constraints/)：资源额度属于环境条件，不能视为无意义限制一概删除。
