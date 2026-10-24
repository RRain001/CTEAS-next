# S4-R1c9y — genuine NOAA fourth-hour G26B COMP stage12–15

## Scope and provenance

- Research-only fourth hour (UTC end 05) of the 2022-06-01 02–08 UTC genuine NOAA six-hour 82×85×9, 2SS/1US, 63-WATER-cell case. Follow-up to S4-R1c9w/x after S4-R1c9v third-hour positive G14 commit. Generic P6/P7 paths remain rejected.
- Read-only original CALMET 6.5.0 at `/home/lhy/CTEAS/engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`, source SHA256 `835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23`. Pristine original six-hour COMP stage trace SHA256 `4851f7be2d19df7a6e5e2cf5d73653c282cfea579b9c0b2444365a842d27a02e`, generated previously by a separate write-only Fortran trace instrument that retains the identical original MET file. This development run does not claim to have independently rerun original Fortran.
- Frozen original/native input hashes (met.inp/GEO/SURF/UP respectively): `c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744`, `5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a`, `6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655`, `a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00`. Use the observed `met/surface/final/surf.dat` input, not the different raw `run/smerge/surf.dat`; the latter has missing SS1 cloud entries and fails the G17C source guard.
- Native GCC12 Release -Werror binary SHA256 `d2dfd32ddd35f983de4f445979417d29752a816f199118ae2264a564ecd2dbde`; native 4-stage binary trace SHA256 `6851712d61ae90c6666c54101ba7c4f17c3600f1d00aceec41af9cb7535cbd2f`.
- Private run and independent report: `/home/lhy/dev/CTEAS-next/local-science/s4-r1c9x-hour4-native-comp15-retry3-20261024/`, `original-native-hour4-comp15.json`. Original reference resides only in local-science, never copied into the native computation or Git.

## Physical handoff and scientific comparison

- Extend only the explicitly opted-in fourth-hour G52 source WATER/LAND partition, G53 source-local WATER neutral state and G63 MIXHT; require `hour_index==3`, matching current-hour actual source clock, frozen grid/63 WATER cells and original station cardinality. Keep production hour_index>1 reject guards. G26A G22/G23/G24 completes before the *same* live fourth-hour G26B actor runs stage12 MIXHT, stage13 AVEMIX, stage14 WSTARR and stage15 TEMP3D. G14 committed third-hour ZI/ZICONV/DPTT and station clocks remain unchanged throughout.
- Native trace uses fixed stage headers (hour-end 05 UTC, stage number, 82,85,9) and full field arrays. The independent Python comparator reads both binary files separately, validates each SHA, time, grid, ordering, shape, finite values and applies the **unchanged** frozen third-hour field tolerances. Neither original reference values nor fields enter C++.
- **PASS_SCOPED_HOUR4_G26B_COMP_STAGE12_15**: **132,430 / 132,430 REAL4 within frozen tolerances; zero exceedances; 108,484 bitwise identical**. The result covers seven stage12 fields, two stage13 fields, one stage14 field and nine vertical levels of TEMP3D at stage15.
- Ubuntu Docker **DEV_ONLY** GCC12 Release -Werror compile passed (`dev-20261024T020845-ba2fb645`), and selected Python comparator regressions passed. The previous batch `dev-20261024T020401-c524aa82` completed **30/30 selected tests**. This is not exact-SHA Docker full or independent scientific admission.
- Failed read-only trials remain archived: initial incorrect nonexistent SURF/UP path; raw SURF missing original observed cloud; original G52 partition limited to hour3 before explicit fourth-hour opt-in. No failed run is rebranded as success.

## Limitations and next gate

- Fourth-hour G64/P6F stage16, original 45-field output, fourth-hour G14 rollback/positive commit and clocks: **NOT_RUN**.
- Real hours5–6, generic multi-case P6, CALPUFF/P7, wet deposition and independent science review: **NOT_RUN / NOT_ACCEPTED**.
- Do **not** merge Draft PRs or publish `ubuntu-docker-full`, `merge-verified` or scientific PASS on this scoped DEV_ONLY result.
- Next: opt-in source-native fourth-hour G64 stage16 and compare 313,650 45-field REAL4 values to frozen original; only then run fourth-hour atomic rollback/positive commit tests. Proceed to hours5–6 using newly committed native memories, followed by exact-SHA freeze and independent scientific review.
