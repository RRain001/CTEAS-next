# ISD 下载风数据处理(移植 CTEAS-Atmos 方法 + 站号约定修复)

更新日期:2026-10-10。本轮把 CTEAS-Atmos `98d214e`(ADR0119 / Plan0142,
`ISD_FORWARD_FILL_CALM_ARC_V1`)对下载 ISD 风数据的处理方式移植到 CTEAS
地面气象预处理链,并按 `isd-history.txt` 修正站点编号约定;全部结论在 Linux
主机上用 2022 全年真实数据验证,并实际运行了 `smerge.x`。

## 改动点

1. **风速码 0000**:`isd_to_smerge_and_fill.parse_wind` 不再改写为 0.1 m/s、
   方向不再强制 0°(北风);0000 保留为 0.0 m/s 静风,报告方向原样保留。
   方向与速度的可用性彼此独立(5 段结构 + QC 码 `{0,1,4,5,9}` + 取值范围),
   WND 解码规则与 Atmos `decode_wnd` 相同。
2. **缺测填补**:`interpolate.fill_wind_forward_calm` 取代原 u/v 时间插值 +
   全年均值兜底。逐字段(方向、速度独立)沿用上一个可用原始值,整点缺报同样
   沿用;每个填充值记录来源时刻;不插值、不用均值、不跨站点/年。
3. **静风处理与主表口径**:按填充后速度 `speed < 0.5 m/s` 判定静风。
   静风段风向取两端非静风填充风向的最短弧,`angle = θ0 + m/(L+1)·Δ`
   (Δ 为最短弧有向角,精确 180° 顺时针),与 Atmos 公式逐字一致。
   主表(SMERGE/CALMET 输入)风速取**计算口径**:静风小时写 `0.5 m/s`,
   非静风写实际填充速度;审计文件保留 filled/statistics 口径的 `0.0 m/s`。
4. **站点编号 = isd-history.txt 的 6 位 USAF**(不再截取前 5 位):
   - 案例站点清单(`surf_station_list_*.txt`)本就来自 `isd-history.txt`,其中
     `sid = USAF(6)+WBAN(5)`;站号取 USAF 原值(583210、583211、583620、…),
     6 位站号互不冲突,不再需要按「末位为 0」的假设筛站。
   - 全链一致:SMERGE 输入通用格式 CSV 头部 ID = `IFSTN` = 6 位 USAF
     (SMERGE 会逐站校验该 ID,不一致直接 FATAL);`clean_merge` 以
     `<USAF>-<WBAN>` 归组命名;`isd2smerge_ready/`、`stations.csv`、
     `prepare_met.py` 生成的 CALMET 输入组 7 均使用 6 位站号。
   - 依据:SMERGE 变更记录「Allow station ID to exceed 5 digits」,站号按整数
     列表定向读取;CALMET 的 met.inp 模板明确要求
     「Six digit integer for station ID」,SURF.DAT 站号按整数处理(文本输出 i8)。
   - 保护:USAF 非 6 位数字(如 `A12350`)时显式报错——SMERGE/SURF.DAT 需要
     整数站号;同一 USAF、不同 WBAN 的重复站也会显式报错。
   - 注意:案例配置中的 `isurft_station_id` / `iupt_station_id` 等站号需与
     `stations.csv` 一致,即改前 5 位、改后 6 位。
5. **健壮性修复**(同轮排查发现):
   - `generate_smerge_input_sections`:`IFSTN` 取 6 位 USAF 的校验/冲突保护(见上);
   - `download_isd_by_grid`:USAF 非 6 位数字的站点**在下载阶段即排除**并写入
     `excluded_stations_{year}.txt`,不再等到整套预处理后才发现 SMERGE 无法建站号;
   - `run_smerge_and_monitor`:站点在站点清单(`surf_station_list_*.txt`)中缺少
     经纬度元数据时显式报错并指明文件,不再写出空的 lat/lon 让下游崩溃;
   - `prepare_met`:经纬度缺失或非数值时给出带站号的明确错误,替代
     `could not convert string to float: ''`;
   - `isd_to_smerge_and_fill`:未生成 `_filled.csv` 时保留中间文件并告警,
     不再无条件删除。

## 产物

- 主表:`met/surface/isd2smerge_and_fill/<USAF>-<WBAN>-<年>_filled.csv`
  (12 列,缺失写 9999)→ `isd2smerge_cleaned/<USAF>-<WBAN>.csv` →
  `isd2smerge_ready/` → SMERGE。
- 审计 sidecar(不匹配下游 glob):
  - `..._filled_wind_audit.csv`:逐时原始/填充风向风速、`*_was_filled`、
    `*_fill_source_utc`、`is_calm`、统计风向、`wind_speed_statistics_m_s`(0.0
    口径)、`wind_speed_calculation_m_s`(0.5 口径)、补值方法、静风段编号;
  - `..._filled_wind_audit.json`:静风阈值、填充小时数、静风段数、主表口径说明,
    以及网关清单 `leading_missing` / `boundary_calm_segments`。
- 网关语义(Atmos 同型):区间首小时缺前置可用值 → `LEADING_MISSING_NO_PREDECESSOR`;
  静风段贴区间边界、缺少非静风端点 → `CALM_SEGMENT_MISSING_NONCALM_ENDPOINT`。
  默认**非致命**(保留前向保持值并在审计中标出);`interpolate.py --strict`
  抛出与 Atmos 相同的错误码与时段范围。

## 验证(2022-01-01 ~ 2022-12-31,Linux)

数据:NCEI S3 原始 ISD,583210(合肥骆岗)、583211(浦东)、583620(上海)、
583670(虹桥),每站 8760 小时。两家实现选源一致(Pudong/虹桥每小时 `:00`/`:30`
两条报文,双方都只用 `:00`)。

| 站点 | 审计口径 vs Atmos | 主表口径 vs Atmos | 静风写 0.5 小时 |
|---|---|---|---|
| 583210 | 速度/风向/静风/方法 全部 0 处不一致 | 速度 0.0,风向 ≤0.5°(取整),0 处不一致 | 281 |
| 583211 | 同上 | 同上 | 99 |
| 583620 | 同上 | 同上 | 495 |
| 583670 | 同上 | 同上 | 100 |

- 站号链(4 站同一案例):生成 `IFSTN=583210/583211/583620/583670`,
  `XELEV=63/4/4/3`;`isd2smerge_ready` 头部 ID 与 IFSTN 完全一致;
- **真实 SMERGE 运行**:`/home/lhy/CTEAS/bin/linux-x86_64/smerge.x smerge.inp`
  返回 0、无 FATAL、产出 `surf.dat`(2,330,177 字节),表头站号依次为
  583210/583211/583620/583670;
- CALMET 输入组 7 渲染:`! SS1  ='PUDO'    583211       386.085      3446.065    0   10.0 !`
  (6 位站号,符合模板文档);
- 非数字 USAF(`A12350-99999`)→ 显式报错、退出码 1;
- 网关一致性(合成用例):前置方向缺失、年末贴边界静风两例,错误码与时段范围
  与 Atmos 完全一致;
- 静风主表值抽查:583670 `isd2smerge_ready` 中 `0.5` 出现 100 次 = 该站静风小时数。

**CALMET 级端到端回归**(真实案例 `smoke5d_coldstart_20260701` 的 2023 数据,
5 天窗口,复用案例自带的 geo.dat / 高空数据与 native 二进制):

1. 新代码全链:`isd_to_smerge_and_fill` → `clean_merge_…` →
   `convert_cleaned_to_smerge_ready` → `generate_smerge_input_sections` →
   `run_smerge_and_monitor`(调用真实 `smerge.x`);
2. `stations.csv`:`583210, LUOGANG / XINQIAO, 31.988, 116.977, 63 m`
   (6 位站号键匹配站点清单);
3. `smerge.inp`:`!IFSTN = 583210 !` / `!XELEV = 63 !`,`smerge.x` 正常完成;
4. `prepare_met --case …`:`! SS1  ='LUOG'    583210       497.827      3539.106    0   10.0 !`;
5. `run_met --case …`(真实 `met.x`):正常结束,`met.lst` 无 FATAL/ERROR,
   产出 `met.dat`(53.9 MB),用时 25 s。

验证脚本与完整结果在 Linux 主机 `/home/lhy/cteas-isd-verify/`
(`harness/{compare,run_reference,gate_parity,smerge_sections}.py`、
`out/{comparison.json,gate-parity.txt,smerge-sections.txt}`)。

## 已知限制

- SMERGE/SURF.DAT 站号是整数,USAF 含字母的站点(ISD 允许)暂不支持,会显式报错。
- 静风 0.5 m/s 已通过 SMERGE 输入/运行验证;CALMET 的计算效果(诊断风场差异)
  仍需真实案例全链回归。
- 非风字段(温度/湿度/气压/云量/降水)仍沿用原有填补规则,不在本轮范围。
