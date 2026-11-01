# agent-led-swe

v0.2.0：以 Agent 主导执行、人类把关目标与关键决策的软件工程 skill。围绕用户的语义需求与变更目标组织 process，以 SWE lifecycle 指导每项需求的开发活动；通过 workflow 协调多个相关 process。人机协作、工程基线、文档与决策追溯贯穿其中。根据任务规模裁剪，复用项目已有材料。

## 入口与组织

- [SKILL.md](SKILL.md)：调用范围、关键规则和按需读取入口。
- [Process](references/process.md)：识别与组织单项需求，指导必要的开发活动、反馈与完成判断。
- [Workflow](references/workflow.md)：协调多个 process 的产出依赖、共享约定与整体交付。
- `references/phases/`：process 内部按需使用的开发活动指导，目录名保留，不代表项目只有一个当前阶段。
- [人机协作](references/mechanisms/human-collaboration.md)：阶段性和反馈触发的介入，问题／证据／建议／影响。
- [工程基线](references/mechanisms/engineering-baseline.md)：编码前确定适用约定，持续检查与演进。
- [文档与追溯](references/mechanisms/documentation-and-traceability.md)：模板导航、项目目录、append-only 决策日志和工作单元记录。
- [工程实践](references/practices/catalog.md)：可选择、可裁剪的实践及来源，初版为一个文件。
- `assets/templates/`：输出模板；protocol 在机制文件中，项目事实写入目标项目。

## 首轮重点 review

本轮分批审阅与整体一致性复核已完成，结论见 [验证记录](tests/validation.md)。下表保留为设计导航；当前版本的真实开发效果仍需后续对照测试验证。

| 顺序 | 文件 | 需要检查的设计 |
| --- | --- | --- |
| 1 | [主入口](SKILL.md)、[Process](references/process.md) 与 [Workflow](references/workflow.md) | 需求如何归组、延续或拆分，开发活动如何裁剪，多个 process 如何协调及整体验收。 |
| 2 | [人机协作](references/mechanisms/human-collaboration.md) | 什么交给人类决定，什么由 Agent 自主处理。 |
| 3 | [工程基线](references/mechanisms/engineering-baseline.md) 与 [Catalog](references/practices/catalog.md) | 是否能约束工程偏好，又不会无条件套用规范。 |
| 4 | [文档机制](references/mechanisms/documentation-and-traceability.md) 与 [决策日志模板](assets/templates/decision-log.md) | 当前设计和历史记录的区别，决策主体、时间、版本及替代关系。 |
| 5 | [Design：设计](references/phases/design.md) 与 [交付清单](assets/templates/delivery-checklist.md) | general 方案到实现的细化程度，以及实现前的交付承诺。 |
| 6 | [Verification and Validation：验证与确认](references/phases/verification.md) | 功能、需求／设计、工程质量的检查与未验证项处理。 |

## claudespace 归档与宿主适配

源码仓库为 [LKCY23/agent-led-swe](https://github.com/LKCY23/agent-led-swe)，默认分支保留 `master`。发布基于已接受的 v0.2.0（`1c65c0016a59cce025e31960cc106ea577a80c02`）；后续实验候选独立维护，未接受的候选不随主线发布。

按 [claudespace 的资源规范](https://github.com/LKCY23/claudespace/blob/main/docs/operations.md)，在 `claudespace-personal` catalog 中以 `kind: skill`、`source.kind: external` 和准确 Git commit 登记，更新检查跟踪 `master`。Codex 与 Claude Code 都使用根目录 `SKILL.md`；Claude Code 原生 marketplace 另以相同固定提交提供已有插件入口。登记通过 PR、固定来源检查及合并后基线发布完成，实际采用版本以 claudespace catalog 为准。

资源登记和发布不自动安装：使用方在 Agent Profile 中明确选择并采用基线，再由 claude-config 预览和部署。

采用现有自有 skill 的单源结构：根目录 `SKILL.md` 与 references/templates 共享；`.claude-plugin/plugin.json` 提供 Claude Code 插件入口；`agents/openai.yaml` 提供 Codex UI 元数据。它们不引入后台 agent、hooks 或 MCP。此版本提供 Codex 标准 skill 发现方式，不声称已接入 Codex 原生 marketplace。

可以由用户显式选择后，将完整目录暴露给目标项目的 skill 发现入口；不要仅复制 `SKILL.md`，也不要同时安装多个副本。宿主实际发现的调用名以技能列表为准，可能带插件命名空间。验证脚本只在临时目录做加载检查。

## 验证与限制

测试机制与改造安排见 [测试方案](tests/README.md)和 [统一协议](tests/protocol.md)，覆盖代码、文档、项目管理和人机衔接。pytest／packaging 已接入统一任务、执行和独立验收流程，并通过受控检查；真实仓库的首次模型对照及整体收益评价仍待推进。既有 D1 试跑证据保留，SDK 暂缓，DSPy 尚需稳定运行环境。

在已初始化 Codex／Claude CLI 的日常终端中，进入仓库根目录后运行：

```sh
uv sync --locked
uv run --locked python tests/check_package.py
uv run --locked python tests/check_hosts.py
```

uv 根据 `.python-version`、`pyproject.toml` 和 `uv.lock` 创建本地 `.venv` 并安装锁定的测试依赖。包检查覆盖元数据、本地文件与章节链接、模板可达性；宿主检查在临时项目中验证 Codex 与 Claude Code 的发现，不调用模型或安装全局插件。自动化工具的 shell 初始化方式及行为测试入口见 [测试环境说明](tests/README.md#本地测试环境)。

结构和加载检查不能证明模型遵循规则。用例定义、可运行性与历史验证版本统一见 [场景与状态](tests/scenarios.md)，详细执行证据见 [validation.md](tests/validation.md)。这是一份行为指导 skill，不是操作系统权限控制或不可篡改审计系统。

## 来源与实现选择

基于用户确认的流程与机制独立编写。实践来源在 [catalog](references/practices/catalog.md) 中维护。参考 Matt Pocock Skills 的术语／决策、规格到任务、Standards／Spec 评审思路，未复制其指令正文，也未绑定其术语、固定审批、测试方式或执行器。

README 与 tests 是源码包的开发、审阅和验证材料；Agent 使用时从 SKILL.md 按需读取，不必把整个源码包加载进上下文。
