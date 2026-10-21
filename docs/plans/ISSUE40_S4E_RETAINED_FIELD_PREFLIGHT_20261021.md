# Issue #40 S4-E — raw retained-field / Fortran record preflight

Date: 2026-10-21. Scoped follow-up to merged #215 (20SS/20US independent original 45-field science), #216–#217 (input shape and aggregate UP budgets), and #218 (measured 12x12x9 1h/6h small-case peak process RSS).

## Source-owned finding

The single S4-B2 selected G14 driver `native_cpp/modules/p6_calmet/src/p6g_s4b2_unified_selected_main.cpp` appends **all** 45 original-format grid fields of every completed hour to `all_hours.hourly`, and only after the last accepted hour calls `serialize_calmet_dat21(*all_hours)` to produce a second complete byte image. The current path is **not streaming**. In contrast to #218 (a measured Linux small-case process peak), this PR provides only checked arithmetic for the minimum uncompressed **hourly field values** retained by this particular selected driver, not a forecast of its RSS.

For the selected 9-layer 45-field-per-hour/no-precipitation CALMET.DAT 2.1 path:

- One-hour raw value bytes = `NX × NY × 45 × 4`.
- Source-window raw retained bytes = `NX × NY × 45 × 4 × hours`.
- Each 2-D P6F Fortran record payload is `24 + NX × NY × 4` bytes; a Fortran unformatted record length and `IRLG` have signed int32 storage. Reject a format-incompatible length **before** solver allocation.
- Checked `size_t` multiplication and addition reject overflow. These equations omit headers, all station data, staging vectors, serialized copy, temporary per-stage three-dimensional fields, allocator overhead, and kernel workspace, so the number is explicitly a **lower bound**, never an upper-bound RAM estimate.

Illustrative exact raw retained-field sizes (not executed benchmarks, not source science):

| Selected shape | Hour count | Raw retained 45-field values |
| --- | ---: | ---: |
| 12×12 | 6 | 155,520 B |
| 100×100 | 143 | 257,400,000 B = 245.48 MiB |
| 100×100 | 8760 | 15,768,000,000 B = 14.69 GiB |

These examples do **not** imply that the 100×100 year calculation is admitted or economically runnable; `all_hours` plus the serializer can hold separate large copies, and true peak RSS must be measured on supported source/host/duration.

## Bounded code change

1. Add checked `one_hour_raw_field_bytes`, `retained_raw_field_bytes`, and `field_record_payload_bytes` to the existing source-only S4-B1 admission report. Reject record payloads or hour counts outside the actual selected signed int32 P6F format.
2. Add opt-in `--max-retained-field-bytes N` to the **existing selected-experimental-only** G14 CLI. For a prefix probe it estimates *only executed* hours. If explicitly supplied and below the raw field-value lower bound, it refuses **before the first physical hour**. If absent, no guessed memory limit is imposed; a passed limit cannot guarantee actual peak RSS because the number is only a lower bound.
3. Retain exactly the same G19 original input parser, G14 17-stage physical actor, C1/C2/Huoshan scientific reference, original 45-field ordering and P6E frozen numerical comparator. Do not enable normal G26 `run()`, modify scientific formulas, introduce a 20-station cap, or change P7.

## Acceptance / blockers

- Source-only Release CTest must pass positive 1–N and 20/20 cases, 100×100/8760 exact raw arithmetic, exact budget and one-less rejection, 32-bit Fortran record and IRLG negative cases, and `size_t` overflow tests.
- Existing physical regression / independent unchanged original Fortran CALMET 45-field Actions must stay green at exact PR HEAD before merge. No test-only numerical result is promoted to production acceptance.
- This PR is a **software resource-preflight** improvement, not measured peak RSS, not a full-domain memory stress test, not a streaming writer, and not production G26. Next: measure legally staged real Huoshan 100×100 1h/6h and longer available windows; audit growth of stage buffers, source state and serialized copies; implement separately reviewed production G26 entry and real independent multi-observation station science. S5 #161 still owns broad capacity/chunking work; #36 P7 remains blocked.
