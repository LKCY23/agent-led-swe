# C 场景：空项目 gRPC 服务运行结果

两版均完成两轮协作并获得用户接受；原验收 7/7、交付时真实读写和独立重启后的读写均通过。本记录只保存事实与证据入口，不评价文档数量或归因 skill 差异。

## 配置与结果

沿用 [C 接入计划](grpc-integration-2026-10-08.md)。工具提交 `571a415`；current 为已接受 skill `1c65c00`，candidate 内容为 `42fc6f9`，实际文件已冻结。Claude Code 2.1.278 + DeepSeek Flash high，单开发 Agent，独立原生用户；每组共享 3600 秒，current 先运行，各一次，无重试。

| 项目 | current | candidate |
| --- | --- | --- |
| 开发回合 / 用户回复 | 2 / 2 | 2 / 2 |
| 用户接受 | 是 | 是 |
| 原 7 项验收 | 7/7 | 7/7 |
| 开发容器停止前真实读写 | 通过 | 通过 |
| 最终产物独立启动及真实读写 | 通过 | 通过 |
| 原生调用、隔离、单开发 Agent | 有效 | 有效 |
| 开发 Agent capture 时间 | 69.61 秒 | 280.59 秒 |

验收无失败、错误或跳过，测试身份与结果指纹匹配参考实现，未改动提交成果。时间不含环境、用户审阅和独立验收；不根据单次耗时判断版本优劣。服务在证据采集后随测试容器停止，不继续占用端口。

## 文档清单与证据

current 生成 `README.md` 和 `docs/verification.md`。candidate 生成 `README.md`、`docs/README.md`、requirements、engineering baseline、design overview/contracts、decisions/log，以及本次 change 的 plan、delivery、verification，共 10 个 Markdown 文件。这里只列实际文件；是否必要、何时形成、是否准确精炼，留待统一审阅。

运行目录：`/Users/liyao/agent-led-swe/tests/runs/grpc-versions-20261008`。

- `plan.json`、`task-inputs/`、`scenario/`、冻结的两版 skill：配置、来源和哈希。
- `results.json`、`execution-summary.json`：运行状态、计数和文档列表。
- `<variant>/conversation/`、`<variant>/user/`：完整原生开发与用户轨迹，每轮材料及回复。
- `<variant>/before/`、`<variant>/after/`：空项目起点与最终产物。
- `<variant>/live-service/`：停止前真实 RPC 结果；未替 Agent 启动服务。
- `<variant>/verifier/`、`<variant>/verifier-result.json`：独立重启日志、原测试 JUnit、补充 RPC 与合并结果。

结果只支持所测的小型服务范围；不代表完整并发语义、缺失键行为或文档机制均已通过审阅。
