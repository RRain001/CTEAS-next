# Issue #84 — authentic NOAA science expansion: D0 source reconnaissance (2026-10-19)

Issue: https://github.com/RRain001/CTEAS-next/issues/84

**Current disposition: OPEN / NO NEW SCIENTIFIC PASS.** Preserve the #56 scoped
original-SMERGE versus native RAW SURF byte-parity verdict from
[manual Run #39127603584](https://github.com/RRain001/CTEAS-next/actions/runs/39127603584).
The 2022 and 2023 genuine two-station source had the **same** primary
(58321099999); the synthetic source-selection tests are not observed primary
switching, observed 0/1/3 full production, or observed leap-day parity.

## D0: independently screen a new real station/year candidate

[Issue #119](https://github.com/RRain001/CTEAS-next/issues/119) freezes a
**Wolsong** P2-B 20 km × 20 km WGS84/UTM52N grid:
`XREFKM=533.215`, `YREFKM=3942.629`, `DGRIDKM=0.100`,
`NX=200`, `NY=200`. Its representative point
35.716670 N / 129.477780 E is **not** a surveyed stack coordinate.
Using this frozen *geographic candidate* for NOAA screening does not
implicitly approve a #84 P5 production result.

New read-only (except temporary scratch) source-screen entrypoint:
`scripts/s2g/issue84_noaa_source_screen.py`. A
**manual** [issue84-noaa-source-screen.yml](../../.github/workflows/issue84-noaa-source-screen.yml)
retrieves authentic NOAA **full Global Hourly ISD CSV** and independent
**ISD-Lite gzip** for the 2023/2024 candidate years. The script:

- Uses the repository's original station history and existing P5
  `station_in_utm_grid` / `covers_interval` logic. Screens **all**
  catalogued in-grid stations and six closest out-of-grid catalogued
  candidates (configurable, maximum 12).
- Counts **original, unfilled, unique UTC hours** for each data product
  separately. It records actual 2024-02-29 raw hourly presence and
  calendar denominator **8784** (vs. **8760** for 2023).
- Records per-file **SHA-256**, station ID, original coordinates,
  official direct source URLs, individual source failures, and
  strict **>90% on both products** as a *virtual-station eligibility
  screening metric only*.
- Writes only metadata and pipeline commit SHA to short-retention
  Actions artifacts. Original NOAA bytes stay in temporary storage;
  no vendor source is published.
- Emits only `SOURCE_SCREEN_COMPLETE_METADATA_ONLY`,
  `SOURCE_SCREEN_PARTIAL`, or `SOURCE_SCREEN_NO_CANDIDATES`.
  An absence of observations cannot become PASS. Candidate
  year-to-year top-rank differences are **hypotheses**, not proof of
  original-selector primary switching.

There is **no** software-modeled meteorological data in this D0 step,
and neither vendor nor C++ SMERGE is executed. GitHub PR events only
run a small offline syntax/import contract check. NOAA downloads are
**manual workflow_dispatch only**; run from merged `main` to retain
provenance. If network fetches fail, preserve the partial report and
record BLOCKED, not a synthetic replacement.

## Scientific follow-up after real-source screening

| Gate | Required evidence | Current |
| --- | --- | --- |
| D1 natural primary switch | Same *actual* site, >=2 calendar years, unchanged production annual selector, source SHA and raw per-year Lite/full coverage, different **observed** selected primary SID, stable IFSTN; independent Fortran/C++ same-deck byte compare across switch | NOT_RUN |
| D2 zero in-domain | Authorized grid with authentic zero in-domain station count from full station catalog; nearest virtual requires independent original full **and** Lite raw coverage strictly >90%; complete actual GENERIC/native/Fortran execution | NOT_RUN |
| D3 one in-domain | Another admitted real grid with exactly one catalogued observed in-domain station; full producer and original SMERGE byte parity | NOT_RUN |
| D4 >=3 in-domain | Another admitted real grid with at least three original in-domain stations; full producer and original SMERGE byte parity, consistent global alias/order across years | NOT_RUN |
| D5 2024 leap year | Actual 2024 full ISD + ISD-Lite SHA and 8784 annual **raw denominator**, recorded leap-day observation hours, actual 2024 Feb 29 `(BEGIN,END]` SURF window and original/native same-deck equality | NOT_RUN |
| D6 publication policy | Distinguish raw SURF byte parity from published SURF with **ICC=9999→0** cloud policy; independently count modified station-hours and source precipitation codes; missing precipitation does **not** prove wet deposition | PARTIAL / SITE-SPECIFIC NOT_RUN |
| D7 options | Only JDAT8 / IOFORM2 / IOPACK0 / LPREV-F / LPCALC-F / UTC can inherit the #56 limited science branch; anything else independently source-audited, executed and added to the option matrix | NOT_RUN |

**Execution boundary:** once screening identifies defensible sites/years,
implement a separately reviewed manual **real P5 producer plus two-binary
SMERGE parity** workflow reusing `p5_case_producer.produce` and
`issue56_real_noaa_p5_case.compare_original_smerge`. Freeze actual
`grid.cmn`, `case.yaml`, raw source identity/SHA, original
`SMERGE.INP` SHA, all identical GENERIC input hashes, original/vendor
binary SHA, native binary SHA, RAW `SURF.DAT` hashes and first difference
(if any). Do not widen the #56 algorithm. Full P1–P5/G19 remains #42;
wet-deposition data/format is separate.

**Closure condition:** #84 may close only when the required authentic
scenarios show explicit successful independently reproduced evidence,
or when the owner formally narrows the issue's acceptance scope.
Source reconnaissance **does not close #84**.
