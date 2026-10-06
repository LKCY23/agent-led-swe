# 统一评测机制：保留的通用验证

任务适配器统一工作区、环境、来源与可信验证材料；FeatureBench 遮蔽和修复型来源的补丁方向在适配器内处理。提交包含新文档和未跟踪文件，评分在独立副本恢复可信测试，不改写提交。

packaging 的无模型 Docker 检查确认：未实现产物目标测试失败、参考产物通过、回归通过。伪造提交中的测试不能覆盖可信测试；新增 handoff 文档保留，提交哈希不变。

现存证据在 `tests/runs/unified-validation-20261005-v2/packaging/` 及其 `results.json`；worker 检查在 `tests/runs/unified-pipeline-20261005/packaging-worker-check/`。已退出任务的专属目录与报告已清理。

这些是测试框架检查，不是 skill 效果。当前流程已将模型 judge 从自动评价中移除，任务成绩仅由 verifier 决定；实现以 [统一协议](../protocol.md)为准。
