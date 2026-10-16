# Docker Native Build

## 构建环境

Dockerfile：

- `./docker/fortran/Dockerfile`

基础镜像：

- `debian:12`

安装工具：

- `gfortran`
- `make`
- `bash`
- `file`

## 构建 Linux x86_64

```bash
./scripts/build_native_linux_x86_64.sh
```

产物输出到：

- `./bin/linux-x86_64/`

## 构建 Linux ARM64

```bash
./scripts/build_native_linux_arm64.sh
```

产物输出到：

- `./bin/linux-arm64/`

说明：

- 该脚本依赖 Docker 支持 `--platform linux/arm64`
- 若当前 Docker 未启用多架构，会直接失败；此时应改在 ARM64 Linux 或启用 buildx/QEMU 后执行

## 验证架构

```bash
file bin/linux-x86_64/*.x
file bin/linux-arm64/*.x
```

## 后端检查

```bash
./scripts/test_native_backend.sh linux-x86_64
./scripts/test_native_backend.sh linux-arm64
```

说明：

- 脚本会检查必需 `.x` 是否存在且可执行
- 并尝试执行 `--help`
- 若程序不支持 `--help`，脚本会记录说明，不作为硬失败
