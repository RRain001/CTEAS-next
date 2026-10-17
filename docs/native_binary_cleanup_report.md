# Native Binary Cleanup Report

本轮清理目标是只保留正式运行目录 `bin/linux-x86_64/*.x`，移除 `engine/vendor/bin/*.x` 和 `engine/vendor/src/*/*.x` 下的重复 ELF 副本。

## 结论

- `bin/linux-x86_64/*.x` 保留为正式运行路径。
- `engine/vendor/bin/*.x` 与 `bin/linux-x86_64/*.x` SHA256 完全一致，判定为重复分发副本，已删除。
- `engine/vendor/src/*/*.x` 与 `bin/linux-x86_64/*.x` SHA256 完全一致，判定为源码目录历史编译产物，已删除。
- 历史备份目录：`docs/refactor_logs/removed_native_binaries_backup/`，用于清理审计；现已删除。

## 说明

- 删除前已完成 `file` 和 `sha256` 核验。
- 备份脚本第一次执行时遇到 shell 环境异常，删除后曾使用保留的 `bin/linux-x86_64/*.x` 按相同目标路径重建过备份。由于哈希完全一致，重建备份与被删文件字节级一致；该历史备份目录现已删除。

## 清单

| 文件 | 架构 | sha256 | 是否保留 | 原因 |
| --- | --- | --- | --- | --- |
| `bin/linux-x86_64/terrel.x` | `ELF 64-bit LSB executable, x86-64` | `fcf107389bb428f8550c1a5a19306a9a04fc372e944e4596a947fc0b529d0022` | `yes` | 正式运行目录 |
| `bin/linux-x86_64/ctgproc.x` | `ELF 64-bit LSB executable, x86-64` | `199ac21d5bef023778dd6d32400560076abd9d37941e83177d5d00b877c20bdd` | `yes` | 正式运行目录 |
| `bin/linux-x86_64/makegeo.x` | `ELF 64-bit LSB executable, x86-64` | `38d4ebe670400348adc93d91ba0bfae81f5e65bf20263696639091091e9a0f95` | `yes` | 正式运行目录 |
| `bin/linux-x86_64/read62.x` | `ELF 64-bit LSB executable, x86-64` | `e6bd23c1d5ce1d78a7f299a502b0f0c636ddc0a9d06de9525f097dfd03692913` | `yes` | 正式运行目录 |
| `bin/linux-x86_64/smerge.x` | `ELF 64-bit LSB executable, x86-64` | `cc8be4a8e816960a9db73e8d4c05764f2b29881c50cb143dc0ed846718bc5106` | `yes` | 正式运行目录 |
| `bin/linux-x86_64/met.x` | `ELF 64-bit LSB executable, x86-64` | `00d51b15c77ede44b60a0abd5e794e11ee6d1a4ae54613d08076c410522168a2` | `yes` | 当前正式运行目录（物理名已改为 `met.x`） |
| `bin/linux-x86_64/puff.x` | `ELF 64-bit LSB executable, x86-64` | `9fa3d5a80a3efc86ca0370c505f53e5f675a2d6ed04877a73679d779c95856a5` | `yes` | 当前正式运行目录（物理名已改为 `puff.x`） |
| `engine/vendor/bin/terrel.x` | `ELF 64-bit LSB executable, x86-64` | `fcf107389bb428f8550c1a5a19306a9a04fc372e944e4596a947fc0b529d0022` | `no` | 与 `bin/linux-x86_64/terrel.x` 哈希一致，重复分发副本 |
| `engine/vendor/bin/ctgproc.x` | `ELF 64-bit LSB executable, x86-64` | `199ac21d5bef023778dd6d32400560076abd9d37941e83177d5d00b877c20bdd` | `no` | 与 `bin/linux-x86_64/ctgproc.x` 哈希一致，重复分发副本 |
| `engine/vendor/bin/makegeo.x` | `ELF 64-bit LSB executable, x86-64` | `38d4ebe670400348adc93d91ba0bfae81f5e65bf20263696639091091e9a0f95` | `no` | 与 `bin/linux-x86_64/makegeo.x` 哈希一致，重复分发副本 |
| `engine/vendor/bin/read62.x` | `ELF 64-bit LSB executable, x86-64` | `e6bd23c1d5ce1d78a7f299a502b0f0c636ddc0a9d06de9525f097dfd03692913` | `no` | 与 `bin/linux-x86_64/read62.x` 哈希一致，重复分发副本 |
| `engine/vendor/bin/smerge.x` | `ELF 64-bit LSB executable, x86-64` | `cc8be4a8e816960a9db73e8d4c05764f2b29881c50cb143dc0ed846718bc5106` | `no` | 与 `bin/linux-x86_64/smerge.x` 哈希一致，重复分发副本 |
| `engine/vendor/bin/calmet.x` | `ELF 64-bit LSB executable, x86-64` | `00d51b15c77ede44b60a0abd5e794e11ee6d1a4ae54613d08076c410522168a2` | `no` | 与当前正式 `bin/linux-x86_64/met.x` 哈希一致，重复分发副本 |
| `engine/vendor/bin/calpuff.x` | `ELF 64-bit LSB executable, x86-64` | `9fa3d5a80a3efc86ca0370c505f53e5f675a2d6ed04877a73679d779c95856a5` | `no` | 与当前正式 `bin/linux-x86_64/puff.x` 哈希一致，重复分发副本 |
| `engine/vendor/src/TERREL_v7.0.0_L141010/terrel.x` | `ELF 64-bit LSB executable, x86-64` | `fcf107389bb428f8550c1a5a19306a9a04fc372e944e4596a947fc0b529d0022` | `no` | 与 `bin/linux-x86_64/terrel.x` 哈希一致，源码目录历史编译产物 |
| `engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.x` | `ELF 64-bit LSB executable, x86-64` | `199ac21d5bef023778dd6d32400560076abd9d37941e83177d5d00b877c20bdd` | `no` | 与 `bin/linux-x86_64/ctgproc.x` 哈希一致，源码目录历史编译产物 |
| `engine/vendor/src/MAKEGEO_V3.2_L110401/makegeo.x` | `ELF 64-bit LSB executable, x86-64` | `38d4ebe670400348adc93d91ba0bfae81f5e65bf20263696639091091e9a0f95` | `no` | 与 `bin/linux-x86_64/makegeo.x` 哈希一致，源码目录历史编译产物 |
| `engine/vendor/src/READ62_v5.661_L110225/read62.x` | `ELF 64-bit LSB executable, x86-64` | `e6bd23c1d5ce1d78a7f299a502b0f0c636ddc0a9d06de9525f097dfd03692913` | `no` | 与 `bin/linux-x86_64/read62.x` 哈希一致，源码目录历史编译产物 |
| `engine/vendor/src/SMERGE_v5.7.0_L121203/smerge.x` | `ELF 64-bit LSB executable, x86-64` | `cc8be4a8e816960a9db73e8d4c05764f2b29881c50cb143dc0ed846718bc5106` | `no` | 与 `bin/linux-x86_64/smerge.x` 哈希一致，源码目录历史编译产物 |
| `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.x` | `ELF 64-bit LSB executable, x86-64` | `00d51b15c77ede44b60a0abd5e794e11ee6d1a4ae54613d08076c410522168a2` | `no` | 与当前正式 `bin/linux-x86_64/met.x` 哈希一致，源码目录历史编译产物 |
| `engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.x` | `ELF 64-bit LSB executable, x86-64` | `9fa3d5a80a3efc86ca0370c505f53e5f675a2d6ed04877a73679d779c95856a5` | `no` | 与当前正式 `bin/linux-x86_64/puff.x` 哈希一致，源码目录历史编译产物 |
