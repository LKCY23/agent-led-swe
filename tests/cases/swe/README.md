# 旧 SWE 校准任务

以下四题已接入并完成两轮起始／参考预检，现已退出当前推荐测试组合。定义、适配器、规范冻结输入和资格记录保留供显式回归。当前状态见 [STATUS](../../STATUS.md)，效果与限制见 [历史索引](../../history.md)。

| CLI 名称 | 来源与任务 | 验收与环境 |
| --- | --- | --- |
| [smolagents](../../reports/qualifications/smolagents.json) | FeatBench，XML 迁移与自定义指令 | 冻结 F2P／P2P，Linux ARM64 CPU 环境 |
| [xarray](../../reports/qualifications/xarray.json) | FeatBench，Grouper／Resampler 公共 API | 冻结 F2P／P2P，Linux ARM64 环境 |
| [nodebb](../../reports/qualifications/nodebb.json) | SWE-bench Pro V2，邮件验证状态管理 | 原生 verifier，Linux AMD64，容器内 Redis |
| [navidrome](../../reports/qualifications/navidrome.json) | SWE-bench Pro V2，SQLite 备份恢复 | 原生 TestDB 套件，另做 cmd／conf 补充回归，Linux AMD64 |

任务定义在同名 JSON；上表链接的资格记录锁定 spec、输入、镜像和验收结果。读到已注册名称不等于可以跳过资格检查：材料变化或资格缺失时，运行器在调用模型前拒绝执行。

完整接入结果见 [报告](../../reports/four-task-integration-results-2026-10-06.md)，选题依据见 [样例组合](../../reports/sample-suite-candidates-2026-10-06.md)。所有这些任务均属于开发／校准用例。

## 冻结输入

本机统一输入目录是：

```text
/Users/liyao/agent-led-swe/tests/runs/four-task-inputs-v2-20261006/
  <task>/
    metadata.json      原始任务记录
    public.tar.gz      公共起始工作区
    request.txt        原始任务要求
    reference.patch   私有参考实现
    validator/        私有可信验收材料
    environment.json  固定运行环境
    validation.json   固定验收方式
    inputs.json       输入文件哈希
```

执行 Agent 只获得公共工作区和任务要求。参考补丁与 validator 不放入 worker；验收在独立副本／新容器中进行。原始来源和准备日志位于此前的 `four-task-inputs-20261006/`，其中重复 `public/` 展开副本已清理，压缩包与元数据保留。Python 环境配方保存在 [environments](environments/README.md)。

## 准备与资格检查

准备原始 metadata／源码或官方任务材料后，用指定镜像冻结公共输入；命令不覆盖已冻结的 inputs.json：

```sh
uv run --locked python tests/prepare_suite_task.py smolagents \
  --inputs '<原始输入根目录>' --image '<准备好的依赖镜像>'
uv run --locked python tests/preflight_suite.py smolagents \
  --inputs '<冻结输入根目录>' --output '<新预检目录>' --register
uv run --locked python tests/check_suite_workers.py smolagents \
  --inputs '<冻结输入根目录>' --output '<新 worker 检查目录>' \
  --skill-path /Users/liyao/agent-led-swe
```

名称可替换为其余三题。预检先检查 control／reference，再重复一轮；每组上限 600 秒，异常即停止该题。只有成功时 --register 才登记资格。Worker 检查不调用模型，验证两种 CLI、skill 安装、网络、任务运行时和产物回收。

Python 测试中的项目自身条件跳过按具体测试身份与原因登记，skip／xfail 单独保留，不计为 passed。缺依赖导致的跳过须先补齐依赖；新增跳过、错误、缺失结果或与参考不一致的结果不能通过。

SWE-bench Pro 的原生脚本、parser 和评分清单保持原样。Navidrome 的补充回归与 OFFICIAL 成绩分别保存，不把它写成官方 P2P。未执行额外接续变体或人机交互测试。

## 其他任务

packaging 同样退出当前推荐组合，旧冻结输入和 [独立环境资格](../../reports/packaging-execution-environment-2026-10-06.json)保留。DSPy、Agents SDK 不启用。pytest benchmark 已退出并清理；pytest 测试工具仍用于 Python 项目的正常验收。
