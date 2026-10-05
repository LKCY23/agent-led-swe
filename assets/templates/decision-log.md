# Decision log

Append consequential settled decisions using the [decision-log protocol](../../references/mechanisms/documentation-and-traceability.md#decision-log-protocol) and the project's ID convention. Use the following entry shape without rewriting prior entries. Copy the shape only when an actual decision exists.

## Decision ID — short summary

- **Time:** timestamp and timezone.
- **Decision-maker:** human, or agent acting within delegated scope. Identify the confirmation or delegation source; optionally identify a different proposer.
- **Decision and reason:** what was settled, under which conditions, and why, with evidence or remaining uncertainty as relevant.
- **Affected scope:** requirements, design, contracts, baseline, or work items.
- **References:** supporting material and related work.
- **Supersedes / corrects:** earlier ID when applicable.
- **Context revision:** optional observed commit or working-tree reference; state unavailable if relevant.

An implementation commit/PR can be linked later by appending a linkage entry identifying the original decision. Extended analysis may live in a linked detail document. Proposals that have not been decided remain open matters rather than settled log entries.
