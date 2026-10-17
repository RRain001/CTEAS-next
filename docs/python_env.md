# Python Environment

## 仓库根目录

当前远程迁移上下文的规范仓库根目录是：

```bash
/home/lhy/CTEAS
```

如果仓库位于其他位置，也应从该仓库根目录执行相同命令。

## 推荐方式

优先使用：

```bash
./bootstrap_venv.sh
```

要求与行为：

- Python `>= 3.11`
- 优先使用 `uv`
- 若没有 `uv`，回退到标准 `python -m venv` + `pip`
- 若现有 `.venv` 使用 Python `< 3.11`，脚本会拒绝继续复用

可选覆盖变量：

- `PYTHON_BIN`
- `UV_PYTHON`
- `PIP_INDEX`

示例：

```bash
PYTHON_BIN=python3.11 ./bootstrap_venv.sh
UV_PYTHON=3.11 ./bootstrap_venv.sh
PIP_INDEX=https://pypi.org/simple ./bootstrap_venv.sh
```

## 手工回退方式

若需要手工执行，可使用：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## 依赖文件

- 已有：`./requirements.txt`
- 已有：`./pyproject.toml`
- 未发现：`environment.yml`
- 未发现：`setup.py`

## 当前 requirements

- `numpy==2.4.4`
- `pandas==3.0.2`
- `pyyaml==6.0.3`
- `PySide6==6.11.0`
- `matplotlib==3.10.9`
- `imageio-ffmpeg==0.6.0`

## 说明

- `PySide6` 用于桌面 GUI
- `matplotlib` 用于后处理绘图
- `imageio-ffmpeg` 用于动画导出
- 环境初始化优先走 `./bootstrap_venv.sh`
- `PIP_INDEX` 可覆盖默认包索引
