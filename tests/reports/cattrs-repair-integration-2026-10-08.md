# D 场景：已有 cattrs 成果的接续修复

从上一轮真实成果继续修复，观察局部修改、已有文档更新与回归验证。任务定义沿用[四场景方案](multi-scenario-design-2026-10-08.md#5-d接续-cattrs-的真实待修复成果)。本轮只收集证据，不修改 skill；所有场景完成后再统一归因。

## 起始状态与任务

两组均从 `cattrs-user-revision-20261008/candidate/after` 启动新会话。来源文件清单哈希为 `73293608b5759f45971b62e835edd6dab5dd6feae11f26dd1b35513a5ed25a1b`，与选题时记录一致。保留实现、自测及现有文档，包括需要同步修正的旧说明。

公共输入仅移除 `.pytest_cache`、`.hypothesis`、`.ruff_cache`、`.benchmarks` 缓存目录。原快照不改动；隐藏验收、参考修复和旧成绩不进入开发或用户工作区。

本轮要求：TypedDict 必需字段失败时 `value` 为 None；详细验证时，默认值使对象可构造也应在 `errors` 保留字段失败信息。第二条作为本轮明确要求，不伪装成此前无歧义的承诺。其他能力保留，不要求重做设计或补造历史记录。见[请求](../cases/collaboration/cattrs-repair/request.md)与[用户设定](../cases/collaboration/cattrs-repair/user.md)。

## 接入与预检

`cattrs_repair_task.py` 冻结接续输入，复用 `cattrs_task.py` 的独立验收。参考修复仅用于确认验收链路，保存在私有材料中；不改原测试断言。

| 检查 | 结果 |
| --- | --- |
| 起始成果 | 基础 7/7，新增 67/69；两个失败及全部结果指纹与历史记录一致 |
| 私有修复样本 | 基础 7/7，新增 69/69 |
| 本地回归 | 111 项通过，包含保留旧文档、自测、移除缓存和来源变化拒绝检查 |
| 原生链路 | 实际任务输入 + 真实 CC CLI + 模拟 API，两组均通过两轮接续、skill 调用与只读用户检查；没有真实模型调用 |

使用现有离线依赖镜像 `sha256:109267215d8f1561410b43332314754e0801e72a75f347c43f3e0c61412a7da3`。预检材料保存在 `/Users/liyao/agent-led-swe/tests/runs/cattrs-repair-integration-20261008`。

## 对照设置

- current：已接受 skill `1c65c00`；candidate：内容 `42fc6f9`，均冻结实际文件。
- Claude Code 2.1.278 + DeepSeek Flash high；独立原生模拟用户使用同模型与 high；单开发 Agent。
- 每组共享 3600 秒，无单轮或轮数限制；current 先运行，各一次，无自动重试。
- 独立 verifier 判断功能，用户接受单列；保存原生轨迹、各轮材料和最终文件，不自动调用 LLM judge。

这是已分析成果派生的开发集，不是新的榜单成绩或独立未见测试。完整 canonical 验收为 7+69 项，不等同于整个 cattrs 项目的全量回归。
