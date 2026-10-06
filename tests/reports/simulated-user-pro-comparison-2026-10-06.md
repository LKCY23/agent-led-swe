# 模拟用户：Pro 小样本对照

后续已停用本报告中的自写 API 工具循环，改为[原生 CC 用户](native-cc-user-2026-10-06.md)。以下为历史检查记录。

**Pro 也未通过当前模拟用户协议检查，完整 skill 对照仍不启动。** 本轮只改变模型，不修改用户规则、工具或执行逻辑；不能据这一次结果判断两种模型的总体能力。

## 对照条件

使用 `8b31874` 中的适配器和用户规则，将模拟用户从 `deepseek-flash` 换成 `deepseek-v4-pro`。仍为非 thinking 模式，两个顺序问题：完整需求澄清；纠正一份有明显语义错误的设计。最多 10 次 API 调用，每条回应最多 5 次、120 秒，每次最多 4,096 生成 tokens，不自动重试。

运行入口为 [check_simulated_user.py](../check_simulated_user.py)。它在调用前冻结问题、公开工作区、用户规则、需求和工具代码；只检查协议完成与结束标志，回复内容另行审阅，不自动成为资格通过记录。

已逐字段核对 Pro 与之前 Flash v6 的第一个 API 请求：**除 model 外完全相同**。工作区来自同一个冻结源码归档。后续上下文会随各模型的回答和工具调用分化，不声称后续请求逐字相同。

## 实际结果

Pro 在第一条需求澄清中调用了 5 次 API，尚未给出可转发的用户回复，第二个设计问题没有执行。

| 调用 | 实际行为 |
| --- | --- |
| 1 | 列出文件。 |
| 2 | 读取 `converters.py` 与顶层入口。 |
| 3、4 | 用 `offset` 参数调用 `read_file`；该工具定义的是 `start`，两次均返回参数错误。 |
| 5 | 当前请求只提供 `respond_to_agent`，并指定调用它，但模型仍调用 `read_file`。程序拒绝执行并停止。 |

原始 usage 合计 20,019 prompt tokens、353 completion tokens，费用未核对。全部请求、响应、工具结果和错误保留。没有忽略错误继续评测，也没有改动目标 skill。

## 对下一步的影响

这次结果没有支持“换 Pro 就能解决”的预期。应优先排查当前接入：必选工具是否诱导了不必要的读取、工具参数是否清晰一致，以及服务端是否按声明的工具列表和 `tool_choice` 生成响应。模型能力、提示词和 API 兼容性的影响还没有被分离，不能直接归因给其中一个。

建议下一步先做只包含一个回复工具的最小协议检查，核实工具名称、参数和结束语义；通过后再加入文件读取与多轮历史。不要继续扩大完整开发试跑。

[Pro 资格记录](qualifications/cattrs-user-pro.json)为 `qualified=false`；[Flash 资格记录](qualifications/cattrs-user-flash.json)也保持失败。证据位于 `/Users/liyao/agent-led-swe/tests/runs/cattrs-user-pro-20261006/`，其中 `comparison.json` 保存同条件核对，`result.json` 保存本次终止结果。
