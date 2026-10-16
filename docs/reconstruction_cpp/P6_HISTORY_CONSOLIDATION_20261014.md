# P6 historical PR consolidation / source audit (2026-10-14)

## Single accepted physics source
PR #53 accepted HEAD `8d6642272d0abb77153880591e150f93e14d4479` is the only scientific authority for frozen Hefei 2022 1SS+1US / 143h / 45 fields. Multi-station PR #63 directly descends from this HEAD. P6D/P6E/P6F native physics and hourly scheduler are unchanged by this transfer.

## Preserved historical components
- PR #40: **strict WGS-84 UTM P4/P5 selection**, frozen provenance auditing and P4 UP/P5 SS consistency checks, now isolated P4/P5/test additions on #63. Original single-station reference remains immutable.
- PR #42: independent REAL*4 P6D reference routines are already in #53, and historical 143h shard scripts retained in the closed source-branch history. These diagnostics are NOT a second production wind authority.
- PR #51: commit ancestry fully contained by #53 (GitHub compare source-branch to accepted 143h HEAD reports `ahead`, `behind=0`).
- PRs #54–#62: G5 GUI, P4/P5 shared UTM and G6–G13 selected multi-station kernels, tests and original vendor source comparisons transferred to #63. The old divergent physics-only implementations remain historical; no existing accepted P6D/E/F physical source overwritten.
- PR #41: unrelated P7/CALPUFF work, left open.

## Explicit tests and non-claims
CI on #63 must independently run: frozen 143h 45-field original CALMET parity, frozen native P6F output tests; 10km 2SS+2US 8784h selected-source kernels Debug/Release; G13 2SS 10km literal original Fortran SURFVAR; GUI isolation/offscreen smoke; P4/P5 strict UTM selection tests and original frozen-input hash audit.

Passing those selected gates does NOT imply fully coupled multi-station DIAGNO↔COMP full 143h/8784h source parity, original radiative/CGAMMA multi-station forcing, or rainfall/wet deposition. The experimental G5 GUI remains fail-closed for generic P6/P7; do not enable the old GUI as a fallback.

## Closing policy
Close only superseded historic PRs after this migration is committed and relevant CI passes. Close, **do not merge** old branches, and leave branch histories/comments accessible via PR URLs. PR #53 is not auto-merged to main by closing old PRs; #63 remains Draft until generic P6 validation.
