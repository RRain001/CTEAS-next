# Vendor SRC 重编译经验

本文记录 `engine/vendor/src/` 下 7 个上游源码目录在本仓库中的重新排查、修复和重编译经验，目的是让后续维护者避免重复踩坑。

适用范围：

- `CALMET_v6.5.0_L150223`
- `CALPUFF_v7.2.1_L150618`
- `CTGPROC_v7.0.0_L150211`
- `MAKEGEO_V3.2_L110401`
- `READ62_v5.661_L110225`
- `SMERGE_v5.7.0_L121203`
- `TERREL_v7.0.0_L141010`

不适用范围：

- 不保证所有编译器、所有优化参数、所有平台都等价
- 当前主要验证的是本仓库现有 `gfortran + Docker Debian 12` 构建链

## 总结结论

当前这 7 个源码目录已经整理到“没有已知结构性编译障碍”的状态。

对当前脚本和当前验证范围，可以成立的结论是：

- 7 个目录都已对照官网下载源码重新排查
- 会导致编译异常的坏 symlink 已经补成真实文件
- 7 个目标程序都能重新编译
- `ctgproc`、`makegeo`、`read62`、`smerge` 已额外通过最小 runtime smoke
- `terrel` 已单独通过 runtime 验证

不能直接外推的结论是：

- 不能保证以后任何源码改动后都不会再出问题
- 不能保证更换编译器版本或激进优化参数后仍完全稳定

## 通用经验

### 1. 先对照官方源码，不要直接假设仓库内 vendor/src 是干净的

本轮对照了用户放在 `/Users/rain/Downloads/` 的 7 个官网下载 `src` 目录，发现仓库内多个小写文件其实是坏 symlink，而不是可读源码。

如果不先补齐这些文件，后续编译和运行会出现随机报错，且不容易第一时间定位到是文件系统问题。

### 2. 对这类上游 Fortran 代码，优先服从原始 `cpl.bat` 的编译组织方式

一个常见误区是“把目录下所有 `.for` 都扔给 gfortran 一起编”。对这批代码这并不总是对。

本轮确认：

- `CTGPROC`、`MAKEGEO`、`READ62`、`SMERGE` 应优先按官方 `cpl.bat` 方式，只编主程序 `.for`
- `CALPUFF` 需要 `modules.for + calpuff.for`
- `TERREL` 需要额外 helper 源文件
- `CALMET` 保持当前仓库脚本的多文件编译方式

尤其 `SMERGE`，若把已被主程序包含或重复定义的辅助源再次单独链接，会直接报 multiple definition。

### 3. 固定格式老 Fortran 代码要谨慎处理行宽和旧语法

`READ62`、`SMERGE` 这一类更接近老式 fixed-form 风格，当前脚本里需要单独使用：

```text
-std=legacy -ffixed-line-length-72 -fno-automatic -fno-align-commons -fallow-argument-mismatch -O0
```

否则容易因为 72 列截断、旧格式注释或参数传递不严格而出现大量语法/兼容性错误。

### 4. COMMON block 对齐不要随意改

当前脚本把 `-fno-align-commons` 加进了通用 flags。

原因不是为了“让编译通过”，而是为了尽量降低老 Fortran `COMMON` 内存布局和历史二进制行为漂移的风险，尤其对 `TERREL / CALMET / CALPUFF` 这类代码更重要。

## 坏 symlink 修复记录

本轮确认并补成真实文件的典型项目包括：

- `CTGPROC_v7.0.0_L150211/`
  - `blockdat.crd`
  - `filnam.ctg`
  - `grid.ctg`
  - `gspan.ctg`
  - `nima.crd`
  - `qa.ctg`
- `MAKEGEO_V3.2_L110401/`
  - `grid.geo`
- `READ62_v5.661_L110225/`
  - `control.r62`
  - `station.r62`
  - `submet.r62`
- `SMERGE_v5.7.0_L121203/`
  - `control.smg`
  - `datehr.smg`
  - `precip.smg`
  - `presutil.for`
- `TERREL_v7.0.0_L141010/`
  - 多个 `.trl` / `.crd` / `terrel.for` 小写入口文件

维护建议：

- 如果以后再次从外部同步 vendor 源码，先跑一次“坏 symlink 审计”
- 不要假设小写文件一定是真实文件

## 七个目录逐项经验

## 1. TERREL

当前结论：

- 已可重编译
- 已做过 runtime 验证

经验点：

- 需要保留 `dd_dem.for` 等 helper 文件参与编译
- 目录内小写 `.trl/.crd/.for` 入口文件必须真实存在，不能是断链

## 2. CTGPROC

当前结论：

- 已可重编译
- 已通过最小 runtime smoke

关键修复：

- `params.ctg` 中打开二进制直存文件的参数，需从旧写法切到 `unformatted/direct`
- `ctgproc.for` 中 `read(dataver,'(f)') rver` 需要改成 list-directed `read(dataver,*) rver`

经验点：

- 应按官方 `cpl.bat` 只编 `ctgproc.for`
- 不要额外把目录下其他辅助 `.for` 强行拼进链接阶段

## 3. MAKEGEO

当前结论：

- 已可重编译
- 已通过最小 runtime smoke

关键修复：

- `makegeo.for` 中 `read(dataver,'(f)') rver` 需要改成 `read(dataver,*) rver`

经验点：

- 应按官方 `CPL.BAT` 只编 `makegeo.for`
- 如果以后又出现 `Nonnegative width required in format string`，优先先查这里

## 4. READ62

当前结论：

- 已可重编译
- 已通过最小 runtime smoke

经验点：

- 应按官方 `CPL.BAT` 只编 `read62.for`
- 必须使用 fixed-form 72 列兼容 flags
- 若不用 72 列限制，常见表现是出现大批量语法错误，而不是一个清晰的单点错误

## 5. SMERGE

当前结论：

- 已可重编译
- 已通过最小 runtime smoke

经验点：

- 应按官方 `cpl.bat` 只编 `smerge.for`
- 不要额外单独再编 `presutil.for` 参与链接；否则容易 multiple definition
- 当前 runtime smoke 中出现过 `ICC` 缺测统计，但这是数据质量提示，不是源码/编译链故障

## 6. CALMET

当前结论：

- 已可重编译
- 当前正式物理二进制命名为 `met.x`

经验点：

- 保持现有仓库脚本的多文件编译组织
- 这里的源码名仍是 `calmet.for`，但正式产物名已切到 `met.x`

## 7. CALPUFF

当前结论：

- 已可重编译
- 当前正式物理二进制命名为 `puff.x`

关键经验：

- 当前应编 `modules.for + calpuff.for`
- `CALPUFF` 单独使用 `-ffixed-line-length-72 -fdec-format-defaults`

原因：

- `modules.for` 负责模块定义
- `calpuff.for` 是主程序
- `fdec-format-defaults` 用于兼容这套老源码里的部分格式行为

## 当前建议的维护顺序

后续如果有人再次大规模处理 `vendor/src`，推荐顺序如下：

1. 对照官网下载目录，先检查坏 symlink
2. 优先查看各目录原始 `cpl.bat` / `cpl_unix.bat`
3. 再调整 `scripts/build_native_linux_x86_64.sh` 和 `scripts/build_native_linux_arm64.sh`
4. 先验证能编
5. 再至少补一个最小 runtime smoke

## 最小验收标准

如果以后再次改动这 7 个源码目录，最低建议验收为：

- `bash -n scripts/build_native_linux_x86_64.sh`
- `bash -n scripts/build_native_linux_arm64.sh`
- 重新构建对应平台二进制
- `python scripts/check_native_binaries.py --platform linux-x86_64`
- `ctgproc / makegeo / read62 / smerge` 至少各跑一个最小 runtime smoke

更高标准再加：

- `terrel` runtime smoke
- `met/puff` 数值回归对比

## 目前仍需保留的风险意识

虽然当前状态已经比最初干净很多，但后续仍要注意：

- 这批上游代码对编译器兼容细节敏感
- 小改 flags 也可能改变行为，不应把“能编过”当成“结果一定等价”
- 如果后续引入更高优化等级，建议重新做 runtime 和必要的数值回归
