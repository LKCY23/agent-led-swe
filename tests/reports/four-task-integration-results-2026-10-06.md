# 四题接入结果

原四题已接入统一执行与验收入口，每题的 control／reference 都通过两轮资格检查。两种 Agent 的 worker 均完成无模型安装、网络与产物回收检查。没有修改 skill 正文，没有启动 baseline／skill 效果对照，也没有调用 LLM judge。

工作分支：`feat/four-benchmark-tasks-20261006`，基于 `ae568a3`。主工作区未合并；worker 检查显式使用 `/Users/liyao/agent-led-swe` 的已接受 skill，不使用工作分支继承的候选正文。

## 1. 验收结果

下表列出每轮 reference 的结果，两轮一致。各题 control 的目标验收均失败；已有回归／补充回归按约定通过。

| 任务 | 目标／官方验收 | 回归与覆盖限制 |
| --- | --- | --- |
| smolagents | 7 个展开测试通过 | 668 passed、2 项原测试条件 skip；没有把 skip 计为通过 |
| xarray | 11 个展开测试通过 | 12,301 passed、290 项原测试条件 skip、26 xfailed；分别保留 |
| NodeBB | 官方 verifier 通过；配置要求 5 个 F2P 和 190 个 P2P 选择器，原生 parser 实际记录 197 个结果 | 官方必要测试均满足；使用容器内 Redis，没有外部数据库服务 |
| Navidrome | 官方 TestDB 聚合套件通过；不是只有一个断言 | 官方 P2P 为空；另行通过 cmd 包构建及 conf 包原生测试，不伪装成官方 P2P |

Python 的 control／reference 回归指纹一致，各条件重复两次的结果也一致。原生 Pro 的解析结果在重复检查中一致。资格只说明这套环境和验收能够工作，不证明测试覆盖每项自然语言要求，更不能证明 skill 有增益。

## 2. 环境适配及遇到的问题

- **smolagents：** 官方镜像压缩层约 12.5 GB，本机改用 Linux ARM64 CPU 依赖镜像。补齐 SciPy／scikit-learn；MLX 使用真实 Linux CPU 包 `mlx[cpu]==0.30.0` 和 `mlx-lm==0.25.2`，不是伪造模块或删掉对应测试。MLX 是发布时期约束的明确例外，其余已装依赖通过 constraints 保持不变。
- **xarray：** 补齐旧版 h5py 所需 HDF5／netCDF 编译依赖，以及 numexpr、pint、array-api-strict。剩余 skip 来自原项目中不适用的参数组合、未来 pandas 条件分支等；按具体测试名与原因冻结，新增 skip 不能自动通过。
- **NodeBB／Navidrome：** 保留官方 Linux AMD64 镜像、工作目录和原生 verifier。源码与镜像依赖分开处理，避免用空 bind mount 隐藏 node_modules。Agent 的 Node 22 独立安装，实际确认 NodeBB 仍使用原来的 Node 18.20.8。
- **Navidrome：** 去除 executor 中的预编译程序，避免将其作为实现参考；UI node_modules 作为镜像依赖保留，不复制成约 10 万个提交文件。源码工作区约 952 个文件。修复 Claude 隔离 HOME 内 root 创建缓存目录的所有权后，非 root 用户可运行 Go 工具检查。
- **判分解析：** 官方配置可能把测试清单存成 Python 字面量字符串，已支持安全解析；原 reward、退出状态与实际测试集合不一致时保持 unknown。此前解析误报保留在失败记录里，没有修改原始 verifier。
- **失败收尾：** 产物导出失败会记录错误、保留执行事件、清理容器，并将执行状态设为 error；不会把导出前的旧工作区当作完整提交去判分。

没有删除功能测试、改写隐藏测试或放宽断言。Skip／xfail 的语义来自原测试，缺依赖导致的跳过已先补齐依赖；具体覆盖限制保留在结果中。

## 3. 代码与使用方式

- 四题定义：`tests/cases/swe/{smolagents,xarray,nodebb,navidrome}.json`。
- 冻结与资格：`suite_tasks.py`、`prepare_suite_task.py`、`preflight_suite.py`；通过记录在 `tests/reports/qualifications/`。
- Pro 原生验收：`swe_pro_verifier.py`；复制型工作区及回收：`container_workspace.py`。
- 实际 worker 检查：`check_suite_workers.py`。它不调用模型，不把 CLI 启动或 skill 文件存在冒充实际效果。
- 正式执行／评价仍使用 `run_evaluation.py` 和 `evaluate_results.py`，名称分别为 smolagents、xarray、nodebb、navidrome。

本机统一冻结输入根目录：

```text
/Users/liyao/agent-led-swe/tests/runs/four-task-inputs-v2-20261006/
```

输入哈希、任务定义或资格不匹配时，运行器在调用模型前拒绝执行。Python 环境的实际构建步骤保存在 [环境配方](../cases/swe/environments/README.md)。重建镜像后须重新资格检查，不把版本相同当作环境相同。

本地回归共 61 项通过，覆盖补丁转换、输入／资格拒绝、原生结果一致性、明确的条件 skip 和产物导出失败后的状态；四题准备入口及两种 worker 已做实际检查。

## 4. 证据

本机根目录为 `/Users/liyao/agent-led-swe/tests/runs/`：

| 目录 | 内容 |
| --- | --- |
| `four-task-inputs-20261006/` | 原始来源、补丁、镜像下载、依赖构建及早期准备记录 |
| `four-task-inputs-v2-20261006/` | 统一的四题冻结输入，不向执行 Agent 提供私有 reference／validator |
| `four-task-preflight-20261006/{smolagents,xarray,navidrome}-v2/` | 最终两轮资格验证；v1 保留环境缺失／解析问题 |
| `four-task-preflight-20261006/nodebb-v1/` | NodeBB 两轮原生资格验证 |
| `four-task-workers-20261006/smolagents-v1/`、`xarray-v1/` | 两种 Python worker 的安装、网络、源文件读写与回收 |
| `four-task-workers-20261006/nodebb-v2/` | 两种 worker；任务 Node 版本保持不变；v1 的旧 apt 源升级失败保留 |
| `four-task-workers-20261006/navidrome-v2/` | 两种 worker 和 Go 工具检查；v1 的 Claude 缓存权限失败保留 |

这些是基础设施与无模型任务预检，不是 Agent 完成题目的轨迹。下一步才是固定模型、预算和比较组进行实际效果对照；接续变体和人机协作测试尚未执行。
