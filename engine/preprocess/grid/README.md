# grid 使用说明

本目录用于根据用户输入的中心点与研究域参数，自动更新 CALMET 网格配置文件 `grid.cmn`。

## 文件说明

- `grid.cmn`：CALMET 网格参数文件
- `center_location`：中心点经纬度记录文件
- `configure_grid_cmn.py`：交互式配置脚本（单文件可运行，不依赖其他 Python 模块）

## 运行方式

```bash
python3 -m engine.preprocess.grid.configure_grid_cmn
```

## 交互输入顺序

1. 输入中心点经度（十进制度，例如 `117.2345`）
2. 输入中心点纬度（十进制度，例如 `31.939774`）
3. 输入研究域长度（X 方向，整数，单位 km）
4. 输入研究域宽度（Y 方向，整数，单位 km）
5. 输入网格分辨率 `DGRIDKM`（单位 km）
6. 输入垂向层数 `NZ`（直接回车则默认 `9`）

## 脚本逻辑

1. 校验经纬度范围
   - 经度：`[-180, 180]`
   - 纬度：`[-90, 90]`
2. 自动识别东西经与南北半球
3. 基于 WGS-84 将中心点经纬度转换为 UTM
4. 根据研究域长宽计算左下角坐标
   - `XREFKM = X_center - length/2`
   - `YREFKM = Y_center - width/2`
5. 根据分辨率计算网格数
   - `NX = ceil(length / DGRIDKM)`
   - `NY = ceil(width / DGRIDKM)`
6. 更新 `grid.cmn` 关键参数 
   - `IUTMZN`, `LSOHEM`
   - `XREFKM`, `YREFKM`
   - `DGRIDKM`, `NX`, `NY`
   - `NZ` 与 `ZFACE`
7. 更新 `center_location` 文件

## 默认垂向设置

当 `NZ=9`（默认）时，`ZFACE` 写为：

`0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000`

## 输出结果

脚本执行后会打印：

- UTM 分区与半球
- `XREFKM` / `YREFKM`
- `DGRIDKM`, `NX`, `NY`, `NZ`

并落盘修改：

- `./project/current/grid/center_location`
- `./project/current/grid/grid.cmn`
