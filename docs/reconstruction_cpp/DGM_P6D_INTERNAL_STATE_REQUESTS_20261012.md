# DGM round 2 — original CALMET internal state for the two P6D requests

Date: 2026-10-12. Track: **DGM**, round 2 (round 1: [DGM_INTERNAL_STATE_DUMP_20261012.md](DGM_INTERNAL_STATE_DUMP_20261012.md)).
Target case: `project/cases/hefei5km_2022_reference_case_20261011` (read-only).
Vendor tree `engine/vendor/src/CALMET_v6.5.0_L150223/` is **unmodified**. Artifacts on the
build host under `/home/lhy/build/dgm2/`.

## 1. What P6D asked for

1. **The `zii` that `SIMILT` receives.** `ELUSTR2` reads the grid `ZI` into a local
   `zii`, overwrites it through `MIXHTST`/`MIXHT2ST`, and only then calls `SIMILT`,
   which early-stops its level loop at `zface(k) <= amax1(zi+0.001, zimini)`. P6D's
   port feeds the reference `ZI` there, which early-stops one level too soon at its
   hour 80 (2022-01-04 09). Wanted: per hour, the station cell's `zii` plus the
   routine's inputs and the entering values.
2. **The whole-grid fields around `SLOPE` and `DIVCEL`.** `USLOPE`/`VSLOPE` after the
   `SLOPE` call, `UG`/`VG` before and after the slope-flow addition, and `DIV`/`W`
   after the `DIVCEL` loop — at least one hour, whole `50×50×(levels)` — to locate the
   planar tilt of the reference `U/V` field (`U-LEV 3` de-meaned spread `0.0106`,
   fitted `dU/di = -1.30e-05`, `dU/dj = +3.78e-05`) that makes every `WFACE` fail.

## 2. What was executed

One command on `lhy-desktop` (`/usr/bin/gfortran-11`, GNU Fortran 11.4.0):

```
python3 original_internal_state_dump.py audit \
  --vendor CALMET_v6.5.0_L150223 --case case-src --out out --compiler /usr/bin/gfortran-11
python3 original_internal_state_dump.py celltable \
  --dump out/case/run/met/dgm_cell.bin --out out --hours 143 \
  --state-dump out/case/run/met/dgm_state.bin
python3 original_internal_state_dump.py extract-fields \
  --dump out/case/run/met/dgm_fields.bin --out out --hours 1 2 3 81 82 83
```

The round-1 instrumentation (five points in `COMP`, helper `DGMSTATE`, `dgm_state.bin`)
is unchanged and still produced. Round 2 adds two more write-only helpers:
`DGMCELL` (unit 96, `dgm_cell.bin`) inside `ELUSTR2` and `DGMFLD` (unit 95,
`dgm_fields.bin`) inside `DIAGNO`.

### 2.1 Write-only proof

| run | `MET.DAT` sha256 |
|---|---|
| untouched original | `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30` |
| write-only instrumented | `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30` |

Both runs completed all 143 hourly intervals and both hashes equal the frozen
reference. The untouched binary wrote **no** dump file (`dgm_state.bin`, `dgm_cell.bin`,
`dgm_fields.bin`); the audit fails closed if it does or if any is missing. Evidence:
`dgm-audit.json` (`status: ORIGINAL_MET_DAT_IDENTICAL`). Inputs were the frozen case
files, hashed by the audit: `geo.dat c71133b3…`, `surf.dat 082202c9…`,
`up_58424.dat ffdd5415…`, `met.inp 94b6d346…`.

The round-1 dump is reproduced bit for bit by this run: `dgm_state.bin` is again
`e6b8ab309f81ddc3015dc750272eeb2ee8289a2d34563b364884d9e443be6ece`, so the round-1
metadata and neighbourhood tables still describe it exactly.

## 3. Source anchors

Vendor `calmet.for` sha256 `430381b4fb87f15127e20b13cc3e99be8a0e0fccf1d5821110af7f980558d134`
(re-verified before any insertion; any drift aborts). Each insertion is one comment plus
one call; no original statement is altered.

| point | routine | vendor line | where | fields | inserted text sha256 |
|---|---|---|---|---|---|
| 6 | `ELUSTR2` (called by `STHEOR`, per surface station; `DIAGNO` calls `STHEOR`) | 6893 | immediately before `call similt(...)` at 6894 | `ZII_TO_SIMILT`, `ZICONVI_AFTER_MIXHTST`, `ZI_GRID_ENTERING`, `ZICONV_GRID_ENTERING`, `DPTT`, `EL`, `USTAR`, `QQH`, `RHO`, `ZZANEM`, `Z0`, `ZIMIN`, `DPTTMIN` + 12 integer tags | `114c0ce0ad44ccbae80d3b2d8345e41c5fd72618f7cabed52aa7b32b494aa3b2` |
| 7 | `DIAGNO` | 5723 | after the `SLOPE` call (5722–5723) | `USLOPE`, `VSLOPE` | `24a1e955f758e1d33a14fcfab3d68181ee2836cd4378eb6f7099daab0500a9bc` |
| 8 | `DIAGNO` | 5726 | before the slope-flow addition (5727–5732) | `UG`, `VG` | `54492b42dc808a4cb8eca9fcee8de9a4bc3b00c7b22cb166f2b5d57dc5028883` |
| 9 | `DIAGNO` | 5732 | after the slope-flow addition | `UG`, `VG` | `384210e94f829177ae64c08e687a253b43472704261e0c093b16710753e3bdef` |
| 10 | `DIAGNO` | 6148 | after the `DIVCEL` loop (6129–6131) and the `W` integration loop (6139–6148) | `DIV`, `W`, `U`, `V` | `b7b289158b89d99a0b6af3d33a573941a1a744b5841904ea4917f0d6c64615d0` |

Note on the request's wording: point 6 sits in **`ELUSTR2`**, not `DIAGI`. The chain is
`COMP` → `DIAGNO` (L4511) → `STHEOR` (L5943, `|IEXTRP|=4`) → `ELUSTR2` (L31152) →
`MIXHTST` (L6881) → `MIXHT2ST`/`MIXHTST` overwrite the local `zii`, then `SIMILT`
(L6894). `DIAGI` is a different routine (the initial-guess builder).

Supporting hashes:

- whole instrumented file `calmet_instrumented.for`:
  `2905c67094fbe8e911baa77d407be2ed5699bcb3aea6495f417e742e8ffeb50f`
- helper `DGMCELL` (starts at vendor line 40250):
  `8fdb59b25adc6745f0a851ff458336a288822f44aba621516e566677e5266d89`
- helper `DGMFLD` (starts at vendor line 40313):
  `5179fe11d76a31bfcabefb4cc13a7a63cafcf02069fe0d5a5a5ce8f2a87796da`
- instrumented source segments: `ELUSTR2` L6888–6894
  `92d295c12905e19217b4ce4ec123c9d4d34ada07cf1bd2cd180cb11af54892a1`;
  `DIAGNO` slope/addition L5719–5733
  `c94237863538f9698facd67461c00205af0d03a1e033324f7e402dd7c4616d65`;
  `DIAGNO` `DIVCEL`/`W` L6126–6149
  `6cf9b4a03cfc0664dfa6d5935f0230ffdf97c07bdfd241387b3c01bc53e4cef2`
- round-1 segment (unchanged) L4657–4751
  `9855666ed86d6a9dd3456fee000478e476054b5ddbe4807f0f85827b3d9fd92b`

## 4. Request 1 — the `zii` handed to `SIMILT`

`dgm_cell.bin` — 18,876 bytes = 143 records × 132 bytes, sha256
`c82a63f62a2a09fc3fe704c751edfcfc737df758995e77d638026a05c69ce7ed`. Layout:
`int32[8]` header `(kpt=6, packed YYYYJJJHH, seconds, IS, JS, nx, ny, nz)`, then
`int32[12]` tags `(IS, JS, NS, IUPT, ITPROG, IPSIFCN, IHR2GMT, NEARU, ILANDU, IWAT1,
IWAT2, IMIXH)` and `float32[13]` values (field list above; units in
`dgm_cell.json`). No sentinel is inserted or interpreted. `dgm_cell.json` (sha256
`c4ef3b4cd116b0ed8d48967b8050b199bd094f35ccbe40863585c9dcb2f9ff5f`) holds the whole
143-row table plus per-field units and the tag meanings.

**Independent cross-check.** `ZI_GRID_ENTERING` at hour *h* is the grid `ZI` at the
station cell when `ELUSTR2` runs, i.e. the post-`AVEMIX` `ZI` of hour *h−1* that round 1
dumps at point 4. Over all 142 hour pairs the two agree with **maximum absolute
difference 0.0**.

### 4.1 `zii` is not the grid `ZI`

`SIMILT` (vendor L30307–30311) loops `k = 2..nzp1` and processes a level when
`zface(k) <= amax1(zii + 0.001, zimini)`; for this case `ZFACE = 0, 20, 40, 80, 160,
320, 640, 1200, 2000, 3000` m and `ZIMIN = 50` m. Using the grid `ZI` instead of `zii`
changes the level count in **50 of the 143 hours**. Examples (`n` = number of faces
`k=2..10` that pass):

| `nh` | packed | grid `ZI` (m) | `n` | `zii` (m) | `n` | `QQH` (W/m²) |
|---|---|---|---|---|---|---|
| 1 | 202200100 | 0.00 | 2 | 230.96 | 4 | 126.35 |
| 10 | 202200109 | 1009.95 | 6 | 50.00 | 2 | 0.04 |
| 34 | 202200209 | 995.49 | 6 | 153.34 | 3 | 0.33 |
| 58 | 202200309 | 894.72 | 6 | 50.00 | 2 | 0.00 |
| 78 | 202200405 | 651.51 | 6 | 811.67 | 6 | 127.31 |
| 79 | 202200406 | 811.70 | 6 | 744.35 | 6 | 98.72 |
| 80 | 202200407 | 749.84 | 6 | 764.17 | 6 | 55.73 |
| 81 | 202200408 | 768.20 | 6 | 640.39 | 6 | 1.48 |
| **82** | **202200409** | **659.97** | **6** | **153.34** | **3** | **−30.17** |
| 83 | 202200410 | 153.34 | 3 | 276.74 | 4 | −44.93 |
| 84 | 202200411 | 276.74 | 4 | 189.24 | 4 | −34.98 |

(`ZI_GRID_ENTERING` is the hour's *starting* `ZI`, i.e. hour *h−1*'s post-`AVEMIX`
value, which is why it equals the previous row's `zii` in several places.)

At **nh 82 = 2022-01-04 09:00 UTC** — the hour P6D named — `QQH` is negative, so
`MIXHTST` takes its stable branch and `zii` becomes the mechanical value **153.341 m**,
while the grid `ZI` is **659.966 m**; `SIMILT` therefore processes 3 levels, not 6.
The largest divergence in the run is nh 10 (2022-01-01 09:00): grid 1009.95 m against
`zii = 50.0` (= `ZIMIN`).

## 5. Request 2 — the `SLOPE`/`DIVCEL` fields

`dgm_fields.bin` — 130,148,304 bytes = 143 hours × 910,128 bytes, sha256
`e32b43880a561f878e4376ed766ce39ec5a050f1af1319b540a19ca0b6a4159f` (build host only,
too large to track). Layout: `int32[8]` header `(kpt, packed YYYYJJJHH, seconds, i0, j0,
nx, ny, nz)` then whole-grid `float32` fields, i fastest, then j, then k
(`((k-1)*ny+(j-1))*nx+i`). Sizes per point: 7/8/9 = 180,032 B, 10 = 370,032 B.
`U`/`V` were added to point 10 beyond the literal request because they are the fields
`CALMET.DAT` writes as `U-LEV`/`V-LEV` and they are what settles "which step".

Committed subset `dgm_fields_hours.bin` — 5,460,768 bytes = hours
**1, 2, 3, 81, 82, 83**, sha256
`972af841552f7a0eda6b02b221b6b2a808c61806054e634c617425d9ca9babdf` — byte-identical
records copied out of the full dump in the same format. `dgm_fields.json` (sha256
`5f9368b92c87a7cfe87ec49aeb8eaa55c72cee86592c826401928b3da5829046`) documents units,
per-field statistics for the six hours, and the byte offset of **every** record of all
143 hours, so any other hour can be sliced out of the full dump without re-running
anything.

### 5.1 The slope-flow step cannot create a level-3 tilt

`USLOPE`/`VSLOPE` are non-zero **only at level 1** in every committed hour (level 1
max 0.0244 / 0.0343 / 0.0390 / 0.0090 / 0.0558 / 0.0638 m/s at hours 1, 2, 3, 81, 82,
83; levels 2–9 are exactly `0.0`). `SLOPE` (vendor L30570–30579) fills a level only
while `hd > zface(k)`, so this case's slope-flow depth never exceeds `zface(2) = 20 m`.
Consequently the addition at L5730–5731 changes `UG`/`VG` only at level 1 — at hours 1
and 82 the largest `|UG(point 9) − UG(point 8)|` is `0.024386` and `0.055839` m/s at
level 1 and exactly `0.0` at levels 2–9.

### 5.2 Point 10 `U`/`V` are what the frozen file writes

For the six committed hours, point-10 `U` and `V` equal the frozen `CALMET.DAT`'s
`U-LEV`/`V-LEV` records **cell for cell (maximum absolute difference 0.0)** at every
level checked (`U-LEV 1`, `U-LEV 3`, `U-LEV 9`, `V-LEV 3`). The tilt P6D measures in
the reference is therefore exactly the tilt of the field this dump exposes.

### 5.3 The tilt is already in the initial guess

`U-LEV 3` of the frozen file at **hour 1 (202200100)** is de-meaned spread `0.010594`,
fitted `dU/di = -1.299e-05`, `dU/dj = +3.779e-05` — the numbers P6D quoted
(`0.0106`, `-1.30e-05`, `+3.78e-05`). At the same hour and level, the fields this dump
carries are:

| point | field | mean | de-meaned spread | `dU/di` | `dU/dj` |
|---|---|---|---|---|---|
| 8 | `UG` (before the slope addition) | −0.710223 | 0.023788 | −1.466e-05 | +4.263e-05 |
| 9 | `UG` (after the slope addition) | −0.710223 | 0.023788 | −1.466e-05 | +4.263e-05 |
| 10 | `U` (after `ADJUST`+`SMOOTH`+`DIVCEL`, = `U-LEV 3`) | −0.643824 | 0.010594 | −1.299e-05 | +3.779e-05 |

The tilt is **already present in the initial-guess field `UG`** before the slope-flow
addition, with the same signs and the same order of magnitude; the `SLOPE` step is
level-1-only and cannot contribute to level 3 at all. The `ADJUST`+`SMOOTH`+`DIVCEL`
chain (points 9 → 10) halves the de-meaned spread (0.0238 → 0.0106) and slightly weakens
the tilt at hour 1, but it *strengthens* it at hours 82/83 (hour 82: `UG`
`-7.44e-06/+2.16e-05` → `U` `-3.53e-05/+1.03e-04`; hour 83: `UG`
`-1.43e-05/+4.16e-05` → `U` `-3.54e-05/+1.03e-04`). So the tilt enters **upstream of
the slope-flow step**, in the initial-guess field that `DIAGNO` builds from the
sounding, and is then modified by the adjustment/smoothing chain — not introduced by
`SLOPE`.

## 6. Artifacts

Committed under `native_cpp/modules/p6_calmet/reference/dgm_p6d_requests_2022/`:

| file | bytes | sha256 |
|---|---|---|
| `dgm_cell.bin` | 18,876 | `c82a63f62a2a09fc3fe704c751edfcfc737df758995e77d638026a05c69ce7ed` |
| `dgm_cell.json` | 111,541 | `c4ef3b4cd116b0ed8d48967b8050b199bd094f35ccbe40863585c9dcb2f9ff5f` |
| `dgm_fields.json` | 79,192 | `5f9368b92c87a7cfe87ec49aeb8eaa55c72cee86592c826401928b3da5829046` |
| `dgm_fields_hours.bin` | 5,460,768 | `972af841552f7a0eda6b02b221b6b2a808c61806054e634c617425d9ca9babdf` |
| `dgm-audit.json` | 10,292 | `54ac5c6dcfa70ef833b19fa1b45b66ae97f18640872027e79668ebd3fff4ba9f` |
| `dgm-instrumentation.json` | 6,650 | `f9018364e567845f5badca102053a07b898ec377dd81fb86667aa03806901a74` |

`dgm_cell.bin` and `dgm_fields_hours.bin` are force-added because the repository ignores
`*.bin`. Full dumps stay on the build host:
`/home/lhy/build/dgm2/out/case/run/met/dgm_state.bin`
`e6b8ab309f81ddc3015dc750272eeb2ee8289a2d34563b364884d9e443be6ece`,
`.../dgm_cell.bin` `c82a63f6…`, `.../dgm_fields.bin` `e32b4388…`.

Tool: `native_cpp/modules/p6_calmet/reference/original_internal_state_dump.py`
(`instrument` / `audit` / `metadata` / `celltable` / `extract-fields`). The round-2 run
reproduced every artifact hash bit for bit on a repeat.

## 7. Scope and limits

- Selected case and configuration only: 50×50×9, 100 m, one surface station, one
  `UP.DAT 2.1` station, 143 hourly steps, `IMIXH=1`, `IZICRLX=1`, `THRESHL=0`,
  `IAVEZI=1`, `IWFCOD=1`, `ISLOPE=1`, `IEXTRP=-4`, `IOBR=0`, `NOOBS=0`, `ITPROG=0`.
- Six hours are committed for request 2; the other 137 are on the build host with the
  offsets needed to slice them (see `dgm_fields.json`).
- The dump is internal state, not a `CALMET.DAT` field contract, and must not be written
  into one.
- **Not** covered: where inside the initial-guess construction the tilt originates
  (upstream of `DIAGNO`'s slope step, e.g. `DIAGI`/`VERTAV`/`PREPHDI`), and the effect
  of `ADJUST`/`SMOOTH` on `U/V` separately. The last is reachable by extending point 10
  or adding a point after `SMOOTH` (L6119) if P6D needs it.
- `OBRIEN` (`L6153`, skipped at `IOBR=0`) and `MINIM` (`L6180`, skipped) do not run in
  this case, so point-10 `U/V`/`W` are already the final fields.
