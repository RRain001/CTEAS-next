# Structure Refactor Summary

## 本轮完成项

- 删除 launcher 对 `webgui` / `streamlitgui` 的支持，只保留 `desktopgui` 和 orchestrator CLI。
- 新增 `engine.ui.desktop` 兼容入口，为后续桌面 GUI 模块化预留结构。
- 新增 `engine.native.registry`，集中声明必需 `.x` 程序。
- 新增 `engine.core.case_manager` 与 `project/current_case.yaml`，当前 case 选择不再只依赖 `project/current` symlink。
- 新增 `pyproject.toml`，补齐标准 Python 包入口。
- 新增 native / current case 检查脚本与 Docker x86_64 runtime 测试脚本。

## 本轮未做

- 未拆分现有 `engine.gui.workbench` 大文件。
- 未改动科学计算逻辑。
- 未实现 ARM64 编译或 Windows 打包。
- 未执行 Docker runtime test。
