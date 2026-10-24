# S4-R1c9z/aa — NOAA fourth-hour P6F parity and G14 transaction

## Scope / provenance (2026-10-24)
- Issue #40 OPEN, Issue #36 OPEN. Test-only selected C++ CALMET P6 path, **NOT** generic production validation.
- Genuine 2022-06-01 02–08 UTC NOAA, 82×85×9, 2SS/1US, 63 WATER cells. The fourth hour is 04:00–05:00 UTC.
- Read-only original Fortran CALMET 6.5.0 source SHA256: 835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23. Original met.x SHA256: 1c2d1227d1ba7e8135bd81488be48d3d1e54f041839f20cd466bcd0176f41322. Private original six-hour MET.DAT SHA256: a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14. This task uses the previously captured pristine original result; **no fresh original Fortran run**.
- Frozen input SHA256: met.inp c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744; GEO 5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a; observed final SURF 6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655; UP a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00. Raw SURF is not substituted.

## Fourth-hour source-native P6F stage16 (S4-R1c9z)
- G26B/G64 enable only the explicit fourth-hour hour_index=3 trial. Requires valid preceding native G22/G23/G24/COMP, committed native third-hour memory, source station cardinalities, 63 WATER cells and same G14 live frame. Existing production guards remain unchanged.
- The dedicated command flag --fourth-hour-g26b-p6f45-trial-only emits an **uncommitted** 45-field CALMET 2.1 candidate; the original MET is **never** an input to native.
- Ubuntu Docker DEV_ONLY GCC12 -Werror build: dev-20261024T022455-88e09c9b, binary SHA256 829e82d60da139e0949fa5cce2879f99261680d6946b2814506f091c330c75d2; exit 0. Native candidate SHA256 750a22cd06aceaaac21dbf555d95bf39bfc6195115b0dc897333fa14b1846ab7.
- An independent Python comparator (scripts/s4/s4r1c9z_compare_hour4_p6f45.py) checks fixed artifact SHA, original six-hour and native one-hour header, station counts, fourth-hour clock, all 45 labels, record shape, finite values, exact INTEGER4 IPGT/IRH and **unchanged per-field frozen REAL4 tolerances**.
- **PASS_SCOPED_HOUR4_ORIGINAL_NATIVE_P6F45_PRECOMMIT**: **313,650 / 313,650** values within frozen limits, **0 exceedances**, **240,362 bitwise equal**. Private report at /home/lhy/dev/CTEAS-next/local-science/s4-r1c9z-hour4-native-p6f45-20261024/original-native-hour4-p6f45.json; report SHA256 fdad8d1f9df3c6ab42f419f4c22a99cfa4e3fcc427ef3d7a8e703d6bc42e15e6.

## Fourth-hour atomic rollback and positive retry (S4-R1c9aa)
- Explicit flag --fourth-hour-g14-commit-trial-only, separate fourth-hour actor constructed anew for each attempt. Following all 17 source-native stages the first attempt force-throws **after candidate validation, before clock preflight**. Both previously committed third-hour ZI/ZICONV/DPTT and AA/BB/CGAMMA station clocks remain unchanged.
- A new actor recomputes the same 17 stages on the actual scheduler frame and verifies **byte-exact identity** with the independent unpublished P6F candidate. After station clock preflight G14 commits fourth-hour memory and publishes upper/gamma clocks. The fifth-hour scheduler preview inherits identical prior memory and contiguous station time.
- Docker DEV_ONLY GCC12 -Werror build: dev-20261024T023014-dfb9a330 exit 0; tested binary SHA256 3227ead813e6db6440edc922f0bb4c969d4c1f5c339fec466440c46c607f3881.
- Full local fourth-hour transaction exit 0, private /home/lhy/dev/CTEAS-next/local-science/s4-r1c9aa-hour4-g14-transaction-20261024/. Its independently regenerated P6F candidate has SHA256 **750a22cd06aceaaac21dbf555d95bf39bfc6195115b0dc897333fa14b1846ab7**, matching the original fourth-hour native precommit artifact.
- Docker DEV_ONLY selected 22/22 Python unit tests passed in dev-20261024T023123-c83f01d9, including six additional synthetic structure and negative comparator tests. Synthetic tests **are not** scientific original model validation.

## Limits and next milestones
- **Exact-SHA Docker full, external independent science review, fifth/sixth-hour native stages/45-field parity/transaction, generic P6 program, P7 and wet deposition: NOT_RUN / NOT_ACCEPTED.** No PR auto-merge or science-validated/merge-verified label warranted.
- Continue from real committed fourth-hour state to fifth-hour PREPDI/WIND1/FRADJ, then G22, G23/G24, COMP/P6F and atomic G14; repeat sixth hour. Freeze one exact SHA after this functional batch for Docker full and independent scientific review.
