# cattrs 接入：环境与原生多轮协议验证

本轮已完成任务输入冻结、独立 verifier 和两种 Agent 的原生两轮接续。**尚未接入真实模拟用户模型，也未运行 cattrs 的 baseline／skill 开发对照。** skill 正文与资源保持接受版本 `1c65c00`。范围与顺序见[实施计划](cattrs-integration-plan-2026-10-06.md)。

## 实现与结果

| 部分 | 改动及验证结果 |
| --- | --- |
| 任务准备 | [cattrs_task.py](../cattrs_task.py) 固定起始代码及上游版本；公共源码与私有需求、参考补丁、可信测试分开冻结，以哈希检测变更。 |
| 执行环境 | [Dockerfile](../cases/swe/environments/cattrs/Dockerfile) 使用固定 Python 镜像和哈希锁定依赖；镜像不含 cattrs 源码，运行时离线安装公共工作区。预检核实 import 来自 `/testbed`。本轮只验证 Linux ARM64／Python 3.12。 |
| 功能验收 | 保留原题 `test.sh base/new`，在独立副本恢复可信测试，不要求原五步或特定提交顺序。检查前后的提交产物哈希一致。 |
| 原生多轮 | [collaboration_runtime.py](../collaboration_runtime.py) 传递提问／成果与用户回应；同一容器及显式 session ID 继续，skill 仅第一轮显式调用。不安排开发阶段。 |
| 宿主检查 | [check_collaboration_worker.py](../check_collaboration_worker.py) 使用真实 Codex 0.160.0、CC 2.1.278，后端为本地模拟 API。两种宿主各 baseline／skill 共四组通过两轮检查，确认历史保留和原生 skill 调用／缺席。 |
| 错误与记录 | 记录逐轮消息、执行日志、文件快照和停止原因。单元测试覆盖会话错误切换、服务故障、超时、轮数上限、错误响应、证据改写等情况；不将用户接受当成功能通过。 |

### cattrs 功能预检

| 版本 | 既有测试 | 新增测试 |
| --- | --- | --- |
| 起始代码 | 7 通过 | 收集时无法导入 `PartialResult`，原判据 reward=0 |
| 参考补丁 | 7 通过 | 69 通过，原判据 reward=1 |

起始代码的新增测试属于预期缺失能力导致的收集错误，原始错误保留；一般提交的收集错误仍标为待归因，不统一当作功能断言失败。`base` 只覆盖原题指定的 `test_errors.py`，不是全项目回归，也未完成每条需求与测试的一一覆盖审计。

全部本地工具测试：77 项通过，其中新增 11 项。原生模拟检查证明接入机制可用，不证明真实模型会遵循 skill 或文档质量合格。

## 调整与未完成项

- 第一轮离线安装失败：源码归档没有 Git 版本元数据，hatch-vcs 未识别按包名设置的占位版本。改为镜像内通用 `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0` 后通过；此值只用于测试安装，不修改源码功能。
- 第一轮原生检查在 baseline 成功后，因冻结 skill 目录与 skill 组结果目录重名而中止。改用 `frozen-skill/`，新目录重跑后四组通过。失败材料保留。
- 当前通过普通原生对话轮次提供问答和反馈，不启用 MCP `ask_user`；这已能支持 Agent 提问后收到用户回复。尚未测试执行中异步插入反馈，也未改变现有工具允许列表。
- 模拟用户模型接入、对公共产物的受限只读检查、cattrs 配对入口及全流程预算尚未完成。当前 `responder` 是测试回调接口，其 timeout 需由实际 I/O 实现执行；返回后超时检查不是可中断的用户服务。
- Codex 原生 resume 的 usage 可能是会话累计值；逐轮原始值已保存，尚未实现真实配对总用量核算，不能直接逐轮相加。

## 证据与下一步

原始材料保存在 `/Users/liyao/agent-led-swe/tests/runs/cattrs-integration-20261006/`：`inputs-v2/`、`preflight-v2/qualification.json`、`protocol-cc-v2/report.json`、`protocol-codex-v2/report.json` 和 `unit-tests.log`。真实模型调用为 0。

下一步先完成模拟用户与真实配对入口，并测试需求回答、设计审阅、轮末反馈和服务错误。通过后冻结 solver／用户模型、有限预算与两组条件，再开始真实开发对照。环境预检通过不会自动启用旧的单次请求执行入口。
