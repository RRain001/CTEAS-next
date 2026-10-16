# P6 CALMET 6.5.0 — 合肥 100 m 科研最小重构总计划
Date: 2026-10-11. Status: **P6A_PASS_SOFTWARE, P6B_ORIGINAL_CALMET_REFERENCE_PASS, P6C_PASS_SCOPED_HEFEI_2022_OBSERVATIONS, P6D_READY_FOR_INTEGRATION_NOT_PASS (FRADJ isolated PASS), P6E–G_NOT_COMPLETE, P6_FULL_SOLVER_INCOMPLETE, P6_CALPUFF_READY_FALSE**.
Authority: user-chosen research-specific **minimal reconstruction**; no claim of full CALMET feature parity.
Repository: `RRain001/CTEAS`; immutable foundation `60b7b1d93866fff772926b6ac32dc0af7235552b`; implementation branch `codex/cteas-p6-calmet-hefei-100m`. Do not edit any existing P1–P5 branch, source or the original `engine/vendor/src`.

**2026-10-11 P6C 独立原版最终观测预处理验收 PASS（固定 2022 研究案例）**：在此前 GEO/UP/SURF、TERSET/DIAGI/VERTAV/PREPDI/FACET 原版数值证据之上，[原版 143h COMP + RDSN + CGAMMA 完整复算 CI](https://github.com/RRain001/CTEAS/actions/runs/38113874913) 通过：AA/BB 两物理缓冲 286 时次、RDSN 1,144 个真实观测字段及 858 个时次、CGAMMA 143 个真实源码调用（86 正常插值/51 当前对流/6 先前对流状态）全部 PASS，最大直减率误差 5.0e-11 K/m；临时只读插桩与原版 MET.DAT SHA 完全相同。专项 [RDSN/CGAMMA 审计](P6C_RDSN_CGAMMA_2022_AUDIT.md) 及 [A→G 最终阶段台账](P6_A_TO_G_SEQUENTIAL_EXECUTION_LEDGER.md) 为本阶段最新状态依据。**下面仍带有 P6C PARTIAL/COMP 未验证字样的是过往分期验收记录，已被本段最新结果覆盖。P6D 三维诊断风场集成允许开始但尚未 PASS；P6E–G 不得跳过。** 仅验收一地面虚拟站 + 探空站 58424、真实 143 小时的固定格式输入；降水 IPCODE 143/143 缺测、NPSTA=0 继续独立 HOLD，禁止湿沉降可用性宣称。



**2026-10-11 P6C UP.DAT v2.1**：[P6C_UPDAT_RDUPN_2022_AUDIT.md](P6C_UPDAT_RDUPN_2022_AUDIT.md)：原版 `COMP` 对 v2.1 调用 `RDUPN`（不是老 `RDUP`）；真正 2022 年 P4 `UP.DAT` 的 13 条探空记录、785 层、6,280 原生 Fortran/C++ 读入与 U/V、高度转换字段 **PASS**。P6C 尚欠 `COMP` AA/BB 各时段资料选择、`VERTAV/FACET` 垂直插值及原版观测场集成对照，仍然不能标 P6C COMPLETE 或开启 P6D 整链。

**2026-10-11 P6C 模型层/时次物理对照更新**：[P6C_VERTAV_PREPDI_FACET_2022_AUDIT.md](P6C_VERTAV_PREPDI_FACET_2022_AUDIT.md)。真实 P4 2022 13 次探空：原版 `VERTAV` 完整源码风速层积分 **234/234 PASS**；原版 `PREPDI` 逐层时次插值源码片段和独立时次序列 **2574/2574 PASS**（143h×9层×U/V，最大 U/V 误差 5.0E-9 m/s）；原版 `FACET+INTP` 两个完整子程序 **130/130 PASS**（最大 5.0E-9 K）；原版 CALMET 同一 CI 完整参考结果回归 PASS。**P6C 仍 PARTIAL**：原版 `COMP` 实际 AA/BB 缓冲状态、全部逐时有效性与观测场合成未完成，P6D–G 暂缓。

**2026-10-11 P6C READGE/SURF 真正案例数据实测对照**：[P6C_READGE_SURFACE_2022_AUDIT.md](P6C_READGE_SURFACE_2022_AUDIT.md)。原版 P3 实际 GEO.DAT 8 字段 × 2500 单元的原生 Fortran 读取对照 **20,000/20,000 PASS**；原版 P5/SMERGE 新的 2022 SURF.DAT 143 时段 × 8 气象值及站点时次标识，原生 Fortran 输入格式对照 **PASS**。目前有效降水代码 **0/143**；P6C 仅部分完成，2022 UP.DAT/RDHDU/RDUP/站点插值及垂直高度时次处理仍需原版对照，P6D 集成按用户要求继续 HOLD。

**顺序执行台账（用户明确要求 P6A→P6G 严格逐阶段验收）**：[P6_A_TO_G_SEQUENTIAL_EXECUTION_LEDGER.md](P6_A_TO_G_SEQUENTIAL_EXECUTION_LEDGER.md)。当前 P6C 仍未完成；已通过的独立 `FRADJ` 单元对照不等于 P6D 阶段验收，不允许跳过 P6C 的真实资料读取与时间/高度处理。

## 0. Current evidence, critical distinction

- Original P6: `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`, Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`, ~1.46 MB; `calmet.inp` Git blob `8f0a6b6d2150c56d0e3724f3972aed67f7a00fcc` (control file SHA256 `159161afd6db598a73614acc9525179ff9c842df80402403f06c4a5611f30da7`); `cpl.txt` Git blob `c0d9fa57734bfcf7cf108bd7505e7f76cf79412c`, relevant `*.met` common blocks. The compiler's routine inventory and original control text are initial anchors. **This is an inventory, not a completed line-by-line physical-code audit.**
- The committed `calmet.inp` is a **legacy example**: 2000 dates, `NX=NY=100`, `DGRIDKM=1`, generic `SS1`/`US1` placeholders and a 2023 path. **It is not a real 2022 Hefei 50×50 100 m runnable control file.** Never use the sample to certify the study.
- P3 [PR #5](https://github.com/RRain001/CTEAS/pull/5): real and synthetic scoped `GEO.DAT 2.1` eight fields, 20,000/20,000 printed field matches against original Fortran. Its legacy output writer is independent; no P1/P2 modern standalone full pipeline yet.
- P4 [PR #6](https://github.com/RRain001/CTEAS/pull/6): current scoped C++ READ62 `JDAT=2,IFMT=1` **full-year 2022 UP.DAT byte-identical to original Fortran** (730 profiles); pinned commit `dc4e3f0`. Other READ62 options not implemented.
- P5 [PR #7](https://github.com/RRain001/CTEAS/pull/7): current 2022 ISD/Lite processing inputs can be supplied to **original SMERGE** to publish `SURF.DAT`; new pinned source `dd473ce`. C++ P5 is not declared a complete source-equivalent SURF.DAT writer.
- **A usable 2022 original CALMET numerical reference now exists** for P6 diagnostic+micrometeorology **without precipitation**. Independent source-pinned workflow P6B reproduced `MET.DAT`, SHA256 `968b2dd24f0eb4ad428709b52a154d9022e8c7e37a4be3fb9498e3d7e756d04e`, and proved **143 one-hour intervals × 45 fields** from 144 endpoint labels. Separate original-subroutine reference audits P6C TERSET / P6D FRADJ have PASS; full C++ wind field equivalence remains untested. See [P6_CALMET_BCD_REFERENCE_AUDIT.md](P6_CALMET_BCD_REFERENCE_AUDIT.md). No rainfall source has been qualified for wet deposition.

## 0.1 Newly supplied historical *complete* P1–P7 case (2026-10-10)

The user newly pushed the old successful-through-P7 case under `project/cases/smoke5d_coldstart_20260701` in `main` `2908293f061af93e754bc9fe1f00d857d1d6a0d8`. Its control-file audit is committed in **[`P6_HISTORICAL_SMOKE5D_INP_AUDIT.md`](P6_HISTORICAL_SMOKE5D_INP_AUDIT.md)**. This is the preferred *historical configuration* reference for P6, more operationally specific than the bundled vendor example, but **never** a numerically trusted meteorology baseline: the user explicitly states the old processing was erroneous.

Critical distinctions: old study **2023 Jan 1–5**, centered **117.0°E/32.0°N**, **50 km × 50 km @ 1 km**, compared with target **2022 Jan 1–6**, stack-centered **5 km × 5 km @ 0.1 km**. Both have 50×50 and identical nine vertical layers, so a dimension-only validator would miss serious wrong-domain reuse.

Historical P6 `run/met/met.inp` enables diagnostic wind, slope flow and Froude effects; original `NOOBS=0, IPROG=0, IRTYPE=1, IFRADJ=1, ISLOPE=1, IEXTRP=-4, IFORMO=1, IFORMS=2`. This validates that these **switches were operationally used** in the old workflow, not that their physics have been reconstructed. Old P5 `119` records includes 41 missing cloud values and **zero valid precipitation-code values**, old P6 `NPSTA=0`, and old P7 `MWET=0`. None of this can be transplanted into a scientific wet-deposition scenario. Check the 119-record vs 120-label *time-boundary convention* before interpreting a discrepancy. P6 P4/P5 source compatibility and new precipitation remain gated.

## 1. Frozen study geometry, subject to Fortran-control verification

- Hefei stack center: 31.939774444 N, 117.141610855 E. Entire model domain **5,000 m × 5,000 m** centered on stack, **not 5 km radius**. Cartesian `50×50` at `0.100 km`, grid origin SW *cell corner*, i-fastest / j increasing northwards; UTM zone 50 N, WGS84. Use the P1/P2/P3 independently verified case origin rather than recomputing/rounding stack coordinates.
- Nine CALMET cell layers, 10 interfaces: `ZFACE=[0,20,40,80,160,320,640,1200,2000,3000] m`. Do not confuse interface heights, layer-center heights, heights AGL, MSL, or sensor heights.
- 2022-01-01 00:00 through 2022-01-06 23:00, 144 nominal hourly labels. **`ABTZ`, `NSECDT`, observation-time conventions, beginning/ending-of-hour labels, and Fortran `CALMET.DAT` record semantics must be proven, not inferred.** No automatic assumption that nominal 144 labels = 144 saved records.
- Retain surface roughness, elevation, albedo, Bowen ratio, soil heat flux, anthropogenic heat flux, LAI, dominant land-use / water mask from verified P3; suppress unsupported inputs fail-closed.
- Stack emission/physical source parameters belong to P7 CALPUFF, **not** P6 CALMET input (prevent scope leakage).

## 2. Research-critical physics: mandatory vs optional

The first end-to-end *usable* P6 must support a selected original-observations pathway:
`NOOBS=0`, `IWFCOD=1` diagnostic wind, `IPROG=0`, `IRTYPE=1`, gridded non-snow GEO, surface station winds/temperature/humidity/cloud, upper-air profiles, and meteorological variables used by CALPUFF. These are **proposed study choices**, not asserted final original controls. Station counts and precipitation mode remain pending user data.

| Workstream | Original CALMET routines (initial anchors from compiler listing) | Original control levers | Research importance / gate |
|---|---|---|---|
| Time, geometry, consistency, upper/surface/geophysical readers | `SETUP`, `READCF`, `READGE`, `READHD`, `RDHD`, `RDHDU`, `RDS`, `RDUP`, `RDP` | Groups 0–4: `GEODAT`, `SRFDAT`, `UPDAT`, `IBYR..`, `IEYR..`, `ABTZ`, `NSECDT`, `PMAP`, `NX`, `NY`, `NZ`, `ZFACE`, `NOOBS`, `IFORMS`, `NPSTA` | Mandatory; no fabricated inputs or invisible time shifts |
| Terrain gradients and initial diagnostic adjustments | `TERSET`, `TOPOF2`, `SLOPE`, `FRADJ`, `WIND1`, `PREPDI`, `DIAGNO`, `DIAGI`, `DIAG2`, `BARIER` | Group 5 `IWFCOD`, `IFRADJ`, `ISLOPE`, `IKINE`, `IOBR`, `TERRAD`, `CRITFN`, `ALPHA`, `NBAR` | **Must retain every effect enabled in the frozen real control.** The example currently has Froude and slope ON, kinematic and O'Brien OFF. Terrain-following geometry must be source-verified. |
| Observational wind reconstruction and blending | `INTERP`, `INTP`, `INTER2`, `PROGRD`, `WIND1`, `SMOOTH`, `MINIM`, `DIVPR`, `DIVCEL`, `ADJUST`, `SIMILT` | `IEXTRP`, `ICALM`, `BIAS`, `RMIN2`, `RMIN`, `RMAX1/2/3`, `R1`, `R2`, `DIVLIM`, `NITER`, `NSMTH`, `NINTR2` | Mandatory selected route: surface/profile heights, calm wind, objective weights, Step 1/Step 2 fields, divergence metrics; mapping of each routine to physical phase subject to full source audit |
| Temperature/humidity, radiation and surface fluxes | `TEMP3D`, `AVETMP`, `SURFVAR`, `SOLAR`, `HEATFX`, `PGTSTB`, `ELUSTR`, `AIRDen` | `IRHPROG`, `ITPROG`, `TRADKM`, `IRAD`, `NUMTS`, `IAVET`, `TGDEFB`, `TGDEFA` | Mandatory for `IRTYPE=1` CALPUFF chain, not an optional cosmetic field |
| Boundary-layer and stability / mixing-height | `MIXHT`, `MIXHT2`, `MIXHTST`, `MIXHMC`, `AVEMIX`, `HEATFX`, `WSTARR` | `IMIXH`, `CONSTB`, `CONSTE`, `CONSTN`, `FCORIOL`, `IAVEZI`, `MNMDAV`, `HAFANG`, `IZICRLX`, `TZICRLX`, `ZIMIN`, `ZIMAX` | Mandatory mixed-layer / Monin-Obukhov / friction velocity and convection parameters for CALPUFF |
| Precipitation and cloud | `RDP`, `RDPN`, `RDS`, `RDCLD`, `CLOUD3`, `CLOUD4` | `NPSTA`, `IFORMP`, `ICLOUD`, `NFLAGP`, `SIGMAP`, `CUTP` | **Separate forcing blocker:** P5 SURF.DAT alone is not proof of valid CALMET precipitation station input; a verified precip path is required for wet-deposition studies |
| CALMET output for downstream CALPUFF | `OUTFIL`, `OUTHD`, `OUTHR`, `PACK`, `OUTPC`, `WRT*` | `METDAT`, `LSAVE`, `IFORMO`, `IRTYPE=1`, `LCALGRD` | Preserve original file version/record order/time, arrays, masked values, units and provenance; downstream P7 read test required |

**Optional legacy branches not targeted initially**: `NOOBS=1/2` prognostic-only; `IPROG` CSUMM/MM4/MM5/WRF/3D meteorology; `IGFMET` coarse-CALMET input; `NOWSTA`/SEA.DAT, overwater `COARE`/OCD flux, wave/SST handling, `LLBREZE` lake-breeze boxes; gridded CLOUD.DAT prognostic modes and other output/QA modes. **Only exclude after final 2022 control and landuse/water characterization confirm they are unused**. For any requested off-branch mode, fail closed; document original procedure and switch rather than silently ignore.

### Why ordinary “wind-only” / simplified power law is insufficient
- `IRTYPE=0` produces wind-only fields; it is **not** a CALPUFF-ready replacement for the selected CALMET chain.
- Simple inverse-distance station winds are not equivalent to terrain-adjusted `IWFCOD=1` with `IFRADJ=1` and `ISLOPE=1`; Step 1/2 differences and vertical divergence must be compared.
- No missing station data should be silently filled, no scientific constants retuned to fit output, no option silently defaulted.

## 3. Dependencies and ownership

P3 supplies `GEO.DAT v2.1` as a *pinned input*. P4 must supply independently validated, original-compatible `UP1.DAT` (with station ID, sounding layers, units, validity); P5 must supply original-compatible `SURF.DAT` (with hourly station observations and validity). Verify P4/P5 file-format choices match P6 `IFORMS` and time-zone controls exactly.

**Current P4/P5 public meteorological capture workflows are not substitute evidence of `UP.DAT` / `SURF.DAT` Fortran parity.** The P6 branch must not change P4/P5 source or tests or “repair” their output implicitly. Interface adapters must be explicit, local to P6, and versioned when provided. The authors of P4/P5 retain authority over those branches.

One P6 owner controls P6 option contracts/physics; parallel tasks allowed only after interfaces are frozen: (a) input readers/time QA; (b) wind diagnostics/terrain; (c) surface/BL physics; (d) independent output parser + reference comparison. Avoid multiple agents modifying the same files or shared branch concurrently.

## 4. Execution plan and stop/go criteria

| Substage | Deliverable | Data prerequisites | Exit criterion |
|---|---|---|---|
| **P6A** — inventory/control contract | Source version/blob inventory; original control / routine path matrix; case geometry/time/units/validity schema; strict fail-closed C++20 module + CTest | No weather needed | PASS_SOFTWARE_CONTRACT_ONLY; intentionally **no physics equivalence** |
| **P6B** — original input/output capture | Source-pinned real 2022 P3/P4/P5 GEO/UP/SURF, original SMERGE and unchanged original CALMET; original CALMET.DAT record/time/field decoder | **PASS**, precipitation mode `NPSTA=0` explicitly retained for diagnostic-reference only | Original `MET.DAT` SHA256 and 7,562 Fortran records; 143 hourly intervals/45 meteorology fields each, no missing or reordered field labels |
| **P6C** — geometry and observation preprocessing | Terrain-following height transformations, station spatial mapping, surface-height adjustment, upper profiles, height/UTC interpolations, masks | Real or artificial snapshots; golden original P6 intermediate states | Unit/geometry/synthetic tests; then Fortran comparison per stage |
| **P6D** — diagnostic 3D wind | Froude `FRADJ` **isolated original parity PASS**; still must implement slope `SLOPE`, observation `WIND1`/`SIMILT`, `DIAGNO`, smoothing/divergence and complete 3D wind | P6B runnable data and frozen original subroutine outputs | Current original 7-case FRADJ/TERSET compare: 315,000 U/V values PASS. **Full P6D is NOT yet passed**: separate full-hour `u/v/w`, validity, physics and station-weight reference required |
| **P6E** — complete surface and boundary-layer physics | Radiation, friction velocity, sensible heat, stability, mixing depth, 3D temperature/RH, precip/cloud | P6D + verified surface upper/precip | Independent reference per output and intermediate field on day/night/stable/convective/rain |
| **P6F** — `CALMET.DAT` writer | Original versioned header/record and binary/text formats, correct time indexing, field ordering, SI/display conversions | P6D/E physics | Original reader and CALPUFF original P7 reader accept C++ product; checksums/record count and numeric comparison |
| **P6G** — full-scoped scientific acceptance | Compare **143 hourly intervals over 144 endpoint labels** of original/C++ P6 under identical inputs; audit per field time/layer/cell and cases | P6B–F; independent reviewers | `PASS_REFERENCE_SCOPED_P6_HEFEI_100M` and separate physical observation validation clearly distinguished |

Important: a software PASS, synthetic field or C++ writer's successful self-read **never establishes original Fortran parity**. Fortran source-to-C++ physical formulas, array ordering and original implicit `REAL*4` behavior are audited at each phase. Do not loosen tolerance after inspecting failures.

## 5. Reference comparison and QC protocol to freeze before numerics

1. **Provenance:** original Fortran source SHA/commit, compiler and options, input and control hashes; preserve isolated `stdout/stderr`, `CALMET.LST`, `CALMET.DAT` and key intermediate diagnostics. Original sources read-only; record any unavoidable original compatibility shims outside vendor tree.
2. **Dimensions and time:** compare `NX×NY×NZ×record_count` with explicit layer-face and local/UTC policy. For each field record valid/missing denominators, NaN/Inf, masked positions, exact categorical/QC flags, unsupported options and unit conversions.
3. **Physics fields:** step-1 and final `u/v/w` (m/s), flow/stability/terrain flags, friction velocity `u*`, Monin–Obukhov length, convective `w*`, `zi` (m), temperature (K), RH (%), precip (mm/h), cloud, surface flux (W/m²). Detailed availability and units must be confirmed from the selected original `CALMET.DAT` version before freezing comparisons.
4. **Error metrics:** for floats: MAE, RMSE, max absolute, max relative (only where magnitude is meaningful), p99, counts over predeclared absolute + relative tolerances and first offending coordinates/time/layer; for integers/masks exact. Tolerances must account for original output quantization and source precision **before** running the candidate C++ comparison.
5. **Stress tests:** flat terrain; analytic slope/ridge/saddle; near-zero and opposing winds; finite calm, dry/rain, low-/high-stability, sharp vertical gradients, missing surface/upper observations; terrain roughness and 100 m grid sensitivity, and a 144h repeatability/cross-platform test.
6. **Regulatory / use bound:** no claim that the 5×5 km science-domain wind field reproduces regional processes using only 5 km weather. CALMET influence radii can exceed domain size by orders of magnitude; station availability, representativeness and region-boundary physics need explicit assessment.

## 6. Initial P6A safety boundary (superseded for source-backed P6B–D)

P6A initially allowed contracts/tests only. **Source-backed TERSET and FRADJ physics are now implemented after verifying original reference inputs and extracting the exact vendor Fortran procedures.** Subsequent physical work follows the same independent original-subroutine numerical gates. The original source, P4/P5/P1/P2/P3 branches and frozen shared foundation remain read-only.

### P6A implementation and evidence (2026-10-10)

- `native_cpp/modules/p6_calmet/include/cteas/p6/calmet_contract.hpp`: strict selected-case geometry and coordinate ordering, 9 layers/10 faces, missing/valid distinction, UTC nominal clock labels, selected observed diagnostic mode and forcing readiness guard. These are **data contracts, not the CALMET solver**.
- `native_cpp/modules/p6_calmet/tests/p6_contract_tests.cpp` + isolated `CMakeLists.txt`, strict `-Werror`; 50×50×9 index bounds, 144 nominal labels, valid calm vs missing data, invalid time/CRS/mode, absent P4/P5/precip source tests.
- `native_cpp/modules/p6_calmet/reference/inspect_calmet_control.py`: read-only actual bundled legacy control audit, with negative test `--expect-not-ready`. Confirmed its 2000 year, 100×100 1km etc are **not** valid 2022/50×50/0.1km study settings. It does not change original vendor controls.
- [GitHub-hosted P6A CI](https://github.com/RRain001/CTEAS/actions/runs/38048807603): **PASS** C++20 contract tests and correct failure classification of vendor example control. Branch PR [#8](https://github.com/RRain001/CTEAS/pull/8) remains **Draft** pending full source audit, validated P4/P5 and user-approved station controls. No original Fortran P6 reference run.

**Current scientific status (2026-10-11): P6A_PASS_SOFTWARE_CONTRACTS, P6B_ORIGINAL_CALMET_REFERENCE_PASS, P6C_TERSET_60K_FORTRAN_PARITY_PASS, P6D_FRADJ_315K_FORTRAN_PARITY_PASS, P6_COMPLETE_DIAGNOSTIC_WIND_NOT_IMPLEMENTED, P6_WET_FORCING_NOT_VALIDATED, P6_CALPUFF_READY=FALSE.** See [detailed current audit](P6_CALMET_BCD_REFERENCE_AUDIT.md).
