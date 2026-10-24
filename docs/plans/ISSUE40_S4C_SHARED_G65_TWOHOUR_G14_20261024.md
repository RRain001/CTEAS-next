# Issue #40 — S4-C unified native G14 genuine NOAA WATER two-hour continuation

Date: 2026-10-24, Draft PR #308. Only scoped fixed-source original
CALMET reference parity; **neither** generic production P6 nor P7 admitted.

## Code provenance and the single executable

The unchanged original `G65RealNoaaSecondHourActor` 17-stage G26A/G26B/
G64 physical code was extracted from `p6g_g65_noaa_firsthour_atomic_commit.hpp`
into **the same** `p6g_g65_shared_noaa_firsthour_actor.hpp` header already
shared by G65 and S4B2 for hour one. Both original G65 research executor and
`cteas_p6g_s4b2_unified_selected` now instantiate the same native first/
second hour actors, without duplicating scientific equations or original
Fortran readbacks into solver input.

S4B2 adds `--selected-experimental --water-secondhour-g14-trial-only`
requiring *genuine six-hour original-format input*, exactly `--hours 6
--probe-prefix-hours 2`, a distinct fresh `--out` and known provenance
82×85×9 / 2SS / 1US / 63 WATER. Production mode, mixing with WATER source
preflight, first-hour-only switch, `--g26-normal-entry-trial`, source-state
trace, any other prefix/hours and reused output paths are refused.

The same G14 scheduler advances with fresh actors from original source UTC
at hour zero to committed hour one to full hour two, enforcing byte-for-byte
prior committed **ZI/ZICONV/DPTT** at the next preview, independent live
AA/BB/CGAMMA clocks and 45-field G64 P6F precommit *before* atomic G14
commit. Source G41/G43 computes genuine COMP five nonwind missing-input
reference without modifying source P5 wind/precip/upper or injecting original
CALMET.DAT into native stages. Hour2 actual physical input remains the same
G65 accepted original raw source, with separate G43 source integrity check.

## Independent original-vs-native validation

Original Fortran six-hour `MET.DAT` is **read-only**, pinned SHA256
`a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14`.
It was created by prior native Ubuntu original CALMET source execution;
**original Fortran was not rerun during this batch**. Input SHA256 values
are already documented in
`ISSUE40_S4C_WATER_SOURCE_PREFLIGHT_20261024.md` and unchanged.

The newly compiled unified native S4B2 emitted two-hour `MET.DAT` SHA256
`30eb55977283f7b9c09a4002e9781d32e1d58af30ac408e15959d8c928d9f0f3`.
Separate strict offline `scripts/s4/s4c_compare_noaa_unified_twohour.py`
checks original/header/source hours and output source identity, Fortran record
integrity, exactly 90 P6F fields with original 01:00–03:00 UTC chronology,
45 labels/order, 82×85×9 / 2SS/1US, floats finite and fixed existing
field-specific frozen tolerances, integer fields exact. Only audit reads the
original output file after native G14 has completed.

| Test | NOAA hour 1 | NOAA hour 2 | Total |
| --- | ---: | ---: | ---: |
| Original vs C++ grid field values | 313,650 | 313,650 | **627,300** |
| Bitwise-equal 4-byte words | 298,578 | 239,527 | **538,105** |
| Beyond fixed REAL4 field tolerance / nonmatching INTEGER4 | **0** | **0** | **0** |

Status: `PASS_SCOPED_S4C_SHARED_TWOHOUR_FORTRAN_90`.
This result does not claim S4 production physics, 3–6h equivalence or
independent *human* review. Pre-existing native first-hour candidate SHA
`d8e6065e2d26bc517f72619bd1822c6832d04ec7c42c4b93d12d32910a3c984c`
is reproduced byte-identically by the **same new binary**, verifying no
regression in the first-hour actor.

The private original/candidate output and JSON live on Ubuntu under
`/home/lhy/dev/reports/cteas-s4c-unified-20261024/`; never put private
original trace, proprietary input or data in public GitHub.

## Software, boundary, and following steps

- GCC12 compiled S4B2 and original G65 target against the extracted shared
  first/second-hour actor; targeted S4B2 CTest **4/4 PASS** including new
  `p6g_s4c_water_shared_secondhour_no_implicit_production` negative CLI
  checks. Python independent comparator negative/tamper tests 3/3 PASS;
  first-hour comparer safety tests 2/2 PASS.
- `PRODUCTION_ADMISSION=NOT_ACCEPTED` is permanent for these research flags;
  `scientific-admission` and non-bot same-SHA reviewer remain NOT_ACCEPTED/
  NOT_RUN even when native full software PASS and this scoped original
  numerical parity is PASS.
- For hour3, G65's G66 prior-WATER P6F derived from committed hour2 **native**
  P6F and the full hour3 source-only G43 MISSFC need a reusable caller-facing
  stage adaptor: do not copy hour3–6 per-hour flags wholesale or hardcode
  original output arrays. Then verify hour3 native 17-stage P6F vs Fortran,
  G14 history and UTC, followed by hours4–6 and C1/C2 143h plus a second
  independent site/station geometry. No P7 promotion before these gates.
- Formal full Docker validation remains scheduled *after* S5.
