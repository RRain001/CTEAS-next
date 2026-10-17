# S2-2A1 native case contract — read-only

This module implements **only** a bounded, JSON-producing `dry-run` contract for the frozen Hefei 2022 case. It is *not* a runner, general case planner or claim of numerical/scientific acceptance.

```bash
python -m native_cpp.orchestration.plan --case-yaml project/cases/hefei5km_2022_reference_case_20261011/case.yaml
python -m unittest discover -s native_cpp/orchestration/tests -p 'test_*.py' -v
```

The CLI **only reads the YAML** and prints a JSON object with immutable source-YAML SHA256, known grid/UTC/meteorology/point-source admission, and P1–P7 DAG. The returned status is always `DRY_RUN_ONLY_EXECUTION_BLOCKED` (`ready=false`, no legacy fallback, no files written). Invalid/out-of-scope cases yield exit code 2 and a blocked JSON result. No execution flag exists.

Strictly accepted *schema profile for planning*: exact 2022 Hefei case identity, 50x50x9 @ 100 m, UTM50N WGS84, locked UTC dates/station/source and known dry-deposition-free wet/chemistry switches. Case file SHA is reported, not claimed as independent source provenance. No implicit assumption about a 143-hour execution is made from the inclusive 2022-01-01..2022-01-06 labels.

This intentionally differs from `engine/gui_g5/pipeline.py` and neither imports nor modifies it. Existing C++/Fortran numerical kernels and P3 independent reference outputs remain unmodified. Next: build source-audited TERREL.DAT/LU.DAT writers and test their exact I/O contract before linking P3, then integrate P4/P5, P6/P7 under separately accepted stage permissions.
