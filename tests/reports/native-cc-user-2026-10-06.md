# 模拟用户改为原生 Claude Code

**已用独立 Claude Code 2.1.278 + DeepSeek Flash 替换自写用户工具循环。真实的需求回答、文件审阅和会话接续已通过检查；尚未运行完整 cattrs 开发对照。** 正式 skill 未修改。

## 改了什么

```text
开发 Agent（Codex 或 CC） ↔ 对话转发与记录 ↔ 用户 CC + DeepSeek
                                              ↓
                                  只读的初始源码／当前产物快照
```

- 用户使用 CC 原生工具、session resume 和 `--json-schema`。角色与固定需求通过系统提示提供；收到新对话后，由 CC 自己决定是否读取文件。
- `simulated_user.py` 只负责启动独立实例、更新快照、传递对话和检查原生结果。删除自写 HTTP transport、文件工具、tool choice 循环及调用格式修补。
- 用户实例不安装目标 skill，不挂载参考实现或 verifier。工具限定为原生读取能力与结构化输出；项目快照通过 Docker 只读挂载，实际写入探测返回只读文件系统错误。
- 配对入口的 solver 与用户模型配置分开，用户固定使用 CC；复用现有 Anthropic Messages 网关，真实凭据仍只在网关中。Pro 配置也改为 CC 接入，但本轮真实检查只使用 Flash。

普通需求问答无需先读文件。设计认可仍返回 `accepted=false`；只有接受最终交付才能为 true，而且程序要求本轮有成功的当前产物读取。这个检查不替代功能 verifier，也不能证明用户审阅已经充分。

## 验证结果

| 检查 | 结果 |
| --- | --- |
| 真实需求澄清 | 返回完整接口与失败语义，以及委托给开发 Agent 的内部选择；获得原生 `structured_output`，结束标志为 false。 |
| 真实只读审阅 | 在同一 session 中读取新加入的草案，指出“缺失字段算成功”和“必填字段失败仍返回残缺对象”两处冲突；没有将设计审阅当作最终交付。 |
| 双宿主模拟联测 | Codex／CC solver 各 baseline／skill，共四组通过。两侧都运行真实 CLI，模型 API 为模拟响应；用户成功读快照、回复并接续。 |
| 本地回归 | 85 项通过。旧 HTTP／自定义工具专用测试随实现移除，新增原生工具边界、结构化结果、session、模型和验收条件检查。 |
| 配对准备 | 新资格记录通过入口匹配，已用 `--prepare-only` 冻结试跑配置，没有调用 solver 模型。 |

第一次启动在自写只读探测命令处失败（字符串引号遗漏，未调用模型）；第二次 CC 已生成正确格式，但检查器把随 CLI 附带的内置命令目录误判为外部 skills。修正探测并复用既有内置目录允许列表后，第三次两轮检查通过。目标 skill、自定义插件和 MCP 仍不允许出现在用户实例。

本次更换了 runtime、输出协议和相应角色说明；这是接入验证，不是与旧直连 API 的严格性能对照。两轮通过也不代表所有模拟用户行为都可靠，完整开发试跑仍需审阅其回应内容。

## 当前入口与边界

- [用户适配器](../simulated_user.py)、[真实小检查](../check_simulated_user.py)、[多轮配对入口](../run_collaboration.py)。
- 使用[原生 CC + Flash 资格](qualifications/cattrs-user-cc-flash.json)，范围仅支持首次开发 pilot。旧 Flash／Pro 直连 API 的失败资格继续保留，不能用于当前配置。
- 用户限制改为原生 `--max-turns`、每次回应时长与最大回应次数；不再声称自行统计或硬限制 CC 内部 API 调用数。原生 usage 保存但不直接累加为会话费用。

真实证据：`/Users/liyao/agent-led-swe/tests/runs/native-cc-user-20261006-v3/`。两种宿主联测：`native-cc-user-20261006-mock-cc/`、`native-cc-user-20261006-mock-codex/`。已准备配置：`native-cc-user-20261006-prepared/`（均在主工作区 `tests/runs/` 下，未挂载给 solver）。
