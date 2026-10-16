# Source reuse provenance and rights review

User explicitly confirmed on 2026-10-10 that CTEAS-Atmos is their project and authorized direct copying where useful. This is project-specific authorization; CTEAS-Atmos `LICENSE.md` currently says no general license to third parties. Preserve provenance and do not present these copies as open-source. Before any public redistribution, clarify rights of all contributors and third-party dependencies.

Copied **unchanged** from private RRain001/CTEAS-Atmos main `449c17b733d0874151be5f6a14811eaa61da9bed`:
- `include/cteas_atmos/core/shape.hpp` Git blob `55a14f9bcc38eb158fee2e42edf665f1d77319a5`
- `include/cteas_atmos/core/array.hpp` Git blob `de3846367d6e4dad27bf4fba81689611adb7fc23`
- `include/cteas_atmos/core/validity.hpp` Git blob `eb1de86aea20aa42a0b2d1c4045ad73aadf494ea`
- `include/cteas_atmos/core/regular_grid.hpp` Git blob `6c4b165953b8f729d5f372c7bafd53177019ce8d`
- `include/cteas_atmos/core/unit.hpp` Git blob `3d87a4472fce382044e04701b0509d423d617abd`

They live in the same relative header paths under `native_cpp/include/`, preserve original `cteas::atmos` namespace, and are utility primitives only. No diagnostic wind, puff, physical parameterization, reference data, third-party dependency, or entire repo was transferred. This is a scoped design reuse; all Fortran equivalence gates remain independent. Original Fortran source is copyrighted separately; no vendor Fortran source copied into C++.
