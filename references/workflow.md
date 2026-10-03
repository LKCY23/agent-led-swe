# Workflow and entry

## Recover the current position

Identify the requested result and scope from the latest instruction together with prior decisions. Inspect existing requirements, engineering conventions, design, work records, and relevant code. Distinguish settled facts, suggestions, assumptions, and missing information. Report the next meaningful activity briefly; a document inventory is not a new approval ceremony.

Existing material can satisfy a phase. Normalize only what the next activity genuinely needs; do not restart discovery or rewrite accepted designs because their names differ from the templates.

## Six recurring activities

| Phase | Work | Sufficient basis to proceed |
| --- | --- | --- |
| Problem and goals | Understand users, scenarios, current behavior, purpose, scope, and unknowns. | The current problem and intended outcome are clear enough to define requirements. |
| Requirements and success | Define behavior, constraints, quality goals, and acceptance conditions. | This increment has actionable requirements; material ambiguity is resolved or explicitly isolated. |
| Solution design | Determine responsibilities, interactions, contracts, mechanisms, and trade-offs. | Consequential choices are settled and the intended increment has an implementation and verification approach. |
| Implementation and integration | Build bounded increments, test, integrate, and track deviations. | The current increment is inspectable and its actual completion state is known. |
| Verification and evaluation | Check behavior, requirement coverage, design conformity, and code quality. | Evidence supports a precise statement of what passed, failed, or remains unknown. |
| Delivery and evolution | Reconcile deliverables, explain operation/maintenance, and incorporate feedback. | The recipient can use or continue the work and understand remaining issues. |

These are activities, not a waterfall or six mandatory files. Verification starts with defining success and continues during implementation. Refine interfaces and internal design together. Work at a useful increment instead of specifying every future module up front.

## Tailor the work

- Discussion or design-only: inspect, reason, and present decisions at the requested level. Persist a spec when requested; suggestions are not accepted requirements.
- Small implementation: reuse repository conventions; identify the changed behavior, make the focused change, verify it, and report evidence. A short issue or work note can carry the whole record.
- Substantial or cross-module implementation: establish relevant requirements, engineering baseline, design/contract boundaries, delivery criteria, and implementation steps. Reuse existing approvals and fulfill explicit implementation authorization.
- Exploratory prototype: identify the uncertainty being investigated and the permitted experiment. Record findings as evidence, not a production design or completed feature.
- Maintenance/resumption: compare the current tree and evidence with records. Revalidate only where changes or missing evidence warrant it.

## Feedback loop

Implementation defect → repair against the existing requirement. Technical uncertainty → investigate with suitable evidence. A design conflict → revisit design. A goal/preference conflict or consequential change → use [human collaboration](mechanisms/human-collaboration.md). Revise affected documents and checks after the decision; do not redefine success to fit an implementation.

A blocker applies to dependent work, not automatically the entire project. Keep unresolved matters visible. A verified increment does not establish completion of the whole work item.

Project records live in the target project. The installed skill and its templates are reusable guidance, never a storage location for project decisions or progress.
