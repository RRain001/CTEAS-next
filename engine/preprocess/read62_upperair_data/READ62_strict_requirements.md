# READ62 对输入探空数据的严格要求（实操版）

本文基于 `READ62_v5.661_L110225/read62.inp` 与 `READ62.FOR` 代码行为总结，面向将 IGRA 等资料转换后喂给 READ62 的场景。

## 1. 输入文件与格式

1. 必需控制文件：`READ62.INP`
2. 必需探空文件：`SOUNDING.DAT`
3. 可选替代文件：`SUBSOUND.DAT`（仅当 `ISUB>0`）
4. `JDAT` 只能取：
   - `1` = TD-6201
   - `2` = NCDC FSL

> IGRA 原始 `#...` 文本不能直接作为 `SOUNDING.DAT`，必须先转为 READ62 可读格式（通常用 FSL 结构）。

## 2. 层数上限（硬约束）

1. `MXLEV=200`（源码参数）
2. 对每次探空，要求 `NUMLEV <= 200`
3. 若 `NUMLEV > 200`，程序报错并停止（`ERROR -- too many levels...`）

## 3. FSL 结构要求（JDAT=2）

每次探空需满足“4行头 + N行层数据”：

1. 头1：时间信息（程序读取 `HOUR DAY MON YEAR`）
2. 头2：纬度/经度/站高
3. 头3：总行数 `NLINES`，并计算 `NUMLEV = NLINES - 4`
4. 头4：风速单位 `WSUNIT`，仅识别 `kt` 或 `ms`
5. 层数据读取格式对应字段：`PRES, HEIGHT, TEMP, WD, WS`

## 4. 单位与缺测值

1. 压力 `PRES`：mb(hPa)
2. 高度 `HEIGHT`：m
3. 温度 `TEMP`：°C（程序内部再转 K）
4. 风向 `WD`：度（0–360）
5. 风速 `WS`：
   - `WSUNIT=kt` 时，转 m/s（乘 `0.514791`）
   - `WSUNIT=ms` 时，按“0.1 m/s 整数”解释并除以 10

FSL 常见缺测处理：

1. `HEIGHT=32767` -> 内部缺测 `9999.`
2. `TEMP=3276.7` -> 内部缺测 `999.9`
3. `WD=32767` -> 内部缺测 `999`
4. `WS=32767` -> 内部缺测 `999.9`

## 5. 时间窗口与时次检查

1. 只处理 `READ62.INP` 指定 UTC 起止时间窗口内的探空
2. 相邻探空若出现重复、缺失或时间间隔大于 12 小时，会在输出中标记问题

## 6. 物理与剖面一致性要求

READ62 对探空做 QA，关键要求如下：

1. 第一层应在地面：`height(1) <= station_elevation(igrd)`
   - 否则标记：`First level in sounding is above surface`
2. 压力应随高度递减
   - 若出现 `pres(i) >= pres(i-1)`，标记：`Pressure increasing with height`
3. 高度应随层递增（对非缺测层）
4. 风向范围必须在 `0~360`
5. 风速不得为负
6. 温度与压力需在程序允许范围内（超界会标记）

## 7. PSTOP 覆盖要求

1. `PSTOP` 是提取的顶压层（如 500 mb）
2. 探空应覆盖到 `PSTOP` 或更高空（更小压力）
3. 若未到达 `PSTOP`，会标记“top of sounding below PSTOP”
4. 仅在满足条件时，才可能通过 `LXTOP` 进行自动外推修复

## 8. 缺测处理开关会影响是否丢层

`READ62.INP` 中：`LHT/LTEMP/LWD/LWS`

1. 若为 `T`，对应变量缺测的层会被直接剔除
2. 若为 `F`，允许保留该层并写缺测标志

## 9. 对转换脚本的建议约束

将 IGRA 转 FSL/READ62 输入时，建议强制执行：

1. 每次探空输出层数不超过 200
2. 保证层按压力从大到小排序
3. 保证至少有 2 个有效层（避免后续 `ISTOP==1` 被跳过）
4. 风速统一按 `ms` + 0.1 m/s 整数编码，头4写 `ms`
5. 缺测统一写 FSL 缺测码（`32767` 或 `3276.7`）

## 10. 你当前这套数据链路对应关系

1. IGRA 原始字段：`PRESS/GPH/TEMP/DPDP/WDIR/WSPD`
2. 预处理 CSV：`pressure_hPa, geopotential height_m, temperature_C, dew point temperature_C, wind direction_degree, wind speed_m/s`
3. 输出到 FSL（供 READ62）：
   - `PRES`=hPa（整数）
   - `HEIGHT`=m（整数）
   - `TEMP`=0.1°C 整数
   - 第5列（露点/露点差位）可缺测 `32767`
   - `WD`=度整数
   - `WS`=0.1 m/s 整数

---

如需，我可以再补一份“自动检查脚本规范”（在转换后逐条检查以上硬约束并出报告）。
