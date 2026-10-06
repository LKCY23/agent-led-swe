# Model-only Docker network and task scope — 2026-10-06

Added a fixed model gateway on a separate network, keeping real credentials outside the worker. Native CLI and live model checks, packaging worker checks, and the independent verifier pipeline passed. Removed the retired pytest task and its dedicated history at the user’s request. No skill content or benchmark-effect trial changed. [Current report](reports/network-and-task-scope-2026-10-06.md) records evidence, failed infrastructure attempts, limits and candidate review.

---

# Verifier-only outcomes and clean packaging executor — 2026-10-06

Removed automatic model judging from the evaluation entrypoint. Task outcomes derive only from frozen verifier checks; execution state and native-comparison validity are separate, historical judge fields cannot alter scores, and no-verifier cases remain unknown. Process/skill analysis is an optional later reading of complete history, documented separately without a new automated analysis service.

Built and qualified a distinct packaging executor image while retaining the verifier image. Removed installed/vendored/archive/cache copies; actual worker auditing also caught npm/node-gyp's copy, fixed by copying only the agent namespace. Two control/reference repetitions matched original test fingerprints, then both Codex and CC workers passed installation, pytest startup and source audits. Added a repeatable no-model qualification command and ran it successfully. This addresses local source exposure, not unrestricted network retrieval.

Forty-nine local tests passed for verifier/environment tooling. See [report](reports/verifier-environment-results-2026-10-06.md). Retired task trials have been removed by user request.

---

# Native skill invocation correction — 2026-10-06

Corrected both adapters to install the frozen skill under each agent's native user skill directory and prefix the prompt with `$agent-led-swe` (Codex) or `/agent-led-swe` (CC). Baselines keep the same CLI mode without the target installed. Native activation is checked from Codex session injection or CC discovery and command replay; ordinary file reads are insufficient. Native evidence is hashed and verified before review.

Forty-seven local tests passed. Real CLI/mock API checks for local Codex, Docker Codex and Docker CC confirmed full native instruction expansion before the first model request and target absence in baselines. Two bounded real-model smoke calls confirmed native activation and unchanged workspaces; the Codex final-answer check needed manual correction because it concatenated progress commentary with the final message. Original results were preserved. [Detailed report](reports/native-skill-invocation-2026-10-06.md) records evidence and limitations.

All earlier path-prompt evaluations are document-reading mode, not native-skill acceptance evidence. No benchmark was rerun and no skill-content change or merge occurred in this correction.

---

# Isolated requirements-coverage candidate — 2026-10-05

Froze baseline 1c65c00 and created an independent candidate worktree. Tooling commit 462e38a supports explicit target/reference paths, immutable skill snapshots, three-arm execution/review and snapshot-integrity checks. Candidate 8b706d2 changes four skill documents only; local tests (44), package checks and skill metadata checks passed. Main remains unchanged and the candidate is not merged.

Packaging candidate timed out at 300 seconds. Current was stopped at about 289 seconds after traces showed both started agents reading alternate installed implementations; baseline was not launched. A read-only audit confirmed packaging 26.2 and setuptools-vendored 24.2 source in both the dependency and worker images. No hidden reference patch was mounted, but source masking did not remove these alternative implementations. Packaging outcomes remain unknown pending environment eligibility review; no additional judge calls or retries were made. [Full report](reports/requirements-coverage-results-2026-10-05.md) preserves raw evidence, interruption details and recommendations.

---

# Live DeepSeek and Claude container connection — 2026-10-05

After the user supplied the local credential, the official Anthropic Messages probe passed a two-request tool-call/tool-result exchange. A single real Claude Code 2.1.278 Docker run with DeepSeek Flash/high then read a random fixture marker and returned it exactly in 2.318 seconds, within a 120-second limit. Native completion, actual Read evidence, requested model, discovery isolation and unchanged workspace checks passed; the container was removed. Normalized usage was 2680 input tokens (1152 cached) and 70 output tokens, with cost unknown.

The [adapter report](reports/agent-adapters-2026-10-05.md#真实服务连通验证) contains evidence locations. No target skill or SWE benchmark was evaluated in this connection check; real baseline/skill comparisons remain pending. Credentials were not printed or copied to evidence.

---

# Swappable agent adapters and DeepSeek configuration — 2026-10-05

Extracted native Codex launch/context handling and added a Claude Code Docker adapter, independent model profiles, pinned container CLI versions and an ignored local credential placeholder. Provider requests remain inside the agent; the separate connection probe is only a bounded synthetic API check. The judge remains Codex. User requested an empty credential placeholder, so no DeepSeek call or real SWE model pair was run.

Real CC 2.1.278 container checks against a local synthetic API passed for baseline and skill, including native streaming events, Read/tool-result exchange, model identifiers and discovery checks. Codex's credential-free native context regression also passed. The [adapter report](reports/agent-adapters-2026-10-05.md) records scope, evidence and retained failures; these results do not establish model or skill effectiveness.

---

# Unified task/execution/evaluation flow — 2026-10-05

Implemented the approved [shared protocol](protocol.md): benchmark patch semantics and frozen task material are owned by task adapters; the paired runner consumes normalized workspaces/environments; functional validation and independent qualitative review consume immutable execution artifacts. Existing behavior cases remain supported. Preflight and formal functional checks now share the same Docker check function.

Packaging is enabled through the unified CLI. Their dependency images were extended with Codex 0.160.0; credential-free, no-model checks confirmed the CLI/context entrypoints and tested absence of evaluator materials in the worker. Docker is the real-task execution boundary; the CLI uses full access inside that container without elevated capabilities or a host Docker socket. Existing authentication is only mounted read-only for actual model runs, not copied to images/evidence. No authenticated model trial was performed in this revision.

Thirty-one local checks passed. Actual Docker integration checks distinguished unchanged from reference source for both tasks, restored trusted tests over a synthetic submitted test replacement, preserved a new handoff document, and left submitted snapshots unchanged. Qualitative passes cannot erase functional failures; functional-only evaluation leaves missing qualitative judgments unknown. Incomplete real-task execution does not become a functional failure merely because starting code still lacks the requested feature. [Report and evidence locations](reports/unified-evaluation-2026-10-05.md) distinguish these checks from skill-effect trials.

Historical reports were preserved. SDK remains parked, DSPy remains unqualified, and real SWE model comparisons have not started.

---

# Real SWE candidate preflight — 2026-10-05

Update after user decision: SDK was parked and DSPy-8139 was selected for a separate preflight. Its target tests distinguish control and reference, but the full local regression matrix is not stable: a mock-service startup exceeded the original 10-second limit, and a later reference repeat failed an async timing assertion. Public image/PDF downloads required bridge networking. Proxy dependencies were completed, and a packaged LiteLLM cost map was tried without eliminating setup errors. All attempts were retained; further repeats were stopped, and no test threshold or source requirement was changed. Expected xfails are now distinguished from ordinary skips, and repetition checks include per-test outcome fingerprints. Twenty-six local tests passed before the final documentation update; the retained SWE candidates are packaging and DSPy, with only packaging passing preflight.

Prepared frozen task records and source archives for packaging metadata Level 1 (FeatureBench fast), and Agents SDK-842 (community FeatBench-Verified). Added a bounded, non-LLM Docker preflight adapter that separates learner, control and reference code and preserves FeatureBench's opposite patch semantics. The local adaptation uses ARM64 Python containers and uv-managed dependencies, records image/package versions, disables network during tests, and removes test containers after use.

The retained packaging and SDK cases completed two control/reference repetitions: 16 test commands. Control consistently exposed target failures; references and all selected regression tests passed without collection errors or skips. These are local environment/contract checks, not official image results or skill trials. [Report](reports/swe-preflight-2026-10-05.md) and [structured evidence](reports/swe-preflight-2026-10-05.json) retain counts, hashes, settings, failures during SDK preparation, and source locations.

The SDK task remains on hold: a separate mock-client probe confirmed that the reference implementation forwards dictionary entries with None values, contrary to the published task statement. Existing tests do not detect this discrepancy. No requirement, gold implementation or acceptance test was silently changed. The user subsequently chose the DSPy replacement; its results are recorded above.

Four new local regression tests cover fix/mask patch directions, learner/validator separation, SDK dependency selection, missing/failed XML, and incomplete or inconsistent run summaries. Real-repository Agent execution and integrated functional/qualitative scoring remain pending.

---

# First real paired pilot — 2026-10-05

[Pilot report](reports/pilot-2026-10-05.md) records two real D1 executions and two fresh read-only judges using Codex 0.160.0, gpt-6.1-sol/high, 180 seconds per call, without retries. All completed; both variants passed the frozen acceptance check and left the fixture unchanged. Baseline made no tool calls; the skill variant successfully read the target entrypoint and five relevant guides plus the fixture. Author inspection confirmed the independent judgments and observed access boundaries. This is a small development-case pilot, not evidence of general SWE gains.

Added per-invocation discovery checks. The inspected skip-host-discovery flag did not remove the local catalog; the adapter instead disables discovered skill paths through CLI overrides, disables extra guidance sources, and re-renders context before execution. All four calls passed. User config and installed skills were not edited. Receipts distinguish verified discovery from filesystem read isolation, and raw traces remain necessary for access review. The first pilot passed both checks; future trials are not pre-certified.

Twenty local tests passed, including rejection of unexpected inherited skill instructions and verification that discovered paths are disabled before launch. Both paired execution and independent review retained their inputs, logs, version hashes and judgments. Step 3 has now completed its initial real-pilot validation; real SWE cases, functional-validation adapters and human rubric calibration remain for the next stage.

---

# Paired execution and independent review infrastructure — 2026-10-05

Added [paired execution](run_evaluation.py), [independent review](evaluate_results.py) and shared runtime helpers. The runner freezes task inputs, acceptance, skill/rubric snapshots, helper and adapter hashes, settings, time limits and the planned trial matrix. Each variant/repetition uses a fresh workspace; raw logs and before/after artifacts remain outside it. Review uses fresh read-only Codex sessions and preserves per-check reasons/evidence alongside execution status, missing trials and available resource telemetry. No automatic retry, global installation or user configuration change was added.

Eighteen local tests passed in the locked uv environment. Eight new pipeline tests use local fake CLIs and the real skill-evaluator capture/trace helpers: a complete paired execution/review path, timeout and absent completion handling, exact judge checks with evidence, missing trials, modified artifacts/logs, invalid judge output, preserved launch failure, and invalid budgets. They prove infrastructure behavior only; the fake CLI does not prove Codex sandbox enforcement or model behavior. Package checks passed (31 Markdown files, 18 fragment links, 25 reachable resources); both new CLI help commands and `git diff --check` passed.

Step 3 is partially complete: the tools are implemented and locally checked, but no real model pair or independent model judgment was run. The adapter records baseline isolation as unknown because global/user/plugin discovery and inherited instructions have not been excluded. Summary conclusions therefore remain inconclusive about incremental value. Judges are independent, not guaranteed blind; visible traces may reveal the treatment. Tokens/cost have no enforced caps, missing cost remains null. Real SWE task/environment/functional-validation adapters remain for the next stage, after isolation verification and a small real-model pilot.

---

# Rubric alignment and case migration — 2026-10-05

Current runnable/planned cases and their historical target versions are indexed in [scenarios.md](scenarios.md). This log retains prior checks and outcomes; historical passes do not apply automatically to the current skill.

Aligned the [rubric](rubrics.md) with current guidance, including overall/module design and cross-process coordination. Shared task outcomes are distinguished from skill-specific execution diagnostics; the rubric introduces no new approval rules or fixed design depth. Qualitative calibration and real-task scoring remain pending.

Extracted seven existing runnable cases into `cases/behavior/*.json`, preserving their requests and fixture contents. [Migration hashes](case-migration-2026-10-05.json) were captured from the original inline definitions and verified after extraction. The loader rejects undefined cases, invalid input paths and absent acceptance criteria before execution. Case definitions and criteria stay outside the writable fixture; new runs save a case snapshot and pre-execution hashes. Historical result JSON and raw runs were retained without regrading.

Ten local tests passed through the locked uv environment: five package-link tests and five case/runner tests. These cover preserved inputs, rejection of undefined/malformed cases, grading-material separation, frozen case evidence and propagation of a synthetic capture failure. The latter uses stubs, not a model call. The runner's CLI help lists the seven supported cases. Package checks and `git diff --check` passed.

No new model behavior trials, baseline comparisons or independent grading were run. The legacy smoke runner still uses explicit skill loading and its existing single-case timeout. The next step is the planned comparison/evaluation flow, followed by real SWE task selection.

---

# Automatic Markdown fragment validation — 2026-10-05

`check_package.py` now validates local Markdown heading fragments, including same-file links, Unicode/percent-encoded titles and duplicate-heading suffixes, and excludes fenced examples. Five [checker regression tests](test_check_package.py) passed, including negative cases for removed and nonexistent sections. The package check passed for 31 Markdown files, 17 fragment links and 25 reachable resources through the locked uv environment. `git diff --check` passed. No model behavior trial was run. Test-status consolidation remains deferred to the planned test-system migration.

---

# uv test environment — 2026-10-05

Added a repository-local uv environment: Python 3.11 is selected by `.python-version`, PyYAML is declared in the dev dependency group, and `uv.lock` pins the resolved dependencies. `uv sync` created the environment with CPython 3.11.13 and PyYAML 6.0.3; a subsequent `uv sync --locked` passed. `.venv/` is ignored and excluded from package-document scans. Smoke capture subprocesses now use the runner's `sys.executable`.

README and test instructions use `uv run --locked`. CLI checks were executed through an interactive login zsh, matching the user's normal terminal initialization without hardcoded CLI paths. [Host receipt](host-discovery-uv-2026-10-05.json) records successful Codex CLI 0.160.0 and Claude Code 2.1.278 discovery. Missing executables are now described as unavailable on the current process PATH, rather than uninstalled.

Package checks, smoke-runner `--help`, helper compilation and dependency imports passed in the uv environment. An initial Git check outside the initialized shell selected the macOS launcher and encountered the Xcode-license prerequisite; rerunning Git checks inside the initialized terminal environment passed without changing global configuration. No model behavior trial was run for this environment change. Earlier receipts remain associated with their recorded environments and instruction snapshots.

---

# Overall consistency review — 2026-10-05

Reviewed the final entrypoint, both work-organization guides, six activity guides, three mechanisms, practice catalog, all thirteen templates, README and host metadata. This was an author review of the working tree, not an independent behavioral evaluation. [Instruction snapshot](document-review-snapshot-2026-10-05.json) records the reviewed content hashes.

| Relationship checked | Finding |
| --- | --- |
| Request → process → workflow | Work is grouped by requirement outcomes; workflow coordination is for related processes. Scoped the implementation guide's workflow dependency reference accordingly. |
| Lifecycle → activity guidance | Lifecycle retains the agreed development/delivery/maintenance scope; activities are selected for current needs. Replaced the entrypoint's shorthand “lifecycle activities” with “development activities”. |
| Human decisions → autonomous work | Existing agreements/delegation remain effective; required decisions block only dependent work. Clarified the entrypoint's waiting sentence to match the collaboration guide. |
| Requirements → design → implementation → verification | Guides identify the current basis, required outputs and return paths; overview/design completion is not feature completion. No unresolved cross-file conflict found in this review. |
| Mechanisms → templates | Templates support the defined document roles; important decisions, authoritative agreements and actual evidence have distinct records. Existing fields and optional document sizing are retained. |
| Local evidence → delivery → overall result | Unknown behavior is separated from observed failure; environment blockage is a cause. Partial-request, process and workflow conclusions use their respective scope. |
| Navigation and historical evidence | Live references use the current names. Earlier test snapshots and outcomes remain historical; they do not establish the final revision's behavior. |

Skill metadata validation and package checks passed: 31 Markdown files, 25 reachable reference/template resources. All 14 local fragment links in the active entrypoint/README/reference/template set passed. `git diff --check` passed; no active old filenames or superseded activity names were found in entrypoint, README, references, templates or host metadata. README now records completion of this review round.

No new design decision requiring human resolution was identified. Full behavioral validation remains outstanding: current runtime rules and templates have not been tested together on real development tasks, and the earlier overlong-plan observation is not declared fixed by document review. Test-infrastructure work remains at its recorded planning stage. Host discovery and external reference sources were not revalidated in this review.

---

# Implementation, verification and delivery revision — 2026-10-05

Updated three activity guides and the verification-record/delivery-checklist templates. Implementation follows design and dependency evidence with explicit return paths. Verification separates observed requirement failure from unknown behavior and records environment blockage as a cause; it covers agreed usage scenarios without introducing new acceptance requirements. Delivery reports artifacts, checks and remaining work at the promised scope, and maintenance returns to the appropriate process/design/requirements work. Templates retain their fields and clarify actual execution, evidence and scope. Content review, package links/reachability, local fragment checks and `git diff --check` passed. No behavioral trial was run; earlier receipts apply to their recorded instruction snapshots.

---

# Requirements and design revision — 2026-10-05

Updated Problem Framing, Requirements Analysis and Design guidance, plus requirements, architecture, module-design and interface-contract templates. Guidance now states use conditions, work/products, progression criteria and return paths. Design scope follows affected responsibilities, mechanisms and contracts; templates retain their existing sections and describe information needed by implementers and consumers. Shared authorization, decision, baseline and documentation rules are referenced. Removed the project-specific AgentInfra reminder. Content review, package links/reachability, local fragment checks and `git diff --check` passed. No behavioral trial was run; earlier results describe their recorded instruction snapshots.

---

# Documentation mechanism revision — 2026-10-05

Updated the documentation guide and project-index template. The guide now specifies proposal/agreement/implementation ownership, creation and update events, and concrete writing/deduplication rules. The index retains a goal overview, document entrypoints and pending matters; detailed progress stays in process/workflow plans. Existing document types, directory example, decision-log fragment target and historical evidence rules were preserved. Package structure/links/reachability, local fragment targets and `git diff --check` passed. No behavioral trial was run; reduced repetition in generated project documents remains to be evaluated rather than claimed from this edit. Earlier receipts apply to their recorded snapshots.

---

# Engineering baseline revision — 2026-10-05

Updated the baseline guide, practice catalog and baseline template. The guide distinguishes engineering conventions from requirements/design, defines implementation readiness, and separates implementation repair, scoped exceptions and shared rule changes. The catalog connects each existing reference to a project use and check; examples are identified as optional adaptations. The template retains its fields while requiring checkable rules, authoritative references and the work affected by unresolved choices. Package links/reachability, local fragment targets and `git diff --check` passed. Content review and static checks only; no behavioral or external-source revalidation was run for this revision. Earlier receipts describe their recorded snapshots.

---

# Human collaboration revision — 2026-10-05

Updated the collaboration guide with activity-specific decision topics and review materials, agreement-based agent discretion, and separate preparation/waiting/application steps. Decision templates retain their fields and link to the governing protocol, with scope and conditions clarified. Package links/reachability, local fragment targets and `git diff --check` passed. This revision received content review and static checks only; behavioral trials were not rerun. Earlier results below apply to their recorded instruction snapshots.

---

# Current validation — Process/workflow revision — 2026-10-05

Updated the two guides and both plan templates against the approved outlines. Renamed `implementation-plan.md` to `process-plan.md` and repaired live callers in SKILL.md, Design guidance and the documentation mechanism. Existing section fragment targets remain valid.

## Static checks and author review

- Skill metadata validation, package links/fences/reachability and `git diff --check`: passed.
- Package checker covered 29 Markdown files and 25 reachable reference/template resources.
- All five local fragment links in the active entrypoint/reference/template/README set resolved to headings.
- Python compilation of the extended smoke runner: passed.
- Reviewed the four documents for when to act, the basis for progression, required outputs, feedback paths and human decisions. The process guide now connects gaps to activities and plans; completion is tied to the process goal rather than the latest partial request. Workflow guidance checks output readiness and distinguishes implementation deviations from agreed contract changes. Templates separate planned coordination from actual progress.

## Behavioral development trials

[Results and instruction hashes](process-workflow-results-2026-10-05.json) record two fresh target-present trials with Codex CLI 0.160.0 and `gpt-6.1-sol / high`, one attempt per case and a 180-second timeout. Both completed with exit 0; target hashes match each other and the reviewed instruction files.

| Case | Functional result | Writing observation |
| --- | --- | --- |
| D13 — plan for a general recovery requirement | Requested plan created; original files unchanged. Includes clarification/design, dependencies, compatibility and verification; leaves human decisions open and distinguishes plan delivery from process completion. | The plan repeats authorization, unresolved semantics and non-completion across sections. Functional criteria passed, but concise artifact production still needs refinement. |
| D11 — coordination with existing work | No file changes. Reuses contract, advances ready work, waits for the specific integration output and requires overall evidence. | Response was concise; no material repetition noted. |

These are author-assessed development trials, not independent grading or a baseline comparison. No broad reliability or writing-quality guarantee follows from them. The D13 observation should inform the subsequent documentation-mechanism review; raw outputs are retained under ignored tests/runs. Earlier receipts below apply to their recorded snapshots.

---

# Current validation — v0.2.0 — 2026-10-04

Entrypoint update after the naming change: replaced SKILL.md with the user-approved Chinese draft, organized into purpose, task entry, work progression, cross-cutting mechanisms, and guidance/template navigation. Reviewed its links and rules against the existing references. Skill validation, package structure/links/reachability and `git diff --check` passed again. Behavioral trials and host discovery were not rerun for this entrypoint revision; the receipts below describe earlier snapshots.

Naming update after the trials: adopted the six user-confirmed activity names and renamed `delivery-and-evolution.md` to `delivery-and-maintenance.md`, updating live references. Guidance behavior was unchanged. Skill validation, package links/reachability and `git diff --check` passed again. The behavior results below identify the pre-rename instruction snapshot; they were not rerun for this naming-only edit.

The update organizes work by requirement-level processes, guides their development activities with the lifecycle, and coordinates related processes through workflows. Reviewed the entrypoint, process/workflow guides, six activity guides, three mechanisms, and affected templates against the accepted update plan. This is author review.

## Executed checks for this version

- `skill-creator/scripts/quick_validate.py`: passed.
- `tests/check_package.py`: passed metadata, Markdown links/fences, and reference/template reachability.
- Python compilation of test helpers and `git diff --check`: passed.
- Codex CLI 0.160.0 and Claude Code 2.1.278 actual discovery: passed in temporary projects, with no global installation. See [host receipt](host-discovery-v0.2.0.json).
- Four target-present behavior trials: all completed; author assessment and fixture checks found all four met their case criteria. See [results, responses and content hashes](smoke-results-v0.2.0.json).

| Case | Observed result |
| --- | --- |
| D10 — general cross-module goal | Kept recovery as one coherent change; surfaced requirements/design questions without settling semantics or writing files. |
| D11 — related goals with partial work | Reused the accepted contract, identified activity-specific dependencies, allowed ready work, and required real integration for overall acceptance. |
| D12 — upstream change and failed integration | Rejected overall completion; distinguished the unapproved contract deviation, reusable evidence, and affected revalidation. No file changes. |
| D4 — changed human decision | Preserved the old log byte prefix, appended an attributed superseding decision, and updated current design only. |

Each trial used a fresh temporary fixture and explicit skill entrypoint with `gpt-6.1-sol / high`, workspace-write sandbox, ephemeral execution and multi-agent tools disabled. Each had a 180-second timeout and completed on its first attempt. Target hashes matched across all four runs and the instruction files at the time of those trials. Discussion fixtures were unchanged; D4 changed only its two authorized documents.

These are development smoke cases with author assessment, not independent grading or evidence of improvement over a baseline. Natural routing, Claude behavior and broad project performance remain untested. D1–D9 results from the previous version do not automatically apply to this version; only D4 was rerun here. Earlier evidence follows unchanged.

---

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

## Runtime repair verification — 2026-10-03

The original failure above is retained as a historical attempt. The model name is valid: official documentation supports `gpt-6.1-sol`, and the Codex CLI 0.159.1 release added it to the bundled catalog. The selected 0.154.0 client predates that change. See [Models](https://learn.chatgpt.com/docs/models) and [Codex changelog](https://learn.chatgpt.com/docs/changelog).

The user's NVM CLI was updated to **0.160.0**. The duplicate npm installation under `/opt/homebrew` was removed; interactive and non-interactive shell resolution now selects the NVM client. The OpenAI OAuth login and persistent model configuration were preserved.

`tests/run_smoke.py` now accepts `--codex-bin`, records the exact entrypoint and resolved path, disables multi-agent tools for these single-agent cases, and propagates capture failure/timeout status. A synthetic failing-CLI check confirmed failure propagation without an LLM call.

D1 was rerun once with the explicit NVM CLI, the same **gpt-6.1-sol / high** settings, a fresh disposable fixture, `--ephemeral`, and `agents.enabled=false`. The provider accepted the request; Codex read the target entrypoint and relevant references, completed the discussion, and emitted `turn.completed`. The process exited **0** after approximately **61 seconds**, with no timeout. Before/after fixture hashes match; no subagent dispatch was observed and no persistent session file was created.

New raw evidence: ignored `tests/runs/D1-20261003T061523476183Z/`. The committed `runtime_repair` section in [smoke-results.json](smoke-results.json) records this separate attempt without rewriting the earlier model rejection. This establishes that the original CLI/model execution blockage is resolved for D1. It is not an uncontaminated baseline or an independent behavioral grade.

D4 and D7 were not rerun in this repair. Reproduce a selected case with the intended CLI explicitly:

```sh
python tests/run_smoke.py D1 --codex-bin /path/to/nvm/bin/codex
```

## Author review

Reviewed against the agreed design: six activities, three cross-phase mechanisms, discussion/implementation scope, reuse of prior authorization, engineering practice selection, append-only decision attribution, work-unit records, pre-implementation delivery criteria, and separate behavior/spec/standards checks. The review index in [README](../README.md#首轮重点-review) points to the consequential design choices for the user.

This is author review, not independent model grading. The static checks do not prove the instructions cause the intended behavior.

## Remaining validation

- Run D4 and D7 if completing the original three-case behavior plan; preserve the original failed D1 and successful repair retry as separate attempts.
- Exercise the remaining development scenarios as warranted by first use or further changes.
- Natural selection/routing, Claude behavior, uncontaminated baseline comparison and measured quality improvement remain untested.
- Remote publication, marketplace registration and deployment are separate from this local package validation.
