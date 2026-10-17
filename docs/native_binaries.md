# Native Binaries Mapping

| 当前 `.x` 文件 | 当前架构 | 推测功能 | 对应源码 | 编译方式 | 是否可重编译 |
| --- | --- | --- | --- | --- | --- |
| `bin/linux-x86_64/terrel.x` | ELF 64-bit LSB executable, x86-64 | 地形预处理 | `engine/vendor/src/TERREL_v7.0.0_L141010/terrel.for`, `coordlib.for`, `calutils.for`, `dd_dem.for`, `tiffinfo.for` | 原目录有 `cpl.bat` / `build_*.log`；本轮新增 Docker + `gfortran` 脚本 | yes |
| `bin/linux-x86_64/ctgproc.x` | ELF 64-bit LSB executable, x86-64 | 土地利用预处理 | `engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for`, `coordlib.for`, `calutils.for`, `tiffinfo.for`, `readctg.f` | 原目录有 `cpl.bat`；本轮新增 Docker + `gfortran` 脚本 | yes |
| `bin/linux-x86_64/makegeo.x` | ELF 64-bit LSB executable, x86-64 | 地理场合并 | `engine/vendor/src/MAKEGEO_V3.2_L110401/makegeo.for`, `calutils.for` | 原目录有 `cpl.bat`；本轮新增 Docker + `gfortran` 脚本 | yes |
| `bin/linux-x86_64/read62.x` | ELF 64-bit LSB executable, x86-64 | 高空气象转换 | `engine/vendor/src/READ62_v5.661_L110225/read62.for`, `calutils.for` | 原目录有 `cpl.bat`；本轮新增 Docker + `gfortran` 脚本 | yes |
| `bin/linux-x86_64/smerge.x` | ELF 64-bit LSB executable, x86-64 | 地面气象合并 | `engine/vendor/src/SMERGE_v5.7.0_L121203/smerge.for`, `calutils.for`, `presutil.for` | 原目录有 `cpl.bat`；本轮新增 Docker + `gfortran` 脚本 | yes |
| `bin/linux-x86_64/met.x` | ELF 64-bit LSB executable, x86-64 | 诊断风场 | `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`, `coordlib.for`, `calutils.for`, `auxutils.for` | 原目录有 `cpl.bat`；本轮新增 Docker + `gfortran` 脚本 | yes |
| `bin/linux-x86_64/puff.x` | ELF 64-bit LSB executable, x86-64 | 烟团扩散主程序 | `engine/vendor/src/CALPUFF_v7.2.1_L150618/modules.for`, `calpuff.for`, `coordlib.for`, `calutils.for`, `api_chem.for`, `isorropia_v2.2.for`, `lwcsubs.for` | 原目录有 `cpl_unix.bat` / `cpl_calpuff.bat`；本轮新增 Docker + `gfortran` 脚本 | yes |

## 备注

- 本轮未发现 `source_missing` 的 `.x` 文件。
- `engine/vendor/src/*/*.x` 与 `engine/vendor/bin/*.x` 为历史重复分发副本，活跃运行面已切换到 `bin/<platform>/met.x`、`puff.x` 等正式命名。
- 7 个上游源码目录的重编译经验、典型坑点和当前验证边界，见 [docs/vendor_src_rebuild_notes.md](./docs/vendor_src_rebuild_notes.md)。
