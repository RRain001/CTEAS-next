# P6G 端到端验收记录：首次全链 C++ 重建 vs 原版 2022 冻结参考

日期：2026-10-12。轨道分支 `ci/p6g-end-to-end-20261012`（base `origin/main` `9197e6f`），
[PR #27](https://github.com/RRain001/CTEAS/pull/27)。
主题：把**已重建的 P6D 风场产出器 → P6F `CALMET.DAT` 写出器 → P6E `emit-realcase` 消费端**串成
一条可复现链路，并对冻结的 2022 参考 `met.dat` 做**全 45 字段**的逐字段判定，两种口径分列。

本记录的全部数字来自真实运行，未做任何替代或外推；每一个"未产出"字段都显式保留分母 0。

---

## 0. 本轮结论摘要

| 项 | 结论 |
|---|---|
| 链路可复现 | **PASS**：`scripts/run_p6_end_to_end.py` 一条命令，从空目录（空 build + 空 work）跑通全部三段，端到端墙钟 **8:21**（其中链路本体 477.87 s） |
| 口径 B（原版风场驱动） | 45 字段判定齐备，**7 PASS / 3 FAIL / 35 分母 0**（FAIL：`ZI`、`EL`、`WSTAR`）〔基点 `9197e6f`；当前 main `3be69bb` 为 **12 PASS / 6 FAIL / 27 分母 0**，见 §8〕 |
| 口径 A（重建风场驱动） | 45 字段判定齐备，**6 PASS / 4 FAIL / 35 分母 0**（FAIL：`USTAR`、`ZI`、`EL`、`WSTAR`）〔基点 `9197e6f`；当前 main `3be69bb` 为 **11 PASS / 7 FAIL / 27 分母 0**，见 §8〕 |
| A−B（P6D 风场重建段引入的端到端误差） | 45 字段判定齐备，**7 PASS / 3 FAIL / 35 分母 0**（FAIL：`USTAR`、`EL`、`WSTAR`；`ZI` 差值在容差内）〔当前 main `3be69bb` 为 **15 PASS / 3 FAIL / 27 分母 0**，FAIL 集合不变，见 §8〕 |
| AUX（P6F 重建 `CALMET.DAT` vs 冻结） | 45 字段判定齐备：27 个 P6D 风场字段全部 FAIL（真实数值差异，见 §3.4），18 个非风字段逐位 0 差 |
| 本轮新发现 | **P6F `write-from-p6d` 的 U/V/W 平面索引置换缺陷**（旧代码按 cell-major 读层主序 P6D 平面），已修复并补上可捕获它的回归断言，见 §5 |
| 正式门槛 | `P6G=IN_PROGRESS / FIRST_END_TO_END_VERDICTS_RECORDED`；`P6D_FULL=NOT_PASS`；`P6E_FULL=NOT_PASS`；`P6_CALPUFF_READY=FALSE`（无变化） |

**一句话**：端到端链路第一次真正闭环并给出逐字段判定；P6D 风场本身在第 1 层已逼近原版
（`U-LEV 1` 最大绝对差 1.518e-03 m/s），但随高度增大到第 9 层 13.51 m/s，并把
`USTAR`、`EL` 推出容差；`ZI`/`WSTAR` 的超差主体**不在风场**，而落在 P6E 内核。

> **§3–§4 的表基于本 PR 的分支基点 `9197e6f`。** 合入时 main 已前进到含 P6E E31–E35 的 `3be69bb`，
> 该版本会额外产出 `T-LEV 2..9`。**当前 main 的判定表见 §8**（`USTAR/ZI/EL/WSTAR/TEMPK/RHO/QSW/IRH/IPGT`
> 与 `T-LEV 1` 的两种口径数值与 §3 **完全一致**，AUX 表 45 行也完全一致；只有 `T-LEV 2..9` 从
> `NOT_PRODUCED` 变为已产出）。

---

## 1. 链路、命令与输入来源

一条命令（`--build-dir` 会给四个目标各做一次 `cmake` 配置与构建；只想跑链路就给 `--bin-dir`）：

```
python3 scripts/run_p6_end_to_end.py \
    --case project/cases/hefei5km_2022_reference_case_20261011 \
    --build-dir <build> --work <work>
```

脚本按固定次序执行 5 个动作 + 4 次对照，任何一段非零退出即 fail-closed（`P6G_END_TO_END_BLOCKED`，报告不落盘）：

| # | 段 | 工具 | 输入来源 |
|---|---|---|---|
| 1 | P6D 风场产出器 | `cteas_p6_realcase_wind_field`（`native_cpp/modules/p6_calmet`, 目标同名） | 案件树只读：`run/met/met.inp`、`geo/**/geo.dat`、`met/surface/final/{surf.dat,stations.csv}`、`met/upperair/final/up_58424.dat`、`case.yaml` |
| 2 | P6F 写出器 | `cteas_p6f_calmet_dat21_writer write-from-p6d`（`native_cpp/modules/p6_calmet/p6f`） | `--fields <P6D 产物> --variant blend --w-field w_face --statics-from <冻结 met.dat> --met-fields-from <冻结 met.dat> --irtype 1` |
| 3 | E15 观测桥 | `p6e_p6c_hourly_bridge`（`.../p6e`） | `SURF.DAT` + `UP.DAT` + 站号 `58424` → `hourly.csv` |
| 4 | P6E 消费端（**A**） | `p6e_calmet_dat21 emit-realcase` | `--reference <冻结 met.dat> --observations <hourly.csv> --wind-file <P6F 重建 CALMET.DAT> --geo-file <geo.dat>` |
| 5 | P6E 消费端（**B**） | `p6e_calmet_dat21 emit-realcase` | 同上，但 `--wind-file <冻结 met.dat>`（原版风场，对照基线） |
| 6 | 对照 A / B | `p6e_calmet_dat21 compare` | A、B 候选各自对冻结 `met.dat` |
| 7 | 对照 A−B | `p6e_calmet_dat21 compare` | `--reference <B 候选> --candidate <A 候选>` |
| 8 | 对照 AUX | `p6e_calmet_dat21 compare` | P6F 重建 `CALMET.DAT` 对冻结 `met.dat` |

**输入来源如实标注**

- **A 口径的风场是重建产物**：P6D 的 `blend_u/blend_v`（原版 `INTER2` 两分量融合在 step-one 场上的结果）与
  `w_face`（SLOPE 补偿、SMOOTH/DIVCEL/W 之后的层顶面 W），经 P6F 写成 `CALMET.DAT 2.1` 后交给 P6E。
  它**不含** DIAGNO 的 `WINDBC`、也不含作用在 U/V 上的 `SMOOTH/DIVCEL`，FRADJ 因 GAMMA 缺失仍为 `PENDING_GAMMA`
  （P6D metadata 自述）。
- **B 口径的风场是原版产物**：直接使用冻结 `met.dat` 自身的 `U-LEV/V-LEV/WFACE`。
- **A/B 共用的其它输入**（观测、地形、静态记录、时间标签、2-D 气象场）都来自冻结案件树或冻结 `met.dat`，
  两口径完全一致；因此 **A−B 的差就是 P6D 风场重建段单独引入的差**。
- `P6D` 自带的原版对照是**子程序级**证据（对未改动原版 `WIND1`/`INTER2` 驱动同一输入），
  本轮给出的是**文件级端到端**证据，两者不互相替代。

冻结参考身份（脚本内 fail-closed 校验，不匹配即中止）：

```
met.dat   sha256 b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30  64,762,556 B
puff.inp  sha256 cf5cca70cb75b1aac92f86fdc100500e901a8b904d056c73b2330175793532bc
布局      143 时段 × 45 字段 × 2,500 格 = 357,500 格/字段
```

---

## 2. 判定口径

- **分母**：该字段在 143 时段 × 2,500 格中，参考与候选**都非缺测**的格数；缺测格与候选缺测格
  （`9999.` / `-9999`）都从分母中排除，并单列 `miss(ref/cand)`。
- **容差**：`p6e_calmet_dat21 compare` 的冻结源门槛，超差判据为
  `|a-b| > abs_limit + rel_limit*|a|`。
- **PASS/FAIL**：分母 > 0 且超差数 = 0 → PASS；分母 = 0 且存在缺测 → `NOT_PRODUCED`（显式列出分母 0）。
- 单位与容差表：`IPGT`/`IRH` 精确；`TEMPK`/`T-LEV*` K；`U/V/W` m/s；`USTAR/WSTAR` m/s；`ZI/EL` m；
  `RHO` kg/m³；`QSW` W/m²。

---

## 3. 逐字段判定表（45 字段 × 4 张表）

### 3.1 口径 A —— 重建风场驱动 vs 冻结 `met.dat`

27 个 P6D 所有的风场字段：`U-LEV k` / `V-LEV k` / `WFACE k`（k=1..9）

| 字段 | 分母 | miss(ref/cand) | max_abs | max_rel | 容差 | 超差 | 判定 |
|---|---|---|---|---|---|---|---|
| `U-LEV 1` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `V-LEV 1` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `WFACE 1` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `U-LEV 2` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `V-LEV 2` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `WFACE 2` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `U-LEV 3` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `V-LEV 3` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `WFACE 3` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `U-LEV 4` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `V-LEV 4` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `WFACE 4` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `U-LEV 5` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `V-LEV 5` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `WFACE 5` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `U-LEV 6` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `V-LEV 6` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `WFACE 6` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `U-LEV 7` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `V-LEV 7` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `WFACE 7` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `U-LEV 8` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `V-LEV 8` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `WFACE 8` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `U-LEV 9` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `V-LEV 9` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `WFACE 9` | 0 | 0/357500 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |

其余 18 个字段：

| 字段 | 分母 | miss(ref/cand) | max_abs | max_rel | 容差 | 超差 | 判定 |
|---|---|---|---|---|---|---|---|
| `T-LEV 1` | 357500 | 0/0 | 5.7983e-04 | 2.0921e-06 | 5e-4 + 1e-5·\|ref\| | 0 | **PASS** |
| `T-LEV 2` | 0 | 0/357500 | 0 | 0 | 5e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `T-LEV 3` | 0 | 0/357500 | 0 | 0 | 5e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `T-LEV 4` | 0 | 0/357500 | 0 | 0 | 5e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `T-LEV 5` | 0 | 0/357500 | 0 | 0 | 5e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `T-LEV 6` | 0 | 0/357500 | 0 | 0 | 5e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `T-LEV 7` | 0 | 0/357500 | 0 | 0 | 5e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `T-LEV 8` | 0 | 0/357500 | 0 | 0 | 5e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `T-LEV 9` | 0 | 0/357500 | 0 | 0 | 5e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `IPGT` | 357500 | 0/0 | 0 | 0 | 0（精确） | 0 | **PASS** |
| `USTAR` | 357500 | 0/0 | 5.7228e-05 | 4.8966e-04 | 3e-5 + 5e-5·\|ref\| | **9213** | **FAIL** |
| `ZI` | 357500 | 0/0 | 51.0637 | 5.61028e-02 | 0.07 + 8e-5·\|ref\| | **4465** | **FAIL** |
| `EL` | 357500 | 0/0 | 18282 | 7.69106e-02 | 0.04 + 5e-5·\|ref\| | **1581** | **FAIL** |
| `WSTAR` | 357500 | 0/0 | 2.62769e-02 | 2.4397e-02 | 2e-5 + 3e-5·\|ref\| | **5027** | **FAIL** |
| `TEMPK` | 357500 | 0/0 | 5.7983e-04 | 2.0921e-06 | 3e-4 + 1e-5·\|ref\| | 0 | **PASS** |
| `RHO` | 357500 | 0/0 | 2.7418e-06 | 2.1196e-06 | 1e-5 + 1e-5·\|ref\| | 0 | **PASS** |
| `QSW` | 357500 | 0/0 | 7.2479e-04 | 6.3625e-05 | 0.02 + 3e-5·\|ref\| | 0 | **PASS** |
| `IRH` | 357500 | 0/0 | 0 | 0 | 0（精确） | 0 | **PASS** |

汇总：**PASS 6 / FAIL 4 / NOT_PRODUCED 35**（45 字段）。

### 3.2 口径 B —— 原版风场驱动 vs 冻结 `met.dat`（对照基线）

27 个风场字段与 8 个 `T-LEV 2..9` 全部 `NOT_PRODUCED`（分母 0，miss `0/357500`），与 §3.1 完全一致，
不再重复：P6E `emit-realcase` 只消费风场，不写出风场。

| 字段 | 分母 | miss(ref/cand) | max_abs | max_rel | 容差 | 超差 | 判定 |
|---|---|---|---|---|---|---|---|
| `T-LEV 1` | 357500 | 0/0 | 0 | 0 | 5e-4 + 1e-5·\|ref\| | 0 | **PASS** |
| `IPGT` | 357500 | 0/0 | 0 | 0 | 0（精确） | 0 | **PASS** |
| `USTAR` | 357500 | 0/0 | 5.5134e-07 | 5.0724e-06 | 3e-5 + 5e-5·\|ref\| | 0 | **PASS** |
| `ZI` | 357500 | 0/0 | 51.0623 | 5.61028e-02 | 0.07 + 8e-5·\|ref\| | **4488** | **FAIL** |
| `EL` | 357500 | 0/0 | 10734 | 3.22548e-02 | 0.04 + 5e-5·\|ref\| | **630** | **FAIL** |
| `WSTAR` | 357500 | 0/0 | 2.62769e-02 | 1.9062e-02 | 2e-5 + 3e-5·\|ref\| | **4880** | **FAIL** |
| `TEMPK` | 357500 | 0/0 | 0 | 0 | 3e-4 + 1e-5·\|ref\| | 0 | **PASS** |
| `RHO` | 357500 | 0/0 | 0 | 0 | 1e-5 + 1e-5·\|ref\| | 0 | **PASS** |
| `QSW` | 357500 | 0/0 | 7.2479e-04 | 6.3625e-05 | 0.02 + 3e-5·\|ref\| | 0 | **PASS** |
| `IRH` | 357500 | 0/0 | 0 | 0 | 0（精确） | 0 | **PASS** |

汇总：**PASS 7 / FAIL 3 / NOT_PRODUCED 35**（45 字段）。
`TEMPK`/`T-LEV 1`/`RHO`/`IRH`/`IPGT`/`USTAR` 在 B 口径下逐位精确或远优于容差；
`QSW` 有界残差（7.25e-04 W/m²，容差 0.02+3e-5）；
`ZI`/`EL`/`WSTAR` 超差与所选风场无关（见 §4）。

### 3.3 口径 A−B —— P6D 风场重建段引入的端到端误差

`compare --reference <B 候选> --candidate <A 候选>`。27 个风场字段与 8 个 `T-LEV 2..9` 在两口径下**都是缺测**，
故分母 0 且 `miss(ref/cand) = 357500/0`，仍逐字段列出：

| 字段 | 分母 | miss(ref/cand) | max_abs | max_rel | 容差 | 超差 | 判定 |
|---|---|---|---|---|---|---|---|
| `U-LEV 1..9`, `V-LEV 1..9`, `WFACE 1..9`（27 个） | 0 | 357500/0 | 0 | 0 | 1e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `T-LEV 2..9`（8 个） | 0 | 357500/0 | 0 | 0 | 5e-4 + 1e-5·\|ref\| | 0 | NOT_PRODUCED |
| `T-LEV 1` | 357500 | 0/0 | 5.7983e-04 | 2.0921e-06 | 5e-4 + 1e-5·\|ref\| | 0 | **PASS** |
| `IPGT` | 357500 | 0/0 | 0 | 0 | 0（精确） | 0 | **PASS** |
| `USTAR` | 357500 | 0/0 | 5.7228e-05 | 4.8966e-04 | 3e-5 + 5e-5·\|ref\| | **9213** | **FAIL** |
| `ZI` | 357500 | 0/0 | 7.48291e-02 | 1.8529e-04 | 0.07 + 8e-5·\|ref\| | 0 | **PASS** |
| `EL` | 357500 | 0/0 | 18282 | 7.69106e-02 | 0.04 + 5e-5·\|ref\| | **1260** | **FAIL** |
| `WSTAR` | 357500 | 0/0 | 4.9968e-04 | 2.4403e-02 | 2e-5 + 3e-5·\|ref\| | **159** | **FAIL** |
| `TEMPK` | 357500 | 0/0 | 5.7983e-04 | 2.0921e-06 | 3e-4 + 1e-5·\|ref\| | 0 | **PASS** |
| `RHO` | 357500 | 0/0 | 2.7418e-06 | 2.1196e-06 | 1e-5 + 1e-5·\|ref\| | 0 | **PASS** |
| `QSW` | 357500 | 0/0 | 0 | 0 | 0.02 + 3e-5·\|ref\| | 0 | **PASS** |
| `IRH` | 357500 | 0/0 | 0 | 0 | 0（精确） | 0 | **PASS** |

汇总：**PASS 7 / FAIL 3 / NOT_PRODUCED 35**（45 字段）。

### 3.4 辅助表 AUX —— P6F 重建 `CALMET.DAT` vs 冻结 `met.dat`（风场段的直接判定）

P6E `emit-realcase` 不写出风场，所以 27 个 P6D 风场字段的**直接**判定放在这里：把 P6F 写出的
`CALMET.DAT` 本体与冻结文件对照。其中 U/V/W 来自 P6D，其余 18 个字段是 P6F 从冻结文件逐值拷贝
（用于证明拷贝语义，不应有差）。

| 字段 | 分母 | miss | max_abs | max_rel | 容差 | 超差 | 判定 |
|---|---|---|---|---|---|---|---|
| `U-LEV 1` | 357500 | 0/0 | 1.51843e-03 | 953.912 | 1e-4 + 1e-5·\|ref\| | 1413 | FAIL |
| `V-LEV 1` | 357500 | 0/0 | 1.31562e-03 | 16305 | 1e-4 + 1e-5·\|ref\| | 884 | FAIL |
| `WFACE 1` | 357500 | 0/0 | 2.6536e-04 | 1491.51 | 1e-4 + 1e-5·\|ref\| | 36 | FAIL |
| `U-LEV 2` | 357500 | 0/0 | 0.564197 | 25.9374 | 1e-4 + 1e-5·\|ref\| | 357306 | FAIL |
| `V-LEV 2` | 357500 | 0/0 | 0.565827 | 10.2959 | 1e-4 + 1e-5·\|ref\| | 357098 | FAIL |
| `WFACE 2` | 357500 | 0/0 | 3.81483e-03 | 4.1524e+07 | 1e-4 + 1e-5·\|ref\| | 25181 | FAIL |
| `U-LEV 3` | 357500 | 0/0 | 1.36094 | 3.029e+05 | 1e-4 + 1e-5·\|ref\| | 357482 | FAIL |
| `V-LEV 3` | 357500 | 0/0 | 2.6993 | 3.029e+05 | 1e-4 + 1e-5·\|ref\| | 357314 | FAIL |
| `WFACE 3` | 357500 | 0/0 | 1.22024e-02 | 4.6137e+06 | 1e-4 + 1e-5·\|ref\| | 72519 | FAIL |
| `U-LEV 4` | 357500 | 0/0 | 2.21738 | 3.029e+05 | 1e-4 + 1e-5·\|ref\| | 357498 | FAIL |
| `V-LEV 4` | 357500 | 0/0 | 3.44477 | 3.029e+05 | 1e-4 + 1e-5·\|ref\| | 357433 | FAIL |
| `WFACE 4` | 357500 | 0/0 | 3.01357e-02 | 1.1954e+07 | 1e-4 + 1e-5·\|ref\| | 143530 | FAIL |
| `U-LEV 5` | 357500 | 0/0 | 2.90567 | 9.39176 | 1e-4 + 1e-5·\|ref\| | 357500 | FAIL |
| `V-LEV 5` | 357500 | 0/0 | 3.44192 | 54.016 | 1e-4 + 1e-5·\|ref\| | 357500 | FAIL |
| `WFACE 5` | 357500 | 0/0 | 8.51e-02 | 1.5729e+06 | 1e-4 + 1e-5·\|ref\| | 215410 | FAIL |
| `U-LEV 6` | 357500 | 0/0 | 3.69158 | 21.3543 | 1e-4 + 1e-5·\|ref\| | 357499 | FAIL |
| `V-LEV 6` | 357500 | 0/0 | 4.07169 | 132.81 | 1e-4 + 1e-5·\|ref\| | 357478 | FAIL |
| `WFACE 6` | 357500 | 0/0 | 0.158154 | 57343 | 1e-4 + 1e-5·\|ref\| | 288588 | FAIL |
| `U-LEV 7` | 357500 | 0/0 | 6.28396 | 1733.66 | 1e-4 + 1e-5·\|ref\| | 357500 | FAIL |
| `V-LEV 7` | 357500 | 0/0 | 4.09881 | 32.7873 | 1e-4 + 1e-5·\|ref\| | 357500 | FAIL |
| `WFACE 7` | 357500 | 0/0 | 0.158166 | 6554.6 | 1e-4 + 1e-5·\|ref\| | 321427 | FAIL |
| `U-LEV 8` | 357500 | 0/0 | 10.0186 | 7.7289e+06 | 1e-4 + 1e-5·\|ref\| | 357500 | FAIL |
| `V-LEV 8` | 357500 | 0/0 | 6.76852 | 50.9976 | 1e-4 + 1e-5·\|ref\| | 357500 | FAIL |
| `WFACE 8` | 357500 | 0/0 | 0.158157 | 82.9049 | 1e-4 + 1e-5·\|ref\| | 337384 | FAIL |
| `U-LEV 9` | 357500 | 0/0 | 13.5074 | 33.4001 | 1e-4 + 1e-5·\|ref\| | 357500 | FAIL |
| `V-LEV 9` | 357500 | 0/0 | 6.70272 | 29.8419 | 1e-4 + 1e-5·\|ref\| | 357500 | FAIL |
| `WFACE 9` | 357500 | 0/0 | 0.158103 | 84.918 | 1e-4 + 1e-5·\|ref\| | 348363 | FAIL |
| `T-LEV 1..9`（9 个） | 357500 | 0/0 | 0 | 0 | 5e-4 + 1e-5·\|ref\| | 0 | PASS |
| `IPGT` | 357500 | 0/0 | 0 | 0 | 0（精确） | 0 | PASS |
| `USTAR` | 357500 | 0/0 | 0 | 0 | 3e-5 + 5e-5·\|ref\| | 0 | PASS |
| `ZI` | 357500 | 0/0 | 0 | 0 | 0.07 + 8e-5·\|ref\| | 0 | PASS |
| `EL` | 357500 | 0/0 | 0 | 0 | 0.04 + 5e-5·\|ref\| | 0 | PASS |
| `WSTAR` | 357500 | 0/0 | 0 | 0 | 2e-5 + 3e-5·\|ref\| | 0 | PASS |
| `TEMPK` | 357500 | 0/0 | 0 | 0 | 3e-4 + 1e-5·\|ref\| | 0 | PASS |
| `RHO` | 357500 | 0/0 | 0 | 0 | 1e-5 + 1e-5·\|ref\| | 0 | PASS |
| `QSW` | 357500 | 0/0 | 0 | 0 | 0.02 + 3e-5·\|ref\| | 0 | PASS |
| `IRH` | 357500 | 0/0 | 0 | 0 | 0（精确） | 0 | PASS |

**18 个非风字段逐位 0 差**证明 P6F 的拷贝语义正确；27 个风场字段的差异全部是数值差异（无缺测、无 NaN）。

---

## 4. 误差归因

### 4.1 A−B 差值把误差劈成"风场段"与"非风场段"

| 字段 | A 对原版 max_abs（超差） | B 对原版 max_abs（超差） | A−B max_abs（超差） | 归因 |
|---|---|---|---|---|
| `USTAR` | 5.7228e-05（9213） | 5.5134e-07（0） | 5.7228e-05（9213） | **完全是风场段**：B 已 PASS，A 的全部超差都由重建风场带来 |
| `EL` | 18282（1581） | 10734（630） | 18282（1260） | **风场段为主**：A−B 的 1260 格超差是风场增量，余下是 P6E 自身 |
| `ZI` | 51.0637（4465） | 51.0623（4488） | 7.48291e-02（**0**） | **不是风场段**：A、B 对原版的误差几乎相同，A−B 差值在容差内；主体是 P6E `MIXHT` |
| `WSTAR` | 2.62769e-02（5027） | 2.62769e-02（4880） | 4.9968e-04（159） | **主体不是风场段**：A、B 对原版几乎同量级，风场只贡献 159 格 |
| `TEMPK` | 5.7983e-04（0） | 0（0） | 5.7983e-04（0） | 风场段导致，但在容差内（`AVETMP` 的 IAVET=1 用风向来做上游平均） |
| `RHO` | 2.7418e-06（0） | 0（0） | 2.7418e-06（0） | 风场段经 `TEMPK` 传递，容差内 |
| `QSW` | 7.2479e-04（0） | 7.2479e-04（0） | **0** | 与风场无关（只依赖太阳几何与云量），A、B 对原版的同一残差属 P6E |
| `IRH`/`IPGT` | 0 | 0 | 0 | 风场段在此阈值下不可见 |
| `T-LEV 1` | 5.7983e-04（0） | 0 | 5.7983e-04（0） | 跟随 `TEMPK` |

**结论**：A 口径多出的 4 个 FAIL 里，`USTAR` 与 `EL` 是 P6D 风场段引入的真实增量误差；
`ZI`、`WSTAR` 本来就是 P6E 的问题，风场不是主因（A−B 对 `ZI` 甚至 0 超差）。

### 4.2 风场段自身随高度退化（AUX 表）

`U-LEV 1` 最大绝对差 1.518e-03 m/s、`V-LEV 1` 1.316e-03 m/s、`WFACE 1` 2.654e-04 m/s：近地层已经逼近原版。
但随高度单调退化：第 2 层约 0.56 m/s，第 5 层约 2.9 m/s，第 9 层 13.51 m/s。

结构性原因（与代码事实一致，非推测）：

1. A 口径的 U/V 是 P6D 的 **INTER2 融合结果**，**未经过**作用在 U/V 上的 DIAGNO `SMOOTH`（1-2-1 平滑）
   与 `DIVCEL`（无散度化）尾段——P6D 只把 `SMOOTH/DIVCEL/W` 的 **W 面**写出（`w_face`）。
2. P6D 未执行 `WINDBC`（边界条件段）。
3. `FRADJ` 仍是 `PENDING_GAMMA`（GAMMA 数组需 P6E 的 `CGAMMA` 链内状态，本 case 该分支实测无数值影响，
   但状态上仍未闭合）。
4. 近地层被观测站剖面强约束（`INTER2`、`WO=1.0`），上层主要由 IEXTRP=-4 的首猜决定，
   因此平滑/边界/散度化缺失的效应随高度放大。

---

## 5. 本轮发现并修复的 P6F 缺陷（P6G 首个实质产出）

**缺陷**：`native_cpp/modules/p6_calmet/p6f/src/p6d_fields.cpp` 的 `build_calmet_from_p6d`
把 P6D 的层主序平面（文档化布局 `idx = i + nx*(j + ny*k)`，metadata 的 `grid.layout_note` 也如此声明）
按 **cell-major** 读取：

```cpp
value = winds.u_mps[cell * levels + (level - 1)];      // 旧：静默置换整场
value = winds.w_face_mps[cell * (levels + 1U) + level];
```

对每个 `U-LEV/V-LEV/WFACE` 字段这是一次固定置换：格 `c` 取到的是平面元素 `c*NZ+(k-1)` 而不是 `c + cells*k`。
它不报错、不缺测、不产生 NaN，因此既有的 P6F 测试**没能发现**：`verify_p6d_array_input.py` 的合成夹具
按文档布局生成、又用同一套 cell-major 下标做期望值，两边犯同一个错，所以"自洽地"通过。

**证据（真实运行，`compare --reference <冻结 met.dat> --candidate <P6F 产物>`）**：

| 指标 | 修复前 | 修复后 |
|---|---|---|
| `U-LEV 1` max_abs | 6.68927 m/s | **1.51843e-03 m/s** |
| `V-LEV 1` max_abs | 5.98817 m/s | **1.31562e-03 m/s** |
| `WFACE 1` max_abs | 2.6403e-04 m/s | **2.6536e-04 m/s** |
| `U-LEV 9` max_abs | 21.2179 m/s | **13.5074 m/s** |
| A 口径判定 | PASS 5 / FAIL 5 | PASS 6 / FAIL 4 |

独立的布局诊断进一步确认平面是层主序：把 P6D 平面按 `i + nx*(j + ny*k)` 解释时，
`U-LEV 1` 对原版最大差 **5.77e-05 m/s**、`WFACE 1` 对原版最大差 **4.77e-08 m/s**；
按 cell-major 解释时分别为 3.983 m/s 与 1.817e-05 m/s。

**修复**：改为按文档布局取 `cell + cells*(level-1)`（U/V）与 `cell + cells*level`（W 面），
并删除随之失去引用的 `levels` 局部变量。
**回归保护**：`verify_p6d_array_input.py` 的期望值改为**按文档公式**重建
（`i + nx*(j + ny*k)`，W 面的顶层断言同样改为 `w[nx*ny*nz]`），不再复刻实现的下标算术——
修复前该测试会失败，修复后通过（`ctest -R p6f_calmet_dat21_p6d_array_input`：Passed，217.76 s）。

---

## 6. 未达成项与缺口（如实列出）

1. **A 口径仍有 4 个字段超容差**：`USTAR`(9213 格)、`ZI`(4465)、`EL`(1581)、`WSTAR`(5027)。
   `ZI`/`WSTAR` 的主体已归因于 P6E（见 §4.1），但**尚未修复**。
2. **P6D 风场上层未闭合**：`U-LEV 9` 最大绝对差 13.5074 m/s。缺口 = U/V 上的 `SMOOTH`/`DIVCEL`、
   `WINDBC`、以及 `FRADJ`（GAMMA）。P6D 的 `blend` 变体虽对未改动原版 `INTER2` 自证 PASS
   （metadata：143 h、6,435,000 分量、最坏 4.22e-05 m/s），但**"子程序等价"不等于"整段 DIAGNO 等价"**。
3. **P6E 不写出风场**：`U-LEV/V-LEV/WFACE` 在 A/B 两张表里分母恒为 0，这是产品边界而非失败；
   风场段的直接判定放在 §3.4 的 AUX 表。
4. **`T-LEV 2..9`**：在本 PR 的基点 `9197e6f` 上 P6E `emit-realcase` 只给 `T-LEV 1`（= `TEMPK`），
   9 层温度场缺 `TEMP3D` 的完整层结构；**当前 main `3be69bb` 已产出 `T-LEV 2..9`**（§8.4），
   其中 `T-LEV 5/6/7` 仍有 18/137/557 格超差，且已归因于 P6E `TEMP3D` 残差而非风场。
5. **降水/湿沉降不适用**：`NPSTA=0`，`RMM`/`IPCODE` 不写出，`P6_WET_FORCING_VALIDATED=FALSE`（无变化）。
6. **本站点代表性、扩散结果（P7）不在本轮范围**：本轮只做同源同控制的 143 时段逐格逐场判定。
7. **观察（未改码）**：P6F `write-from-p6d` 报告里 `variant_source_verified` 硬编码为
   `variant == "wind1"`，因此 `blend` 即使携带 P6D 的 PASS 判定也显示 `false`；
   `w_face_source_verified` 同样为 `false`。这两个标签与 metadata 的实际判定不一致，建议后续单独收敛。
8. **`IRTYPE=0` 与 `NPSTA=-1` 仍不支持**（P6F fail-closed，无本轮变化）。

---

## 7. 复现证据

**环境**：`lhy-desktop`，Linux 6.8.0 x86_64，g++-12 12.3.0，GNU Fortran 11.4.0，CMake 3.22.1，
Python 3.10.12；`--build-type Debug`（模块文档化的 `-Werror` 构建，Release 会因真实存在的
strict-aliasing 警告而失败，故不采用）。

**干净目录全量复现**（空 `clean/` + 空 `clean-work/`，包含三次 CMake 配置与四个目标的构建）：

```
$ cd /home/lhy/g6/CTEAS
$ /usr/bin/time -v python3 scripts/run_p6_end_to_end.py \
      --build-dir /home/lhy/build/g6/clean --work /home/lhy/build/g6/clean-work
...
[p6d]   32.82 s  exit=0
[p6f]   77.77 s  exit=0
[bridge]    0.19 s  exit=0
[p6e-A]  121.07 s  exit=0
[p6e-B]  120.90 s  exit=0
   A: PASS=6, FAIL=4, NOT_PRODUCED=35, NO_DATA=0  (of 45 fields)
   B: PASS=7, FAIL=3, NOT_PRODUCED=35, NO_DATA=0  (of 45 fields)
 A-B: PASS=7, FAIL=3, NOT_PRODUCED=35, NO_DATA=0  (of 45 fields)
total wall time: 477.87 s
Elapsed (wall clock) time (h:mm:ss or m:ss): 8:21.22
Maximum resident set size (kbytes): 402376
```

脚本退出码 1 = `FAIL_NUMERIC`（A/B 存在超差字段），即"如实报告失败"，不是崩溃；
`P6G_END_TO_END_BLOCKED`（退出码 3）在任一段 fail-closed 时才会出现。

**复现性**：连续两次独立运行（增量构建目录 `work/` 与空目录 `clean-work/`）的产物逐字节相同：

| 产物 | sha256 |
|---|---|
| 重建风场 `p6f/reconstructed_wind.dat`（P6F `write-from-p6d` 输出，62 MB） | `a309d4f1a97ff4f1de102e2543a417a8316afb531d1710871cf714a524f67c81` |
| A 候选 `A/candidate.dat`（P6E `emit-realcase`，重建风场驱动） | `f29fc56ec21cd0300c161aed55312bfa5072d11d9ad44e56269f8feed856f868` |
| B 候选 `B/candidate.dat`（P6E `emit-realcase`，原版风场驱动） | `036793b977155a46d0018142fdee75059ee4248b74c7d7fbb77b60382e23c1e1` |
| 观测桥 `bridge/hourly.csv`（E15） | `eae56e3b621acf018a6b47080fb393a35419b699412edf59a890c418858fa41e` |
| P6D metadata `p6d/metadata.json` | `3f4559cc7f623939e9c4b5c78315470ab996f045e66955e4a84d5d662f29c1ee` |
| 对照 A `compare_A.json` | `dfe27be0af2e91d2506051dcc0448c90cccab8b2cabc490fdf6123708243752d` |
| 对照 B `compare_B.json` | `c3926ddfac8c8ad30f09629f399efc4cf8a3e7ac570fff71dc3d827bc38933bf` |
| 对照 A−B `compare_AB.json` | `f2a8bbc38e787166016342b841ad4bf03d4a95631763a705a908c6d2b6dd58b8` |
| 对照 AUX `compare_wind.json` | `22d7d9f0390637c76b274e5ef7ac36b69dbd0830bff005414a9856d1622a82a8` |
| 汇总 `p6g_report.json` | `0fc513504e114027ad971f5fd9c133b89e837da0281e0b59abd40ce601e706a9` |

（`compare_*.json` 与 `p6g_report.json` 内嵌绝对路径，故其哈希随 `--work` 目录变化；上表取自
`clean-work/`。`.dat` 产物与 `p6d/metadata.json` 与路径无关，两次运行完全一致。）

**分段证据链**

- P6D：`metadata.json` `status = PARTIAL_WIND1_BLEND_SLOPE_TEMP2D_QH_TERSET`、`hourly_labels = 143`、
  `blend.verification = PASS_REALCASE_BLEND_ORIGINAL_INTER2…`、`FRADJ = PENDING_GAMMA`。
- P6F：`report.json` `status = PASS_WRITTEN_FROM_P6D_ARRAYS`、`variant = blend`、`w_field = w_face`、
  `irtype = 1`、`hours_written = 143`、`out_sha256 = a309d4f1…`。
- E15：`hourly.csv` 表头 + 143 行（一站一探空的逐小时观测轨迹），桥自身 `exit=0`。
- P6E：`A/candidate.json`、`B/candidate.json` 的 `produced_fields` 含
  `TEMPK/IRH/T-LEV 1/QSW/RHO/IPGT/USTAR/EL/ZI/WSTAR`，其余为 `9999.` 缺测。

**本轮改动文件**

- `scripts/run_p6_end_to_end.py`（新增，端到端运行器）
- `native_cpp/modules/p6_calmet/p6f/src/p6d_fields.cpp`（修 U/V/W 平面索引映射）
- `native_cpp/modules/p6_calmet/p6f/tests/verify_p6d_array_input.py`（期望值改为按文档布局独立重建）
- `docs/reconstruction_cpp/P6G_END_TO_END_20261012.md`（本记录）
- `docs/reconstruction_cpp/P6_A_TO_G_SEQUENTIAL_EXECUTION_LEDGER.md`（P6G 行）

---

## 8. 并入最新 main 后的复跑（base `3be69bb`）——当前 main 的判定

本 PR 合入时 main 已前进到 `3be69bb`（含 P6E E31–E35：`calmet_dat21_tool_main.cpp` 增量 69 行、
`temp3d_observed_land.hpp` 增量 23 行），P6E 现在会通过 `TEMP3D` 产出 `T-LEV 2..9`。
为给出**当前 main** 的判定，把同一条命令在 `3be69bb` 上从空目录重跑（P6D/P6F 段源码与 §3 相同）。
（此后 main 又前进到 `2c03ad4`，但 `native_cpp/modules/p6_calmet/**` 与 `scripts/run_p6_end_to_end.py`
在 `3be69bb..2c03ad4` 之间**没有变化**，故本节数字仍对应当前 main 的代码状态。）

**命令与耗时**（`/home/lhy/g6/CTEAS-main`，空 `main/` 与空 `main-work/`）：

```
[p6d]   32.77 s  exit=0
[p6f]   77.75 s  exit=0
[bridge]    0.19 s  exit=0
[p6e-A]  122.19 s  exit=0
[p6e-B]  122.20 s  exit=0
   A: PASS=11, FAIL=7, NOT_PRODUCED=27, NO_DATA=0  (of 45 fields)
   B: PASS=12, FAIL=6, NOT_PRODUCED=27, NO_DATA=0  (of 45 fields)
 A-B: PASS=15, FAIL=3, NOT_PRODUCED=27, NO_DATA=0  (of 45 fields)
total wall time: 480.77 s
Elapsed (wall clock) time (h:mm:ss or m:ss): 8:23.59
```

27 个 P6D 风场字段在 A、B 两表中仍是 `NOT_PRODUCED`（分母 0，`miss(ref/cand)=0/357500`），
在 A−B 表中是 `NOT_PRODUCED`（分母 0，`miss=357500/0`）；与 §3 逐字相同，不再重复。
所有 18 个已产出字段的分母均为 357500、`miss(ref/cand)=0/0`，容差见 §2。

### 8.1 A —— 重建风场驱动 vs 冻结 `met.dat`

| 字段 | max_abs | max_rel | 超差 | 判定 |
|---|---|---|---|---|
| `T-LEV 1` | 5.7983e-04 | 2.0921e-06 | 0 | PASS |
| `T-LEV 2` | 4.5776e-04 | 1.6475e-06 | 0 | PASS |
| `T-LEV 3` | 1.58691e-03 | 5.593e-06 | 0 | PASS |
| `T-LEV 4` | 8.2397e-04 | 2.9116e-06 | 0 | PASS |
| `T-LEV 5` | 4.28772e-02 | 1.5394e-04 | **18** | **FAIL** |
| `T-LEV 6` | 1.43555 | 5.10876e-03 | **137** | **FAIL** |
| `T-LEV 7` | 2.51669 | 9.09273e-03 | **557** | **FAIL** |
| `T-LEV 8` | 0 | 0 | 0 | PASS |
| `T-LEV 9` | 0 | 0 | 0 | PASS |
| `IPGT` | 0 | 0 | 0 | PASS |
| `USTAR` | 5.7228e-05 | 4.8966e-04 | **9213** | **FAIL** |
| `ZI` | 51.0637 | 5.61028e-02 | **4465** | **FAIL** |
| `EL` | 18282 | 7.69106e-02 | **1581** | **FAIL** |
| `WSTAR` | 2.62769e-02 | 2.4397e-02 | **5027** | **FAIL** |
| `TEMPK` | 5.7983e-04 | 2.0921e-06 | 0 | PASS |
| `RHO` | 2.7418e-06 | 2.1196e-06 | 0 | PASS |
| `QSW` | 7.2479e-04 | 6.3625e-05 | 0 | PASS |
| `IRH` | 0 | 0 | 0 | PASS |

汇总：**PASS 11 / FAIL 7 / NOT_PRODUCED 27**。

### 8.2 B —— 原版风场驱动 vs 冻结 `met.dat`

| 字段 | max_abs | max_rel | 超差 | 判定 |
|---|---|---|---|---|
| `T-LEV 1` | 0 | 0 | 0 | PASS |
| `T-LEV 2` | 1.2207e-04 | 4.2992e-07 | 0 | PASS |
| `T-LEV 3` | 1.5564e-03 | 5.4855e-06 | 0 | PASS |
| `T-LEV 4` | 8.5449e-04 | 3.0181e-06 | 0 | PASS |
| `T-LEV 5` | 4.29382e-02 | 1.5416e-04 | **18** | **FAIL** |
| `T-LEV 6` | 1.43555 | 5.10876e-03 | **137** | **FAIL** |
| `T-LEV 7` | 2.51669 | 9.09273e-03 | **558** | **FAIL** |
| `T-LEV 8` | 0 | 0 | 0 | PASS |
| `T-LEV 9` | 0 | 0 | 0 | PASS |
| `IPGT` | 0 | 0 | 0 | PASS |
| `USTAR` | 5.5134e-07 | 5.0724e-06 | 0 | PASS |
| `ZI` | 51.0623 | 5.61028e-02 | **4488** | **FAIL** |
| `EL` | 10734 | 3.22548e-02 | **630** | **FAIL** |
| `WSTAR` | 2.62769e-02 | 1.9062e-02 | **4880** | **FAIL** |
| `TEMPK` | 0 | 0 | 0 | PASS |
| `RHO` | 0 | 0 | 0 | PASS |
| `QSW` | 7.2479e-04 | 6.3625e-05 | 0 | PASS |
| `IRH` | 0 | 0 | 0 | PASS |

汇总：**PASS 12 / FAIL 6 / NOT_PRODUCED 27**。

### 8.3 A−B —— P6D 风场重建段引入的端到端误差（当前 main）

| 字段 | max_abs | max_rel | 超差 | 判定 |
|---|---|---|---|---|
| `T-LEV 1` | 5.7983e-04 | 2.0921e-06 | 0 | PASS |
| `T-LEV 2` | 4.5776e-04 | 1.6475e-06 | 0 | PASS |
| `T-LEV 3` | 4.5776e-04 | 1.6492e-06 | 0 | PASS |
| `T-LEV 4` | 4.5776e-04 | 1.6527e-06 | 0 | PASS |
| `T-LEV 5` | 4.8828e-04 | 1.7661e-06 | 0 | PASS |
| `T-LEV 6` | 4.2725e-04 | 1.5682e-06 | 0 | PASS |
| `T-LEV 7` | 8.5449e-04 | 3.1456e-06 | 0 | PASS |
| `T-LEV 8` | 0 | 0 | 0 | PASS |
| `T-LEV 9` | 0 | 0 | 0 | PASS |
| `IPGT` | 0 | 0 | 0 | PASS |
| `USTAR` | 5.7228e-05 | 4.8966e-04 | **9213** | **FAIL** |
| `ZI` | 7.48291e-02 | 1.8529e-04 | 0 | PASS |
| `EL` | 18282 | 7.69106e-02 | **1260** | **FAIL** |
| `WSTAR` | 4.9968e-04 | 2.4403e-02 | **159** | **FAIL** |
| `TEMPK` | 5.7983e-04 | 2.0921e-06 | 0 | PASS |
| `RHO` | 2.7418e-06 | 2.1196e-06 | 0 | PASS |
| `QSW` | 0 | 0 | 0 | PASS |
| `IRH` | 0 | 0 | 0 | PASS |

汇总：**PASS 15 / FAIL 3 / NOT_PRODUCED 27**。

### 8.4 归因更新（新增 `T-LEV 2..9`）

- `T-LEV 2/3/4/8/9` 已产出且在两种口径下都 PASS，A−B 也 PASS。
- **`T-LEV 5/6/7` 在两种口径下都 FAIL**，且 A、B 的 max_abs 几乎相同（`4.28772e-02` vs `4.29382e-02`、
  `1.43555` vs `1.43555`、`2.51669` vs `2.51669`），而 A−B 的 max_abs 只有 `~5e-04` 且 0 超差：
  **这是 P6E `TEMP3D` 的残差，不是风场段的问题**（与 `ZI`/`WSTAR` 同一类）。
- `USTAR` 仍是唯一"B PASS、A FAIL"且 A−B 超差全部来自风场段的字段；
  `EL` 以风场段为主，`WSTAR` 的风场贡献只有 159 格。

### 8.5 当前 main 的复现哈希

| 产物 | sha256 |
|---|---|
| 重建风场 `p6f/reconstructed_wind.dat` | `a309d4f1a97ff4f1de102e2543a417a8316afb531d1710871cf714a524f67c81`（与 §7 逐字节相同） |
| A 候选 `A/candidate.dat` | `b60b50b773de47f5ae69296c5bb0363e9d0d1b8742b3a5741df952ddf626645b` |
| B 候选 `B/candidate.dat` | `71f4afbd5c3f003969a915ac4b479d39adba28676bf5f7ac32c9d68003ae36dc` |
| 观测桥 `bridge/hourly.csv` | `eae56e3b621acf018a6b47080fb393a35419b699412edf59a890c418858fa41e`（与 §7 相同） |
| `compare_A.json` | `b3f51f14105a3bc1175fc73403ce3f6d4b24b8e99c82c556577d50fce63e9d48` |
| `compare_B.json` | `b17b20fd654cef46f7d0f7ab8e9c90a475f60df489f5bf2e520b0329d83be128` |
| `compare_AB.json` | `8853040bbf2d76df77ee5abc718c260950b6fb08592f518510a297316d5046a6` |
| `compare_wind.json` | `4cc13bf5bb502d63730ab9893e533c3bd1c8db4d1a17fcf72cb0bb37022b7021` |
| `p6g_report.json` | `030ff8a4c0153d2ae97632e71842d4213774e1103d381577cbf8044999b186f5` |

`p6d/metadata.json` 内嵌案件树绝对路径，故其哈希随 `--case` 路径变化（本次 `3f731ced…`，案件树经符号链接解析）；
`reconstructed_wind.dat` 与 `bridge/hourly.csv` 与路径无关，跨基点（`9197e6f` / `3be69bb`）逐字节相同。
