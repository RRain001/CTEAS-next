# Scheduler handoff — 2026-10-12（用户断网暂停）

本文件由调度 agent（Main）在暂停时刻落盘，用于网络恢复后无损续接。

## 1. 仓库状态

| 项 | 值 |
|---|---|
| `main`（本地 = `origin/main`） | **`9bedb8e`**（本地无独有提交） |
| 未并入 `main` 的轨道提交 | P7 `ef6a449`（P7G + 缺口表更正；**已推送**）、P6D `d98c43453`（第 18 轮 docs；**已推送**）——代码态均已 gate PASS（P7 的 code gate 在 `c3f6650c2`，P6D 在 `d98c43453`），恢复后按 SHA **重新 gate 再合并** |
| 本轮 campaign 累计新增提交 | **+300 余**（自基线 `6b0fe72`） |
| CTest 目标合计 | p6_calmet 29 / p6e 27 / p6f 7 / p7_calpuff 44+ |
| gate 证据 | `/home/lhy/gate/evidence/*.json`（80+ 份，按运行 token 隔离） |

## 2. 各轨道状态与下一步入口

| 轨道 | 状态 | 下一步入口（精确） |
|---|---|---|
| **P6E** | ✅ 完成：18 个自有字段**总超差 0**（已固化为 gate 可见 CTest `p6e_calmet_dat21_real_full_field_reference`，197 s） | — |
| **P6F** | ✅ 条款达成：逐字节等价 + 原版 CALPUFF 读取并复现参考 `puff.con` | — |
| **P6D** | ⚠️ `U/V` 第 7–9 层 PASS；第 2–6 层 0.0017–0.0027 m/s；**第 1 层 0.00156724（1,450 格）**——已判定为**自身 INTER2/分析路径的伪结构**（原版第 1 层在抽样小时**完全均匀**，spread 0.000000；产物带 4e-5–1.8e-4 结构）；W 面尾部 | **INTER2 权重插桩**：`calmet.for` 8124–8616，单小时内四格（中心 (26,26)/边缘 (1,26)/角 (1,1)/中半径 (13,13)）的 `RS(L)`/`SUM`/`RSQ(L)`/站点次序 + `WO` 所在层 |
| **P7** | ⚠️ 烟团模型：释放/抬升/记账/sigma/平流/步进/`GETCELL`/`/CURRENT/` 全部对照（含 `PUFFDZ` 逐位、`ADVECT`/`distm`/`xnew`/`ynew` 0 不符）；`CONC.DAT` **结构**对照成功（429 条数据记录 1:1，差 3,226 条头部记录） | ① **先做验证（非移植）**：用 dump 的逐子步输入驱动 P7Q 的 `sigma_update`，对照 `syb1/sym1/sye1`、`szb1/szm1/sze1`、`sigyb_out`、`sigzb_out`（**缺口表已更正：`SETPUF` sigma 簿记并非缺口**）；② `WROUT1` 头 3,226 条；③ `AVET`（先判定本案例是否生效）→ 之后是 **whole-case driver** 与**浓度值对照**（P7G 终门） |
| **DGM** | ✅ 四轮插桩（CALMET 内部状态、CALPUFF 步进/平流、站点装配），均为**只写式且证明非侵入**（`MET.DAT`/`puff.con` 逐字节不变） | 第 5 轮：INTER2 权重（同上 P6D 的请求） |
| **REF / G6** | ✅ 冻结 2022 参考案例（10 阶段 / 802 产物 / SHA 冻结）；端到端一键脚本 `scripts/run_p6_end_to_end.py` | — |

## 3. 端到端当前判定

| 口径 | 结果 |
|---|---|
| **B（原版风场驱动）** | **18 PASS / 0 FAIL / 27 NOT_PRODUCED** ✅ |
| **A（重建风场驱动）** | 15 PASS / 3 FAIL（`USTAR` 9,379 格 / `EL` 1,105 格 / `WSTAR` 165 格——全部由 P6D 风场残差传播而来） |

## 4. 恢复步骤（按序执行）

1. `git fetch` 并核对 `main` 与各轨道 tip；
2. 合并两个已 gate 的提交（P7 `c3f6650`、P6D `d98c434`）；
3. 派 **DGM 第 5 轮**（INTER2 权重插桩）→ **P6D** 修第 1 层 → 重跑端到端（目标 A 口径 `18/0`，B 已 `18/0`）；
4. 派 **P7** 继续三件阻塞 → whole-case driver → `puff.con` **浓度值**对照（P7G 终门）。

## 5. 环境提醒

- Mac 侧 GitHub 走 Clash 代理（repo-local `http.proxy` 已配置）；构建机 `lhy-desktop` 经 SSH（BatchMode 免密，Tailscale）。
- **gate driver 在 `/home/lhy/gate/driver`**（独立检出，避免与 agent 的工作区互相干扰）；gate 用法：
  `python3 /home/lhy/gate/driver/scripts/local_gate.py --track <p6d|p6e|p6f|p7|shared> --repo /home/lhy/gate/driver`
- 断网期间：GitHub push/merge 与 SSH 到 `lhy-desktop` 都可能失败——**不要重试风暴**，恢复后一次性处理。
- 调度纪律（本轮已固化）：**先取 tip SHA → gate 该 SHA → 再合并该 SHA**；gate 失败一律不合并；每轮后跑回归。
