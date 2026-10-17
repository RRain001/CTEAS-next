# Docker Setup For macOS Clash

适用环境：

- macOS
- Docker Desktop
- Clash 代理
- 项目目录：`.`

## A. 用户本机设置

如果 Docker 容器网络失败，先检查宿主机：

- Clash 是否正在运行。
- 当前代理端口是多少，例如 `7897`。
- Clash 是否开启了 `Allow LAN` / `允许局域网连接`。
- Docker Desktop 虚拟机是否允许访问宿主机代理。

## B. Docker 容器访问宿主机代理

容器内不能使用：

```text
127.0.0.1:7897
```

因为容器里的 `127.0.0.1` 指向容器自身，不是宿主机。

容器内应优先使用：

```text
host.docker.internal:7897
```

如果 Clash 端口不是 `7897`，请替换为实际端口。

## C. 诊断命令

```bash
PROXY_PORT=7897 bash scripts/docker_network_diagnose.sh
```

这个脚本会检查：

- Docker 是否可用
- `linux/arm64` 和 `linux/amd64` 容器能否启动
- 容器无代理时能否访问 Debian 源
- 容器是否能访问宿主机代理端口
- 容器启用代理后能否访问 Debian 源

## D. 运行 Docker runtime 测试

当前推荐路线：

- 默认镜像：`debian:12`
- 默认不启用代理：`USE_DOCKER_PROXY=0`
- Docker runtime 测试只安装后端最小依赖：`requirements-docker-runtime.txt`
- Docker runtime 测试不安装 `PySide6`

不启用代理：

```bash
./scripts/test_linux_x86_64_runtime_in_docker.sh
```

启用代理：

```bash
USE_DOCKER_PROXY=1 PROXY_PORT=7897 ./scripts/test_linux_x86_64_runtime_in_docker.sh
```

如果 Clash 端口不是 `7897`，应替换 `PROXY_PORT`。

如果需要覆盖镜像：

```bash
RUNTIME_IMAGE=debian:12 ./scripts/test_linux_x86_64_runtime_in_docker.sh
```

## E. Docker Desktop 手动设置提示

如果脚本传代理后仍无法拉取镜像，需检查 Docker Desktop 图形界面设置：

```text
Docker Desktop -> Settings -> Resources/Proxies 或 Proxies
```

可以尝试把 HTTP/HTTPS proxy 设为：

```text
http://127.0.0.1:7897
```

或者让 Docker Desktop 继承系统代理。

这一步需要用户手动完成，脚本不能替代 Docker Desktop GUI 设置。
