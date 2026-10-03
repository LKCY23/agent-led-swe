# Verification and evaluation

Use the originating requirements, accepted design/contracts, engineering baseline, delivery criteria, and actual diff. Identify the revision or working-tree snapshot being checked. A checklist item is not satisfied by a promise to run a command.

## Check separately

| Question | Evidence |
| --- | --- |
| Does behavior work? | Suitable automated tests, actual operation, measured properties, or domain-specific validation. |
| Does it implement the intended work? | Requirement/design coverage, omissions, partial behavior, unintended additions, contract and failure semantics. |
| Does it meet engineering expectations? | Applicable standards, responsibility ownership, dependency direction, clarity, complexity, compatibility, and documentation consistency. |

A success in one dimension cannot hide a failure in another. For significant changes, an independent review may be useful when authorized; it does not guarantee correctness. Ordinary bounded fixes do not require a multi-agent ceremony.

## Validate the validation

Use acceptance grounded in requirements rather than reproducing implementation logic. Confirm what the test actually observes, whether it would fail for the relevant defect, and whether mocks conceal the behavior under review. Choose checks proportionate to the change. Broad test repetition needs a changed dependency, new failure, or another unresolved concern.

Record pass/fail/unknown, actual operations completed, environment/configuration/input references, evidence location, and limits in a [verification record](../../assets/templates/verification-record.md). Distinguish a missing dependency or inaccessible environment from a verified product failure. Preserve unsuccessful attempts relevant to the conclusion and subsequent corrections.

When a check fails: repair implementation defects against the agreed contract; investigate requirement/design conflicts before changing the contract. If upstream commitments must change, use [human collaboration](../mechanisms/human-collaboration.md), update affected artifacts and rerun the impacted checks.

Reconcile the [delivery checklist](../../assets/templates/delivery-checklist.md) with evidence. Existing passes are reusable only where the checked version and conditions remain relevant. Leave unverified items visible; do not change thresholds or delete items to report completion.
