# Validation — v0.1.0 — 2026-10-03

## Executed checks

| Check | Actual result |
| --- | --- |
| skill-creator `quick_validate.py` | Passed: frontmatter, naming and entrypoint scaffold checks. |
| `tests/check_package.py` | Passed: metadata consistency, 27 Markdown files' local links/fences, and reachability of all 23 reference/template resources from SKILL.md. |
| Python compilation of test helpers | Passed. |
| Codex actual discovery | Passed via a temporary project skill link: Codex CLI 0.154.0 found exactly one enabled target, loaded UI metadata, and reported zero discovery errors. |
| Claude actual plugin validation/inventory | Passed with Claude Code 2.1.278 and session-local `--plugin-dir`: one skill, no agents/hooks/MCP/LSP servers. |

Host receipt: [host-discovery.json](host-discovery.json). The Python test helpers resolved `/opt/homebrew/bin/codex`; the interactive shell also exposed a different CLI version. Results here refer to the executable recorded by the checks, not all installed clients or desktop UI paths. No global installation or host configuration was changed.

## Behavioral smoke attempt

Planned: D1, D4, D7 from [scenarios.md](scenarios.md), one attempt each, at most 180 seconds per case. Target instruction content hashes and actual outcome are in [smoke-results.json](smoke-results.json).

D1 used a fresh `codex exec`, a temporary writable fixture, explicit target SKILL.md, `--ephemeral`, and `workspace-write`. The test carried the configured `gpt-6.1-sol` model and `high` effort while suppressing unrelated user configuration for that invocation. The provider rejected the model as unsupported for the ChatGPT account, before any target entrypoint read or task execution. Exit code was 1 after approximately 7 seconds; the fixture was unchanged. This is an execution/configuration error, not a behavioral pass or a demonstrated skill failure.

D4 and D7 were not run after that failure. No fallback model was silently substituted. Raw local evidence remains under ignored `tests/runs/`; the committed result summary retains the failure and target hashes.

## Author review

Reviewed against the agreed design: six activities, three cross-phase mechanisms, discussion/implementation scope, reuse of prior authorization, engineering practice selection, append-only decision attribution, work-unit records, pre-implementation delivery criteria, and separate behavior/spec/standards checks. The review index in [README](../README.md#首轮重点-review) points to the consequential design choices for the user.

This is author review, not independent model grading. The static checks do not prove the instructions cause the intended behavior.

## Remaining validation

- Complete the three smoke cases with a model supported by the selected CLI, recording any new attempt separately.
- Exercise the remaining development scenarios as warranted by first use or further changes.
- Natural selection/routing, Claude behavior, uncontaminated baseline comparison and measured quality improvement remain untested.
- Remote publication, marketplace registration and deployment are separate from this local package validation.
