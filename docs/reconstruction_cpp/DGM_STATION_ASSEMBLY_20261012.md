# DGM round 4 — original CALMET station assembly and upper-air columns (P6D request)

Date: 2026-10-12. Track: **DGM**, round 4 (rounds 1-3:
[DGM_INTERNAL_STATE_DUMP_20261012.md](DGM_INTERNAL_STATE_DUMP_20261012.md),
[DGM_P6D_INTERNAL_STATE_REQUESTS_20261012.md](DGM_P6D_INTERNAL_STATE_REQUESTS_20261012.md),
[DGM_P7_PUFF_STEP_DUMP_20261012.md](DGM_P7_PUFF_STEP_DUMP_20261012.md)).
Target: the frozen Hefei 2022 case, **CALMET 6.5.0**. The vendor tree is
**unmodified**; artifacts on the build host under `/home/lhy/build/dgm4/`.

## 1. What P6D asked for

P6D's round 17 (PR #23) records the request verbatim: for hours 17, 18, 41, 42,
47, 48 dump

- **(a)** the surface station column as it enters the analysis, and
  `US(1,1)/VS(1,1)` after `DIAGI`'s anemometer-to-`ZMID(1)` adjustment,
- **(b)** `UDAT/VDAT` after `RDUPN` for all nine levels,
- **(c)** `UG/VG` at the existing kpt 8,

*"that separates the surface observation assembly, the UA low-level
interpolation and the analysis weights"*. The motivating fact: level 1 is the
observed surface wind (anemometer 10 m = `ZMID(1)`), so no SIMILT is involved and
the EL/ZII tables cannot move it; the two level-1 fields agree at the station
cell to ~1.2e-04 while the worst cell differs by 1.567e-03, i.e. they have
different *spatial patterns*.

Hours 17/18/41/42/47/48 are P6D's index (hours since the run start minus one):
they are the UTC intervals **2022-01-01 18/19, 2022-01-02 18/19, 2022-01-03
00/01**, i.e. packed labels `202200118, 202200119, 202200218, 202200219,
202200300, 202200301`. The dump covers **all 143 hours**, so no hour is lost to an
index convention.

## 2. What was executed

One command on `lhy-desktop` (`/usr/bin/gfortran-11`, GNU Fortran 11.4.0):

```
python3 original_station_assembly_dump.py audit \
  --vendor CALMET_v6.5.0_L150223 \
  --case <frozen case dir> --out out --compiler /usr/bin/gfortran-11
python3 original_station_assembly_dump.py metadata \
  --dump out/case/run/met/dgm_station.bin --out out \
  --hours 202200118 202200119 202200218 202200219 202200300 202200301
```

`audit` copies the pinned original `calmet.for` to a temporary file, appends four
write-only calls and four helper subroutines, compiles **both** the untouched
original and the instrumented copy with one compiler and one flag set
(`-std=legacy -ffixed-line-length-none -fno-automatic -fno-align-commons
-fallow-argument-mismatch -O0`), stages the frozen case, runs both binaries on
it, and requires the two produced `MET.DAT` files to hash identically.

### 2.1 Write-only proof

| run | `MET.DAT` bytes | `MET.DAT` sha256 |
|---|---|---|
| untouched original | 64,762,556 | `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30` |
| write-only instrumented | 64,762,556 | `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30` |

Both runs returned 0 and both hashes equal the frozen reference. The untouched
binary wrote **no** dump file; the audit fails closed if it does or if the
instrumented run's dump is missing. Evidence: `dgm-audit.json`
(`status: ORIGINAL_MET_DAT_IDENTICAL`).

Inputs, hashed by the audit: `geo/makegeo/geo.dat c71133b3…`,
`met/surface/final/surf.dat 082202c9…`, `met/upperair/final/up_58424.dat
ffdd5415…`, `run/met/met.inp 94b6d346…` (the frozen values).

## 3. Source anchors

Vendor `calmet.for` sha256
`430381b4fb87f15127e20b13cc3e99be8a0e0fccf1d5821110af7f980558d134` (re-verified
before any insertion; any drift aborts). Each insertion is one comment plus one
call; no original statement is altered.

| kpt | routine | vendor line | where | inserted text sha256 |
|---|---|---|---|---|
| 1 | `PREPDI` | 13906 | after the surface observations are converted to U/V (`10 continue`, L13878-13906) | `27e7b210134b28ce64e2afc68c14a4cae5c72b908a9a9a4bee5f2cab931611a3` |
| 2 | `DIAGNO` | 5958 | after the per-station loop (`70 CONTINUE`, L5797-5958) | `86e2679713c9b59c876adce37d89562474fb01459a961bc772e29ca4d733cd59` |
| 3 | `COMP` | 4392 | after the AA `VERTAV`/`FACET` block (fires only when a new sounding is read) | `3ad7e6928d9c8a7ea963d8cdbdb728b9464d7e82e9c051737a6c31934b51dbab` |
| 4 | `COMP` | 4423 | immediately before the `PREPDI` call (L4424-4426), so it fires every hour | `d9a6c2c86f4be6d714f921df733748d9df813e824119ea1b15cb3d5565fb1130` |

Point 3 answers the literal reading of (b) *after `RDUPN`* (it fires 7 times in
this run, once per newly read sounding); point 4 answers the operational reading
*the columns the analysis consumes this hour* (143 times). Both carry the same
payload, and point 4 additionally records which soundings were in use
(`justa`, `ntzaa`, `ntzbb`, `jusdt`).

Supporting hashes: whole instrumented file `calmet_instrumented.for`
`532f7f0aa10fed48c2ad08720b96aa6f4e2f42d3e2c90ebd9c397ba2b5438251`; helper block
(`DGMSURFIN`, `DGMSURFADJ`, `DGMSOUND`, `DGMSOUNDHR`, appended from vendor line
40199, unit 94)
`994459d9e3a793cff9728a31017a6fa9293c0c002b11284b8f81b48d596e9502`; instrumented
source segments `prepdi_station_conversion` L13868-13907
`7b747db63ccd4ffab602545bd3af756337558afa1b729db3d3b6054660b5ab5e`,
`diagno_station_loop` L5797-5959
`a2645907a62175d506aff204dac80468b31813afa9374a5e04788f5dbe2cfcdd`,
`comp_vertav_aa` L4379-4393
`64bd07eeba15a0d4c8d1c5902d9c9f3b5d1656b4601fab3f5923dd76f0d33b07`,
`comp_prepdi_call` L4416-4427
`6a260cec16a322ffe4d9901fd9579b8015c04f866733f0feaadafdf279e62126`.

## 4. Array index order — the `STDAT1(K,L)` trap, checked

Main asked for this explicitly, and it is worth stating per array, because the
round-15/16 failure came from filling a level-major array station-major:

| array | declaration | index order | vendor line |
|---|---|---|---|
| `/UPMET/` `uaa`, `vaa`, `ubb`, `vbb`, `zlaa`, `zlbb` | `uaa(mxus,mxlev)` | **station-major**: element `(iu,k)`, the level index varies fastest | `upmet.met` L5-6 |
| `VERTAV` inputs `uu`, `vv`, `zz` | `uu(mxus,mxlev)` | station-major | `calmet.for` L32287 |
| `VERTAV` outputs `uave`, `vave` | `uave(mxnz)` | level-major | `calmet.for` L32290 |
| `COMP` `uaveaa/uavebb/vaveaa/vavebb` | `uaveaa(mxnz,mxus)` | **level-major**: element `(k,iu)`, the station index varies fastest | `calmet.for` L3612-3613 |
| `/D1/` `US`, `VS` | `us(mxnz,mxwnd)` | level-major: element `(k,l)` | `d1.met` L12 |
| `INTER2` `STDAT1` (fed `US`, `VS`) | `STDAT1(mxnz,*)` | level-major | `calmet.for` L8226 |

Three numerical checks back this up on the dump itself:

1. **Reimplemented `VERTAV`.** Recomputing the layer averages from the dumped
   sounding columns exactly as the original does (insert each cell face by
   linear interpolation, then the trapezoid average over the layer,
   `calmet.for` L32317-32399) reproduces the dumped `UAVERAA/VAVERAA/UAVERBB/
   VAVERBB` for **all 2,574 layer averages** (143 hours × 2 soundings × 9 layers)
   with a maximum absolute difference of **1.73e-04 m/s** (Fortran f32
   accumulation versus the f64 recomputation). A transposed read could not do
   this.
2. **Height columns.** `ZLAA` and `ZLBB` are non-decreasing in `k` for every
   record: **0 violations** in 143 hours.
3. **Sounding pairing.** `justa` agrees with the times: at `202200118`,
   `ntzaa=202200200` and `ntzbb=202200112` with `justa=-1` (AA follows BB); at
   `202200300`, `ntzaa=202200300` and `ntzbb=202200312` with `justa=+1` (AA
   precedes BB). `jusdt=43200 s` (12 h) throughout.

`VERTAV`'s internal `+1000/-1000` shift (a missing-value trick around `xmiss`,
`calmet.for` L32299-32398) cancels, so the dumped averages are true m/s.

## 5. The dump

`dgm_station.bin` — 1,813,760 bytes = **436 records × 4,160 bytes**, sha256
`879350905f77128fe92bde4b32b0579267bfe9268c75810df63a46c5f6fe7d47`. Records:
`kpt=1` 143, `kpt=2` 143, `kpt=3` 7, `kpt=4` 143.

```
record := int32[16] header + float32[1024] payload   (little endian)
```

Header: `kpt`, `packed` (YYYYJJJHH), `seconds`, `nssta`, `nusta`, `npsta`, `nz`,
`nlaa`, `nlbb`, `nsurf`, `iu`, `l`, and — for `kpt=4` — `justa`, `ntzaa`,
`ntzbb`, `jusdt`.

Payload slots (each `kpt` fills its own, the rest stay 0):

| slot | field | kpt | units | index order |
|---|---|---|---|---|
| 0-8 | `US_ENTER_1..nz` | 1 | m/s | `(k,l)`, station 1 |
| 9-17 | `VS_ENTER_1..nz` | 1 | m/s | `(k,l)` |
| 18-26 | `US_ADJUSTED_1..nz` | 2 | m/s | `(k,l)` |
| 27-35 | `VS_ADJUSTED_1..nz` | 2 | m/s | `(k,l)` |
| 36-134 | `ZLAA_1..99` | 3,4 | m | `(iu,k)` |
| 135-233 | `UAA_1..99` | 3,4 | m/s | `(iu,k)` |
| 234-332 | `VAA_1..99` | 3,4 | m/s | `(iu,k)` |
| 333-431 | `ZLBB_1..99` | 3,4 | m | `(iu,k)` |
| 432-530 | `UBB_1..99` | 3,4 | m/s | `(iu,k)` |
| 531-629 | `VBB_1..99` | 3,4 | m/s | `(iu,k)` |
| 630-638 | `UAVERAA_1..nz` | 3,4 | m/s | `(k,iu)` |
| 639-647 | `VAVERAA_1..nz` | 3,4 | m/s | `(k,iu)` |
| 648-656 | `UAVERBB_1..nz` | 3,4 | m/s | `(k,iu)` |
| 657-665 | `VAVERBB_1..nz` | 3,4 | m/s | `(k,iu)` |

Missing values: **no sentinel is inserted**, but CALMET's own `EDIT` (9999.) is
written as-is, so a reader must treat `>= 9998.` as missing. In `kpt=1` records
only level 1 is a real observation and levels 2..nz are `EDIT`; in `kpt=2`
records the profile is filled only up to the mixing height (SIMILT's
`zface(k) <= amax1(zi+0.001, zimini)` test) and is `EDIT` above.

Time: the packed `YYYYJJJHH` beginning time of the timestep plus its seconds.
`dgm_station.json` carries the full slot table, the per-field units and index
order, and the six requested hours' rows.

## 6. The six requested hours

`U/V` are the first `nz` slots of each column; `999.0` is `EDIT` (missing).

| packed | UTC | entering `U(1)/V(1)` | adjusted `U(1..9)` | adjusted `V(1..9)` |
|---|---|---|---|---|
| 202200118 | 2022-01-01 18 | −0.394005 / 0.307831 | −0.394, −0.600, 999… | 0.308, 0.561, 999… |
| 202200119 | 2022-01-01 19 | −1.285576 / −1.532089 | −1.286, −2.625, 999… | −1.532, −2.579, 999… |
| 202200218 | 2022-01-02 18 | −0.289778 / −0.077646 | −0.290, −0.430, 999… | −0.078, −0.083, 999… |
| 202200219 | 2022-01-02 19 | −1.969615 / 0.347298 | −1.970, −3.546, 999… | 0.347, 0.984, 999… |
| 202200300 | 2022-01-03 00 | 0.466288 / 0.377592 | 0.466, 0.551, 0.603, 999… | 0.378, 0.419, 0.422, 999… |
| 202200301 | 2022-01-03 01 | 0.000006 / 5.000000 | 0.000, 0.145, 0.374, 0.775, 1.328, 999… | 5.000, 6.259, 6.938, 7.502, 7.921, 999… |

Sounding columns in use (identical payloads at `kpt=3` and `kpt=4`):

| packed | `nlaa`/`nlbb` | `justa` | `ntzaa` | `ntzbb` | `jusdt` | `UAVERAA(1..9)` |
|---|---|---|---|---|---|---|
| 202200118, 202200119 | 63 / 75 | −1 | 202200200 | 202200112 | 43200 | −0.0692, −0.2074, −0.4147, −0.9556, −2.3104, −3.5367, −2.9529, −0.3657, −0.8504 |
| 202200218, 202200219 | 63 / 58 | −1 | 202200300 | 202200212 | 43200 | 0.0, 0.0, 0.0, 0.0, −0.0567, 1.8168, 4.5807, 4.4299, 7.1971 |
| 202200300, 202200301 | 63 / 58 | +1 | 202200300 | 202200312 | 43200 | (as above) |

`UAVERBB`, `VAVERAA`, `VAVERBB`, and the full AA/BB sounding columns are in
`dgm_station.json` for these hours (and in the raw dump for all 143).

## 7. What the dump settles

1. **The anemometer-to-`ZMID(1)` adjustment leaves level 1 unchanged.** Over all
   143 hours the maximum difference between the entering and the adjusted level-1
   wind is **9.54e-06 m/s** — exactly as expected because this deck's anemometer
   height (10 m) equals `ZMID(1)` = (`ZFACE(1)`+`ZFACE(2)`)/2 = 10 m, so the
   neutral-log factor is 1 and the similarity-theory profile reproduces the same
   level-1 value. The level-1 residual therefore cannot come from the observation
   assembly or from that adjustment; it must come from the analysis weighting
   (`INTER2`/`ADJUST`) acting on station positions and radii — P6D's own reading.
2. **The adjusted column stops at the mixing height.** Levels above the SIMILT
   cutoff stay `EDIT`, e.g. 2 valid levels at 202200118 and 5 at 202200301.
3. **The sounding columns and their pairing** are available per hour, with the
   `justa`/`ntzaa`/`ntzbb`/`jusdt` context the interpolation needs.

## 8. Request (c) — `UG/VG` at kpt 8

Sliced from the round-2 fields dump (audited there: `MET.DAT` identical; full
dump sha256 `e32b43880a561f878e4376ed766ce39ec5a050f1af1319b540a19ca0b6a4159f`)
for the same six hours (`nh` 19, 20, 43, 44, 49, 50 = packed 202200118 …
202200301):

| file | bytes | sha256 |
|---|---|---|
| `ugvg_p6d_hours/dgm_fields_hours.bin` | 5,460,768 | `b2bc3cfe63f511eb69173af4f4cb7ffaeca3b78724e9b59ed5044d57dd68e972` |
| `ugvg_p6d_hours/dgm_fields.json` | 79,352 | `efa1a558be2dd6f9bc5d7fc2cfd0104f04ee5b79a1ae7ec32e7b8f1c25531c89` |

The slice uses the round-2 record layout (kpt 7 `USLOPE`/`VSLOPE`, kpt 8 `UG`/`VG`
before the slope-flow addition, kpt 9 after it, kpt 10 `DIV`/`W`/`U`/`V`), whole
50×50×9 grids, i for east and j for north, i fastest.

## 9. Artifacts

Committed under
`native_cpp/modules/p6_calmet/reference/dgm_station_assembly_2022/`:

| file | bytes | sha256 |
|---|---|---|
| `original_station_assembly_dump.py` (the tool) | 30,507 | `58f9541062dcd5e063fdcf10b25dea9435d41be8a4653bf4f6e9eff70bbb9aee` |
| `dgm-audit.json` | 7,197 | `4a177293f935da1f79fae6cce15ed8cfad609fe2c31ff7605a6057eadb0a1940` |
| `dgm-instrumentation.json` | 4,058 | `18bfff54ddf1bf32c088fb581d0632b36bd21e5426a33f2bca9c8c7fc3d05a7b` |
| `dgm_station.json` | 78,644 | `dd5c769f9efbb9b090f52aa37e170c7719d96202361293d6ef57a71383294c49` |
| `dgm_station.bin` | 1,813,760 | `879350905f77128fe92bde4b32b0579267bfe9268c75810df63a46c5f6fe7d47` |
| `ugvg_p6d_hours/dgm_fields_hours.bin` | 5,460,768 | `b2bc3cfe63f511eb69173af4f4cb7ffaeca3b78724e9b59ed5044d57dd68e972` |
| `ugvg_p6d_hours/dgm_fields.json` | 79,314 | `efa1a558be2dd6f9bc5d7fc2cfd0104f04ee5b79a1ae7ec32e7b8f1c25531c89` |

The `.bin` files are force-added because the repository ignores `*.bin`. The same
files remain on the build host under `/home/lhy/build/dgm4/`.

## 10. Scope and limits

- Selected case only: 50×50×9, 100 m, `NSSTA=1`, `NUSTA=1`, `NOWSTA=0`, `NPSTA=0`,
  `NOOBS=0`, `ITPROG=0`, `ISFCMET=0`, `IEXTRP=-4`, `LCALGRD=T`, 143 hourly steps.
- Only the **first** surface station (`l=1`) is dumped; this case has exactly one
  (`nssta=1`), and `nowsta=0`. The sounding payload is station 1 of `nusta=1`.
- `kpt=1` is captured after PREPDI's station loop, i.e. after the over-water
  branch too; with `nowsta=0` only the land branch runs.
- The `STDAT1` order check is numerical (the `VERTAV` reimplementation) plus the
  declaration table; `INTER2`'s own output is not dumped here — that is the
  analysis-weight step P6D is now isolating, and `UG/VG` (request c) plus the
  round-2 kpt 10 `U/V` are the nearest observable points.
- The dump is internal state, not a `CALMET.DAT` contract.
