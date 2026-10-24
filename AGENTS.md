## 2026-10-24 S4-D 真实 NOAA G14 预提交回滚/新 actor 重试（最新）
- 在**唯一显式 NOAA 研究**模式加 `--noaa-precommit-rollback-retry-hour N`（N=2..真实前缀K，必须原生资料和 `--water-noaa-g14-trial-only`），在真实17阶段 P6F precommit后、G14 提交前人为抛出研究异常；同一scheduler验证 committed-hours 不前移、原生 ZI/ZICONV/DPTT逐位不变、AA/BB/CGAMMA时钟不变、未写MET，再新建原生actor同进程重新计算同小时并继续。真实NOAA N=2/5/6 三例6h重跑输出SHA均严格=`32d9f049b1739e1d568a0f7ba65bf9d3718d8bd1c1b7dcdb147c94d41a4753b3`。仅真实预提交异常恢复，不等于提交后崩溃持久化恢复；研究开关不得进入普通C1/C2/生产，不能把此结果说成通用生产稳定性。研发说明追加 `docs/plans/ISSUE40_S4D_143H_DUAL_CASE_AND_CONFIGURED_NOAA_20261024.md`；私有真实输出 `/home/lhy/dev/reports/cteas-s4d-rollback-20261024/`。需新exact SHA软件门槛与C1/C2依旧科学比对后才可发布。

## S4-D 2026-10-24 C1/C2 143h 真实统一二进制对照及单 NOAA 配置入口（最新）
- 当前唯一 Ubuntu 工作树 `CTEAS-next/worktrees/s4-integration`，上一干净 HEAD `f0a3c0aff82e4859503a4a5f726150bbbb208ef2` 的统一 S4B2 实际**重新计算** C1单站1SS/1US 50×50×9完整143h，对锁定原版C1 MET SHA `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30` P6E 143×45=6435 field-hours **0超差** PASS。原版 C1 Fortran 未重新执行，只读冻结原版。
- 同一个统一 S4B2 实际**重新计算**受控C2 2SS/2US 12×12×9完整143h，重新生成原版格式观测、G21 source clock，指定 `/usr/bin/gfortran-11` 重新编译并执行未经改动的锁定 CALMET Fortran Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`，新原版MET SHA `1164c8f992ee40556d1bf26b4e243d773bc67daba14e96785c5b68069cdde31f` vs native SHA `7fbd100b3d75e3b1d0240e3e2c09506ed4333f0ede664081e315425f98e27aac`，P6E 143×45=6435 field-hours **0超差** PASS。C2是受控合成，不等于第二独立实测场址。
- 新通用科研命令 `--water-noaa-g14-trial-only --hours 6 --probe-prefix-hours K` (K=1..6) 严格受限NOAA，复用之前6个原生G65 actor，旧按小时开关仅历史回归兼容；K=1..6所有6份原生 MET SHA与旧研究路径逐字节一致，现有G14/USTAR/EL与G43物理无改动。新增单个 fail-close 负向CTest；P6 research targeted 9/9 PASS。当前修改需要新HEAD软件native full与同HEAD C1/C2 143h复验后才能声称新SHA验收；禁止提前合并。报告 `docs/plans/ISSUE40_S4D_143H_DUAL_CASE_AND_CONFIGURED_NOAA_20261024.md`，私有证据 `/home/lhy/dev/reports/cteas-s4d-c1-c2-20261024/`，禁止上传原版源码和输入。
- 仍需第二独立**实测**场址、相应原版验证，科研rollback和非Bot同SHA独立审核；生产P6/P7没有完全科学准入，PR#308 Draft/scientific-admission 阻止合并。

## 2026-10-24 S4-C 真 NOAA WATER 六小时原生 G14 与原版对照通过（最新）
- G65 第六小时原生完整17阶段actor不改数值公式与前5小时共享，同一参数化 S4B2/G14 `--selected-experimental --water-sixthhour-g14-trial-only --hours 6 --probe-prefix-hours 6`，真实82×85×9/2SS/1US/63 WATER NOAA输入，连续6小时102原生物理阶段、P6F 270字段、G14 ZI/ZICONV/DPTT/AA-BB-CGAMMA原子状态提交且要求完整窗口。hour6水面USTAR/EL仅来自hour5已提交**原生**P6F，G43只在detached模型副本中补原始COMP五个非风缺测量，真实P5风/降水观测不改；绝不将原版Fortran结果当数值求解器输入。
- 独立原版固定6h MET SHA `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14` vs 新原生S4B2完整6h MET SHA `32d9f049b1739e1d568a0f7ba65bf9d3718d8bd1c1b7dcdb147c94d41a4753b3`：**270字段/1881900值、1508074逐位一致、冻结容差0超差**，hour1..6 逐小时位一致 298578/239527/231976/240362/248716/248915，六小时每小时各0超差；结果 `PASS_SCOPED_S4C_SHARED_SIXHOUR_FORTRAN_270`，仅固定一个NOAA场址/站点配置，非通用生产P6/P7验收。原版Fortran本轮没重跑，独立审计 `scripts/s4/s4c_compare_noaa_unified_threehour.py --native-hours 6` 仅后验只读原版。公开报告 `docs/plans/ISSUE40_S4C_SHARED_G65_SIXHOUR_G14_20261024.md`，私有JSON `/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-sixhour-vs-original.json`。
- 任务依然必须执行：新提交精确SHA源native full/verify/publish，旧commit软件status不能继承；之后同SHA C1/C2 143h、第二独立实际原版输入站点配置、原子rollback试验和真人非Bot科学审核。科学admission继续阻止合并，PR #308保持Draft，不加 science-validated/merge-verified、不合并；生产P6/P7仍NOT_ACCEPTED。

## 2026-10-24 S4-C 统一 S4B2/G14 真实 NOAA 第五小时 WATER 通过原版对照（最新）
- 已将 G65 原有第五小时完整17阶段原生 actor 不改数值公式移入共享头，S4B2 新专用研究 flag `--selected-experimental --water-fifthhour-g14-trial-only --hours 6 --probe-prefix-hours 5`，82×85×9/2SS/1US/63 WATER；同一 G14 真正完成前五小时 P6F、ZI/ZICONV/DPTT 与 AA/BB/CGAMMA 原子提交。hour5 WATER USTAR/EL 源自 **hour4 已提交的原生 P6F**，G43 五个非风 COMP 缺测只在 detached G14 模型输入内处理，原始 P5 wind/precip 未变，独立原版 MET.DAT 严禁作为原生物理输入。
- 固定只读原版 Fortran 6h MET SHA `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14` vs 新统一 S4B2 5h MET SHA `41d505e8bc00701b506f6b566fdbe4c2ef3f2400fbc28b94b9130320d1b4cab9`，离线固定原版对照 **225字段/1568250 数值，1259159 逐位一致，冻结容差 0 超差**（hour1–5 逐时 298578/239527/231976/240362/248716 bitwise，每小时0超差）。同一最新二进制分别重算1/2/3/4h MET.DAT SHA 全部与此前代码逐位一致。原版 Fortran 本次未重新跑。仅 `PASS_SCOPED_S4C_SHARED_FIVEHOUR_FORTRAN_225`，不意味生产 P6/P7 科学入场。公开证据文档 `docs/plans/ISSUE40_S4C_SHARED_G65_FIVEHOUR_G14_20261024.md`，私有原生/原版对照 JSON `/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-fivehour-vs-original.json`。
- 新增 fifthhour 研究 opt-in 互斥与负向测试：P6 模块定向 CTest7/7 PASS，已有同一 third/fourth/fifth-hour CLI 负向脚本及3–6h外部科学读数比较器继续复用。最终代码冻结新 exact SHA 后必须运行 Ubuntu native full/verify/publish；旧SHA软件门禁不可继承。下一步仅第六小时 G65 actor接入现有G14、原生hour5 P6F WATER历史、G43非风源和 Fortran 270字段对照，再C1/C2 143h、第二独立场址/配置、非Bot审核。科学入场仍阻止 PR #308 合并；PR Draft、无 science-validated/merge-verified，不合并。

## 2026-10-24 S4-C 真 NOAA WATER 第四小时已接入统一 S4B2/G14（最新）
- 与 G65 科研原版复用**同一个第四小时 17 阶段 native actor**，仅允许显式 `--selected-experimental --water-fourthhour-g14-trial-only --hours 6 --probe-prefix-hours 4`、82×85×9/2SS/1US/63 WATER，跨小时真正从 hour3 原生 P6F `USTAR/EL` 提取下一小时水面历史，继承 G14 ZI/ZICONV/DPTT、原生 station clocks，G43 仅在第四小时 detached 模型源补原始 CALMET COMP 的五个非风缺测，保持原始 P5 风/降水不变。默认 G26/P6 生产模式不开放。
- 只读锁定 Fortran 6h MET SHA `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14` vs 新统一 S4B2 4h MET SHA `412aabb4dfa0ef02af80a70a5ba0dca63fb15ac541ded53a0bb43b484e93177d`：独立**180字段/1254600 数值，1010443 逐位一致，冻结容差超差 0**，四小时逐小时超差均0；用最新二进制重算 1h、2h、3h 原生 MET 输出 SHA 均与旧版完全一致。原版 Fortran 本轮未重跑，且未作为求解器数值输入。仅固定真实 NOAA 四小时 `PASS_SCOPED_S4C_SHARED_FOURHOUR_FORTRAN_180`，不等于通用生产 P6 科学验收。科研报告 `docs/plans/ISSUE40_S4C_SHARED_G65_FOURHOUR_G14_20261024.md`；私有证据 `/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-fourhour-vs-original.json`。
- 同一独立比较器增加 `--native-hours 3|4|5|6` 而不复制脚本；第三/第四小时共享 research CLI 负向验证代码（P6 专项 6/6 CTest PASS）且保护提交/模式边界。此轮须在源代码新 clean SHA 上 native full/verify/publish 后才能声明 GitHub 软件通过；下一步第五、第六小时、最新SHA C1/C2 143h、第二独立配置和非 Bot 科学审查，P7 尚阻塞，PR #308 Draft 不加科学合并标签、不合并。

## 2026-10-24 S4-C 统一 S4B2/G14 第三小时 WATER 原版对照通过（最新）
- S4-C 同一参数化 S4B2 新研究专用选项 `--water-thirdhour-g14-trial-only --hours 6 --probe-prefix-hours 3`，复用 G65 三小时原生完整17阶段 actor，第二小时**已提交的原生 P6F** 提取 USTAR/EL 真实 WATER 前态并检查 source clock，G14 ZI/ZICONV/DPTT 跨小时原子传递。G43 第三小时真实观测非风缺测仅限 detached COMP 源修复，不改原始 P5 风/降水，原版 Fortran MET.DAT 不输入求解器。各科研开关与生产 G26 独立并持续 fail-closed。
- NOAA 原版固定六小时只读 SHA `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14`，新 S4B2 三小时 MET SHA `a80edb2467807635c2c1ea6e285533c6981f4469e41fc4dcf0031a2a035b1989`，独立逐字段对照 **135字段/940950数值，770081逐位一致，冻结容差0超差**，每小时超差均0；既有 1h/2h 输出 SHA 新程序重跑完全不变。原版 Fortran 本轮没有重跑。结果 `PASS_SCOPED_S4C_SHARED_THREEHOUR_FORTRAN_135`，仅针对固定 82×85×9/2SS/1US/63 WATER NOAA 三小时案例。公开说明 `docs/plans/ISSUE40_S4C_SHARED_G65_THREEHOUR_G14_20261024.md`，私有 JSON/原生文件 `/home/lhy/dev/reports/cteas-s4c-unified-20261024/`，严禁上传原始 Fortran 源码/数据/输出。
- 新增 thirdhour 显式 opt-in、错误输入/开关互斥负向模块 CTest（5/5 PASS）及独立 Python SHA/损坏/输出覆盖防护测试（3/3 PASS）。本次代码新 SHA 冻结完成后需运行 Ubuntu exact-SHA 正式 native full/verify/publish；旧提交 software success 不自动继承。后续 hour4 继续 G65 原生 P6F 水面历史和 G43 模型内部五非风补缺，之后 hours5/6、C1/C2 143h 与第二独立场址、非 Bot 科学审查。生产 P6/P7、科学入场未完成，PR #308 保持 Draft，不合并。

## 2026-10-24 S4-C 统一可配置 S4B2 第二小时 WATER G14 原版对照通过（最新）
- G65 原生第二小时完整 17 阶段 actor 未改公式，提取至与第一小时共同的共享头；同一 S4B2/G14 执行器新增 **严格研究-only** `--water-secondhour-g14-trial-only --hours 6 --probe-prefix-hours 2`，真 NOAA 82×85×9、2SS/1US、63 WATER，首小时原子提交的 ZI/ZICONV/DPTT 和 station clocks 直接传递第二小时，不改原始 P5 风/降水，不利用 Fortran MET.DAT 回填求解器。
- 原版 Fortran 固定6h MET SHA `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14` 对独立原生 S4B2 2h MET SHA `30eb55977283f7b9c09a4002e9781d32e1d58af30ac408e15959d8c928d9f0f3`：**90字段/627300值、538105逐位一致、冻结容差0超差**；小时1/2分别 298578/239527 bitwise。首小时独立重跑 output SHA 与上版完全一致，确保首小时无回归。本轮原版 Fortran 未重新跑。私有报告 `/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-twohour-vs-original.json`，源码报告 `docs/plans/ISSUE40_S4C_SHARED_G65_TWOHOUR_G14_20261024.md`。结果仅 `PASS_SCOPED_S4C_SHARED_TWOHOUR_FORTRAN_90`，**不等于第三至六小时/C1/C2/生产P6/P7通过**。
- 增加禁止不带 opt-in/非2h/混用旧 WATER-only 标志的模块 CTest 4/4 PASS、独立 Python 对照安全测试。当前研发改动须以新提交 clean exact SHA 正式 native software full、verify、PR HEAD 一致后才可发布软件 success；PR #308 继续 Draft、science-admission 缺非 Bot 审核不得合并。下一步小时3 用前2h G14 原生 P6F 状态 G66 的水面历史、G43 小时3 的站点非风补缺，统一 G14 继续核原版。

## 2026-10-24 S4-C 同一 S4B2 完成真实 NOAA 第一小时 G14/P6F 原版对照（最新）
- 将 G65 的 **原样** `G65RealNoaaFirstHourActor` 提取为共享头，原 G65 research CLI 与统一 S4B2 都使用该物理 actor；新 S4B2 `--selected-experimental --water-firsthour-g14-trial-only --hours 6 --probe-prefix-hours 1 --out ...` 必须真实 G41/G43 水陆来源、2SS/1US、82×85、63 WATER 与完整 6h 观测时钟，只运行第一小时 17 原生阶段和 G14 原子提交。其它生产与默认 all-land Guard 完全保留。
- Ubuntu 私有真实 NOAA 2022-06-01 01–02 UTC first-hour native `MET.DAT` 与只读固定原版 Fortran 6h 文件独立对照：45 字段 ×6970 网格=313650 数值，298578 逐位一致，冻结阈值 **0 超差**；本轮原版 Fortran 未重新运行。代码科学报告 `docs/plans/ISSUE40_S4C_SHARED_G65_FIRSTHOUR_G14_20261024.md`，私有文件/对照 JSON `/home/lhy/dev/reports/cteas-s4c-unified-20261024/`。这是 `PASS_SCOPED_S4C_UNIFIED_FIRSTHOUR_FORTRAN_45`，**不意味着 hours2–6、生产 P6/P7 与跨案例已被验收**。
- 新增水面第一小时显式 opt-in 负向 CTest、原版对比 SHA/来源隔离 Python 测试；未修改任何数值方程、固定容差或独立评审门槛。下一步接 G65 hour2 的 P6F 原生历史、G43 每小时补缺、跨小时 G14/时钟验证，然后 hours3–6、C1/C2 与第二场址。当前源码有新增变更时，旧提交的软件 full 不可自动继承；在 clean 新 SHA 软件 full/PR status 核验后同步新证据。

## 2026-10-24 S4-C 统一 P6 WATER 来源预检（非物理阶段验收）
- S4B2 `--selected-experimental --water-source-preflight-only` 在同一可配置入口调用 G19/G38/G14 真实源码入场、六小时 UTC/站点时钟，接受 NOAA 82×85×9、2SS/1US、63 WATER，报告 `PASS_SOURCE_ONLY`，但**不**计算 G26/G26B/P6F、不写 CALMET.DAT、不解除 G65 研究模式，`PRODUCTION_ADMISSION=NOT_ACCEPTED`。现有 S4B2 默认模式对含 WATER 数据仍正确拒绝 `G18D3 all-land HFLUX default branch only`。
- 增加 CTest 测试选项互斥/无输出/缺失输入 fail-closed；私有实测路径 `/home/lhy/dev/reports/cteas-s4c-unified-20261024/`，文件身份 SHA 与后续物理改造缺口记录在 `docs/plans/ISSUE40_S4C_WATER_SOURCE_PREFLIGHT_20261024.md`。完整软件 full 仅在本次提交 clean 冻结后有效，旧 HEAD 的 `ubuntu-native-full` success **不能继承到新 SHA**。

## 2026-10-24 S4 软件全量门禁修复候选（未冻结时为 DEV_ONLY）
- 修复 `scripts/ci/cteas_native_full.py`，使用 GCC12 / Python3.11+，在同一提交下额外构建并 CTest P1/P3 独立 CMake，然后用其真实二进制执行全量 S2G Python；manifest 强制验证二进制环境路径、命令、日志、SHA。
- 已本地预检 S2G 190 tests：188 PASS / 2 原有 skip，0 fail/error；P1 CTest 3/3，P3 CTest 1/1。修复已退役 P2-B workflow 检查、仅限 WGS84 浮点投影舍入误差（1e-12 deg；UTM 网格/文件 SHA 不变）、P1 scratch GCC12。
- 必须先在 clean committed exact SHA 执行完整 native full，通过后才可向 GitHub PR #308 头 SHA 发布 `ubuntu-native-full`；此节不是科学 P6/P7 通用验收，独立科学审查仍 NOT_RUN。`docs/ci/S4_S5_NATIVE_POST_S5_DOCKER_POLICY_20261024.md` 为执行细则。

## 2026-10-24 最新：S4 第六小时真实 NOAA 科研限定验收（覆盖下文第五小时状态）
- 第六小时 82×85×9 / 2SS+1US / 63 WATER：G22 181220、风场尾段 446080、COMP stage12–15 132430、P6F 45 字段 313650，原版/原生冻结容差 0 超差；G14 新 actor 回滚与正向提交实测退出 0，候选 P6F 字节一致。详情：`docs/plans/ISSUE40_S4R1C9AH_NOAA_HOUR6_G14_20261024.md`。
- 仅 PASS_SCOPED、研究 opt-in。可配置生产 P6、P7、exact-SHA Ubuntu 原生 full、独立科学审查和 GitHub 研究准入仍 NOT_ACCEPTED/NOT_RUN。PR #308 保持 Draft，正式 Docker full 延至 S5 后。

## 2026-10-24 最新 S4 科学进度（比下方原第五小时 G22 的历史文字更新）
- 第五小时真实 NOAA 82×85×9、2SS/1US、63 WATER：G26B COMP stage12–15 与原版比较 132430/132430 在冻结公差内、0 超差；原生 G64 P6F 45 字段 313650/313650，0 超差，当前记录在 docs/plans/ISSUE40_S4R1C9AF_AG_NOAA_HOUR5_COMP_P6F_G14_20261024.md。
- 第五小时真实 G14 fresh actor 故意失败回滚、正向提交、站点时钟发布全部原生退出 0；正向提交 P6F 文件 SHA256 与独立原版对照过的 stage16 候选完全一致，第六小时 preview 继承 ZI/ZICONV/DPTT 通过。
- **全部是 PASS_SCOPED**：第六小时完整 17 阶段/45 字段、本代码统一可配置生产 P6 C1/C2/非合肥重验、P7、独立科学审查和 S4 正式 full 尚 NOT_RUN/NOT_ACCEPTED。研究 #308 保持 Draft。Ubuntu 原生编译/测试、无 Docker full，正式 Docker 交付延至 S5 后。

## 2026-10-24 最新阶段验收（优先于旧的 Ubuntu Docker/full 要求）
- 本仓库 S4 以 Ubuntu 原生软件全量测试、Fortran/C++ 独立原版科学验收、精确 SHA 和非 Bot 独立审查作为强制门禁。S5 以原生软件 full、规模/内存/性能回归及物理不退化为门禁。**正式 Docker full 和 AMD64/ARM64 容器交付验收延至 S5 完成之后**；Docker 快速调试自愿使用，不能替代真实物理/原生 full。
- 项目脚本 scripts/ci/cteas_native_full.py 只在干净冻结 HEAD 运行全 native_cpp CMake build/CTest 及 S4/S2G Python 单元测试，完整记录日志、命令、SHA，verify 成功后对 GitHub 当前 PR HEAD 发布 ubuntu-native-full（或沿用已有 ubuntu-docker-full）。没有正式原生 full 实际结果就保持 NOT_RUN，禁止把 DEV_ONLY 当软件门禁。
- GitHub repository-admission 支持 exact SHA 两种软件证据；scientific-admission 及 required checks、不变的 science-validated、他人非 Bot 同 SHA APPROVED review、Draft 和 merge-verified 自动合并防护仍有效。Docker 延期不降低原版数值容差、不放宽生产物理 guards、不授予 P6/P7 科学通过。
- 唯一权威文档 docs/ci/S4_S5_NATIVE_POST_S5_DOCKER_POLICY_20261024.md。本文下面 2026-10-23/24 提到 S4/S5 每阶段强制 Docker full、ubuntu-docker-full 唯一准入的内容仅为历史约定。只针对本仓库修改，与其他项目无关。

## S4-0 当前唯一开发基线（2026-10-24）
- Ubuntu 有效 S4 Git 主工作树：/home/lhy/dev/CTEAS-next/worktrees/s4-integration，分支 codex/s4-integration-20261024；实际 common-dir 是 repo-recovered-91a1fff8/.git。旧 /home/lhy/dev/CTEAS-next/repo 存在 210 项历史删除，禁止用于开发或 reset；/home/lhy/CTEAS-next 已删除。
- GitHub 集成 Draft PR #308 是唯一 PR；15 个祖先 Draft 已关闭但保留历史。经 Ubuntu 本地编译/定向测试及应有科学原版比对后，只能 fast-forward push 到 PR #308 现有远程 head，不能 force push/main push，不能为每个 G22/G23/G24 等中间阶段新增 PR。
- GitHub #308 的 workflow_dispatch 修复、当时 main 和七个本地 S4 提交已安全合并；旧 s4-r1c9u 的未提交工作（4 个修改+2 文件）已有本地独立备份，但旧实验 worktrees 不删除。详见 docs/plans/S4_0_CONSOLIDATION_20261024.md。
- 真实 NOAA 第三/第四小时限定 45 字段对照、G14 transaction 与第五小时 G22 已有历史 scoped 证据，绝不升级成统一生产科学通过。第五小时 G23/G24、COMP/P6F/G14、第六小时、通用 P6/P7、外部独立科学评审仍 NOT_ACCEPTED；科学容差、默认 fail-closed guards 和 restricted vendor 数据保护不变。
- L1 定向软件测试；L2 冻结源/输入和原版/C++ 数值独立对照；L3 clean exact SHA Ubuntu Docker full + GitHub required checks + 独立审查。未通过 L3 和科学门禁保持 Draft，不加 merge-verified。

# CTEAS-next agent instructions

## Owner's current CI and merge decision (2026-10-23)
- Keep automatic PR admission checks and scoped software CI; longer science workflows use reviewed, agent-triggered `workflow_dispatch` with exact-SHA evidence. Do not revive the canceled blanket manual-only PR #285; do not re-enable every heavyweight science workflow on PR/push.
- Develop and test candidates with Ubuntu Docker before opening/updating PRs; allow GitHub to auto-run its existing scoped CI on the exact PR HEAD without requiring the owner to click Run workflow.
- Once ALL applicable software tests, original-model/scientific parity, precise input/commit evidence, independent review and required GitHub checks have passed, transition the PR out of Draft and automatically squash merge or enable native GitHub auto-merge; explicit per-PR owner approval is no longer needed. Never activate merge for blocked, NOT_RUN, failed, pending, stale or scope-limited science claims. Enabling repository `allow_auto_merge` alone is not authorization to waive gates.



## Ubuntu Docker / GitHub admission (current deployment, 2026-10-23)
- On the managed Ubuntu host, read `/home/lhy/dev/AGENTS.md` and `/home/lhy/dev/README.md` **before** this repository guide; in other environments those absolute paths may not exist, so use the equivalent documented container and gate contracts. A new ChatGPT session must explicitly read the files, not assume they are automatically injected.
- Refresh remote Git refs and fetch the exact PR HEAD SHA; inspect clean worktrees and all existing tests. Use an isolated short-lived task branch/worktree, never commit directly to `main`, and never force-clean an accepted worktree. The Ubuntu working copy is under `/home/lhy/dev/CTEAS-next/worktrees/local-docker-dev`; the `local-ci` tool currently binds that path, so check the selected SHA before each run.
- Run real builds, focused smoke, scoped `full`, and admissible scientific checks on Ubuntu in Docker. Host entry points: `/home/lhy/dev/bin/local-ci-build`, `/home/lhy/dev/bin/local-ci`, `/home/lhy/dev/bin/local-ci-report`; follow `/home/lhy/dev/infra/local-ci/README.md` for flags and resource limits. A scoped software pass is not all-option or independent scientific acceptance.
- Ubuntu runs its **own Mihomo** HTTP(S) proxy at `127.0.0.1:7897`. Do not require a MacBook/Clash reverse tunnel. Docker daemon, BuildKit and the host-side buildx CLI need compatible proxy settings. Never commit proxy subscriptions, credentials or restricted data.
- The GitHub `main` Ruleset requires the always-running `repository-admission` and `scientific-admission` PR checks. For applicable source/test PRs, publish `ubuntu-docker-full` success **only** after verified `full` software evidence at the exact live PR SHA via `python3 /home/lhy/dev/bin/local-ci-publish-status CTEAS-next <pr> <full-run-id>`; retrigger admission when necessary. This status does not assert science PASS.
- Agents can dispatch longer workflows at a reviewed candidate SHA without asking the owner to click GitHub Actions. Record the run's actual SHA, inputs, checks and scientific conclusion. For science changes, obtain the project-specific external evidence and a genuinely independent, same-SHA human/non-bot APPROVED review as required; never manufacture a `science-validated` claim.
- Only after **all applicable** checks and any required source-specific scientific evidence and independent review succeed, and the current PR is non-Draft and conflict-free, may the agent add `merge-verified`. The trusted `pull_request_target` workflow enables GitHub native squash auto-merge; changing the SHA invalidates the old authorization. NOT_RUN, FAIL, pending, Draft and scientific-review blockers must stay unmerged. No hourly polling or manual-owner click is required.

## Scope and acceptance
- This is the **partial C++20** reconstruction of selected P1–P7 CALMET/CALPUFF pathways, **not** a whole-option Fortran replacement. Consult `README.md` and `docs/physics/CALMET_CALPUFF_OPTION_MATRIX.{md,csv}` before implementing or changing physics.
- C1 (2022 143h) and C2 (controlled synthetic 2024 143h) each **PASS_SCOPED**, as audited in `docs/science_acceptance/C1_C2_143H_RERUN_20261017.md`; Issue #6 is closed for these limited cases. **Full science acceptance NOT_READY.** Do not infer generic P6/P7 or `MWET>0` acceptance from these results.
- C1 original CALMET input was an SHA-locked frozen MET, not freshly rerun original Fortran CALMET. C2 is not independently measured atmospheric observations. Preserve these scientific qualifications.

## Mandatory UTM grid-origin precision (owner decision 2026-10-17)
- **For every current and future case, computational UTM `XREFKM` and `YREFKM` are in km at exactly THREE decimal places (0.001 km = 1 m). Do not increase their precision.** Geographic center latitude/longitude used for projection can retain their original precision, but must not be passed directly to P1/P2 sampling without first quantizing the computed UTM grid origin.
- Treat the generated `grid.cmn` numeric origin as authoritative and carry precisely those three-decimal values into P1/P2/P3, CALMET, manifests and any original comparator. Mere `:.3f` display formatting is insufficient if the computation secretly uses higher-precision floats.
- Frozen Hefei 2022 case: `XREFKM=510.885`, `YREFKM=3531.269`; currently selected P1/P2/P3 C++ CLI must fail closed on any other value or non-three-decimal spelling, not silently round. Future new geographic cases require their own reviewed profile but **the same 3-decimal-km precision**.
- A frozen `MET.DAT` is only an independent reference for an exactly matching GEO/UP/SURF/control input set. Never cross-compare a new GEO with an old-GEO MET or relax science tolerances.
- Evidence: [S2-2C root-cause report](docs/plans/STAGE2_2C_GEO_ORIGIN_ROOT_CAUSE_20261017.md); original 493 exceedances came from 18 terrain heights sampled differently at sub-meter-shifted grid origins. Both original/native 143h same-input comparisons pass when origins match.

## Source ownership and trusted scientific baseline
- Native C++ sources/tests: `native_cpp/`; Python legacy engine and GUI: `engine/`; G5 explicitly native-only authority: `engine/gui_g5/pipeline.py`, currently rejects generic P6/P7/all. Do **not** route G5 through `engine.orchestrator.cli` or legacy model executables.
- The unchanged original CALMET 6.5.0 Fortran source is at old `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13:engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`; CALPUFF 7.2.1 at `engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for`. Follow `docs/physics/VENDOR_SOURCE_LOCATOR.md`.
- Never add external `engine/vendor/**`, restricted CGIAR/SRTM terrain or fonts to the public repository, Action artifacts, logs or Docker images. Restore only from authorized local sources via `scripts/migration/configure_external_assets.py` with hash checks; see `docs/migration/THIRD_PARTY_ASSETS.md`.
- New physics work requires option-specific code authority, frozen input/source provenance, original-versus-native comparison, first differences and an updated option matrix. **Never** silently relax numerical tolerances or fake a PASS from empty plumes.

## Files and runtime
- Preserve still-tracked `project/cases/**` raw inputs, input decks and hash-pinned reference baselines as a deliberate scientific migration exception. Duplicate `deliverables` and generated logs were pruned; do not recreate them as tracked artifacts. Do not commit new generated case outputs, raw downloaded station data, binaries, virtual environments, giant artifacts or unrestricted local `project/` workspaces.
- `docs/migration/SOURCE_MANIFEST.json` records the **frozen pre-cleanup migration export**. Its original content can be checked on the historical commit, not assumed to describe the lean current `main` tree.
- Previously archived 119 disabled workflows, one-off P6 scripts, redundant `deliverables/` and obsolete deployment helpers were removed from current head on 2026-10-17. Restore historical code from pre-cleanup `2f1747434e4217a99b9b9c6fed4d413e90006bd5` via `git show` only if an explicitly authorized scientific task requires it. See `docs/maintenance/REPOSITORY_CLEANUP_20261017.md`.
- Keep C++ work compatible with Ubuntu GCC/GFortran; packaging can target Linux AMD64/ARM64. Python minimum 3.11. `./bootstrap_venv.sh` sets up Python.
- Portable software tests: `scripts/migration/validate_ubuntu.py --portable` and `scripts/migration/validate_python.py --portable`, with `--out` **outside** the checkout. Active Actions workflows in `.github/workflows/` support authorized owner/agent/CI dispatch according to `docs/ci/SCIENCE_TRIGGER_POLICY.md`. The old requirement for owner-only UI/manual science triggers is revoked; retain trusted-main, source SHA and numerical acceptance gates. Do not launch all expensive 143h tests indiscriminately on every push or PR.
- Preserve existing supported legacy PySide6 entrypoints unless expressly migrating them. Current core GUI windows are still separate; do not casually conflate legacy and G5 execution.

## Project-wide science triggering (owner decision 2026-10-19)
- The former **user-manual-only science Actions requirement is revoked** throughout this project, including P1-P7, Wolsong #123, P3 and 143h workflows. Agents may initiate authorized workflow_dispatch via `.github/workflows/cteas-science-dispatcher.yml` and the owner-authenticated Issue comment route, or via supported GitHub Actions-write tools; individual event-triggered science pipelines may run automatically.
- Command on an open Issue: `/cteas run <approved-workflow.yml> [input=value ...]`. Do not claim a dispatch succeeded until GitHub reports it, or scientific PASS until the target run and evidence have been checked. Keep sensitive or destructive release/branch cleanup outside the science dispatcher.
- This current owner decision **supersedes manual-only language in older Issue discussions, historical workflows and plans** as an execution requirement; does not alter the published audit history, legal source constraints, SHA pins, physics options or scientific numerical thresholds.
