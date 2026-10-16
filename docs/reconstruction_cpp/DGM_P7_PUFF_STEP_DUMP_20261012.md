# DGM round 3 — original CALPUFF puff-step state for the P7U advection request

Date: 2026-10-12. Track: **DGM**, round 3 (rounds 1-2:
[DGM_INTERNAL_STATE_DUMP_20261012.md](DGM_INTERNAL_STATE_DUMP_20261012.md),
[DGM_P6D_INTERNAL_STATE_REQUESTS_20261012.md](DGM_P6D_INTERNAL_STATE_REQUESTS_20261012.md)).
Target: the frozen Hefei 2022 case, **CALPUFF 7.2.1** (`CALPUFF_v7.2.1_L150618`).
The vendor tree is **unmodified**; artifacts on the build host under
`/home/lhy/build/dgm3/`.

## 1. What P7 asked for

P7U located and pinned the advection / step-integration chain
(`ADVWND` L2438-2538, `ADVECT` L2540-2765, `PUFFDZ` L2882-3005, `ZFIND`
L18381-18419, `POWLAW` L33463-33516, `XTPRF` L33192-33461 and the inline step code
of `COMP`) and recorded an eight-item instrumentation request in
`docs/reconstruction_cpp/P7_EXECUTION_LEDGER.md` (P7U section) and
`native_cpp/modules/p7_calpuff/reference/p7u_source_anchor.json`: the start-of-step
puff state, the met cell and parameters, `PUFFDZ`'s return, `ADVECT`'s return, the
effective transport speed, the sampling cadence, the end-of-step position and the
`SETPUF` entry/return sigma state — *"observable variables at named lines so the
instrumented run can be diffed against the C++ chain value by value"*.

This round implements exactly that request, as write-only dumps.

## 2. What was executed

One command on `lhy-desktop` (`/usr/bin/gfortran-11`, GNU Fortran 11.4.0):

```
python3 original_puff_step_dump.py audit \
  --vendor CALPUFF_v7.2.1_L150618 \
  --case <frozen case dir> --out out --compiler /usr/bin/gfortran-11
python3 original_puff_step_dump.py metadata \
  --dump out/case/run/puff/dgm_puffstep.bin --out out --slice-hour 202200100
```

`audit` copies the pinned original `calpuff.for` to a temporary file, appends eight
write-only calls and nine helper subroutines, compiles **both** the untouched
original and the instrumented copy with one compiler and one flag set
(`-std=legacy -ffixed-line-length-72 -fno-automatic -fno-align-commons
-fallow-argument-mismatch -O0 -fdec-format-defaults`, the frozen capture's CALPUFF
recipe), stages the frozen case, runs both binaries on it, and requires the two
produced `puff.con` files to hash identically.

### 2.1 Write-only proof

| run | `puff.con` bytes | `puff.con` sha256 |
|---|---|---|
| untouched original | 1,896,056 | `0d51bdb68ff1a5798048bc41067107d3ffe10dc6222f25336df856bcbf48ba10` |
| write-only instrumented | 1,896,056 | `0d51bdb68ff1a5798048bc41067107d3ffe10dc6222f25336df856bcbf48ba10` |

Both runs returned 0, both cover the whole 143-hour period, and both hashes equal the
frozen reference `run/puff/puff.con`. The untouched binary wrote **no** dump file; the
audit fails closed if it does or if the instrumented run's dump is missing. Evidence:
`dgm-audit.json` (`status: ORIGINAL_PUFF_CON_IDENTICAL`).

Inputs (hashed by the audit, pinned in the tool):
`run/puff/puff.inp` `cf5cca70cb75b1aac92f86fdc100500e901a8b904d056c73b2330175793532bc`,
`deliverables/met/met.dat` `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30`
(the frozen CALMET output).

## 3. Source anchors

Vendor `calpuff.for` sha256
`da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568`,
`modules.for` sha256 `115ab7c7e50701a454852106d7c7536d75f1975f66a87a616b4835c5bea353b6`
(re-verified before any insertion; any drift aborts). Every insertion is one comment
plus one call inside `subroutine comp`; no original statement is altered.

| # | request item | vendor line | where | inserted text sha256 |
|---|---|---|---|---|
| 1 | start-of-step state | 10473 | after the `xold/yold/zold` assignment (L10465-10473) | `cf80a90258f5203129b88c180b25c8569c66af3fd8072c84f9e165ee524c6f0a` |
| 2 | met cell and parameters | 10487 | after `z0m=z0(ixs,iys,mdoms)` | `d08fa4a699a73aa140b29693fd4b3bd6006e7eabbbf706acc5fd018360e01368` |
| 3 | `PUFFDZ` return | 10495 | immediately after the `PUFFDZ` call (L10494-10495) | `8f92310e43c44eef158bfcfb3674469b268fdf1d6854a7883a93ca31c50dc523` |
| 4 | `ADVECT` return | 10499 | immediately after the `ADVECT` call (L10498-10499) | `aafc67987cb5b6cab6948a738cec988ab0b313069fa49319e8bde29456b5c759` |
| 5 | after the adjustments | 10528 | after the calm block (L10521-10528) | `86249f502087f3dc7ddc28a08f2914b0b49c5d38468a8cf3c6f423b4e25f0bd6` |
| 6 | sampling cadence | 10347 | after `reftsamp=tsamp`, i.e. after the whole old/new-puff cadence chain | `2fc0343e0beb9e1ea2863e5f45e1166b8a8c7d2f98a46d409bba0c1cb95f56d4` |
| 7 | `SETPUF` entry | 10939 | immediately before the `SETPUF` call (L10940-10942) | `bb4cd87da8c2f8e44df21e2bfd7654eeb2c55ec5cc8158b5a880e10061ed8190` |
| 8 | `SETPUF` return + position + record | 10942 | immediately after the `SETPUF` call | `0494b169859d7e1d63fb792f8aa9023f3658220a054d4910a373bc8b9598de78` |

Two implementation notes:

- Item 6's request names `COMP` L10155-10180 *and the sampling loop*; L10155-10180 is
  only the "new puff" arm of the cadence chain. The single insertion at L10347 sits
  after that whole chain, so it captures the final `nsam`/`nsstr`/`tsamp` for **both**
  old and new puffs, which is a superset of the named lines.
- Items 3, 4 and 8 are captured at the **call sites** in `COMP`, which is where the
  named returns arrive (`ztop`/`zbot`, `uadv`/`vadv`) and where `SETPUF`'s entry and
  return state is observable; `PUFFDZ`, `ADVECT` and `SETPUF` themselves are not
  touched.

Supporting hashes: whole instrumented file `calpuff_instrumented.for`
`7935827f66f2c6fbb1d404c5f5538487a4931c44d68683644a9ed1cef44ae1cc`; helper block
(`DGMSTEP1..6`, `DGMSTEP8E`, `DGMEMIT`, appended from vendor line 88128, unit 94)
`1865c0674e1946e85d37140ca173fcc86121217d8fe7e9a61e98b7c62f570f90`; instrumented
source segments `comp_sampling_cadence` L10335-10353
`7f8fd22c5dbb5ee126d6969d4bb358d4c6a54c39e05e8b863dec4b3d2914571a`,
`comp_step_start` L10460-10490 `bb4d9adf06d7e1e1f93107751319d1833fb633f9d1c50a0495a1dcb15855d6ec`,
`comp_step_wind` L10492-10535 `8abc2bb0ea9e0de36669faeb3078928f78ec487a37738d4babf5ce056d1201b6`,
`comp_setpuf_call` L10936-10943 `f93ed960ad2180e8ba0f5f344c2ce6dbe82482e97f12b76953835ebd02ba9be1`.

The eight capture helpers store into the `/DGMSTEP/` common; `DGMEMIT` writes one
fixed-width record to `dgm_puffstep.bin` (unit 94), taking the current timestep label
from `/DATEHR/` (`ndathrb`, `nsecb`). No model variable is modified.

## 4. The dump

`dgm_puffstep.bin` — 89,649,824 bytes = **254,687 records × 352 bytes**, sha256
`cbbdaa29c6222e6ca6aefe9f605ad13e7dd6d258f6ad243afcac07cb578108c6`.

```
record := int32[24] header  +  float32[64] payload      (little endian)
```

The header carries the key of every record: `kpt` (always 1), `packed` (YYYYJJJHH),
`seconds`, `ii` (puff index), `icode`, `ixs`, `iys`, `mdoms`, `istab`, `ilayer`,
`nsam`, `nsstr`, `iold`, `istype`, `ipno`, `mdstep`, `ksam`, `lcalm`, `nspec`,
`lpuff`, `islug`, `isrcnum` and two reserved slots. Records are ordered by timestep,
then puff index, then sampling substep, and each record carries its own
`(packed, ii, ksam)` key, so no external index is needed. `dgm_puffstep.json` names
every slot with its unit and meaning.

Units worth flagging:

- `xold/yold/xnew/ynew`, `xpb/ypb`, `xb1/yb1`, `xe1/ye1` are in **grid units (cells)
  of the outermost met grid**, not km: CALPUFF stores puff positions as
  `dxmold = dxoldm * dgridi` with `dgridi = 1/dgrid` (`calpuff.for` L40545). Here one
  cell is 100 m, and the source sits at `xold = yold = 25.0` cells = 2.5 km from the
  510.885/3531.269 km corner, exactly the case's stack position.
- `zold/zpb/zb1/ze1/ztop/zbot` are metres above sea level; `distm/xtotb` metres;
  `tsamp/tleft/tsampsum/tmtotb` seconds; winds m/s; `el/dpbl/z0m` metres;
  `sigyb/sigzb/syb1/sym1/sye1/szb1/szm1/sze1` metres.
- `tsamp` is the **cadence** value at the start of the puff's processing; the length
  actually used by the step is `tsamp_effective` (slot 63), which can be shorter when
  the step is split to respect `XSAMLEN`.
- `sigzb_in` is the stored sigma-z **after** any vertical-divergence adjustment of
  this substep (the `szdivfac` block at L10632-10652), which is what `SETPUF` receives.
- `xb1_in…sze1_in` are the `/CURRENT/` values entering `SETPUF`; since `SETPUF` is
  called per puff in sequence, they are the previous puff's return values (a
  carry-over, documented rather than meaningful per puff). The `*_out` values are this
  puff's end-of-step state.
- CALPUFF has no `znew`: the vertical end position is the internal `ze1`, and
  `zpb_out` is the stored result (`zpb(ii)=ze1`, L48723).
- No missing-value sentinel is inserted or interpreted; every value is defined at
  these points.

## 5. Inventory

143 hourly labels, `202200100 … 202200622` (2022-01-01 00:00 UTC … 2022-01-06
22:00 UTC), 254,687 records, mean 1,781 records per hour; puffs 1 … 11,985; 216,080
records for new puffs and 38,607 for old ones; 989 records took the calm treatment;
`nsam` is 99 for 146,769 records (the `MXSAM` cap) and the last substep
(`ksam == nsam`) is reached 3,632 times. `tsamp_effective` spans 18.557 s … 3600 s
(mean 45.374 s), i.e. the substep split is exercised.

The hour-by-hour table (label, seconds, record count, first/last puff, first/last byte
offset) is in `dgm_puffstep.json` under `time.hour_table`, so any hour can be sliced
out of the full dump without re-running anything. The committed slice is hour
**202200100**: `dgm_puffstep_hour202200100.bin`, 448,800 bytes = 1,275 records
(puffs 1…54), sha256
`b51d20d3cd1085902342d5b6d6b2f34c4a84c96d4966b63a2b1231c126087c89`.

## 6. Consistency checks on the dump

Run over all 254,687 records:

| check | result |
|---|---|
| `xpb/ypb/zpb/sigyb/tmtotb/xtotb` at step *n+1* entry vs step *n* return, for 238,908 consecutive-substep pairs | **0 mismatches** (>1e-4) |
| `sigzb` from step *n* return to step *n+1* entry | never decreases (133,733 increases, 0 decreases) — the vertical-divergence factor |
| `distm` vs `ws * tsamp_effective` | max relative difference **5.8e-08** (single precision) |
| `ws` vs `hypot(uadv_adjusted, vadv_adjusted)` | within 1e-4 for every record |
| `zold` inside `[zbot, ztop]` from `PUFFDZ` | holds for every record (0 violations) |
| `ztop >= zbot` | holds for every record |

The dump is therefore an internally coherent trace: consecutive records join exactly,
and the step algebra closes.

### 6.1 Example rows — puff 1, hour 202200100

| ksam | cell | `zbot`/`ztop` m | `uadv`/`vadv` (ADVECT) | `uadv`/`vadv` (adjusted) | `ws` | `tsamp_eff` | `distm` | `xold,yold` → `xnew,ynew` | `xtotb` | `sigyb`/`sigzb` |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 26,26 | 135.40 / 137.40 | −0.5652 / 1.3829 | −0.5793 / 1.3557 | 1.4743 | 66.667 | 98.29 | 25.0000, 25.0000 → 24.6138, 25.9038 | 0 → 98 | 1 → 8 / 1 → 5 |
| 2 | 25,26 | 130.95 / 141.86 | −0.5641 / 1.3803 | −0.5641 / 1.3803 | 1.4911 | 66.667 | 99.41 | 24.6138, 25.9038 → 24.2378, 26.8240 | 98 → 197 | 8 → 16 / 5 → 9 |
| 3 | 25,27 | 126.92 / 145.89 | −0.5614 / 1.3742 | −0.5614 / 1.3742 | 1.4845 | 66.667 | 98.96 | 24.2378, 26.8240 → 23.8635, 27.7402 | 197 → 296 | 16 → 23 / 9 → 13 |
| 4 | 24,28 | 123.22 / 149.59 | −0.5615 / 1.3745 | −0.5615 / 1.3745 | 1.4848 | 66.667 | 98.99 | 23.8635, 27.7402 → 23.4892, 28.6565 | 296 → 395 | 23 → 29 / 13 → 16 |

(All four rows: `ii=1`, `icode=1`, `istab=4`, `ilayer=4`, `dpbl=231.0 m`,
`el=−49.5 m`, `z0=0.250 m`, `zold=htmet=136.404 m`, `nsam=54`,
`nsstr=1`, `iold=0`, `istype=1`, `ipno=1`; 54 × 66.667 s = 3600 s.)

Substep 1 is the only one where the rise-wind adjustment changes the wind
(`RISEWIND`, the puff is still rising), and it is the only one where
`zbot/ztop` is a tight ±1 m bracket — later substeps widen as the plume grows.

## 7. Artifacts

Committed under `native_cpp/modules/p7_calpuff/reference/dgm_p7_advection_2022/`:

| file | bytes | sha256 |
|---|---|---|
| `original_puff_step_dump.py` (the tool) | 35,820 | `96217b3917c56a12d4252db735ed3c285a55402d7531a8a8eda24e13fa969198` |
| `dgm-audit.json` | 8,942 | `38634e799f6c9d1484ba1d15976f7d8975d2dfc7fe6e4a41421fe03ac39b9bae` |
| `dgm-instrumentation.json` | 5,651 | `20841ae338189064a67c83fe3d3b52cdd068e3f8fd1dea2ba9834e6acbffecf4` |
| `dgm_puffstep.json` | 53,285 | `794ec3dea276ae8b0c371c9520e59c42d3629b473f53784485cc49604d461184` |
| `dgm_puffstep_hour202200100.bin` | 448,800 | `b51d20d3cd1085902342d5b6d6b2f34c4a84c96d4966b63a2b1231c126087c89` |

The full dump stays on the build host:
`/home/lhy/build/dgm3/out/case/run/puff/dgm_puffstep.bin`
`cbbdaa29c6222e6ca6aefe9f605ad13e7dd6d258f6ad243afcac07cb578108c6` (89,649,824 bytes,
254,687 records); `dgm_puffstep_hour202200100.bin` is force-added because the
repository ignores `*.bin`.

## 8. Scope and limits

- Selected case and configuration only: `METFM=1`, `MGAUSS=1`, `MSLUG=0`, `MCTADJ=2`,
  `MCTSG=0`, `MBDW=1`, `NSE=1`, `NSPEC=2`, one point source, `NSECDT=3600`,
  143 hourly steps, `XSAMLEN=1.0`, `MXSAM=99`.
- The `POWLAW`/`XTPRF` arms (`METFM` 2-5) and the slug path (`SETSLG`) are off this
  deck and are **not** instrumented; `RISEWIND` is instrumented only through its
  effect on `uadv/vadv/ws` (item 5).
- `xb1_in…sze1_in` are the previous puff's carry-over, as noted in §4; `xsami` is set
  for old puffs and carried over for new ones.
- The dump is internal state, not a CALPUFF output contract, and must not be written
  into `puff.con`.
