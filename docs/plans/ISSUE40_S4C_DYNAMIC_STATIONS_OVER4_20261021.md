# S4-C source-owned dynamic station cardinality beyond four

Issue #40, 2026-10-21. Frozen starting source is `main@cf34e1f4fd9a52931b2f0a7667aff827ce08bf16`. Accepted C1 real Hefei, C2 controlled synthetic 2SS2US, actual NOAA Huoshan 100x100 six hours, previous independent 3/4-station and shifted station ID original science remain protected.

## Physical and engineering boundary

Previous `<=4` tests in G20 WIND1/INTER2 and G18A/G18C3/G18C5/G18C6/G26B/G14 selected G14 source-backed admission encoded *number of scientific test stations* as a new physical ceiling. They are removed from the **opt-in selected scientific path**; no alternative dynamics or formulas are introduced. Preexisting original input/source checks, per-station ordinal/ID concordance, 1h G14 chronology, 9-layer selected option policy, grid size and time budget remain enforced. The normal production G26 `run()` still refuses execution, and this experiment must never be misreported as fully production generalized.

Original-format **test exporter only**, still bounded to 1..8 SS and 1..8 US because the 12x12 controlled case and original compiler will be exercised in that envelope. This is a *fixture scope limit*, **not** a P6 physical or production limit. Each extra station has own physically distinct geolocation and original source-format SURF (for SS4+ unique speed/direction) or UP (for US4+ independent two-layer sounding speeds/directions) values; not a copied or dummy station. Keep prior 1..4 source fixtures unchanged, except no changes to the accepted fourth station values. All are controlled synthetic original format, **NOT real NOAA independent observations**.

## Original and C++ scientific CI

Seven source combinations: `5SS/5US`, `5SS/2US`, `2SS/5US`, `6SS/3US`, `3SS/6US`, `1SS/5US`, `5SS/1US`. Run each on the SAME selected G14 C++ 17-stage physical branch and separately compile and run **unchanged pinned original Fortran CALMET 6.5.0** on **the same original-format source**. Independently check original 45 CALMET fields at first hour and six consecutive hours on all 12x12 cells with frozen P6E tolerance, 0 missing field-cells and `total_exceedances=0`. Preserve original binary/source SHA, full original listing, C++ output SHA, source input SHA, first field/hour/cell of every mismatch.

**PASS_SCOPED** applies only after real GitHub jobs pass. Every existing 1..4, original 45 field C2, C1, actual observed Huoshan S3→P6 science, source-input, ASan and construction scope that CI already covers must remain PASS at the final PR head. No P7, wet deposition, S5 grid capacity or Docker in this scope.

The next S4 substage must explicitly audit non-synthetic multistation NOAA identity/geometry, different grid/UTC scenarios, missingness/upper options and then production G26 admission. This PR alone never closes Issue #40.
