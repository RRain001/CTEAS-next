# S4-R1c9j — genuine NOAA second-hour positive G14 transaction

## Scope and change

This builds on Draft PR #297 (ddb4c0b8e8b155cdd5cc7b680b5f099f187eb283).
The default G65 mode still executes the second-hour **negative** transaction
and must leave only hour one committed. An explicit final
--positive-hour2-g14-transaction option first proves the negative rollback,
then creates a fresh second-hour actor and executes all 17 G14 stages a second
time. The successful precommit checks the entire native P6F serialized
candidate and the ZI/ZICONV/DPTT next state against the independently staged
native candidate, and checks AA/BB/CGAMMA publication preflight before the
scheduler's atomic physical memory commit. The noexcept publication callback
runs only after the scheduler reaches two committed hours. A third-hour preview
must inherit the newly committed memory and clocks.

This is an **opt-in, research-only transaction test**, not the generic P6
production route, not a production MET.DAT writer, and not independent
scientific approval. It does not change frozen tolerances, original Fortran
sources, source P1–P5 data, G14 physics or P7.

## Local actual-case evidence

- Environment: Ubuntu 22.04 x86-64, GCC/G++ 12.3.0, CMake Release.
- Selected NOAA input: 2022-06-01 01:00–07:00 UTC, 82x85x9, two real
  surface stations, one real upper-air station, 63 WATER cells.
- G14 executable SHA256:
  354d88f051275153114ced718ad93d2000bcaa3bce4d6a2c2321e0fefa1557e2
- met.inp SHA256:
  c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744
- GEO.DAT SHA256:
  5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a
- SURF.DAT SHA256:
  6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655
- UP.DAT SHA256:
  a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00
- Unmodified original Fortran six-hour MET.DAT SHA256:
  a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14.
  Original vendor CALMET 6.5.0 is local and read-only; original was previously
  independently run on this same case. No original MET is fed into C++.
- Default rollback-only execution: **PASS**, exit 0.
- Explicit positive hour-two execution: **PASS_SCOPED_TRANSACTION_ONLY**,
  exit 0. Physical G14 committed hours = 2; AA/BB/CGAMMA published hour two;
  hour-three preview inherited hour-two ZI/ZICONV/DPTT bitwise.
- Invalid opt-in flag: exit 2, **PASS_FAIL_CLOSED**.
- Fresh forensic native hour-two candidate independently compared with
  original Fortran hour-two 45 fields x 6970 cells: **313650/313650 within
  frozen tolerance**, 0 exceedances, PASS_SCOPED_ORIGINAL_NATIVE_HOUR2_FULL45.
  Native candidate SHA256:
  d0612c0fee5d25baf1c640f730e6932733ffc82d6878ba56bb7ef6b157464d82.
- Local private evidence:
  /home/lhy/dev/CTEAS-next/local-science/s4-r1c9j-positive-20261024/
  (positive-mode.stdout.log, negative-mode.stdout.log,
  original-native-hour2-45field.json, and input hashes). Raw inputs and
  original MET remain outside the public Git repository.

## Acceptance boundary

- Exact-commit Ubuntu Docker full: **NOT_RUN** until the new commit is
  frozen, built and tested; older PR #297 full is not reusable.
- Independent science reviewer: **NOT_RUN**. The original Fortran same-input
  comparison is an important scoped numerical gate, but is not an
  independent scientific signoff.
- Third-hour actual 17-stage G14 run and hours 3–6 original parity: **NOT_RUN**.
  Only the hour-three memory/clock preview is validated here.
- General P6, P7 and S4 full scientific acceptance: **NOT_ACCEPTED**.
  This Draft PR must remain unmerged until all required checks and science
  gates are satisfied.
