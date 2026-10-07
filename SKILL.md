---
name: agent-led-swe
description: 围绕用户需求和变更目标，指导 Agent 主导的软件开发，从澄清需求、设计到经过验证的交付。结合人类决策、项目工程约定和可追溯记录，协调相关工作。适用于需要这类协调的软件开发或变更任务，也可显式调用；根据任务规模裁剪。
---

# Agent-Led SWE

## 1. 目标与组织方式

主导开发工作，由人类把关目标、工程偏好和重要决策。使产出符合约定意图，并且便于审阅、验证和维护。

使用用户的语言，沿用项目术语。

| 概念 | 含义 |
| --- | --- |
| **Process** | 围绕一项完整需求或变更目标组织的开发工作。 |
| **Lifecycle** | 软件开发、交付与持续维护的整体过程，为开发活动的组织和相关工程问题的考虑提供依据。 |
| **Workflow** | 协调相关 process、它们的依赖、共享约定和整体交付。 |

一项需求或变更目标通过一个 process 推进。Process 参照软件 lifecycle 组织必要的开发活动，并考虑当前工作对后续集成、交付和维护的影响。当多个 process 存在依赖或共同交付要求时，通过 workflow 协调它们的工作安排、共享约定和整体结果。各 process 可以开展不同的开发活动，不要求处于统一的 lifecycle 阶段。

## 2. 从请求与项目状态进入

1. **明确请求。** 明确预期结果，以及用户希望开展讨论、设计、实现、审阅还是交付。
2. **检查已有依据。** 阅读适用的项目说明、相关需求与设计、决策、工作记录、代码和证据。
3. **确定工作归属。** 读取 [Process 指导](references/process.md)，确定继续、调整还是组织新的 process，并据此安排活动、工作深度和依赖。相关 process 需要协调时，使用 [Workflow 指导](references/workflow.md)。
4. **确定记录与下一步。** 安排项目记录时，读取 [文档机制](references/mechanisms/documentation-and-traceability.md)，确定已有记录如何复用、缺少的信息由哪里承载。保存或更新工作安排，向用户简述当前推进的部分。

遵循用户当前要求的范围和已有授权。讨论或接受设计本身不代表授权实现。当实现已获授权、所需依据已明确时，直接推进，不重复请求笼统确认。保留与本次工作无关的用户修改。

## 3. 推进工作

### 选择活动并开展工作

开展选定活动前，读取第 5 节对应的指导，核对所需产出与推进依据。已读取且仍适用的指导直接沿用。

实现前，依据 Design 指导、适用的工程基线和交付标准，检查是否具备实现条件。先解决影响当前变更的缺口，再开展相关实现。

### 处理依赖与反馈

推进前置条件已经具备的工作。依赖应明确某项活动需要什么产出，不默认要求上游整个 process 完成后才能继续。

根据反馈，重新处理受影响的工作：

- 依据约定需求修复实现缺陷。
- 调查不确定的事实。
- 设计假设或机制失效时，重新审视设计。
- 目标或重要承诺需要决策时，使用人机协作机制。
- 共享产出发生变化时，按 Workflow 指导检查受影响的使用方和证据。

仅阻塞依赖未决问题的工作。更新受影响的约定、计划和记录，保留仍然有效的成果与证据。

### 验证完成情况

按照 Verification and Validation 指导，检查行为、需求覆盖、工程约定的遵守情况及预期结果。按照 Delivery and Maintenance 指导，对照交付承诺核对实际产物与证据。

区分已满足、部分满足、未满足和未验证的承诺。接受某项限制，不代表尚未执行的检查已经通过。

对于 workflow，除各 process 的局部结果外，还应验证整体结果与集成证据。局部成功本身不能证明整体完成。

## 4. 执行贯穿机制

| 机制 | 何时以及如何使用 |
| --- | --- |
| [Human Collaboration｜人机协作](references/mechanisms/human-collaboration.md) | 需要明确人类意图、偏好或作出重要决定时，提供问题、证据、建议和影响。沿用已确定的决定与已授予的自主裁量范围。在必要决定作出前，暂停依赖该决定的工作，继续已有授权内的独立工作；不将提案或沉默视为同意。 |
| [Engineering Baseline｜工程基线](references/mechanisms/engineering-baseline.md) | 实现前，明确或复用适用的工程约定与人类偏好。在实现和审阅过程中检查遵守情况。需要改变约定时，遵循该机制。 |
| [Documentation and Traceability｜文档与追溯](references/mechanisms/documentation-and-traceability.md) | 在项目文件中维护约定、进展、决策和证据。共享定义保留一份权威版本，区分决策、实现和验证状态，并保留重要决策的历史。 |

选择或裁剪工程约定时，使用 [工程实践目录](references/practices/catalog.md)。根据项目需要采用实践，不强行套用统一架构或工作流程。

## 5. 指导与模板导航

表中链接分别提供活动指导和参考模板。推进工作时读取项目实际记录；组织新记录时可参考模板，沿用项目已有位置与格式。

| 工作 | 指导 | 模板 |
| --- | --- | --- |
| 组织一项需求 | [Process](references/process.md) | [Process 计划](assets/templates/process-plan.md) |
| 协调相关需求 | [Workflow](references/workflow.md) | [Workflow 计划](assets/templates/workflow-plan.md) |
| 界定问题与定义需求 | [Problem Framing｜问题界定](references/phases/problem-framing.md)、[Requirements Analysis｜需求分析](references/phases/requirements.md) | [需求文档](assets/templates/requirements.md) |
| 设计方案 | [Design｜设计](references/phases/design.md) | [整体设计文档](assets/templates/architecture.md)、[模块设计文档](assets/templates/module-design.md)、[接口文档](assets/templates/interface-contract.md) |
| 实现与集成 | [Implementation and Integration｜实现与集成](references/phases/implementation.md) | 更新 Process 计划及相关设计记录 |
| 验证行为与预期结果 | [Verification and Validation｜验证与确认](references/phases/verification.md) | [验证记录](assets/templates/verification-record.md) |
| 交付或维护成果 | [Delivery and Maintenance｜交付与维护](references/phases/delivery-and-maintenance.md) | [交付清单](assets/templates/delivery-checklist.md) |
| 确定工程约定 | Engineering Baseline 机制 | [工程基线](assets/templates/engineering-baseline.md) |
| 支撑并记录决策 | Human Collaboration 与 Documentation 机制 | [决策日志](assets/templates/decision-log.md)、[决策分析](assets/templates/decision-detail.md) |
| 维护导航与术语 | Documentation 机制 | [项目索引](assets/templates/project-index.md)、[术语表](assets/templates/glossary.md) |

将项目专属产出保存在目标项目中。发布、部署、对外沟通及修改其他环境，需要具有覆盖这些操作的授权。
