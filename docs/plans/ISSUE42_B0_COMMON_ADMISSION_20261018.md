# #42 B-0 reusable staged-case preflight — scoped code

This read-only preflight is a **shared authority for all P1–P5 producers**,
not a P1 or P2-specific grid parser. It wraps the existing
`site_plan._geography` + `engine.run_met.station_grid.load_strict_utm_grid`
rather than replacing their numerical grid/center validation.

The new `admit_case(case_yaml)` validates three physically staged
`case.yaml/grid/grid.cmn/grid/research_time` inputs, rejects lexical
duplicate active keys and non-integer zone/NX/NY/NZ, requires exactly
three decimal km origin digits, checks case/grid geometry and
inclusive hourly UTC research_time, and returns immutable input hashes
and numeric/grid identity. `verify_immutable` invalidates any changed
bytes after the producer has run. The common parser runs outside the
repo and frozen Hefei case tree. No write, data fetch or producer execution.

Scope intentionally **does not** include B-1 fresh scratch orchestration,
producer sidecar JSON or scientific verification. It does not prove the
original/native physics or independent source custody. Later #54 and
#53 must consume this function rather than introduce their own case
parsers; the #42 owner must separately implement B-1. Generic P1/P2/P3
remain blocked until their independently reviewed producers exist.

Only bounded synthetic contract unittest runs in PR Actions. No
long/scientific validation is automatically triggered.
