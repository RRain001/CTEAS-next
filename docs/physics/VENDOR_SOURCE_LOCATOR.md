# 原版 CALMET/CALPUFF 源码定位与受控恢复

**权威来源：原仓库 `RRain001/CTEAS`，非 `RRain001/CTEAS-next`。**

- 冻结 CTEAS 提交：`dfad99a78ed84d655e21411c9d25eb0d2583bf13`；不要用浮动的旧仓库 `main` 代替它。
- [CALMET 6.5.0 原版目录](https://github.com/RRain001/CTEAS/blob/dfad99a78ed84d655e21411c9d25eb0d2583bf13/engine/vendor/src/CALMET_v6.5.0_L150223) — `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for` 和同目录 `calmet.inp`。
- [CALPUFF 7.2.1 原版目录](https://github.com/RRain001/CTEAS/blob/dfad99a78ed84d655e21411c9d25eb0d2583bf13/engine/vendor/src/CALPUFF_v7.2.1_L150618) — `engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for` 和同目录 `calpuff.inp`。
- 原版还包含 CTGPROC、MAKEGEO、READ62、SMERGE、TERREL 等：请从 [旧 CTEAS 的 `engine/vendor/src`](https://github.com/RRain001/CTEAS/blob/dfad99a78ed84d655e21411c9d25eb0d2583bf13/engine/vendor/src/) 查找，并对实际使用文件按迁移 manifest 固定哈希。不能只复制 CALMET/CALPUFF 两个 .for 文件后假定可完成全部编译与数据流程。
- CTEAS-next 的原版依赖**仅在用户授权的本地/私有执行环境暂时恢复**；SCIENCE C1/C2 GitHub Actions runner 同样从锁定旧提交中读取并校验来源。

## 两个仓库在同级目录时

```bash
# 先检查旧仓库是否持有冻结对象；命令只读
git -C ../CTEAS cat-file -e 'dfad99a78ed84d655e21411c9d25eb0d2583bf13^{commit}'
git -C ../CTEAS show dfad99a78ed84d655e21411c9d25eb0d2583bf13:engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for > /dev/null
git -C ../CTEAS show dfad99a78ed84d655e21411c9d25eb0d2583bf13:engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for > /dev/null

# 在 CTEAS-next 根目录，根据 SOURCE_MANIFEST.json 仅恢复不匹配时拒绝覆盖的原版依赖
python3 scripts/migration/configure_external_assets.py --source-repo ../CTEAS
python3 scripts/migration/configure_external_assets.py --check
git status --short
```

`configure_external_assets.py` 是**恢复**工具，会写入被 `.gitignore` 排除的本地目录；先在适当受控目录使用，不要把恢复目录 `git add -f` 或打包进镜像、公开 CI artifact。只读检查用 `--check`。

机器可读的旧版定位索引为 `docs/migration/SOURCE_MANIFEST.json`（`source_commit`、`source_path`、`sha256`、`local_dependency_path`）；运行期仅从批准的旧仓库取原版字节，并按逐文件 SHA256 核验，绝不以文件名相同作为来源可信的依据。

## 推荐的源代码定位方式

1. 在锁定版本的**原版控制文件**中找控制参数（如 CALMET `IFRADJ/ISLOPE`；CALPUFF `MCTADJ/MDISP/MWET`），提取完整的参数值定义和生效条件。
2. 在原版 `calmet.for` / `calpuff.for` 内核对读取、分支判断、被调用子程序、共享状态、输出写入和调用顺序，**记录原版版本与固定提交**；不要仅凭函数名或同名 C++ 文件判断已覆盖。
3. 查找 CTEAS-next 的 C++ 实现和对应 oracle/test 文件（见物理矩阵），分清 `selected kernel`、生产执行链、控制卡仅接受某值、未支持的替代分支。
4. 用同输入的原版 Fortran 真运行、C++ 真运行、独立科学比较器和哈希/质量收支，完成独立验收；原版 DGM/浓度只允许用于事后比对，不能进入 C++ 物理求解状态。

## 已有来源审计给出的主要调用入口（仅限相关分支）

| 子系统 | 原版入口线索（固定文件） | 原生 C++ 来源 |
|---|---|---|
| CALMET | `COMP→DIAGNO`, `WIND1`, `PREPDI`, `FRADJ`, `SLOPE`, `INTER2`, `WINDBC`, `SMOOTH`, `DIVCEL`；已由 [P6 callgraph 审计](../reconstruction_cpp/P6D_CALLGRAPH_COMPLETENESS_AUDIT_20261013.md) 记录 selected-case 调用顺序 | `native_cpp/modules/p6_calmet/include/cteas/p6/`，`src/` |
| CALMET 混合层 | `MIXHT/MIXHTST`, `AVEMIX`, `WSTARR`, `TEMP3D`（选定选项） | P6G G18 对应头文件与 P6E |
| CALPUFF | `POINTS1`, `COMP`, `GRISE/RISEWIND`, `SETPUF`, `PUFFCT2`, `PUFRECS`, `CALCPF`, `DRY/VDCOMP` | `native_cpp/modules/p7_calpuff/src/` |
| 降水/湿清除 | CALMET `NPSTA` 与 CALPUFF `MWET` 的**完整源码调用入口、雨站模板和接口尚未冻结**；不能假定已存在可用 wet-removal C++ 主链 | **NOT_ACCEPTED** |

## 许可与科学边界

`CTEAS-next` 不新增或提交原版 vendor 源代码，不声称具有 CALMET/CALPUFF 的再发布权，也不把原版程序纳入发布镜像。当前 [第三方依赖判断](../migration/THIRD_PARTY_ASSETS.md) 将这些文件列为 external。后续直接从 Fortran 翻译例程、分发衍生实现等涉及权利的问题仍需单独审核；把原文件放在另一个 Git 仓库**不**自动授予许可。

原版参数矩阵覆盖的是**审计台账**，不是完整源程序 callgraph；如果某行 `fortran_locator_grade` 标明需要源审，就应在动手改写前补上确切入口和激活条件。当前 P6/P7 仅有历史限定 C1/C2 证据；新仓库的科学验收依据 [Issue #6](https://github.com/RRain001/CTEAS-next/issues/6) 后续实际运行结果判定。
