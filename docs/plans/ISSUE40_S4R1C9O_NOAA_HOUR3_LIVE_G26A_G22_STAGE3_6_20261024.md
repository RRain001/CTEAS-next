# S4-R1c9o — actual third-hour G26A stage3–6 G22 native trial and original parity

## Change and scope

Stacked on Draft PR #302 (baad4c095b369f3f422f62de42306f3126aa3367). Adds a separately and explicitly opted-in **test-only** route to the real G26A scheduler-bound third-hour actor. G26A stage0 PREPDI, stage1 WIND1, stage2 FRADJ, stage3 HEATFX, stage4 AIRDEN, stage5 ELUSTR, stage6 SLOPE execute in source order on the same native G14 preview. G22 consumes actual prior-hour **native** P6F WATER USTAR/EL and original-source-selected current-hour G43 nonwind MISSFC; original CALMET MET.DAT and trace are never passed to the native program.

Default G26A still calls the unchanged original-selected G22 guard and rejects hour_index>1. This new trial is available only with an explicit native hour2 P6F pointer and explicit trial flag, and it is forbidden to publish G14 memory/AA/BB/CGAMMA clocks or run downstream COMP. It does not change P5 raw wind/precip, production CALMET options, scientific tolerances, or S4/P6/P7 acceptance.

## Actual Ubuntu evidence

- Authentic NOAA 2022-06-01 third hour 03–04 UTC, 82x85x9, 2SS/1US, 63 GEO WATER, same source/inputs SHA pinned in parent R1c9n.
- Ubuntu 22.04, GCC12 Release -Wall -Wextra -Wpedantic -Werror, native executable SHA256 dc0c5ad03c5590667bdf2997fd58823b13d274994dae71efa664dda730c62287.
- Genuine G26A stage0–6 returns native completed stages and source PRECOMMIT-only receipt, 7/7 ordered checkpoints. Default third-hour G22 guard separately rejects as expected. Scheduler remains at two committed hours, previous ZI/ZICONV/DPTT and published AA/BB/CGAMMA clocks unchanged.
- Real G26A stage3–6 produces **exactly the same G22 intermediate bytes** as independent detached G66 native source-only replay, SHA256 a26c94a247befc5e33f5f94cbe9f4134c1ec0588826de28e55796bef6541fe00. The two native paths are not independent original Fortran evidence; their identity only tests correct wiring of G26A.
- Independent original Fortran G22 stage trace (sixhour instrumented source; original MET byte-identical to pristine) vs **actual live G26A G22**: **181,220/181,220 REAL4 within previously registered R1c3/P6B2B tolerances, 0 exceedances**. Bitwise 156,808/181,220 (24,412 tiny REAL4 differences, so NOT byte-identical). Original WATER USTAR/EL 126/126 bitwise, QSW 6,970/6,970 bitwise.
- Python regression tests from parent PRs #300/#301/#302: 27/27 PASS. Actual source-native live trial and independent original comparator PASS_SCOPED, but external independent scientific review NOT_RUN.
- All full original and native trace binary, input data and numerical JSON stay private in /home/lhy/dev/CTEAS-next/local-science/s4-r1c9o-hour3-live-g26a-g22-20261024. No restricted data in GitHub.

## Initial GitHub CI failure and correction

The first PR #303 HEAD 4115663b09fa6ca0af0b541c05e6c97a8ac64a3c **failed multiple CI jobs**, including frozen C2 and dynamic station G19 compilation. Root cause: G26A transitively included the new G66 header, which referenced the P6F writer type without a self-contained include; adding the writer dependency would also incorrectly couple the G26A physics header to P6F linkage. The correction introduces a narrow typed G66NativeHour2WaterState containing only prior native USTAR/EL arrays and begin/end clock. Only G65's P6F boundary decodes the verified native hour2 P6F label/shape/time and constructs that typed physical state; G26A/G66 no longer include or link the P6F writer. No source physics or numerical tolerance changed.

The corrected GCC12 Release compiled both the real G65 executable and the formerly failing G19 header consumer with -Werror. Local ctest p6g_g19_source_file_backed_2ss_2us_g14_input_contract: 1/1 PASS. Initial failed GitHub checks remain historical evidence; they must rerun on the new exact commit SHA, and cannot be called green before GitHub reports success. Corrected native executable SHA is recorded above; a fresh real NOAA source run and independent original comparison are required on this exact binary before any scoped PASS claim.

## Admission boundaries

This is the first authentic third-hour **live G26A G22 stage3–6** bounded native execution with independent original same-input stage comparison. It is **not** the full 12-stage G26A DIAGNO: G23 STHEOR/INTER2 and G24 WINDTAIL stages7–11 are still NOT_RUN for hour3. G26B/G63/G64 COMP stages12–16, G14 third-hour atomic commit, fourth–sixth hours, sixhour 45-field independent Fortran comparison, production P6, P7 and independent science review remain NOT_ACCEPTED / NOT_RUN.

Next verify actual G26A stages7–11 using same committed prior and station clocks against original third-hour WIND1/FRADJ/INTER2/G24 source intermediate arrays. Then independently establish G26B and P6F; only after the complete sixhour original parity and independent review may the guarded production path be reconsidered.
