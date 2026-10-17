# P7: stateful CALPUFF COMP across hourly boundaries (2026-10-13)

## Scientific execution contract

143 input meteorological hours do **not** correspond to 143 independent
CALPUFF simulations. A fresh MET hour drives the same inventory of still-active
puffs; every puff must inherit its exact previous-hour state, plus the current
hour's newly released puffs if POINTS1 produces any. A pause/restart is valid
only when the *complete* state survives the boundary.

In the current restricted C++ point-puff path
`OriginalCompRiseMultiPuffHours` owns and atomically advances:

| Authority | Persistent source-of-truth fields |
| --- | --- |
| `OriginalPuffMotionLifecycle` | met-grid XY, Z, cumulative transport distance, total travel time |
| `OriginalVerticalLifecycle` | SIGYB/SIGZB, ICODE, QM/QU vectors by species, ZIOLD/ZIMAX, sigma/VMASS commit counts |
| `OriginalCompRisePointDriver` | release plume-rise parameters, preceding wind, completed substeps |
| `OriginalCompRiseMultiPuffHours` | active episode IDs / Fortran-style slot order, next monotone ID, committed hour count |

The original 2022 DGM traces are **read-only** and never initialize these
production stores. For each hour, an all-state copy is advanced; failed
meteorology/physics/source admission does not mutate the committed timeline.

### New functionality

`advance_hour_existing_mxsam99_adaptive(met, statics, controls, pg, urban)`
advances the inherited inventory for one **non-emitting hour** with no POINTS1
admissions and no new source mass. This supports the release-stopped state of a
finite-duration event without treating the next meteorological hour as a new
one-hour simulation. A zero-release hour is still a fully committed hour.

The emitting MXSAM99 methods continue to preserve old states and add new
episodes; `compact_original_inactive` applies vendor ROLLDN slot COPY order
to caller-identified old dead IDs and retains the physical state behind each
remaining stable episode ID. **Autonomous** code-99/off-domain/zero-mass
retirement remains an unimplemented scientific gate.

## Executed 143-hour synthetic continuity gate

The native mandatory
`cteas_p7_native_comp_mxsam99_unsplit` CTest performs:

1. At hour 1, admit **one** rising point puff, with two species carrying 7200
   and 10800 source-mass units (2 and 3 units/s × 3600 s).
2. At hours 2–143, add **no** new puff or mass. Alternate signed hourly wind,
   require old motion follows this new wind, and execute real
   MXSAM=99 adaptive substeps.
3. At *every* boundary, assert the old episode ID is unchanged; the first
   old-puff substep starts at the preceding hour's exact stored position and
   accumulated time; all new substeps advance motion/sigma/VMASS/lid clocks;
   QM+QU is conserved for each species in this **no-removal** subset.
4. Accept the vendor SIGADJ rule: non-Gaussian vertical codes can store
   SIGZB=0 after conversion. Do **not** impose a false globally monotonic
   sigma-z invariant.
5. Take an **in-memory complete-state checkpoint at hour 72**. Run the
   remaining 71 hours from both the uninterrupted authority and a copy of the
   saved checkpoint with identical meteorology. Assert exact equality of
   episode order, x/y/z, distance/age, SIGY/SIGZ, ICODE, ZIOLD/ZIMAX, QM/QU
   and counts (REAL4 equality, not tolerance-based matching).
6. Inject an invalid old-puff MET hour after hour 143 and require the entire
   attempted hour to roll back without corrupting old motion/mass/lid history.

**Observed:** 142 non-emitting hours, 6248 old-puff substeps, hour-72
checkpoint to hour-143 bitwise equality on all checked physical fields,
exactly one surviving episode, and one failed-hour rollback.

Hosted Ubuntu 22.04 CI: [run #38356286943](https://github.com/RRain001/CTEAS/actions/runs/38356286943)
(`point-hourly-cadence` SUCCESS, 4/4 cadence tests + mandatory
`cteas_p7_native_comp_mxsam99_unsplit` PASS, direct test output also PASS).

## Acceptance boundaries (do not misreport)

- **PASS:** native C++ in-memory persistent multi-hour state and non-emitting
  old-puff propagation for the synthetic selected noncalm PG/rise subset.
- **PASS:** exact in-memory 72h checkpoint → 143h re-entry equals uninterrupted
  143h on the same synthetic forcing.
- **NOT ACCEPTED:** serialized restart files and cross-process restart.
- **NOT ACCEPTED:** autonomously detected domain exits, code 99, all production
  SWAP/ROLLDN lifetime paths, calm/variable emission and fully coupled
  physical mass removal, chemical transformation and precipitation.
- **NOT ACCEPTED:** full real frozen Hefei 2022 143-hour autonomous
  PRFIN/COMP meteorological and physical trajectory equivalence to Fortran.
- **NOT ACCEPTED:** 2500-receptor hourly concentration accumulation and
  3655-record native WROUT1/`puff.con` equality.

The original-case FSTEP controller *alone* has previously passed the full
254687/254687-record oracle-wind-driven numerical audit; that result must not
be conflated with full physical trajectory equivalence.

P7 development remains on **PR #41 (Draft)**; do not merge on the strength
of this synthetic continuity gate, and do not change P6 as part of it.


## 2026-10-13 extension: opt-in autonomous loss/exit detection

Production scoped interfaces:
- `original_comp_before_step_exit(QM, QU)` mirrors original COMP
  `calpuff.for` L10450–10457: accumulate total species mass in source
  REAL*4 add order; if `QALL<=0`, retire before accessing meteorology.
- `original_comp_after_step_exit(xnew,ynew,bounds)` mirrors original
  COMP L11400–11413: **after** physical transport, a puff center is dead
  iff `xnew<XB || xnew>XE || ynew<YB || ynew>YE`; exact bounds are
  inclusive. Slug-endpoint testing is not implemented.
- `advance_hour_point_mxsam99_adaptive_bounded` and
  `advance_hour_existing_mxsam99_adaptive_bounded` enable these checks
  transactionally. Removed puffs' stable episode IDs, final positions,
  mixed-layer and above-layer per-species mass vectors are returned in
  `OriginalCompMxsamHour::retired`, permitting later source-faithful
  `MBALSUM(OUT/OBC)` accounting.
- Production physical stores must never accept original DGM coordinates
  or mass as input. Bounds are **explicit CALPUFF XB/XE/YB/YE**, not
  synthesized from a CALMET `NX/NY` header.
- The optional wrapper currently compacts its dead slots eagerly using
  source-ported `original_rolldn_slots`. The original `POINTS1` invokes
  `ROLLDN` only on `NPUFFS+NEWPUF > MXPUFF`; reproducing all code-99
  tombstone timing, capacity checks, new-puff SWAP ordering and mass balance
  output is an **OPEN** full original-case integration requirement.

**Verified** on [GitHub-hosted Actions #38358279681](https://github.com/RRain001/CTEAS/actions/runs/38358279681):
`cteas_p7_original_comp_exit_source_contract` PASS;
`cteas_p7_native_comp_mxsam99_unsplit` with bounded autonomous exit and
zero-mass/no-ghost-state/OUT-ledger gates PASS, and the previous stateful
143h synthetic continuity + checkpoint tests remain PASS.

Do **not** interpret this as full original Hefei 143h lifecycle or
`puff.con` numerical equivalence: the actual original 2022 XB/XE/YB/YE
derivation, conditional vendor `ROLLDN` timing, all emitted old-puff
histories, deposition/chemistry and receiver concentration accumulation
remain unaccepted.
