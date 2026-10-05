# Verifier 解耦与执行环境修复计划

从原生接入提交 `d608a2a` 创建独立 worktree：`/Users/liyao/agent-led-swe-worktrees/verifier-and-environment-20261006`，分支 `fix/verifier-and-environment-20261006`。不修改 skill 内容，不合并主工作区，不覆盖旧结果。

本轮交付：
1. 测试只调用任务 verifier；执行状态、实验有效性和任务结果分开。历史分析独立进行，不建设新的自动 LLM 分析系统。
2. packaging 使用独立精简执行镜像；完整 verifier 镜像保留。清理本地实现副本与缓存，重新运行 control/reference 检查，再审计实际 Codex／CC worker。
3. 用 pytest 完成一轮原生 baseline／skill 对照，验证采集、原生调用和 verifier-only 流程。

验证预算：本地回归不调用模型；packaging 两轮 control/reference，各含目标与回归测试，共 8 次固定测试命令。实际 worker 各做一次无模型工具／来源检查，基础设施失败保留并修复后使用新目录。原生 pytest 对照固定 CC 2.1.278 + DeepSeek Flash/high、当前基准 skill `/Users/liyao/agent-led-swe`，每组一次、300 秒上限；最多 2 次 Agent 调用、0 次 judge 调用，不自动追加尝试。

Verifier 沿用原始测试与既有本地适配，不更改测试或预期结果指纹。结果仅支持当前任务与配置，不直接推断 skill 增益。原生调用或环境检查异常会单独记录，不以此替 verifier 给代码判失败。

来源审计处理已发现的本地安装、vendored、wheel／缓存副本；不宣称封锁全部网络来源。若清理破坏必要工具或不能排除已知副本，packaging 继续停用，使用合格任务推进。
