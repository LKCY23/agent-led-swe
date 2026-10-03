# Solution design

Start with effective requirements, the relevant engineering baseline, existing system structure, and prior decisions. Set the requested design depth: an overview explains responsibilities and relationships; an implementation-ready design resolves the material questions for the current increment.

## Elaborate in this order, with feedback

1. **Overall design:** scope/context, major responsibilities and dependencies, key data/runtime flows, and significant trade-offs. Use the [architecture template](../../assets/templates/architecture.md) when a document is warranted.
2. **Contracts and mechanisms together:** refine what consumers must know and how the providers can fulfill it. A [contract](../../assets/templates/interface-contract.md) includes meaning, invariants, relevant ordering, errors and side effects, not only type signatures. [Module design](../../assets/templates/module-design.md) explains important internal state/behavior and where it belongs.
3. **Implementation and verification approach:** choose useful increments and checks. Reference existing code or interfaces where doing so helps implementation; avoid premature exhaustive file/class lists. Use the [plan](../../assets/templates/implementation-plan.md).
4. **Delivery readiness:** reconcile promised deliverables, acceptance conditions and verification methods in the [checklist](../../assets/templates/delivery-checklist.md). Task breakdowns reference these commitments rather than redefining them.

A small change can carry all of this in one spec/issue. Shared contracts stay authoritative in one place; split module documents only where needed. Persistence/recovery, migrations, concurrency and deployment details belong only when they affect this change. Do not prescribe the AgentInfra module taxonomy for unrelated projects.

## Decisions and uncertainty

Present meaningful alternatives for consequential choices and explain why one is recommended. Use prototypes or inspection to reduce factual uncertainty within the user's scope. Label exploratory results; they do not automatically become production decisions.

Apply [human collaboration](../mechanisms/human-collaboration.md) to unsettled consequential choices, carrying forward existing authorization. Record settled decisions via the [documentation mechanism](../mechanisms/documentation-and-traceability.md). Do not mark agent proposals as human-approved.

Proceed into implementation when the intended scope has sufficient requirements, design/contract semantics, an applicable baseline, and delivery criteria, and the user has authorized implementation. A design-only request concludes with the requested design and clearly identified unresolved matters.
