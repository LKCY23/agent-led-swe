# agent-led-swe

v0.1.0：以 Agent 主导执行、人类把关目标与关键决策的软件工程 skill。六项开发活动由人机协作、工程基线、文档与决策追溯三项机制贯穿。根据任务规模裁剪，复用项目已有材料。

## 入口与组织

- [SKILL.md](SKILL.md)：调用范围、关键规则和按需读取入口。
- [Workflow](references/workflow.md)：阶段识别、推进与反馈。
- [人机协作](references/mechanisms/human-collaboration.md)：阶段性和反馈触发的介入，问题／证据／建议／影响。
- [工程基线](references/mechanisms/engineering-baseline.md)：编码前确定适用约定，持续检查与演进。
- [文档与追溯](references/mechanisms/documentation-and-traceability.md)：模板导航、项目目录、append-only 决策日志和工作单元记录。
- [工程实践](references/practices/catalog.md)：可选择、可裁剪的实践及来源，初版为一个文件。
- `assets/templates/`：输出模板；protocol 在机制文件中，项目事实写入目标项目。

## 首轮重点 review

| 顺序 | 文件 | 需要检查的设计 |
| --- | --- | --- |
| 1 | [主入口](SKILL.md) 与 [Workflow](references/workflow.md) | 讨论／实施授权边界，既有材料复用，小任务是否足够轻量。 |
| 2 | [人机协作](references/mechanisms/human-collaboration.md) | 什么交给人类决定，什么由 Agent 自主处理。 |
| 3 | [工程基线](references/mechanisms/engineering-baseline.md) 与 [Catalog](references/practices/catalog.md) | 是否能约束工程偏好，又不会无条件套用规范。 |
| 4 | [文档机制](references/mechanisms/documentation-and-traceability.md) 与 [决策日志模板](assets/templates/decision-log.md) | 当前设计和历史记录的区别，决策主体、时间、版本及替代关系。 |
| 5 | [设计阶段](references/phases/design.md) 与 [交付清单](assets/templates/delivery-checklist.md) | general 方案到实现的细化程度，以及实现前的交付承诺。 |
| 6 | [验证阶段](references/phases/verification.md) | 功能、需求／设计、工程质量的检查与未验证项处理。 |

## claudespace 归档与宿主适配

按照 claudespace 自有插件模式，维护独立 Git 源码仓库，未来发布后以固定 commit 的 submodule 接入其主目录。当前是本地待审阅版本；尚未发布远程、注册 marketplace、选择安装或修改 claude-config-data。不会写入一个不存在的远程 URL 或不可移植的本地 submodule URL。

采用现有自有 skill 的单源结构：根目录 `SKILL.md` 与 references/templates 共享；`.claude-plugin/plugin.json` 提供 Claude Code 插件入口；`agents/openai.yaml` 提供 Codex UI 元数据。它们不引入后台 agent、hooks 或 MCP。此版本提供 Codex 标准 skill 发现方式，不声称已接入 Codex 原生 marketplace。

可以由用户显式选择后，将完整目录暴露给目标项目的 skill 发现入口；不要仅复制 `SKILL.md`，也不要同时安装多个副本。宿主实际发现的调用名以技能列表为准，可能带插件命名空间。验证脚本只在临时目录做加载检查。

## 验证与限制

运行 `python3 tests/check_package.py` 检查包结构、元数据、链接与模板可达性。`python3 tests/check_hosts.py` 在临时项目中检查本机 Codex 与 Claude Code 的实际发现，不调用模型或安装全局插件。

结构和加载检查不能证明模型遵循规则。代表性行为用例见 [scenarios.md](tests/scenarios.md)，实际范围和结果见 [validation.md](tests/validation.md)。这是一份行为指导 skill，不是操作系统权限控制或不可篡改审计系统。

## 来源与实现选择

基于用户确认的流程与机制独立编写。实践来源在 [catalog](references/practices/catalog.md) 中维护。参考 Matt Pocock Skills 的术语／决策、规格到任务、Standards／Spec 评审思路，未复制其指令正文，也未绑定其术语、固定审批、测试方式或执行器。

README 与 tests 是源码包的开发、审阅和验证材料；Agent 使用时从 SKILL.md 按需读取，不必把整个源码包加载进上下文。
