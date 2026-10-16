# Desktop GUI Modularization Plan

本轮只建立目录和兼容入口，不拆现有页面逻辑。

## 当前入口

- 推荐入口：`engine.ui.desktop.main`
- 兼容入口：`engine.pyside_gui`
- 当前主窗口实现仍位于：`engine.gui.workbench`
- 新兼容导出位置：`engine.ui.desktop.workbench`

## 未来页面拆分建议

- `engine/ui/desktop/pages/grid_page.py`
- `engine/ui/desktop/pages/surface_meteo_page.py`
- `engine/ui/desktop/pages/upperair_page.py`
- `engine/ui/desktop/pages/calmet_page.py`
- `engine/ui/desktop/pages/calpuff_page.py`
- `engine/ui/desktop/pages/postprocessing_page.py`

## 未来 widgets 拆分建议

- `engine/ui/desktop/widgets/path_selector.py`
- `engine/ui/desktop/widgets/log_viewer.py`
- `engine/ui/desktop/widgets/stage_card.py`

## 迁移原则

- 不改变现有 PySide6 布局和交互行为。
- 不修改科学计算逻辑。
- 优先通过兼容导出层迁移导入路径，再逐步内聚页面类和通用控件。
- 页面拆分前先补最小 GUI smoke check，避免重构和运行验证耦合。
