# DGM — original CALMET 6.5.0 internal-state dump for the frozen Hefei 2022 case

Date: 2026-10-12. Track: **DGM** (original internal-state diagnostic), serving the P6E
mixing-height residuals. Target case: `project/cases/hefei5km_2022_reference_case_20261011`
(read-only). Vendor tree `engine/vendor/src/CALMET_v6.5.0_L150223/` is **unmodified**.

## 1. Why this run exists

P6E reproduces the frozen reference `CALMET.DAT` except in three coupled places:

| field | cells out of 357,500 | worst | relative |
|---|---|---|---|
| `ZI` | 4,488 (1.26 %) | 51.06 m | 4.9 % |
| `WSTAR` | 4,880 (1.4 %) | 0.0263 m/s | 1.9 % |
| `T-LEV 5/6/7` | 713 | 2.51669 K | — |

All three share one cause at the surface-station cell and its neighbourhood. The
source of that cause **cannot be read out of `CALMET.DAT` 2.1**: the original writes
`ZI`, `WSTAR` and `T-LEV` there, but not the convective mixing height `ZICONV`, the
Maul-Carson lapse-rate memory `DPTT`, nor the fluxes `QH`/`USTAR`/`EL` that feed them
(the P6E writer rejects those names as file labels precisely because the original never
writes them). Sounding datum (`ICONVRT`), `DZZI=200`, the `DPTT` advance order and the
`AVEMIX` geometry had already been excluded (`--skip-avemix` makes `ZI` eight times
worse, so the averaging is required and broadly right).

This track therefore reruns the **unmodified original** with **write-only**
instrumentation, exporting the internal state, and proves the instrumentation changed
nothing.

## 2. What was executed

One command, on the build host `lhy-desktop` (`/usr/bin/gfortran-11`, GNU Fortran 11.4.0),
in `/home/lhy/build/dgm`:

```
python3 original_internal_state_dump.py audit \
  --vendor CALMET_v6.5.0_L150223 --case case-src --out out --compiler /usr/bin/gfortran-11
python3 original_internal_state_dump.py metadata \
  --dump out/case/run/met/dgm_state.bin --out out --dgrid-m 100.0 --station-cell 26,26
```

`audit` copies the pinned original `calmet.for` to a temporary file, appends five
write-only dump calls and one helper subroutine, compiles **both** the untouched
original and the instrumented copy with one compiler and one flag set, stages the frozen
case inputs, runs both binaries on them, and requires the two `MET.DAT` files to hash
identically. Nothing under `engine/vendor/` is written to; the run happens in
`/home/lhy/build/dgm/out/case/`, not in the shared checkout or the gate driver.

### 2.1 The instrumentation is write-only — evidence

| run | binary | inputs | `MET.DAT` bytes | `MET.DAT` sha256 |
|---|---|---|---|---|
| untouched original | `out/bin/met-original.x` | frozen case | 64,762,556 | `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30` |
| write-only instrumented | `out/bin/met-instrumented.x` | same, byte identical | 64,762,556 | `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30` |

Both runs returned 0 and both hashes equal the frozen reference
`P7_FROZEN_2022_MET_DAT` hash, so the instrumented binary is bit-for-bit equivalent to
the original **and** to the run that produced the frozen case. The untouched binary
wrote no dump file (the audit fails closed if it does). Evidence:
`dgm-audit.json` (`status: ORIGINAL_MET_DAT_IDENTICAL`,
`met_dat_identical: true`, `met_dat_matches_frozen_reference: true`).

Staged inputs, hashed by the audit and re-verified against the tracked case files:

| input | bytes | sha256 |
|---|---|---|
| `geo/makegeo/geo.dat` | 161,274 | `c71133b3775bd4d14854a4787bffd1e403e1b4ee869f38adfef7bc769cd603f1` |
| `met/surface/final/surf.dat` | 13,841 | `082202c9d4e87dca35869b5ab4dccde115f243ba129341e2301f123cb2672cff` |
| `met/upperair/final/up_58424.dat` | 1,303,225 | `ffdd54156508a1be23c9e4f484e5a68dc3aab832ad5ab65f1b260029ecac0944` |
| `run/met/met.inp` | 43,942 | `94b6d34639abb3f54719577298c49b6939c9c6eec5b3755c79dddfaa01edc671` |

### 2.2 Build commands and compiler

```
/usr/bin/gfortran-11 -std=legacy -ffixed-line-length-none -fno-automatic \
  -fno-align-commons -fallow-argument-mismatch -O0 -I<include-alias> \
  <source> -o <binary>
```

`<include-alias>` is a lower-case symlink alias tree of the vendor directory (the vendor
sources `INCLUDE` lower-case names while the tracked names are upper case) — the same
recipe the frozen reference capture used. `calmet.for` textually `INCLUDE`s
`calutils.for`, so `calutils.for` must **not** also be compiled as a separate unit.
Compiler: `GNU Fortran (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0`.

## 3. Source anchors

Vendor `calmet.for` sha256
`430381b4fb87f15127e20b13cc3e99be8a0e0fccf1d5821110af7f980558d134`,
`calutils.for` sha256 `1e1fbad6444dcebbcaefed3f5f9a65e5ab0569d45fdf12ea973ca613b8d7cad1`
(both re-verified by the tool before it will insert anything; any drift aborts).

Every insertion is inside `subroutine comp`, in the hourly mixing-height block. Each
insert is one comment plus one `call dgmstate(...)`; no original statement is altered.

| point | vendor line | where | fields dumped | inserted text sha256 |
|---|---|---|---|---|
| 1 | 4686 | after `ELUSTR` (`QH`/`USTAR`/`EL`) and its optional prints, before `MIXHT` | `QH`, `USTAR`, `EL`, `RHO`, `TEMP2D` | `2447d770c6ab0a202ab12a0a7826d3214b46f148047aa7847df522fdaff09815` |
| 2 | 4690 | immediately before the `MIXHT`/`MIXHT2` call (memory entering the hour) | `ZICONV`, `DPTT` | `8a38d9dfcbf9f0f5385bc479cb29343abbca1e41b49ea5882e1b2dcdd4217870` |
| 3 | 4699 | immediately after `MIXHT`/`MIXHT2`, before `AVEMIX` | `ZI`, `ZICONV`, `DPTT` | `66118f6e5f61e6da8a94a6816b9b0c994833b85afb47c20b09f23baebdfb772e` |
| 4 | 4717 | immediately after the `IAVEZI=1` `AVEMIX` averaging | `ZI`, `ZICONV` | `caa86df8e37f030b6d5b76cc043e525ad09015e4d725b59aab44f6474a66d40c` |
| 5 | 4750 | immediately after `WSTARR` | `WSTAR`, `ZICONV` | `c892ffd64cf67e42417d6dc3396ad505d9e9297aae964dd7e1612e6edf774208` |

- Instrumented source segment (vendor lines 4657–4751, the whole `COMP` mixing-height
  block that carries the insertions): sha256
  `9855666ed86d6a9dd3456fee000478e476054b5ddbe4807f0f85827b3d9fd92b`.
- Appended helper `DGMSTATE` (starts at vendor line 40199, opens unit 97,
  `dgm_state.bin`): sha256
  `fd55b1767bef1990bf2647282c7531a61e6342e6369fc2a326ebd637de9fe65a`.
- Whole instrumented file `calmet_instrumented.for`: sha256
  `d763a642d3b9327c1cec40778cb3e2ac0d8f216c290b818c336e6aa278c95d6d`
  (regenerable in seconds from the pinned vendor source; `dgm-instrumentation.json`
  records every hash above).

`DGMSTATE` reads `QH/USTAR/ZI/EL/WSTAR` from `/METGRD/`, `DPTT` from `/TJMP/`, and takes
`RHO`, `TEMP2D`, `ZICONV` (all `COMP` locals) plus the timestep label as arguments. It
only writes to its own unit 97; it never modifies a model variable.

## 4. The dump

- `dgm_state.bin` — 20,042,880 bytes, sha256
  `e6b8ab309f81ddc3015dc750272eeb2ee8289a2d34563b364884d9e443be6ece`
  — 715 records = 143 hours × 5 points.
- `dgm_state.meta.json` — sha256
  `4161abc4f4c36fa08afe7d5c5c03b0027922ffdfdacae76d9bb781285c53182e`
  — field names, shapes, dtype, units, sentinel statement, time labels, per-field
  statistics over the whole grid and over the station 3×3.
- `dgm_station_neighbourhood.json` — sha256
  `0f41e85a0f220ffedb0029edef4f145f6efcf9db635527922d3eaa1d6530cec9`
  — every dumped field at the station cell and its 3×3 neighbourhood, all 143 hours.

Layout (little endian, gfortran 4-byte `INTEGER`/`REAL`):

```
record := int32[8] = (kpt, nh, nyr, ijul, ihr, isec, nx, ny)
          then the point's fields, each nx*ny float32, i fastest
```

i-fastest element `(j-1)*nx + i` for 1-based `i=1..nx` east and `j=1..ny` north; hour
major, then `kpt=1..5`. Fields, units and provenance:

| field | units | meaning |
|---|---|---|
| `QH` | W/m² | sensible heat flux over land, buoyancy flux over water (`/METGRD/`) |
| `USTAR` | m/s | friction velocity (`/METGRD/`) |
| `EL` | m | Monin-Obukhov length, negative when unstable (`/METGRD/`) |
| `RHO` | kg/m³ | air density at the lowest grid level (`COMP` local) |
| `TEMP2D` | K | 2-D surface temperature field (`COMP` local) |
| `ZI` | m | `max(mechanical, ZICONV)` limited to `ZIMIN`/`ZIMAX` (`/METGRD/`) |
| `ZICONV` | m | convective mixing height (`COMP` local); 0 in the stable branch |
| `DPTT` | K/m | potential-temperature lapse-rate memory of `MIXHMC` (`/TJMP/`); 0 in the stable branch and at start |
| `WSTAR` | m/s | convective velocity scale (`/METGRD/`) |

Time: `nyr`/`ijul`/`ihr` are the timestep's **beginning** time as packed `YYYYJJJHH`
(the same label `COMP` computes as `ndathrb`), `isec` its beginning seconds (`0` for
this hourly case), `nh` the `COMP` hour counter. `nh=1..143` maps to
`202200100 … 202200622`, i.e. 2022-01-01T00:00Z … 2022-01-06T22:00Z, one hour each.

Missing values: **no sentinel is inserted or interpreted.** `CALMET.DAT` 2.1 encodes
missing grid values as `9999.`, but every array dumped here is fully populated at the
dump points, so a reader must not special-case any value.

Grid: `nx=ny=50`, `dgrid=100 m` (cells are `(i,j)` centres, CALMET.DAT `/GRID/`
`XORIGR/YORIGR` is the south-west corner). The station cell is `(26,26)` 1-based
(0-based `(25,25)`, i-fastest flat index `1275`), derived from the frozen `MET.DAT`
itself: its `/MET1/` static records `XSSTA` and `YSSTA` both read `2500.0 m`, i.e.
exactly 25 cells inside the 510.885/3531.269 km corner. P6E's E34 experiment had
already located the reference bump at the same 0-based `(25,25)`.

### 4.1 Independent cross-check of the dump against the frozen `CALMET.DAT`

The dump's point-4 `ZI` and point-5 `WSTAR` are compared field-by-field against the
`ZI` and `WSTAR` records the **frozen reference file itself** carries (143 hourly
records × 2,500 cells each): **maximum absolute difference 0.0** — the instrumented
run's internal mixing height and convective velocity scale are bit-identical to the
values written into `project/cases/hefei5km_2022_reference_case_20261011/run/met/met.dat`.
The dump is therefore a faithful window into the state that produced the frozen
reference, not a look-alike.

## 5. Finding — the residual is the station cell's refreshed `DPTT` memory

The residual is **not** in `QH`: across the station 3×3 in the failing hours `QH`
spreads by only `0.003–0.014 W/m²` (relative ≈ 1e-4) and `EL`, `RHO`, `USTAR`,
`TEMP2D` are equally flat. What is not flat is `DPTT`.

`COMP` runs `DIAGNO` (L4511) before the flux block. With `IEXTRP=-4` (the case value,
"extrapolate with similarity theory") `DIAGNO` calls `STHEOR` once per surface station
(L5943), which calls `ELUSTR2` for that station (L31152), which calls `MIXHTST` for
that station's grid cell only (L6881). `MIXHTST` calls `MIXHMC`, which writes `DPTT`
through the `/TJMP/` common (L10782, L11729) — while its own `ZICONV` result stays in a
local, so the grid's `ZICONV` is untouched by this call. The grid-wide `MIXHT` then runs
over all cells and updates `DPTT` again. So:

- the **station cell's** `DPTT` entering `MIXHT` has already been recomputed this hour
  from this hour's `ZICONV`, while
- **every other cell** enters `MIXHT` carrying *the previous hour's* `DPTT`.

`DPTT` enters the Maul-Carson growth with a large lever arm
(`calmet.for` L11723–11729):

```
dpttp1 = sqrt(gamma*twodte*(wt-wto))
unsqrt = htold**2 + 2*((wt-wto)*onedte - dptt*htold)/gamma
zic    = sqrt(unsqrt) + dpttp1/gamma
```

so a stale (larger) `DPTT` suppresses growth while the refreshed one does not. Measured
at the five failing hours (0-based hours 5, 8, 30, 32, 53 = `nh` 6, 9, 31, 33, 54;
values straight from the dump, `j=25`, `i=24/25/26`):

| `nh` | cell | `QH` W/m² | `htold` m | `DPTT` in | `DPTT` out | `ZICONV` pre-`AVEMIX` | `ZI` post-`AVEMIX` (= frozen file) |
|---|---|---|---|---|---|---|---|
| 6 | (24,25) | 126.3489 | 958.07 | 0.7765 | 0.4297 | 985.46 | 985.31 |
| 6 | **(25,25)** | 126.3474 | 955.12 | **0.4245** | 0.4245 | **1222.60** | **1036.44** |
| 6 | (26,25) | 126.3459 | 959.87 | 0.7527 | 0.4328 | 1006.55 | 1009.65 |
| 9 | (24,25) | 0.0432 | 1161.08 | 0.3264 | 0.0084 | 976.53 | 971.01 |
| 9 | **(25,25)** | 0.0390 | 1170.90 | **0.0076** | 0.0076 | **1170.96** | **1009.95** |
| 31 | (24,25) | 97.6779 | 958.55 | 0.4318 | 0.4003 | 1117.12 | 1112.24 |
| 31 | **(25,25)** | 97.6754 | 974.48 | **0.3974** | 0.3974 | **1149.89** | **1115.34** |
| 33 | (24,25) | 0.3250 | 1130.31 | 0.2830 | 0.0227 | 978.94 | 979.20 |
| 33 | **(25,25)** | 0.3208 | 1140.43 | **0.0235** | 0.0235 | **1140.84** | **995.49** |
| 54 | (24,25) | 127.8952 | 568.32 | 0.9341 | 0.5618 | 699.52 | 714.60 |
| 54 | **(25,25)** | 127.8937 | 580.57 | **0.5114** | 0.5114 | **889.12** | **741.24** |

Two facts fall out of the table:

1. At the station cell `DPTT` in = `DPTT` out (refreshed before `MIXHT`); at every
   neighbour it does not.
2. The original's own `MIXHMC` formula, fed the dump's own `QH`/`RHO`/`htold`/`DPTT`
   values, reproduces the observed pre-`AVEMIX` `ZICONV` **to 1e-4 m** at every cell
   and hour (e.g. `nh=6`: 985.4585 vs 985.4585, 1222.6008 vs 1222.6009, 1006.5546 vs
   1006.5546). Substituting the station cell's *refreshed* `DPTT` into a neighbour
   raises that neighbour to the same spike (e.g. `nh=6` cell `(24,25)`: 1221.43 instead
   of 985.46) — the asymmetry is entirely the entering `DPTT`.

`AVEMIX` then smooths the 1222.60 m pre-average spike down to the 1036.44 m the frozen
file carries, and `WSTARR`/`TEMP3D` turn the same state into the `WSTAR` and
`T-LEV 5/6/7` residuals. One internal mechanism, three symptoms.

**Consequence for P6E:** feeding the raw station sounding uniformly to every cell cannot
reproduce this, because the per-cell asymmetry lives in the `DPTT` *memory* and in the
extra `MIXHTST` call `DIAGNO`→`STHEOR` makes for the station cell. To close the bound,
P6E's hourly chain needs that station-cell `MIXHTST` refresh (per surface station, with
`|IEXTRP|=4`) before the grid-wide mixing-height pass — the `ZICONV`/`DPTT`/`QH` values
to align against are in this dump.

## 6. Artifacts

Committed under `native_cpp/modules/p6_calmet/reference/dgm_internal_state_2022/`:

| file | bytes | sha256 |
|---|---|---|
| `dgm_state.bin` | 20,042,880 | `e6b8ab309f81ddc3015dc750272eeb2ee8289a2d34563b364884d9e443be6ece` |
| `dgm_state.meta.json` | 32,438 | `4161abc4f4c36fa08afe7d5c5c03b0027922ffdfdacae76d9bb781285c53182e` |
| `dgm_station_neighbourhood.json` | 1,293,978 | `0f41e85a0f220ffedb0029edef4f145f6efcf9db635527922d3eaa1d6530cec9` |
| `dgm-audit.json` | 5,817 | `fd14132e62b1ce9250399c5be9353eecd00fba119535bf1bf5a5b55670de9193` |
| `dgm-instrumentation.json` | 2,861 | `43abfab91d00f202ce56f7b2acf1bcd362cbd5b15d718a16000c11952cc0e33f` |

The two JSON files record absolute build-host paths
(`/home/lhy/build/dgm/out/...`) as provenance; the bytes are the same files listed
above. `dgm_state.bin` is force-added because the repository ignores `*.bin` (the same
way the tracked `project/` case outputs are), and its hash is what the metadata pins.
Tool: `native_cpp/modules/p6_calmet/reference/original_internal_state_dump.py`
(`instrument` / `audit` / `metadata`), which pins the vendor hashes and fails closed on
any source drift, on a changed `MET.DAT`, or on a missing dump.

## 7. Scope and limits

- Selected case only: 50×50×9, 100 m, one surface station, one `UP.DAT 2.1` station,
  143 hourly steps, `IMIXH=1`, `IZICRLX=1`, `THRESHL=0`, `IAVEZI=1`, `NOOBS=0`,
  `ITPROG=0`, `LCALGRD=T`, `IWFCOD=1`.
- The dump is internal state, not a model output contract; it is not a `CALMET.DAT`
  field and must not be written into one.
- Only the paths the selected case exercises were instrumented (`MIXHT`, not
  `MIXHT2`/`MIXHTST`'s own outputs; `IAVEZI=1`). `MIXHTST`'s effect is visible here
  through the `DPTT` it leaves behind, not through its own `ZICONV`, which it keeps
  local.
- No claim is made about other cases, other mixing-height options, overwater paths, or
  the remaining P6/P7 stages.
