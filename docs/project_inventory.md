# CTEAS Project Inventory

## 当前项目入口

- CLI 总入口：`./calpuff-cli`
- 编排入口：`./engine/orchestrator/cli.py`
- 桌面 GUI 入口：`./engine/pyside_gui.py`
- GUI 主模块：
  - `./engine/gui/app.py`
  - `./engine/gui/workbench.py`
- 已废弃入口：`./engine/gui/__main__.py`
  - 当前只提示旧 Web GUI / Streamlit GUI 入口已移除。

## 项目结构

- `engine/`
  - Python GUI、业务逻辑、预处理、后处理、模板、资源、native 源码和旧二进制
- `project/cases/`
  - 示例工程
- `calpuff_terrain_and_landuse_data/`
  - 地形和土地利用基础数据
- `bin/`
  - 本轮新增的平台化二进制目录
- `docker/fortran/`
  - 本轮新增的 Docker 编译环境
- `scripts/`
  - 本轮新增的 native 构建和测试脚本

## 代码与配置盘点

### Python 入口脚本

- `./calpuff-cli`
- `./engine/pyside_gui.py`
- `./engine/orchestrator/cli.py`

### GUI 主脚本

- `./engine/gui/app.py`
- `./engine/gui/workbench.py`

### YAML / JSON / INI

- YAML
  - `./engine/config/case.schema.yaml`
  - `./project/cases/*/case.yaml`
- JSON
  - 未发现项目级运行状态 JSON；当前 case 选择依赖 `project/current` 软链接
- INI
  - 未发现 `.ini` 配置

### shell 脚本

- `./bootstrap_venv.sh`
- `./calpuff-cli`

### native 源码

- 主要为 Fortran：
  - `*.for`
  - `*.f`
- 当前未发现用于 native 主程序构建的 C / C++ 源文件

### 依赖文件

- 已有：`./requirements.txt`
- 未发现：
  - `environment.yml`
  - `pyproject.toml`
  - `setup.py`

### 数据文件和示例工程

- 示例 case：
  - `./project/cases/test`
  - `./project/cases/test2`
  - `./project/cases/123`
- 地形数据：
  - `./calpuff_terrain_and_landuse_data/china_srtm`
- 土地利用数据：
  - `./calpuff_terrain_and_landuse_data/eurasia_asia_landuse/eausgs2_0la.img`

## 当前 Python 依赖来源

当前依赖由 `requirements.txt` 提供，按实际 import 补齐后包含：

- `PySide6`
- `PyYAML`
- `numpy`
- `pandas`
- `matplotlib`
- `imageio-ffmpeg`

## 当前 `.x` 文件位置

- 旧运行目录：`./engine/vendor/bin/*.x`
- 源码目录自带副本：`./engine/vendor/src/*/*.x`
- 本轮新增统一目录：
  - `./bin/linux-x86_64/`
  - `./bin/linux-arm64/`
  - `./bin/windows-x86_64/`

## `.x` 对应功能推测

- `terrel.x`：地形预处理
- `ctgproc.x`：土地利用预处理
- `makegeo.x`：地理场合并
- `read62.x`：高空气象转换
- `smerge.x`：地面气象合并
- `met.x`：诊断风场
- `puff.x`：烟团扩散主求解

## 是否存在源码可重新编译

存在，源码位于 `./engine/vendor/src/`。

## 当前路径是否写死

仍存在两类问题：

- 代码里若干关键脚本直接写死 `engine/vendor/bin/*.x`
- 历史日志、重构快照或未收敛的旧文档中仍可能保留旧路径示例

本轮已新增统一平台解析模块，逐步把 native 路径改为通过 `engine/core/platform_utils.py` 和 `engine/core/runner.py` 获取。

当前活动用户文档正在收敛到：

- 从仓库根目录执行命令
- 当前远程迁移上下文以 `/home/lhy/CTEAS` 作为规范根目录示例
- 仅保留 PySide6 桌面 GUI 作为受支持 GUI 入口

## 当前平台相关风险

- 现有 `.x` 均为 Linux x86_64 ELF，不能直接跨平台复用
- 当前宿主机若不是 Linux x86_64，则这些原始 `.x` 无法直接运行
- 源码仓库当前没有统一 `bin/<platform>/` 发布结构
- ARM64 构建需要 Docker 多架构支持或 ARM64 Linux 环境
- 仓库解压后自带大量未提交改动，尤其 vendor 源码目录处于脏状态，本轮不回退这些内容
