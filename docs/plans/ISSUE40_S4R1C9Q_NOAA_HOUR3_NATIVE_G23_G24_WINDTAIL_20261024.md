# S4-R1c9q — real NOAA third-hour native G23/G24 stage90/100/110 parity

## Exact input and execution provenance

- Stacked after Draft PR #304 HEAD 13a7f5fb278c04b7d41792d8bf7854f583709894; the new candidate is a separate branch/worktree. No production admission or third-hour G14 commit.
- Real NOAA 2022-06-01 02–08 UTC, 82x85x9, two surface stations, one upper station; original hour-three end is 04 UTC. Original /home/lhy/CTEAS Fortran and its six-hour read-only trace are NOT passed to native C++.
- Original source SHA256 835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23, unchanged and read-only. Original trace SHA256 755fe44499ac8a53f3f959f29cdb28c1515ba6da1d719f198a78813fe9016995; its instrumented full MET output was previously confirmed byte-identical to pristine original SHA256 a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14 in PR #304.
- Input hashes: met.inp c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744; GEO 5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a; SURF 6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655; UP a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00.
- Host Ubuntu GCC 12 Release native binary SHA256 450f8f0464f08d06129b657ba98d6f98c3c41d5601043bf03c8f200ac28a1ea4; third-hour unpublished native trace SHA256 521fc0ed9cedbf5f4232b2bf6e1252c866336e9f8a706a95a66e9dd8e2c7ceab.
- Native output and full per-cell comparison report remain private under /home/lhy/dev/CTEAS-next/local-science/s4-r1c9q-native-windtail-stage100-20261024/; no original source, binary, trace, meteorological data or full field arrays committed.

## Scientific numeric result — third hour only

- PASS_SCOPED_HOUR3_G23_G24_STAGE90_100_110: 446,080/446,080 REAL4 original/native wind-stage values within the pre-existing frozen 2e-4 m/s tolerance; 0 exceedances, 345,914 bitwise identical.
- Stage90 is original post-INTER2 U/V, stage100 is the same invocation native post-SMOOTH U/V snapshot before DIVCEL, and stage110 is final DIVCEL/W U/V/W. Native stage110 W includes ten original W planes; MET.DAT OUTHR uses WFACE(k)=W(:,:,k+1) and is a distinct nine-plane serialization.

| Stage/field | REAL4 compared | Bitwise equal | Frozen exceedances | Max absolute difference (m/s) |
|---|---:|---:|---:|---:|
| 90:u | 62,730 | 51,905 | 0 | 1.90734863e-06 |
| 90:v | 62,730 | 52,786 | 0 | 9.53674316e-07 |
| 100:u | 62,730 | 53,571 | 0 | 1.90734863e-06 |
| 100:v | 62,730 | 54,478 | 0 | 1.43051147e-06 |
| 110:u | 62,730 | 53,571 | 0 | 1.90734863e-06 |
| 110:v | 62,730 | 54,478 | 0 | 1.43051147e-06 |
| 110:w | 69,700 | 25,125 | 0 | 4.76837158e-07 |

## Fail-closed software and transaction boundaries

- G23 hour_index>1 default scientific guard remains. Third-hour stage7–11 is entered only with a new explicit test-only opt-in, after the real native G14 second-hour positive transaction, published AA/BB/CGAMMA clocks, native second-hour P6F WATER USTAR/EL, and native third-hour stage0–6. G22 default guard is not removed.
- Native G26A stage7–11 uses the same scheduler-owned hour-three frame; G23 STHEOR/DIAGI/INTER2 and G24 SMOOTH/DIVCEL/W execute native C++ physics. No original MET or intermediate field is injected. The program checks scheduler committed hours remain 2, prior ZI/ZICONV/DPTT and clocks remain unchanged; it does not run third-hour COMP/P6F or publish hour three.
- Stage100 observer copies the actual SMOOTH result without changing arithmetic. In an independently repeated native trial, stage90 and stage110 output remained byte-identical with and without observer. C++ final-segment unit test checks observed versus unobserved U/V/W/divergence and boundary values.
- New 12/12 Python negative/format tests PASS; combined existing G22/G23 trace and new tests 36/36 PASS; C++ final-segment observer regression PASS; pinned Hefei G19 input-contract CTest 1/1 PASS (correct fixture path). Exact-SHA Ubuntu Docker full and independent science reviewer admission remain NOT_RUN until separately executed.

## Remaining work

- This is a selected, third-hour, test-only original-versus-native numerical result, NOT a general third-hour P6 production approval. Third-hour G26B COMP stages12–15, G64 P6F stage16, positive G14 state/clock commit, hours4–6, new-site generic P6/P7, wet deposition and independent scientific review remain NOT_RUN/NOT_ACCEPTED.
- Next: independently trace original COMP hour3 MIXHT/AVEMIX/WSTARR/TEMP3D, run native G26B/G63/G64 with exact committed hour-two state and clocks, then compare all 45 original/native hour3 fields without changing frozen tolerances. Keep stacked PR Draft until independent science review.
