# Issue #56 P5 — genuine NOAA D3 scoped acceptance and D4 source handoff (2026-10-18)

**Evidence:** [GitHub Actions #39120459913](https://github.com/RRain001/CTEAS-next/actions/runs/39120459913), event `workflow_dispatch`, parameter `scenario=all`, result **SUCCESS** on `main@19992f70`. Downloaded artifact `issue56-real-noaa-newsite-metadata-39120459913` (artifact ID `12134460172`; retained by Actions for 14 days). Original pinned vendor source `RRain001/CTEAS@dfad99a7`; independent original SMERGE executable SHA256 `c80c2bab3ce2d2c1781c04a58a4cd42ebe6bef10d0a5b725b50d7f9e5460beb8`.

## Actual authentic-source science gate

The common new-site UTM50N origin is `XREFKM=426.590, YREFKM=3464.125` (strict three decimal km). Two genuinely **in-domain** NOAA surface stations are `58314099999` (Huoshan, IFSTN 583140) and `58321099999` (Luogang/Xinqiao, IFSTN 583210). This is not the frozen Hefei 5 km grid.

| Original NOAA UTC annual coverage | Huoshan full / Lite | Luogang full / Lite | Real primary |
| --- | ---: | ---: | --- |
| 2022 (8,760 calendar hours) | 2,828 / 2,828 | 8,692 / 8,692 | 58321099999 |
| 2023 (8,760 calendar hours) | 2,729 / 2,729 | 8,642 / 8,642 | 58321099999 |

The Huoshan secondary remains sparse; the Luogang primary uses the unchanged chosen fill/calm/wind policy. **No natural primary switch was observed** in these two years. All source origin/selected effective positions, yearly manifests and source SHA have been captured by the staged producer; no synthetic hourly weather is in this D3 evidence.

Original SMERGE v5.7.0 and the existing native C++ SMERGE were each executed on **exactly the same GENERIC inputs and `smerge.inp`** in separate scratch directories. The compared output is the raw, pre-cloud-fallback `SURF.DAT`.

| Actual scenario | UTC duration (SMERGE hour-ending) | Raw original / native bytes | Both raw SHA256 | Independent P6 source reader |
| --- | ---: | ---: | --- | --- |
| 2022-06-01 00→06-02 00 | 24h | 3,913 / 3,913 | `88b1f54a099b0de124c15afc1ab4333225d3075f0f3347cb89047d7819640c27` | 24h, 2 SS, 32 populated, 16 missing, 32 valid wind station-hours |
| 2023-06-01 00→06-02 00 | 24h | 3,913 / 3,913 | `773e1bda462bd611cb09ffa7c33edd75aba2a558a9832e78246d79398a967068` | 24h, 2 SS, 32 populated, 16 missing, 32 valid wind station-hours |
| 2022-12-31 00→2023-01-02 00 | 48h | 7,561 / 7,561 | `6ab171d52d8c2136af9ebe828d92b6c0ae8bef168c219054f0a9e26a7a864aa6` | 48h, 2 SS, 64 populated, 32 missing, 64 valid wind station-hours |

**D3 scientific conclusion:** `PASS_SCOPED_ORIGINAL_SMERGE_V57_NATIVE_SURF_BYTE_PARITY` for the three specified windows and only `JDAT=8, IOFORM=2, IOPACK=0, LPREV=F, LPCALC=F, UTC`. This conclusion **does not establish** all-sites/all-years/other-control parity, nor naturally changing annual primary, arbitrary station cardinality, wet precipitation processing, or P6/P7 field equivalence.

## Important raw versus published output distinction

Published `met/surface/final/surf.dat` is *not* the byte-identical raw original SMERGE output; the approved legacy cloud-missing fallback can replace `ICC=9999` with zero. Publish SHA:

- 2022: `b9c6df9a70a5b611b3dc1b5cffb88ab55af79c73515d33869b0d0d8ad4fdb5e4`
- 2023: `24968e32343c12689b65d64a29caddbe12013d1e881f5dd15002b6d698112680`
- Cross-year: `e9af0ebfcdf27bf954574e3f2014b589a09bc6d41a72b314217cf27f83ad38e3`

Neither identical raw bytes nor a source-reader PASS can on its own validate the published cloud-fill physics.

## D4 handoff to #42

`native_cpp/modules/p5_smerge/data_prep/p5_handoff.py` defines the versioned `CTEAS_NEXT_P5_TO_ISSUE42_D4_SOURCE_HANDOFF_V1` source contract, emitted by the real-noaa scoped runner. It independently checks shared #42 B-0 immutable case/grid/time SHA, exact original NOAA source SHA, yearly source/effective coordinates, annual coverage and roles, stable IFSTN, station CSV order, original vs published SURF SHA, actual SMERGE hour-ending cardinality and independent source-reader missing/valid counts.

**Status separation:** `P5_D4_SOURCE_HANDOFF=PASS_SCOPED_SOURCE_ONLY` is an independently verifiable *metadata* contract; `P5_TO_G19=NOT_RUN`, `P6_NUMERICAL=NOT_RUN`, `P7=NOT_RUN`. A true #42 G19 verdict still requires **the same new site's** physically generated P1/P2/P3 `GEO.DAT`, P4 `UP.DAT`, P5 published `SURF.DAT`, dynamic `met.inp`, all source SHA, actual joint parser execution, time-bracket checks and station coordinate/role consistency. D4 currently exports aggregate P6-reader coverage, **not per-hour field-level missingness**; #42 must audit that at G19.

No NOAA original archives or vendor Fortran are redistributed through this repository or the Actions metadata artifact.
