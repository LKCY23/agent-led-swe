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
3. **确定工作归属。** 根据 [Process 指导](references/process.md)，继续已有工作、调整其目标，或组织新的 process。相关 process 需要协调时，使用 [Workflow 指导](references/workflow.md)。
4. **确定下一步。** 复用已有的充分成果，识别剩余问题、所需活动和依赖。简要说明下一步行动，或更新已有工作记录。

遵循用户当前要求的范围和已有授权。讨论或接受设计本身不代表授权实现。当实现已获授权、所需依据已明确时，直接推进，不重复请求笼统确认。保留与本次工作无关的用户修改。

## 3. 推进工作

### 选择活动并开展工作

根据当前目标与项目状态，选择必要的开发活动。通过第 5 节查阅相应指导，明确所需产出并开展工作。

实现前，依据 Design 指导、适用的工程基线和交付标准，检查是否具备实现条件。先解决影响当前变更的缺口，再开展相关实现。

已有文档能够满足需要时，直接复用。根据文档机制创建或更新记录；小型变更不需要完整的文档目录。

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

阅读当前工作所需的指导。模板用于帮助编写必要的项目文档，不是必须逐一创建的文件清单。

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

---

<!-- Inline source: references/process.md -->

# Process｜单项需求的开发组织

围绕一项需求或变更目标，结合软件现状与 lifecycle 组织开发工作。本文负责需求归组、工作安排、调整与完成判断；具体活动要求由各活动指导说明。

## Identify the work

收到新需求或对已有工作的补充时，先对照现有目标、约定和实际成果，确定本次输入属于哪项工作。

| 输入情况 | 处理方式 |
| --- | --- |
| 澄清、约束或修复，服务于尚未完成的原目标 | 继续原 process，更新受影响的要求和安排。 |
| 原目标或验收条件发生变化 | 明确改变了什么及其影响，按人机协作机制形成决定后更新约定。 |
| 引入可独立理解、推进和验收的新目标 | 组织新的 process，关联相关工作。 |
| 已交付成果的独立改进或修复 | 组织后续 process，关联原交付和问题证据。 |

需要共同设计和验收的要求归入同一 process；可独立形成结果的目标可以拆分。涉及多个模块本身不构成拆分理由。多个 process 存在依赖或共同交付要求时，使用 [Workflow 指导](references/workflow.md)。

明确 process 的预期结果与范围，并区分本次请求要推进的部分。例如，功能开发中的一次设计讨论，不会自动把整个 process 的目标改成“交付设计”。如果目标本来就是完成设计，则以设计成果验收。

## Organize the work

**形成或调整计划时，依次检查已有依据、工作缺口和后续影响。**

1. **检查已有依据。** 阅读相关需求、设计、工程约定、代码和证据，核对哪些成果仍然有效。了解与本次变更相关的软件状态：已有行为、使用方、交付情况和兼容承诺。
2. **根据缺口选择活动。** 用下表定位需要开展的工作；同一需求可以需要多项活动，也可以复用已有产出。

| 当前缺口或工作需要 | 读取并使用 | 要形成的结果 |
| --- | --- | --- |
| 问题、预期结果或范围不清 | [Problem Framing](references/phases/problem-framing.md) | 可用于定义需求的问题与目标说明。 |
| 行为、约束或验收条件未明确 | [Requirements Analysis](references/phases/requirements.md) | 可以据此设计和验收的需求约定。 |
| 职责、接口或关键机制尚不足以指导实现 | [Design](references/phases/design.md) | 当前变更所需的整体、模块或接口设计，以及未决事项。 |
| 实现依据已具备，需要构建或接入能力 | [Implementation and Integration](references/phases/implementation.md) | 对应约定的实现与集成产物。 |
| 需要检查实现、需求覆盖或工程约定 | [Verification and Validation](references/phases/verification.md) | 可支持完成判断的检查结果与证据。 |
| 准备交付，或处理已交付成果的后续需求 | [Delivery and Maintenance](references/phases/delivery-and-maintenance.md) | 交付结论、必要的使用维护材料，或后续工作的依据。 |

3. **考虑后续影响。** 判断本次变更是否需要兼容处理、迁移、集成验证、文档更新或维护准备，将满足目标所必需的工作纳入计划。例如，修改已有使用方依赖的接口，需要检查兼容与迁移；不能只安排接口提供方的编码。

将选定工作整理为 [Process 计划](assets/templates/process-plan.md)：说明每项工作的产出、依赖和完成检查，再确定推进顺序。现有记录能承载这些信息时直接复用。事实不确定且会影响设计时，先安排调查或试验；当前尚不需要解决的细节，不提前展开。

## Advance and revise the plan

**开展一项工作前，核对其所需产出是否已具备，并读取对应活动指导。** 准备实现时，按 Design 指导检查当前变更的设计依据，同时核对工程基线与交付条件。某个依赖未满足时，先处理该缺口，继续推进不依赖它的工作。

完成一项工作后，对照计划中的完成检查核对实际产出，记录结果或证据链接，再判断依赖它的工作能否继续。记录“设计已确定”“代码已实现”“检查已通过”时，分别给出对应依据。

| 执行中的反馈 | 返回与调整 |
| --- | --- |
| 实现违反已确定的需求或契约 | 返回相关实现，修复并重新验证受影响的行为。 |
| 新证据使设计假设或机制失效 | 返回设计；检查是否需要补充调查，更新受影响的实现与验证安排。 |
| 需求、范围或验收条件需要改变 | 返回需求与决策，明确变化及影响后调整计划。 |
| 所需产出不可用，或发生共享契约变化 | 重新安排依赖工作；涉及其他 process 时使用 [Workflow 变更指导](references/workflow.md#handle-changes)。 |

在约定范围内可以通过调查或实现解决的问题由 Agent 推进；涉及人类意图、偏好或重要承诺的选择，按 [人机协作机制](references/mechanisms/human-collaboration.md)准备问题、证据、建议和影响，等待相关决定后继续依赖它的工作。

按 [文档机制](references/mechanisms/documentation-and-traceability.md)同步受影响的约定、计划和进展。保留仍然有效的成果与证据，不因局部变化重新开展全部工作。

## Establish process completion

准备报告完成时，将实际成果与 process 的约定目标、交付清单及验证记录逐项对应，按 [交付指导](references/phases/delivery-and-maintenance.md)形成结论。仍有未满足或未验证的承诺时，明确它们及其影响；需要接受重要限制时，使用人机协作机制。

当前请求完成不等于整个 process 完成。只完成设计讨论时，记录设计结果和剩余开发工作；目标本身是交付设计时，按设计的验收条件判断完成。参与 workflow 的 process 即使局部完成，也仍需由 workflow 检查整体结果。

若此前完成判断有误，追加更正并处理原有承诺，不能将遗漏包装成新需求。交付后的独立改进或修复，按本文的工作归属规则组织后续 process。

---

<!-- Inline source: references/phases/design.md -->

# Design｜设计

## 何时使用与选择范围

需求需要转化为实现方案，或现有方案受到变更影响时使用。先读取有效需求、相关工程基线、既有结构与接口，以及先前决定，确定需要细化的部分：

| 变更涉及什么 | 更新什么 | 需要说明的结果 |
| --- | --- | --- |
| 系统边界、主要职责、依赖或关键交互变化 | [整体设计](assets/templates/architecture.md) | 组件如何分工与协作，方案怎样满足目标，以及重要取舍。 |
| 模块内部行为或职责实现发生变化 | [模块设计](assets/templates/module-design.md) | 关键状态、规则、算法与错误处理如何工作，代码归属及复用安排。 |
| 对外能力、共享数据或使用方约定变化 | [接口文档](assets/templates/interface-contract.md) | 输入输出含义、约束、行为保证、失败语义和兼容影响。 |

同一变更可以涉及多项设计。沿用仍然有效的整体设计，更新真正受影响的部分；小任务可以将说明合并在已有记录中。请求仅为 overview 时，交付相应层次的说明，并指出尚待细化的问题。

## 工作与产出

1. **形成方案。** 明确行为归属、依赖与关键交互。重要取舍说明推荐方案、理由及有实际意义的备选方案。
2. **联合细化接口与机制。** 检查使用方能否依据契约正确调用，提供方的内部机制能否满足承诺。类型签名之外，补齐影响正确使用的语义；共享契约保持一份权威定义。
3. **检查实现依据。** 结合代码和技术约束核实方案。对影响可行性的事实不确定性，安排调查或授权范围内的试验，并记录结果；试验不自动成为已确定的生产方案。
4. **连接实施与验证。** 说明新增代码归属、已有能力复用、相关迁移及如何验证关键行为，将工作安排写入 [Process 计划](assets/templates/process-plan.md)，与交付条件对应。

代码归属说明到当前实现所需的模块或目录职责即可，不要求预先列出所有类与函数。持久化、恢复、并发和部署等机制在影响当前目标时细化。设计状态、决定和记录的维护使用 [文档机制](references/mechanisms/documentation-and-traceability.md)。

## 推进依据

进入当前部分的实现前，应能根据设计回答：

- 行为由谁负责，各部分怎样交互？
- 使用方依赖什么契约，关键机制及失败处理怎样满足要求？
- 代码归属哪里，复用什么，需要哪些上游产出或兼容处理？
- 如何检查相关需求与工程约定得到满足？

影响这些答案的关键选择已有依据，必要依赖与工程约定已具备，并在当前实施授权内时，进入 [Implementation and Integration](references/phases/implementation.md)。其他未决事项注明影响范围，不阻塞独立工作。设计成果完成不等于功能已经实现。

## 返回与决定

| 发现的问题 | 处理方式 |
| --- | --- |
| 可行性依赖尚未证实的事实 | 调查或试验后重新检查方案，保留仍成立的设计。 |
| 内部机制无法满足既定接口 | 调整机制与相关设计；若必须改变共享契约，识别使用方影响并按既有决定权限处理。 |
| 满足目标必须改变需求、验收或重要约定 | 返回 [Requirements Analysis](references/phases/requirements.md)或相应约定，按 [人机协作机制](references/mechanisms/human-collaboration.md)准备决定，再继续受影响的设计。 |
| 共享设计变化影响其他 process | 按 [Workflow 指导](references/workflow.md#handle-changes)更新依赖与受影响工作。 |

既有目标、约定和授权能够支持的技术细化由 Agent 推进；尚未确定或委托的重要工程偏好和取舍，提交相应设计与证据供人类判断。

---

<!-- Inline source: references/mechanisms/documentation-and-traceability.md -->

# Documentation and Traceability｜文档与追溯

在项目中维护需求、设计、决定、进展和证据，使人和 Agent 能查明当前依据、实际成果及下一步。编辑前先读已有记录，沿用项目位置与术语；文档的创建范围遵循当前请求。

## Select documents by purpose｜按用途选择文档

先确定需要保存什么信息，再选择承载位置。已有文档能够满足用途时直接更新；小型工作可以将需求、设计、计划和结果合并在一份工作记录中。模板只提供内容组织参考。

| 信息与职责 | 模板 |
| --- | --- |
| 当前目标概览、文档入口和待处理事项 | [项目索引](assets/templates/project-index.md) |
| 预期行为、约束和验收条件 | [需求文档](assets/templates/requirements.md) |
| 采用的工程约定、范围与检查方式 | [工程基线](assets/templates/engineering-baseline.md) |
| 项目概念及其含义 | [术语表](assets/templates/glossary.md) |
| 系统结构、职责、交互与设计取舍 | [整体设计](assets/templates/architecture.md) |
| 使用方共同依赖的数据和行为语义 | [接口文档](assets/templates/interface-contract.md) |
| 模块职责、内部机制及实现安排 | [模块设计](assets/templates/module-design.md) |
| 一项需求的工作安排、进展和下一步 | [Process 计划](assets/templates/process-plan.md) |
| 多个 process 的依赖、共享约定和整体交付安排 | [Workflow 计划](assets/templates/workflow-plan.md) |
| 交付承诺、验收条件和实际满足情况 | [交付清单](assets/templates/delivery-checklist.md) |
| 已形成的重要决定及来源、理由和影响 | [决策日志](assets/templates/decision-log.md) |
| 需要保留的决策分析与备选方案 | [决策分析](assets/templates/decision-detail.md) |
| 实际检查、结果、证据及限制 | [验证记录](assets/templates/verification-record.md) |

## Organize and maintain authoritative records｜归属与权威记录

以下目录表达信息归属，按项目已有结构调整，不要求全部创建：

```text
docs/
├── README.md
├── requirements.md
├── engineering-baseline.md
├── glossary.md                       # 需要时维护
├── design/
│   ├── overview.md
│   ├── contracts.md
│   └── modules/<module>.md           # 需要独立模块说明时维护
├── decisions/
│   ├── log.md
│   └── details/<decision-id>.md      # 分析较复杂时维护
├── changes/<work-name>/              # 一项 process 的工作记录
│   ├── plan.md
│   ├── delivery.md
│   └── verification.md
└── workflows/<overall-goal>.md       # 多项工作需要协调时维护
```

项目级需求、设计和基线维护当前约定；`changes/` 记录具体工作的安排与成果；`workflows/` 关联局部计划并记录整体协调。使用、运行和 API 文档沿用项目既有位置，在交付记录中引用。

**从提案到当前约定，按以下方式维护：**

1. **尚未确定。** 将方案放在所属工作记录、设计草稿或决策分析中，明确标为提案或未决事项；同一文档包含多种状态时，区分对应段落。未决方案不覆盖已有效的约定。
2. **决定形成。** 更新权威需求、设计、接口或基线。重要决定在日志中保留来源和理由，提案关联最终决定；已替代的内容不继续作为当前依据。
3. **实现与验证推进。** 在工作记录中分别记录实现和验证状态，并关联证据。已确认但尚未实现的设计明确注明该状态；设计认可、代码实现和检查通过分别有各自的依据。

共享要求和接口语义只保留一个权威定义，其他文件引用它。代码 schema/type 可以维护精确结构，文档补充语义与理由。发现文档与代码不一致时，核查是实现偏差还是已决定但尚未同步的变更，再修正相应内容。

## Update at meaningful events｜创建与更新时机

按实际成果和变化更新记录。用于指导相关实现的约定，应在该实现开始前明确；随后在形成可核查结果、出现影响工作的新信息或准备交付时同步状态，无需逐条记录对话和命令。

| 触发时机 | 创建或更新什么 | 要明确的结果 |
| --- | --- | --- |
| 问题、需求或术语得到澄清 | 需求、必要的术语定义和相关计划 | 当前目标、约束、验收条件及未决问题。 |
| 工作安排和交付范围确定 | Process／Workflow 计划、交付清单 | 要形成哪些产出，依赖什么，怎样检查。 |
| 设计确定或工程约定改变 | 权威设计、接口或基线；重要决定写入日志；同步相关计划 | 哪项约定已生效，哪些使用方和工作受影响。 |
| 实现形成可检查的成果 | 工作进展、相关产物引用；核对设计与实际实现 | 哪些内容已实现，哪些尚待验证。 |
| 完成有意义的测试或审阅 | 验证记录、计划和清单中的对应状态 | 实际检查对象、结果、证据和限制。 |
| 新反馈使需求、设计或依赖需要调整 | 问题与证据、必要的决策材料；决定形成后更新权威约定和受影响计划 | 变化理由、仍有效的成果、需要返回处理的工作。 |
| 结束当前请求或交付成果 | 交付结论、计划进展和必要的使用维护说明 | 本次完成范围、整个 process 的状态、剩余问题和下一步。 |
| 目标、有效文档位置或关键阻塞改变 | 项目索引的摘要和链接 | 读者能找到当前依据和待处理工作。 |

反馈是否需要人类决定使用 [人机协作机制](references/mechanisms/human-collaboration.md)，跨 process 的影响使用 [Workflow 指导](references/workflow.md#handle-changes)。先形成处理依据，再更新约定，不能直接用未确认的实现变化改写需求。

当前约定和计划随工作更新；重要承诺变化保留决定与版本历史。验证记录追加有意义的检查及更正，后续成功不覆盖与结论相关的失败证据。

## Decision-log protocol

使用项目决策位置中的 append-only Markdown 日志，记录影响目标、需求、设计、工程约定、兼容性或后续工作的重要决定。普通局部编码选择无需逐项记录，未决提案保留在相应分析或工作记录中。

每条决定记录稳定标识、时间与时区、决定主体、内容与理由、影响范围及引用。注明人类确认或 Agent 委托的来源；记录者不一定是决定者。条目形状使用 [决策日志模板](assets/templates/decision-log.md)。

追加前检查最新条目和编号，避免并行写入产生冲突。替代或纠正历史决定时，追加新条目并引用原条目，同时更新当前权威文档。冲突按决定的内容、范围和来源核实，不只按时间先后判断。

决定时参考的代码版本与后来实现该决定的 commit／PR 分开记录；后者明确后可追加关联。没有版本引用时如实说明，不编造。较长分析放在链接的详情中。Append-only 是编辑规则，不代表日志不可篡改。

## Evidence and traceability｜证据与关联

保留能够双向查找的关系：需求／工程约定 → 设计／接口／决定 → 工作与代码变更 → 验证 → 交付。用现有文档链接、章节、issue 或决定标识建立关联，能回答“这个要求在哪里实现和检查”“这项变更依据什么”。

证据注明实际检查的代码、配置和相关输入环境、完成的操作、结果与限制。已提交代码使用版本引用；未提交工作使用相关 diff 或内容快照。计划中的命令不能当作已执行证据，旧的通过结果只适用于实际检查过的版本与条件。

Workflow 引用局部验证，并补充整体检查的证据。详细日志保存在证据位置，正文保留判断所需的结论、解释与链接。

## Writing requirements｜写作与去重

使用用户或项目的语言，先明确文档的读者与用途，再组织内容：

- **写项目事实与具体安排。** 需求写目标和约束，计划写要做什么，设计写机制和取舍，验证记录写实际结果。通用开发规则引用指导，不复制到每一份产物。
- **区分信息状态。** 事实、推断、提案、决定、实现和验证结果应能辨认。不要把模板提示保留为项目结论。
- **让重复承担不同作用。** 同一事项可在计划中说明安排、在验证中说明结果；无需在各节重复同一句授权或状态声明。必要摘要引用权威详情，修改时同步受影响的摘要。
- **保持术语与表示一致。** 术语表定义项目概念；图表、接口和正文使用相同含义。图用于展示具体关系，表用于比较，文字解释必要的依据和取舍。
- **按信息价值检查篇幅。** 删除一段后若不影响理解、判断或行动，考虑删除或合并；必要的例子和边界说明保留，不用统一字数限制代替审阅。

项目索引只保存简短概览、入口和待处理事项；详细进展、依赖和下一步安排由 Process／Workflow 计划维护。交付文档前，核对本文档是否完成其用途、关键状态是否有依据、引用是否可用，以及是否重复维护了其他文档的内容。
