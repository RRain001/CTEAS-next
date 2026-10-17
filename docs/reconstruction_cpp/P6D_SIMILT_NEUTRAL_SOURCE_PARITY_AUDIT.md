# P6D7 WIND1: source-scoped original SIMILT neutral vertical extrapolation

Date: 2026-10-11. **Candidate awaiting original numerical CI**.

The immutable CALMET 6.5.0 L150223 `SIMILT` source at `calmet.for` L30097–30370, source blob `437f43bb7f0e51a1919e56664663e1a046986ed0`, is the authority.

Current selected 2022 case `IEXTRP=-4`, `NOOBS=0`, land surface station, positive latitude. `WIND1` L36173–36196 calls `SIMILT` with `EL=ZI=ZIMINI=10000.`, which forces neutral `ELINV=0`: `PSIM=PSIM1=0`, `DH200=12 degrees`; the original still applies the Van Ulden-Holtslag logarithmic wind speed and height-dependent veering function. The first model level uses ZMID(1)=10 m, station observation at ZANEM may differ from 10 m. Do not substitute a plain power-law profile.

C++20 kernel `include/cteas/p6/similt_neutral.hpp` and CLI `src/similt_neutral_main.cpp`; software CTest exercises expected monotonic shear and fail-closed southern/calm/invalid roughness inputs. Reference comparer `reference/compare_original_similt_neutral.py` compiles **literal unchanged Fortran SIMILT** extracted from frozen source, with driver-only `PSIUD/PSIUC` stubs that `STOP` if they are reached: these must be unreachable for the specified neutral branch. 12 scenes × 9 levels × 2 wind components = **216** original-C++ component pairs with declared tolerance **2e-4 m/s**. Includes real Hefei station latitude, four quadrants, near-calm valid, roughness extremes, height changes, and IPSIFCN values 0/1 under neutral mode.

**Limitations**: This is selected neutral surface-layer SIMILT only. No actual original WIND1 50×50 first-guess grid, weight bias blending, calm handling, FRADJ/SLOPE/DIAGNO orchestration or real 2022 full U/V/W model parity is claimed. Stable/unstable SIMILT, other IEXTRP values, southern latitude and overwater station are out of scope and must not be treated as supported. Full P6D remains `NOT_PASS` even after this kernel passes.
