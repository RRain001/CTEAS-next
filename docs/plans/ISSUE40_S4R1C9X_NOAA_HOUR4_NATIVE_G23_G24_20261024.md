# S4-R1c9x — Genuine NOAA fourth-hour G23/G24 original/native windtail, stages7–11

## Exact scientific scope

- Stacked locally on S4-R1c9w commit `753bc0b6bb996fe8d5fd7f2322d6809d7ebbc7ed`, after open Draft PR #308. All production guards still reject `hour_index>1`; this path is opt-in research only.
- True NOAA 2022-06-01 02–08 UTC six-hour case: 82×85×9, 2 surface stations, 1 upper station, source 63 WATER cells, fourth-hour end 05 UTC. Original CALMET 6.5.0 Fortran remains read only at `/home/lhy/CTEAS`.
- The native fourth-hour G26A actor uses actual G14 committed hour-three `ZI/ZICONV/DPTT` and published AA/BB/CGAMMA, source G43 fourth-hour `MISSFC` internal nonwind substitution, and native G64 previous WATER `USTAR/EL`. P5 raw surface meteorology, original MET and Fortran traces are NEVER injected into native C++.
- The prior S4-R1c9w fourth-hour 0–6 thermal stages remain unchanged: `181220/181220` REAL4 within frozen limits, `156712` bitwise, zero exceedances; G66 detached G22 and live G26A G22 byte-identical.
- Newly approved *test-only* G23 STHEOR/INTER2 and G24 SMOOTH/DIVCEL_W stages7–11 enforce `hour_index=3` and exact station/clock/source-provenance checks. The existing hour3 path `hour_index=2` remains distinct; no generic fourth-hour physics admission.

## Read-only original-versus-native audit

- Original six-hour independently instrumented G23/G24 wind-tail stages90/100/110 SHA256 `755fe44499ac8a53f3f959f29cdb28c1515ba6da1d719f198a78813fe9016995`; original MET SHA256 `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14`. An earlier original-only audit verified its own MET-stage110 wind output, but that alone is not native parity.
- New fourth-hour native stage90/100/110 trace SHA256 `2bd680a21927fa43d1c05fb0f2fb2386449f9e90569d4c6634d96e0b5da42b91`. Private output and comparator JSON: `/home/lhy/dev/CTEAS-next/local-science/s4-r1c9x-hour4-native-windtail-retry-20261024/`.
- **PASS_SCOPED_HOUR4_G23_G24_STAGE90_100_110**: `446080/446080` original/native REAL4 within the **unchanged 2e-4 m/s** wind threshold, **0 exceedances**, **363869 bitwise exact**. Compare stage90 INTER2 U/V, stage100 SMOOTH U/V, and stage110 final U/V/WFACE; WFACE indexing follows the validated original `WFACE(k)=W(:,:,k+1)` output convention.
- New and existing wind trace format/frozen tolerance tests: `19/19 PASS`; Ubuntu GCC12 Release -Werror Docker DEV_ONLY build `dev-20261024T005307-1bb42b01` PASS. First native attempt exited nonzero because inherited G65 stage6-only checkpoint was still hard-coded at 7; it is archived privately at `s4-r1c9x-hour4-native-windtail-20261024`. Corrected guard checks 12 stages only for explicitly opted-in windtail path; second native attempt returned exit0 and produced the scoped compared trace.
- This is NOT a software exact-SHA Ubuntu Docker full, formal scientific independence audit, production G14 hour-four commit, or evidence that fourth-hour stage12–16 has passed.

## Next work

1. Reuse the same genuine NOAA hour4 G26A frame to perform opt-in G26B/COMP MIXHT stage12 and AVEMIX/WSTARR/TEMP3D stages13–15, strict original stage12–15 trace comparison. Then G64 P6F stage16 compare 45 fields and hidden `ZI/ZICONV/DPTT`; require one positive G14 memory+clocks commit after a rollback case.
2. Continue hour5–6 only with authentic previous-hour memory and station clocks, source MISSFC on each hour; compare original sixhour 45 fields and internal stage boundaries.
3. Batch/freeze exact SHA, run official Ubuntu Docker full and independent science review only when whole source-native P6 research batch is ready. **P6 six-hour production NOT_ACCEPTED, P7 NOT_RUN, independent science review NOT_RUN.** No relaxation of thresholds, no auto-merge of Draft.
