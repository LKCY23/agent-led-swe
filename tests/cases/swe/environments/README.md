# 四题的 Python 依赖镜像配方

这些文件保留本轮实际使用的构建步骤，不包含待测项目源码、参考实现或测试补丁。NodeBB／Navidrome 直接使用官方 V2 镜像，具体不可变 image ID 在各自资格记录中。

smolagents：

```sh
docker build --platform linux/arm64 -f tests/cases/swe/environments/smolagents/base.Dockerfile \
  -t agent-led-swe-smolagents:20261006-v1 tests/cases/swe/environments/smolagents
docker build --platform linux/arm64 -f tests/cases/swe/environments/smolagents/Dockerfile \
  -t agent-led-swe-smolagents:20261006-v3 tests/cases/swe/environments/smolagents
```

xarray：

```sh
docker build --platform linux/arm64 -f tests/cases/swe/environments/xarray/base.Dockerfile \
  -t agent-led-swe-xarray:20261006-v2 tests/cases/swe/environments/xarray
docker build --platform linux/arm64 -f tests/cases/swe/environments/xarray/Dockerfile \
  -t agent-led-swe-xarray:20261006-v3 tests/cases/swe/environments/xarray
```

依赖一般按任务发布时间限制版本。smolagents 的 MLX 是明确例外：所选测试需要导入 mlx_lm 并 mock 其 load；Linux ARM64 可用的 CPU 包晚于任务发布，因此使用 mlx[cpu] 0.30.0 与 mlx-lm 0.25.2。其他已安装依赖通过 freeze constraints 保持不变，未替换测试或伪造 MLX 模块。

xarray 补齐旧版 h5py 构建所需的 HDF5／netCDF 开发库，以及原测试用到的 numexpr、pint、array-api-strict。源码中的不可用参数组合和未来 pandas 条件分支仍按原测试 skip／xfail 记录。

这些是本地 CPU 环境适配，不是 FeatBench 官方镜像成绩。重建产生新的 image ID 时，必须在新输入／预检目录重新资格检查，不能沿用旧结果声称等价。
