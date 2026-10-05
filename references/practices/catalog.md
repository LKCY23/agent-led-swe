# Engineering Practices and References｜工程实践与参考目录

需要作具体工程选择时查阅相关条目，依据项目目标、已有约定和人类偏好采用并裁剪。知识体系帮助检查问题是否遗漏，设计思路帮助形成工程规则，文档框架帮助组织说明，它们承担不同作用。

下表中的约定和用法是供项目选择的示例，不代表外部来源强制要求。选定后按 [工程基线机制](../mechanisms/engineering-baseline.md)记录范围、理由和检查方式。涉及版本或标准条文时查阅原始资料；引用部分思想不等于全面采用该标准。

## Knowledge and quality｜工程问题与质量目标

| 参考与作用 | 项目如何使用 | 检查与裁剪 |
| --- | --- | --- |
| [SWEBOK](https://www.computer.org/education/bodies-of-knowledge/software-engineering)：工程知识参考 | 在项目规划或较大变更中检查需求、设计、构建、测试和维护问题是否遗漏，将相关问题纳入工作安排。 | 检查本次目标所需的问题是否有对应工作；按适用范围取用，不按知识领域创建文件。 |
| [ISO/IEC 25010](https://www.iso.org/standard/78176.html)：质量模型参考 | 将“质量好”等诉求细化为项目相关的质量目标和场景。目标由需求维护，基线关联实现约定与检查方法。 | 用目标场景和证据检查；度量与阈值需要项目依据，不能从标准名称直接推导。 |

## Architecture and interfaces｜架构与接口

| 参考与作用 | 项目如何使用 | 检查与裁剪 |
| --- | --- | --- |
| [信息隐藏与职责内聚](https://www.cs.lafayette.edu/~gexia/cs301/resources/parnas.html)：模块划分思路 | 按职责及变化原因组织模块，可形成“使用方通过公开接口访问，不依赖内部实现”等约定。 | 对照实际调用、依赖与修改影响检查；具体模块边界在设计中确定。 |
| [arc42](https://arc42.org/overview/)：架构说明框架 | 选择能解释当前系统的结构、交互、部署或贯穿机制视角，用于架构文档。 | 检查图文是否一致、读者关心的问题是否得到回答；只采用有解释作用的视角。 |
| [Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture)：隔离外部技术变化的思路 | 需要替换服务或隔离测试时，可约定核心逻辑通过能力接口使用外部系统，具体接入由 adapter 承担。 | 检查替换接入是否影响预期边界之外的代码；接口与适配层有维护成本，需要由实际变化需求支持。 |

## Language and repository｜语言与仓库组织

| 参考与作用 | 项目如何使用 | 检查与裁剪 |
| --- | --- | --- |
| [PEP 8](https://peps.python.org/pep-0008/)：Python 风格参考 | 对应语言缺少约定时参考社区规范；已有项目优先确认其格式、命名和检查配置。 | 执行项目配置的检查，补充命名与可读性审阅；其他语言采用对应规范。 |
| [PyPA](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)：Python 包组织参考 | 项目需要安装、发布或存在导入歧义时，据此选择包组织方式，并在设计中记录代码归属。 | 检查安装后的导入和运行行为；一次性脚本与可发布库的组织需求不同。 |

## Verification and review｜验证与审阅

| 参考与作用 | 项目如何使用 | 检查与裁剪 |
| --- | --- | --- |
| [面向行为的检查](https://google.github.io/eng-practices/review/reviewer/looking-for.html)与[聚焦修改](https://google.github.io/eng-practices/review/developer/small-cls.html)：测试与变更审阅参考 | 根据变化的行为选择单元、集成或端到端验证，预期结果来自需求和独立依据；按可审阅的工作组织改动。 | 检查测试能否发现目标缺陷、改动是否包含无关内容；TDD 是否采用由项目需要决定。 |
| [Standards／Spec review](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/engineering/code-review/SKILL.md)：分别检查规范与需求的审阅思路 | 形成约定：审阅分别报告工程规范问题，以及需求的缺失、错误或越界实现。 | 每项问题关联规则或需求及具体证据；不因功能可运行就省略工程审阅。 |

## Documentation and delivery｜文档与交付

| 参考与作用 | 项目如何使用 | 检查与裁剪 |
| --- | --- | --- |
| [Diátaxis](https://diataxis.fr/)：使用者文档框架 | 根据读者需要组织教程、操作指南、参考或解释，补齐使用和理解产品所需的信息。 | 检查读者能否找到并完成相应任务；内部需求、设计和决策记录仍由项目文档机制组织。 |
| [决策理由记录](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)：保留背景、选择与后果的思路 | 重要选择关联背景、理由和影响；本 skill 的具体记录方式引用 [文档机制](../mechanisms/documentation-and-traceability.md#decision-log-protocol)。 | 检查决定来源和替代关系是否可追溯；是否需要独立分析文档取决于问题复杂度。 |
| [Semantic Versioning](https://semver.org/)：公开 API 的版本兼容约定 | 使用方依赖版本化契约时，先明确公开 API，再确定版本与兼容策略。 | 对照实际兼容性变化检查版本安排；版本号不能替代兼容性验证。 |

目录覆盖当前通用选择。安全、可访问性、可复现性或运维等方面有具体需求时，再补充对应实践及原始来源；已有约定与候选实践冲突时，按工程基线机制处理。
