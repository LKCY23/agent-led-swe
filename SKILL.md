---
name: agent-led-swe
description: Guide agent-led software engineering from requirements and design through implementation, review, and delivery, with human decisions, project engineering conventions, and traceable evidence. Use when developing or changing software that needs this coordination, or when explicitly invoked; scale to the task. General explanations, unrelated writing, and routine edits do not require the full workflow.
---

# Agent-Led SWE

Lead the engineering work while the human controls goals, preferences, and consequential trade-offs. Turn intent into inspectable requirements, design, implementation, and delivery evidence. Respond in the user's language and follow the project's vocabulary.

## Start from the actual request

Inspect applicable repository instructions, relevant code/configuration, existing design and verification material, and current changes. Identify the requested outcome, current phase, work scope, and authorization. Read [workflow](references/workflow.md) to choose the next activity; reuse sufficient existing material regardless of filenames.

Discussion, proposal, documentation, implementation, and external delivery are distinct scopes. Match the user's current request. An accepted design is not by itself an instruction to code. An explicit implementation request is sufficient to implement within its settled scope; do not demand repeated approval. Preserve unrelated user work.

For a bounded fix, use existing conventions, the affected requirement, a focused verification, and a short result. For larger work, establish the needed engineering baseline and delivery criteria before substantial implementation. Do not create a full document tree merely because the skill was loaded.

## Throughout the work

- Work autonomously within settled goals, constraints, and authorization. Investigate technical uncertainty before asking the human. For a consequential unresolved choice, prepare the problem, evidence, recommendation, and impact; wait on dependent work while useful independent work continues. Read [human collaboration](references/mechanisms/human-collaboration.md).
- Ground implementation choices in the repository and selected engineering practices. Before establishing or changing these conventions, read [engineering baseline](references/mechanisms/engineering-baseline.md).
- When creating or updating project records, read [documentation and traceability](references/mechanisms/documentation-and-traceability.md). Write to the project only within the requested scope. Keep suggestions distinct from settled decisions, implementation distinct from verification, and historical decisions distinct from current design.
- Derive completion from requirements and evidence. Report missing, partial, and unverified work explicitly. A passing test suite does not establish requirement coverage or engineering quality.

## Phase guidance

Read the relevant phase, not every phase in advance. Follow feedback to the phase that owns the unresolved question.

| Current work | Read |
| --- | --- |
| Understand the problem and scope | [Problem framing](references/phases/problem-framing.md) |
| Define behavior, quality, and success | [Requirements](references/phases/requirements.md) |
| Select and refine the solution | [Design](references/phases/design.md) |
| Build and integrate | [Implementation](references/phases/implementation.md) |
| Check behavior, requirements, and standards | [Verification](references/phases/verification.md) |
| Deliver or maintain the result | [Delivery and evolution](references/phases/delivery-and-evolution.md) |

Use the [practice catalog](references/practices/catalog.md) for an actual engineering choice. Templates are linked from the documentation mechanism; adapt only the ones needed. The skill is self-contained and does not require an issue tracker, other skills, background services, multi-agent execution, or global configuration changes. Use specialized tools and reviews when warranted and authorized.
