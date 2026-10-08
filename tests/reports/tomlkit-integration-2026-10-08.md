# A 场景：TOMLKit 接入与测试计划

本轮运行 A 的 current / candidate 对照，只保存执行、功能验收和文档证据。各场景完成后再统一归因与优化；不修改被测 skill。

## 场景与输入

A 是成熟仓库中的普通功能开发。采用[四场景方案](multi-scenario-design-2026-10-08.md#2-atomlkit-表结构转换)中的请求：交付四种表结构转换、必要测试与使用说明，沿用已有规范。不增加 B 的持续协作记录要求，也不限制必要的设计与记录。

- SWE-Interact：`b32f98c3b8f76ca65e84341d1f30e5af7135f85d`，任务 `deepswe_tomlkit-toml-table-converters`。
- TOMLKit：`dd05eebc8ed9e30fc6c223088a5a450cb54c1cab`；测试数据子模块 toml-test：`08ed8697864548b3cdb4b8decbf496bef47e1c82`。公共源码包含该固定子模块，不包含上游 Git 历史。
- [初始请求](../cases/collaboration/tomlkit/request.md)与[用户设定](../cases/collaboration/tomlkit/user.md)随运行冻结。模拟用户得到完整原始要求和只读成果，自主回答，不接触隐藏测试、参考补丁或 skill。
- `tomlkit_task.py` 独立保存公共输入、私有要求、参考补丁与验收材料。验收在成果副本上恢复可信测试与测试配置，执行原 `test.sh base/new`；不使用原 benchmark 的五阶段 Git 操作包装，不修改断言。

## 环境与预检

Python 3.12 的依赖镜像仅包含工具与依赖，项目在运行目录离线 editable 安装。开发依赖按项目 `poetry.lock` 版本固定，另提供固定版本的构建后端与仓库 lint 工具；不安装 Poetry 本体，避免其 TOMLKit 依赖形成另一个实现副本。pytest、Ruff、mypy、Sphinx 等可直接调用；不代表已经验证其他 Python 版本或全部 CI。

镜像：`sha256:78a1d07a4531529646c4742f74a21ab7527ad1dc8ab7df12d7e59f1a6e396701`。未挂载源码时 `find_spec('tomlkit')` 为 None；验收时导入路径为 `/testbed/tomlkit/__init__.py`。执行环境禁止公网访问，模型请求经既有网关转发。

| 检查 | 结果 |
| --- | --- |
| 起始代码 | 原 base 964/964；新增 suite 因缺少 `tomlkit.convert` 无法收集，符合预期 |
| 参考实现 | 原 base 964/964；新增 suite 60/60；无跳过或错误 |
| 原生产线检查 | 真实 CC CLI + 模拟 API，baseline / skill 两组均通过；含两轮接续、skill 调用和只读用户 |
| 本地回归 | 109 项通过；包结构与链接检查通过 |

原 base 命令保留对 toml-test 目录、formatter、merge 和新增 convert 文件的排除；其中固定源码没有 formatter/merge 文件，`test_toml_tests.py` 仍会读取准备好的子模块数据。记录实际命令和计数，不将通过测试等同于所有语义得到完整覆盖。

材料目录：`/Users/liyao/agent-led-swe/tests/runs/tomlkit-integration-20261008`，包含归档、镜像构建日志、`inputs/`、`preflight/`、`native-probe/` 和本地测试日志。上述检查没有调用真实模型。

## 两版实跑

| 项目 | 设置 |
| --- | --- |
| skill | current：已接受 1c65c00；candidate：内容 42fc6f9；按实际文件冻结 |
| Agent / 模型 | Claude Code 2.1.278 + DeepSeek Flash high；独立原生 CC 用户使用同模型与 high |
| 执行方式 | 单开发 Agent，无开发子 Agent；原生主动调用 `/agent-led-swe` |
| 预算 | 每组开发 Agent 与用户共享 3600 秒，无额外单轮或轮数限制 |
| 次数与顺序 | current 先运行，各一次；不自动重试 |
| 结果 | 功能由独立 verifier 判定；用户接受单列；完整保留原生轨迹、各轮快照和最终文件 |

该任务已用于选题和接入预检，属于开发集。两组自然对话可不同，不强制模拟用户走相同回答路径。单次运行不证明版本的普遍优劣；本轮不据结果修改 skill。
