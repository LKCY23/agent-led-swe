# Documentation and decision traceability

## Select documents by purpose

Read before editing. Reuse authoritative project material and familiar filenames. Create only information needed for the authorized work; a discussion or directory-initialization request is not permission to fill unresolved designs. Templates are adaptable starting points, not a mandatory file checklist.

| Information | When needed | Template |
| --- | --- | --- |
| Navigation/current position | Several documents or cross-session work | [Project index](../../assets/templates/project-index.md) |
| Behavior, constraints, acceptance | Requirements clarification | [Requirements](../../assets/templates/requirements.md) |
| Adopted quality/conventions | Engineering choices not already settled | [Engineering baseline](../../assets/templates/engineering-baseline.md) |
| Project-specific vocabulary | Ambiguity or repeated terminology | [Glossary](../../assets/templates/glossary.md) |
| System scope/structure/interactions | Overall solution design | [Architecture](../../assets/templates/architecture.md) |
| Shared behavioral/data agreement | Consumers must coordinate independently | [Interface contract](../../assets/templates/interface-contract.md) |
| Important internal mechanisms | Overall design leaves material implementation questions | [Module design](../../assets/templates/module-design.md) |
| Work ordering and verification | Planning the current increment | [Implementation plan](../../assets/templates/implementation-plan.md) |
| Deliverables and acceptance | Before implementation, reconciled at delivery | [Delivery checklist](../../assets/templates/delivery-checklist.md) |
| Consequential settled decisions | Whenever a decision occurs | [Decision log](../../assets/templates/decision-log.md) |
| Extended decision reasoning | An entry cannot usefully hold the argument | [Decision detail](../../assets/templates/decision-detail.md) |
| Actual review/check outcomes | During verification and delivery | [Verification record](../../assets/templates/verification-record.md) |

A problem brief can become part of requirements. A compact spec or issue can combine requirements, design, plan, delivery criteria, and results. Split only when distinct ownership, scope, size, or maintenance makes it useful.

## Suggested project organization

```text
docs/
├── README.md
├── requirements.md
├── engineering-baseline.md
├── glossary.md                       # when needed
├── design/
│   ├── overview.md
│   ├── contracts.md
│   └── modules/<module>.md           # when needed
├── decisions/
│   ├── log.md
│   └── details/<decision-id>.md      # when needed
└── changes/<work-name>/
    ├── plan.md
    ├── delivery.md
    └── verification.md
```

`changes/` groups an independently scoped work item, not every conversation, day, or commit. One work item may span sessions/commits. A small fix can use one work note or issue. The tree is a proposal, not an initialization command. Keep user-facing run/usage/API documentation in the project's established locations and link it from delivery.

Project documents describe current effective requirements and design. Change records describe the scope, plan, and evidence of a particular effort. Keep each requirement/contract authoritative in one place; use references rather than copying its full definition into every document. Existing schemas/types may own exact structure while prose owns semantics and rationale. If code and docs disagree, investigate rather than automatically treating either as correct.

## Lifecycle and feedback

Separate the status of a decision (proposed/settled/superseded), implementation (not started/partial/implemented), and verification (unverified/pass/fail/unknown). Use simple prose or existing project states; no extra machine state database is required.

| Feedback | Update |
| --- | --- |
| Unclear term or requirement | Open question and relevant glossary/requirement after resolution |
| Design infeasible or materially different trade-off | Evidence, decision support, then accepted design/contracts and affected tasks |
| Ordinary implementation defect | Defect/work record, implementation, relevant regression check and result |
| Test reveals conflicting requirements | Requirement/design decision, then implementation and verification plan |
| Scope or quality target changes | Decision and impact, authoritative requirement/baseline, plan/checklist |
| Maintenance feedback | Relevant issue, investigation and justified design/baseline changes |

Current design, baseline, plans, and checklist status are editable living records. Preserve material commitment changes via decisions and version history. Validation records append meaningful checks and corrections; failed evidence is not replaced by later successes. Retain only evidence useful to diagnosis or conclusions, not a transcript of every command.

## Decision-log protocol

Use one append-only Markdown log in the project's decision location. Record consequential choices affecting goals, requirements, design, engineering conventions, compatibility, or further work; do not log every local coding choice.

Each entry carries a stable ID, time (with timezone), decision-maker (human or agent), the decision and reason, affected scope, and relevant references. Record the source of human confirmation or agent delegation. An agent writing the record is not necessarily its decision-maker. Unconfirmed proposals stay in open questions or decision support material, not as accepted log entries.

Read the current tail/IDs immediately before appending. Use the existing ID convention; avoid collisions with concurrent writers. Preserve previous entries. Append a new decision referencing the prior one when superseding, or append a correction if a record is wrong. Update the current authoritative design/baseline as a separate step. Resolve conflicting decisions rather than assuming the newest timestamp always wins across unrelated scopes.

Context commit is optional: identify the code observed when deciding. Implementation commit/PR is a different optional reference, often unknown until later; append a linkage entry when known. With no Git repository or no commit, record that fact instead of inventing a revision. Link extended reasoning under `decisions/details/` only when useful. Treat append-only as an editing rule, not a tamper-proof audit guarantee.

## Evidence and traceability

Maintain useful links: requirement/baseline → design/contract/decision → work item → change → verification → delivery result. Follow both directions: where was a requirement implemented/checked, and why does this change exist? Stable anchors, issue IDs, or requirement IDs suffice; do not require a full traceability matrix for every small task.

Evidence identifies the checked code/configuration and relevant data/environment, the operation actually completed, result, and limits. Use commit references when available; for uncommitted work record the relevant diff/content snapshot. A command printed in a plan is not an executed check. An earlier pass applies only to the version and conditions actually checked.

On handoff/resumption, the index points to current agreements, actual progress, unresolved matters, and the next action. Verify those against the current tree. Completion of one task does not prove the whole project complete.

## Writing requirements

Be accurate, concise but sufficient, readable, consistent, traceable, and maintainable. Separate observed facts from hypotheses and plans. Lead with purpose and conclusions; use diagrams for specific relationships and tables for comparisons. Preserve terminology across prose, diagrams, interfaces, and code. Keep project-specific glossary definitions separate from implementation instructions. Move detailed evidence behind links; avoid duplicating live rules in index, spec, tasks, and agent steering files.

Templates provide output shapes; this file owns document behavior and lifecycle. Write in the user's/project's language. Do not leave template prompts presented as actual decisions or evidence.
