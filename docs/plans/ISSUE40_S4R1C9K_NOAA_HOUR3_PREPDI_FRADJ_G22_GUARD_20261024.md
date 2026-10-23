# S4-R1c9k — authentic NOAA third-hour source preflight and G22 safety gate

## Background

Draft PR #298 commits the second hour's G14 physical ZI/ZICONV/DPTT state
and AA/BB/CGAMMA source clocks only under explicit test opt-in, and confirms
the third-hour preview inherits the second-hour history. It does not authorize
third-hour COMP/P6F or general P6 production.

The first R1c9k exploratory attempt to execute all twelve third-hour G26A
DIAGNO stages failed closed at stage3 G22 with the actual message
"G22 unvalidated mixed-WATER hour/station/GEO source path". Inspection
confirmed G22 independently restricts its selected WATER thermal source
to hours 0 and 1. This is an intentional scientific admission barrier,
not a compiler error or a missing source file.

## Bounded implementation

Add a third opt-in G65 CLI mode --third-hour-g26a-preflight-only.
It first performs the existing second-hour negative rollback and scoped
positive commit, then runs only real third-hour PREPDI, WIND1 and FRADJ
(stages 0,1,2) on the scheduler-owned preview and the exact committed
second-hour hidden state. The native stage return values, stage count,
input UTC and source cardinalities, previous ZI/ZICONV/DPTT, next memory,
and published station clocks are verified. An attempted third-hour G22
stage3 must reject with its existing source-scope guard; G14 remains
at exactly two committed hours. No G22 source physics is modified and
no third-hour output or station clock is published.

## Actual Ubuntu evidence

- Exact parent PR #298: 0e2a5ef19d686b49224838adee4509e83fb9feaa.
- Ubuntu 22.04, GCC12 Release executable SHA256:
  c078288c97ed8e7133dbb8f7aeef2cab5e0020bf0d4f840c5ba5ea98f859e7c9.
- Authentic 2022-06-01 NOAA 82x85x9, 2SS/1US, 63 WATER,
  same four source SHA as the R1c9j report.
- Actual CLI run exited 0 with:
  S4R1C9K_HOUR3_G26A_STAGE0_2=PASS_PRECOMMIT_ONLY
  S4R1C9K_HOUR3_G22_GUARD=PASS_REJECTED.
- Private logs:
  /home/lhy/dev/CTEAS-next/local-science/s4-r1c9k-hour3-diagno-20261024/
  final-stage02.stdout.log and final-stage02.stderr.log.
- Exact-new-SHA Docker full: NOT_RUN until a commit is frozen and
  previous #298 Docker build/full finishes.
- Independent original Fortran third-hour numerical comparison: NOT_RUN.
- Third-hour G22 HEATFX/AIRDEN/ELUSTR/SLOPE, later G26A and G26B:
  NOT_ACCEPTED. G63/G64 hour_index>1 guards remain in place.
- Third-to-sixth-hour G14/P6 production and S4 P7: NOT_ACCEPTED.

## Next physics gate

Before enabling third-hour G22, instrument the unchanged original CALMET
hour-three source with local read-only Fortran tracing and compare the
third-hour original SURFVAR before/after FRADJ, HEATFX/AIRDEN, ELUSTR,
and SLOPE against native source computations on exactly the same
hour-two committed ZI/ZICONV/DPTT and station clocks. Do not relax
hour_index limits merely because stages0..2 passed. The same principle
applies separately to G63 MIXHT and G64 P6F.
