# 首轮真实任务对照：smolagents 与 xarray

本轮完成 4 次执行：smolagents 的 baseline 失败、skill 通过；xarray 两组均失败。Skill 组在两题均通过可信回归，但没有证据表明整套开发流程已被稳定执行。每题每组只有一次，不能据此断言 skill 有稳定收益。

## 配置与执行

- 被测 skill：主仓库 `/Users/liyao/agent-led-swe`，接受版本 `1c65c0016a59cce025e31960cc106ea577a80c02`；未使用测试 worktree 中继承的候选 skill。
- 测试工具：独立 worktree 的 `5ec80d61a43ad5075fd1cf4b6348f909fbe2f60f`；本轮未修改工具、skill、提示词或验收标准。
- Claude Code 2.1.278 + `deepseek-flash`，high；每次最多 1,800 秒。两个任务依次执行，各 baseline → skill，一次执行，无重试，0 次 LLM judge。
- Skill 组原生安装并以 `/agent-led-swe` 调用；baseline 不安装目标 skill。四次均正常结束，原生调用／目标缺席、模型与网络检查通过，两组初始文件一致。
- 完整配置与历史：运行目录（`/Users/liyao/agent-led-swe/tests/runs/paired-pilot-20261006`）、冻结计划（`/Users/liyao/agent-led-swe/tests/runs/paired-pilot-20261006/round-plan.json`）。每个 pair 保留实际配置、版本哈希、原始事件、用量、前后文件快照和独立 verifier 记录。

## 功能结果：只由 verifier 决定

| 任务 | 组别 | 新增功能测试 | 可信回归测试 | 任务结果 | 执行耗时 |
| --- | --- | --- | --- | --- | --- |
| smolagents | baseline | 7 通过 | 667 通过、1 失败、2 skip | fail | 9 分 05 秒 |
| smolagents | skill | 7 通过 | 668 通过、2 skip | pass | 7 分 48 秒 |
| xarray | baseline | 7 通过、4 失败 | 12,300 通过、1 失败、290 skip、26 xfail | fail | 10 分 24 秒 |
| xarray | skill | 7 通过、4 失败 | 12,301 通过、290 skip、26 xfail | fail | 11 分 17 秒 |

Skip／xfail 是资格预检中已冻结的原始条件分支，单独列出，不算通过。耗时为 Agent 执行时间，不含准备与独立验收。

原始成绩：smolagents summary（`/Users/liyao/agent-led-swe/tests/runs/paired-pilot-20261006/pair-smolagents-20261006T053316642648Z/verification-20261006T055104469057Z/summary.json`）、xarray summary（`/Users/liyao/agent-led-swe/tests/runs/paired-pilot-20261006/pair-xarray-20261006T055159711194Z/verification-20261006T061400364727Z/summary.json`）。Verifier 命令返回非零是提交存在失败，不是执行器崩溃。

### 失败原因及解释边界

- **smolagents baseline**：`test_end_code_appending` 失败。实现改为 XML 结束标签，同时更改了公开测试；独立 verifier 恢复可信测试后，发现旧 `<end_code>` 输出行为不再保留。Skill 组保留旧格式兼容路径。证据：回归日志（`/Users/liyao/agent-led-swe/tests/runs/paired-pilot-20261006/pair-smolagents-20261006T053316642648Z/verification-20261006T055104469057Z/verify-1/functional/run/PASS_TO_PASS/stdout.log:50`）。这是本次可观察的兼容性差异，尚不能证明由 skill 导致。
- **xarray 两组**：4 项新增测试都在调用 `groupby({变量名: Grouper})` 时失败；两组实现了关键字形式，却没有支持位置参数字典。证据：skill 新增测试日志（`/Users/liyao/agent-led-swe/tests/runs/paired-pilot-20261006/pair-xarray-20261006T055159711194Z/verification-20261006T061400364727Z/verify-2/functional/run/FAIL_TO_PASS/stdout.log`）。但公开任务主要要求关键字映射，已有设计也以该形式举例，未明确要求这一位置参数形式。因此原始 fail 保留，但不能把四项失败直接解释为 skill 遗漏了明确需求。资格预检能证明参考实现通过，不能证明每个验收要求都已在任务中说清楚。
- **xarray baseline**：另有 `test_consolidate_slices` 失败，原因是把返回值由 list 改为 tuple；skill 组保留了该 helper 的行为。任务要求 group indices 使用 tuple，但没有精确约束哪些内部 helper 需要变化，这也限制了该差异的归因。证据：回归日志（`/Users/liyao/agent-led-swe/tests/runs/paired-pilot-20261006/pair-xarray-20261006T055159711194Z/verification-20261006T061400364727Z/verify-1/functional/run/PASS_TO_PASS/stdout.log`）。

## 流程与文档观察：不参与判分

### 原生加载成功，配套指导未被读取

两个 skill 执行均有原生调用证据，但工具轨迹没有读取 `references/` 或模板的记录。原生调用入口并不保证 Process、Design、验证与文档机制都会被使用。

两次均完成代码后才写实现／迁移记录，没有观察到新建并持续维护的需求覆盖或实施记录。反证是：xarray 已有设计，两组均先阅读并复用；没有理由要求重写已有设计，也不能用缺少指定文件名判失败。

**待验证假设**：当前导航与推进规则未能稳定促使模型选择必要指导、检查实现前提。下一候选可聚焦“按当前工作读必要指导 → 补齐实质缺口 → 开始实现”，保持轻量，不强制完整文档套件。

### 有文档，但不是 skill 独有收益

Smolagents skill 新增 迁移记录（`/Users/liyao/agent-led-swe/tests/runs/paired-pilot-20261006/pair-smolagents-20261006T053316642648Z/smolagents-1-skill/after/XML_CODE_TAGS_MIGRATION.md`），baseline 没有新增过程记录。Xarray 两组都在现有 `design_notes/` 中补了实现记录：baseline（`/Users/liyao/agent-led-swe/tests/runs/paired-pilot-20261006/pair-xarray-20261006T055159711194Z/xarray-1-baseline/after/design_notes/grouper_objects_public_api.md`）、skill（`/Users/liyao/agent-led-swe/tests/runs/paired-pilot-20261006/pair-xarray-20261006T055159711194Z/xarray-1-skill/after/design_notes/grouper_objects_implementation.md`）。两组共享提示词本身也要求必要的工作记录，这是归因时必须考虑的因素。

Smolagents skill 明知 zh/hi 文档仍有旧格式却保留未改，记录为限制并宣布完成；任务要求整体一致。Verifier 没有覆盖所有文档，因此 pass 不代表全部需求完成。下一候选应更明确地区分“任务已满足”与“主动缩小范围后仍有未完成项”，而不是仅要求写交付说明。

### 记录仍会混入未经核实的信息

Xarray 两组写入了没有本地证据的 PR 编号：baseline 为 `9264`，skill 为 `9070`；初始源码中均无该编号，也未成功联网核实。Issue `6610` 则来自已有设计文档，不能一起称为猜测。

证据为两组 `doc/whats-new.rst` 的前后快照和编辑事件。这说明 skill 尚未稳定约束“记录只陈述已确认事实”。改进应要求明确保留未知信息，而不是补写看似完整的编号。

## 环境与测量边界

两组 baseline 都尝试 `pip download` 获取外部版本，实际因网络不可达失败；skill 组也尝试搜索容器里的其他实现副本，返回未显示取得目标项目的外部实现。网络审计通过，未观察到成功下载或副本泄露。尝试本身偏离了任务的输入范围约束，应作为行为观察保留，不能把自动 `comparison_eligible=true` 理解为所有行为都符合约定。

本轮仍无法排除模型已有训练知识，也不能据此宣称数据完全未被模型见过。两题是开发试跑样例；后续若据此优化，就继续按开发／回归样例处理。

用量如下，来自 CLI 原始遥测；input 包含 cache-read，不能再与缓存列相加。CLI 对第三方模型报告的 cost basis 为 unknown，因此不把其美元数字当成实际账单。

| 任务／组别 | input tokens | 其中缓存输入 | output tokens |
| --- | ---: | ---: | ---: |
| smolagents baseline | 12,238,606 | 12,139,776 | 82,300 |
| smolagents skill | 10,163,912 | 10,064,256 | 77,047 |
| xarray baseline | 8,906,630 | 8,832,256 | 66,917 |
| xarray skill | 14,955,321 | 14,860,672 | 81,334 |

## 建议下一步

1. 先审阅 xarray 的公开任务与验收接口要求是否一致，决定它是否适合继续作效果样例。保留本轮原始成绩；若调整任务，另建版本，不事后修改本轮判据。
2. 再设计一个小候选：让必要指导真正进入执行、交付前对照需求检查剩余项、记录坚持证据。继续在独立 worktree 优化，与接受版本配对比较。
3. NodeBB／Navidrome 尚未跑模型。本轮不自动追加，不因一个有利结果就接受候选或替换主版本。

分析用的工具事件索引保存在 analysis 目录（`/Users/liyao/agent-led-swe/tests/runs/paired-pilot-20261006/analysis`），各条带原始 stdout 行号；它们是阅读辅助，不替代原始事件。未调用 LLM judge，未修改原始判分。测试容器与专属网络已清理，主仓库 skill 未改。
