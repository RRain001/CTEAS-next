# P7 Mode A — original input semantics correction (2026-10-12)

## Fixed in this bounded patch

- Original `run/puff/puff.inp` is the source of truth for the **locked Hefei 2022** stack source parameters. The CMake real-case tests now derive the source X/Y (UTM km), stack height, diameter, exhaust velocity, temperature, and first species release rate from its one active source row. They no longer supply independently reprojected unrounded stack coordinates.
- Selected P7C `point_source_from_control` requires `IPTU=8` (Bq/s). Other `IPTU` modes must not silently be treated as Bq/s.
- The selected C++ source parser now rounds control X/Y to `float` (`REAL*4`) before producing P7C prototype UTM metre coordinates. This is a control-input precision boundary; it is **not** a complete reconstruction of the original `XPT1GRD` path.
- A dedicated locked-case input check verifies the frozen 2022 control values (`513.385, 3533.769, 70.800`), `IPTU`, emitted values, and C++ source conversion. Register this test only when the original frozen `puff.inp` is physically available; do not treat omission as a pass.

## Important distinctions and acceptance blockers

- The C++ P7C replay stores absolute UTM metres; original CALPUFF `XPT1GRD/YPT1GRD` is relative to the meteorological grid. A true original-compatible run must explicitly compute original relative-grid source and receptor inputs **with the original conversion order and REAL*4 semantics**. Do not infer the precise original formula from this patch; instrument original source assembly and compare initial values with C++ before a parity verdict.
- The frozen deck's rounded `XORIGKM/YORIGKM` and the `MET.DAT` REAL*4 origin are different inputs. Never replace either one with higher-precision GIS values. Verify the original conversion and boundary rules with vendor CALPUFF source oracle.
- Some source-supplied arguments in the locked-case probes are intentionally controlled *physics demonstrations* rather than whole-model original states. Keep their scope labels.
- The historical 2023 control and the selected Hefei 2022 control both use `IPTU=8`. No general `IPTU` conversion path is claimed.
- The P7 2022 wet path remains blocked (`MWET=0`); P7 whole-case concentration value parity is NOT_PASS pending input/oracle and driver/output work.

## Gates to run

1. `cmake -S native_cpp/modules/p7_calpuff -B <build> -DCMAKE_BUILD_TYPE=Debug`; `cmake --build <build> -j 4`; `ctest --test-dir <build> --output-on-failure`.
2. Repeat with the locked 2022 `project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.inp` present, confirm the registered `cteas_p7c_locked_original_point_input` and all selected `cteas_p7{m,n,o,p,q,r,s,t,v,w}` tests use original input values. Report test inventory, skipped tests and artifact hashes explicitly.
3. Original CALPUFF vendor oracle: capture original source X/Y after original input parsing and internal `XPT1GRD/YPT1GRD` assignment plus grid origins; compare against C++ initial puff state and original 2022 output. Then run 1h/6h/143h numeric parity **only after** P7 assembled driver exists.

This patch is bounded to P7 C++ source, its test/build definitions, and this report; it does not modify P6, original Fortran, frozen case artifacts, thresholds, or the reference meteorology.