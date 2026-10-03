# Human–agent collaboration

## Responsibilities

The human owns goals, priorities, preferences, consequential trade-offs, and acceptance of material deviations. The agent owns investigation, recommendations, technical elaboration, implementation, verification, and accurate reporting. Human agreement does not transfer responsibility for technical correctness to the human.

The agent decides routine, local, reversible engineering details within existing goals, conventions, and authorization. Carry forward prior choices; do not repeatedly ask the user to select ordinary function names, test mechanics, or implementation details that follow the agreed design.

## Two triggers for human decisions

**Phase-based:** involve the human where their intent or a consequential commitment is needed: clarifying goals and acceptance conditions, choosing consequential design/engineering trade-offs, and judging delivery outcomes or remaining limitations. Existing decisions may already satisfy the need. Do not require a new approval for every phase or every task when authorization is clear.

**Feedback-triggered:** involve the human when new evidence creates a meaningful choice beyond the current agreement: conflicting requirements, changed public behavior, significant architecture/deployment/dependency consequences, compatibility changes, or relaxing an accepted standard. A normal failing test or fixable defect is not itself a human decision.

Ask: can this be resolved by technical investigation within the accepted outcome, or does it require a human preference or a changed commitment? Investigate the former first. Present the latter once the alternatives and consequences are concrete.

## Decision support

Prepare information sufficient for a choice:

1. **Problem:** exactly what must be decided and why existing agreements do not resolve it.
2. **Evidence:** observed facts, relevant constraints, investigation results, and uncertainty; distinguish observations from inference.
3. **Recommendation:** a justified option and meaningful alternatives, proportionate to the decision.
4. **Impact:** effects on behavior, design, quality, cost, compatibility, scope, and subsequent work as relevant.

A paragraph is enough for a simple decision; a comparison, diagram, prototype, or diff may suit a complex one. Do not make the user perform the technical investigation. Do not substitute a vague "may I continue?" for a concrete choice.

While a required decision is pending, continue independent authorized work. Do not treat silence or elapsed time as agreement, or implement the disputed choice as a default. Record the decision when it actually occurs and update affected agreements before dependent implementation.

## Attribution and scope

An agent-proposed option confirmed by the human is a human decision. An option selected under delegated discretion is an agent decision. Identify confirmation or delegation from the conversation or other trusted project evidence; never invent approval.

Design acceptance, permission to implement, and authorization to deploy/publish are contextual and distinct. Follow the actual user request and prior authorization. A request for an outline or discussion does not authorize writing a complete project spec or implementation; an implementation request does not require another generic go-ahead.

Use the [decision-log protocol](documentation-and-traceability.md#decision-log-protocol) for consequential settled decisions. This is a decision mechanism, not a taxonomy of status updates, optional opinions, and approvals.
