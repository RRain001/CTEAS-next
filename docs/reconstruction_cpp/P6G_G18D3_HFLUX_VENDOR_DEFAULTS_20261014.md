# G18D3: original CALMET HFLUX defaults replace the former synthetic heat coefficients

2026-10-14; PR #63 Draft, still stacked on frozen/accepted P6 baseline PR #53.

## Confirmed numerical discrepancy

Previous G17C1 selected 2SS source-hour tests provided:
`HA1=990, HA2=-30, HB1=-0.75, HB2=3.4, HC1=0, HC2=0, HC3P1=1`.
The first four constants match the original CALMET 6.5.0 compiled
BLOCK DATA, but **the latter three do not**. The native implementation
of the immutable PR #53 HEATFX physics was correct against the passed
test fixture; the *source input coefficients* were wrong.

Unmodified `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`
contains the **literal** BLOCK DATA HFLUX defaults:

```fortran
      data ha1/990./,ha2/-30./,hb1/-0.75/, hb2/3.4/
      data hc1/5.31e-13/,hc2/60./,hc3/0.12/
```

And original CALMET `SETCOM` derives `HC3P1=HC3+1.0` in REAL*4.
The correct source vector is thus
`(990, -30, -0.75, 3.4, 5.31e-13, 60, REAL4(0.12)+REAL4(1.0))`.

The pinned source `met.inp` has no explicit `HA1/HA2/HB1/HB2/HC1/HC2/HC3`
override, so these actual vendor defaults apply. Original READCF does
allow overrides for other inputs; the selected implementation **refuses**
a deck containing any such explicit override until that distinct
source-verified path has been implemented.

## Implementation, reuse and strict test

- New `p6g_g18d3_heat_source_defaults.hpp` produces original
  BLOCK DATA HFLUX coefficients and all-land zero water-only unused
  scratch without claiming any new physics or production success.
- The G17C original second `SURFVAR → SOLAR/HEATFX` 2SS source
  selected test now obtains its input from this source-specific
  helper; its direct frozen #53 HEATFX verification uses exactly the
  same source defaults and original frozen formula. The corrected QH
  flows through source selected G17C2 ELUSTR, G18A MIXHT,
  G18C1 AVEMIX, G18C2 WSTARR, G18C3 TEMP3D, and
  G18C4/C5/C6 candidate P6F output; downstream regression must
  pass with this physically corrected energy budget.
- Independent source evidence: new
  `reference/compare_original_g18d3_hflux_defaults.py` extracts
  both **literal vendor Fortran DATA statements** and literal
  `HC3P1=HC3+1.0` statement, compiles them with gfortran,
  and compares all seven native C++ coefficient REAL*4 bit
  patterns at **zero tolerance**. Registered as
  `p6g_g18d3_literal_vendor_hflux_block_data_real4_parity`
  in both GitHub-hosted Ubuntu Debug/Release `^p6g_` suites.
- A missing/overriding HFLUX key, invalid GEO/water-only branch and
  unsupported production promotion fail closed.

## Validation boundary and next blockers

Successful coefficient parity establishes the original source *HFLUX
constants*, **not** complete normal CALMET 2SS/2US meteorology or
all 45 original output records. Additional original G17C radiative
source state and full G18A multi-station CGAMMA/MIXHT inputs must still
be admitted to the production G14 17-stage callbacks. G18D1
precommit and G18D2 per-US clock state are selected-stage guards;
full durable output publication and strict multi-site 1h/6h/143h/year
original 45-field tests remain explicit blockers. Keep PR #63 Draft and
unchanged accepted PR #53 sources.

Check GitHub Actions against the **exact source SHA** before recording
PASS for G18D3; pre-G18D3 21/21 tests are not evidence for this correction.
