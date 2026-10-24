# S4-R1c9p — original CALMET G23/G24 third-hour wind-tail stage oracle

## Scope and independent original provenance

- Stacked after Draft PR #303 HEAD 4a3d426b34fffdf72af65206f8d371fb672aedd5. This change adds only a **scratch-only original Fortran diagnostic generator**, strict read-only parser, original-to-original consistency check, eleven negative/positive software regressions and this audit. It does **not** change native G23/G24/G26, production guards, station observations, model controls or tolerances.
- Original CALMET 6.5.0 Fortran source SHA256: 835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23. The script verifies the exact source before making a scratch copy. It never changes /home/lhy/CTEAS or commits original source.
- Genuine NOAA 2022-06-01 02–08 UTC, 82x85x9, 2 surface/1 upper station; same P1–P5 input hashes as #303: met.inp c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744; GEO 5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a; SURF 6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655; UP a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00.
- Ubuntu GFortran 11, source compiled with -std=legacy -ffixed-line-length-none -fno-automatic -fno-align-commons -fallow-argument-mismatch -O0 and vendor include path; **instrumented executable SHA256 ba12098a364d17c04173aed8d9ca9f4c45b6ed85dc9ee55ff22281d3bc47ad19**.
- Instrumented original full sixhour MET.DAT SHA256 **a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14**, byte-for-byte identical to the independently frozen pristine original. No source physics changes.
- Original private diagnostic S4_DIAGNO_WINDTAIL.BIN SHA256 **755fe44499ac8a53f3f959f29cdb28c1515ba6da1d719f198a78813fe9016995**. Full private source, binary, MET and trace remain in /home/lhy/dev/CTEAS-next/local-science/s4-r1c9p-original-wind-tail-20261024, never uploaded to public GitHub.

## Source-stage trace contract

The trace inserts write-only stream records inside original DIAGNO, without changing arithmetic:

| Original stage | Capture point | Array payload per hour |
| --- | --- | --- |
| 90 | after INTER2, before lake-breeze/second WINDBC | U/V, 9 layers x 6970 cells x 2 |
| 100 | after SMOOTH | U/V, 9 layers x 6970 cells x 2 |
| 110 | after DIVCEL and final WINDBC loop | U/V 9 layers plus W **10 faces** |

For six hours, the parser verified **18/18 correctly ordered stage records and 2,676,480 finite REAL4 words**. Each header pins original NHRZ, NX=82, NY=85, NZ=9 and stage ordinal.

The independently captured stage110 U/V/W fields were then compared against the same original OUTHR MET.DAT: **1,129,140 / 1,129,140 REAL4 bitwise identical**. Critical source-index convention: OUTHR emits WFACE(k) from W(:,:,k+1), not W(:,:,k); the check uses the correct face shift. The 6-hour original trace therefore represents the exact original output wind-tail, not a detached or post-processed substitute.

## Admission boundaries

- 11/11 parser and corruption-regression tests PASS, including wrong stage/clock, nonfinite, truncation, source hash, overwrite refusal and deliberate WFACE off-by-one rejection.
- Original source diagnostics and original-to-original output check **PASS_SCOPED**. No native G23/G24 source-stage numeric comparison has yet been run; native G23 hour_index>1 guard remains unchanged. Do not mistake original-original bitwise equality for original-native equality.
- Next: in a separate, explicitly test-only native G26A third-hour stage7–11 trial, retain committed hour-two memory and published AA/BB/CGAMMA, handle current-hour G43 nonwind MISSFC while leaving raw P5 wind/precip untouched, and compare original stage90/100/110 U/V/W and station STHEOR/INTER2 state. Only after independent original numerical evidence may any scoped guard be reconsidered.
- Third-hour G26B/G63/G64, positive G14 commit, hours4–6, generic P6, P7 and independent scientific review remain NOT_RUN/NOT_ACCEPTED. All Draft PRs remain unmerged.

## Reproduction

Run script from this exact worktree, passing the pinned read-only original Fortran and a fresh private scratch output. Compile the generated source using the command above, run the unchanged met.inp/GEO/SURF/UP in a scratch working directory, then:

    python3 -m scripts.s4.s4r1c9p_original_wind_tail_trace audit \
      --trace /path/to/private/S4_DIAGNO_WINDTAIL.BIN \
      --instrumented-met /path/to/private/met.dat \
      --report /path/to/new/private-windtail-audit.json

    python3 -m unittest scripts.s4.test_s4r1c9p_original_wind_tail_trace -v

Only numerical summaries and SHA hashes are permitted in this public report; original source, observations, executable and raw trace are not redistributed.
