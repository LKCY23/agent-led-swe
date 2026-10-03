# Implementation and integration

Recover the accepted scope, applicable design/contracts/baseline, delivery checklist, and current tree. Preserve unrelated changes. If prerequisites already exist, use them without restarting requirements or requesting another generic approval.

Work in coherent, inspectable increments. Each should produce a useful behavior or verification outcome with genuine dependency ordering. Vertical slices are often useful; mechanical migrations or broad refactors may need staged compatibility or a shared integration boundary instead.

For each increment:

1. Identify the requirement/design obligation and the relevant verification.
2. Implement within declared responsibilities, interfaces, repository conventions and allowed scope.
3. Run suitable targeted checks during development; inspect actual results and fix defects.
4. Review scope and structure as well as behavior. Record material progress and evidence at useful boundaries.

Use TDD where it suits the work and project baseline; expected results should come from requirements, worked cases, or independent evidence. Avoid tests that merely recompute the implementation or assert its private shape. Refactor when justified by the current work, keeping unrelated cleanup separate.

Distinguish local engineering adjustments from changes to agreed behavior, architecture, compatibility, cost, or quality commitments. Investigate the latter and use [human collaboration](../mechanisms/human-collaboration.md) when a human decision is required. Do not silently remove a difficult requirement or expand scope to a speculative framework.

Maintain work records through [documentation and traceability](../mechanisms/documentation-and-traceability.md). Planned, implemented, and verified are separate states. Update current design for accepted changes; preserve decision history.

Hand the inspectable increment to [verification](verification.md). Commits, external publication, deployment, new dependencies and environment changes follow the project's conventions and actual user authorization, not an automatic step inferred from this skill.
