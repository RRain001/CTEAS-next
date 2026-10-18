# S2-G1B-B / Issue #42 — P1–P5 same-site joint-input gate

Status: **DESIGN / BLOCKED_UPSTREAM**. This document freezes the proposed
cross-module *handoff* boundary; it does not assert that the five producers
are complete or that any scientific result is accepted.

## Scope and owners

#42 owns **only** the independently isolated five-producer coordination,
authentic source provenance, co-registration and transfer of GEO.DAT,
UP.DAT and SURF.DAT into the existing P6 G19 source-only parser.

| Producer | Unique implementation owner | Output for #42 | Current entry point / evidence |
|---|---|---|---|
| P1 TERREL | #54 | native TERREL.DAT or reviewed native elevation contract | `scripts/s2g/p1_terrain_source.py` (PR #49 is input-only, **not** native TERREL science) |
| P2 CTGPROC | #53 | native LU.DAT or reviewed native land-use fractions | PR #48 GLCC extractor / PR #52 cached GLC_FCS30D (sources only) |
| P3 MAKEGEO | #46 | real same-grid GEO.DAT | pending dynamic P3 producer and original comparison |
| P4 READ62 | #55 | original-compatible UP.DAT for each selected upper station | PR #44 *specific real 2022/2023 NOAA replay*, not generic executor |
| P5 SMERGE | #56 | original-compatible SURF.DAT for selected surface stations | PR #47 *specific real 2022/2023 NOAA replay*, not generic executor |

Do **not** duplicate source download, DEM mosaicking, GLCC/GLC decoding,
NOAA selection, wind cleaning, native producer mathematics or their
independent original/native scientific comparisons here. Existing
`native_cpp.orchestration.site_plan` is the site/station metadata gate;
`native_cpp.orchestration.p6_g19_handoff` is the G19 original-file-backed
identity, geometry and SHA gate. Reuse these, not a parallel parser.

## B-0 — shared case authority (required before execution)

The run must bind one immutable `case.yaml`, one published `grid/grid.cmn`
and the matching `grid/research_time`. Capture SHA256 of all three before
calling any producer; a changed byte after admission invalidates the run.
`case_name` must identify the **new** site and match the independent case
directory, never the frozen Hefei reference.

- `case.yaml` governs study domain, physical stack location, research UTC
  begin/end, supported input products and independent paths. Point-source
  emissions/time history are recorded for downstream P6/P7 orchestration;
  P1–P5 meteorology/terrain **must not be recomputed because of a rate change**.
- `grid.cmn` is the single horizontal numeric footprint authority: WGS84
  UTM zone 1–60, actual hemisphere, `NX/NY`, `DGRIDKM`, `XREFKM/YREFKM`
  **exactly three decimal places in km**; every stage must use its exact
  footprint and row/column ordering. `NZ/ZFACE` follow only the existing
  supported P6 G19 profile, not new vertical physics.
- `research_time` has inclusive whole-hour UTC labels and correct calendar
  years (including leap/cross-year cases); P4 original 00/12 sounding brackets
  and P5 every selected surface hour must cover the requested input windows.
- The P4/P5 station aliases and effective/source locations are obtained
  **solely** from original annual selectors. Never pad 1US to 2US, synthesize
  a surface station or silently swap annual primary/secondary ordering.
- The existing selected original processing switches are immutable:
  P4 JDAT=2 / IFMT=1; P5 JDAT=8 / IOFORM=2, including existing original
  missing/calm handling and source selection science. Unsupported options
  are errors, never automated fallbacks.
- P1 source A = user-provided local 90m SRTM TIFF collection (or one TIFF);
  B = official OpenTopography SRTMGL1 30m TIFF. P2 source A = original
  Eurasia GLCC 1km `eausgs2_0la.img`; B = **offline** locally cached
  GLC_FCS30D 2022 30m TIFF from PR #52. Record the chosen combination;
  unlike-format resolutions are not expected to match pixel for pixel.

The existing G0 metadata and G1A G19 gates remain useful but **cannot**
serve as evidence of a five-producer execution.

## B-1 — isolated scratch and source custody

Create a fresh, initially nonexistent run directory **outside**
`project/current`, frozen Hefei case data, producer caches and the
repository worktree. It must contain a physically independent new-site
copy of `case.yaml`, `grid/grid.cmn` and `grid/research_time`, then
producer-owned output paths:

```text
<new scratch>/<new-case-id>/
  case.yaml
  grid/{grid.cmn,research_time,center_location,stack_location}
  geo/{terrel/,ctgproc/,makegeo/}
  met/{upperair/,surface/}
  run/{read62/,smerge/,met/}
  evidence/{p1.json,p2.json,p3.json,p4.json,p5.json,g19.json,joint.json}
```

An evidence record for **each** producer must specify: producer issue and
version/commit/executable hash, selected input route, *original* data product
and immutable source SHA256, observed coverage, resolved CRS and UTM grid,
case/grid/time SHA256, the exact input/output paths and their SHA256,
original-control branch, actual execution command/exit and CI run ID
(if any), plus independent original/native comparison status. Distinguish
`NOT_RUN`, `BLOCKED`, `SOURCE_ONLY`, `PRODUCED_UNVERIFIED`,
`INPUT_CHECKED`, and `SCIENCE_ACCEPTED_SCOPED` **per producer**.
An evidence JSON written by the producer itself is a claim until
independently checked against original bytes/outputs; do not self-certify.

Fail closed for missing/zero-length/changed files, symlinks escaping the
staged case, wrong source product, inconsistent bounding box, unapproved
GLC class mapping, DEM void, date/alias/row order mismatch or credentials
unavailable. No substitutions from historical Hefei GEO, captured
reference outputs, synthetic meteorology or unknown-license assets.

## B-2/B-3 — staged source input and G19 acceptance

1. Admit the **same actual research footprint** into upstream #54 and #53;
   obtain a real, reviewed P1/P2 contract. #46 alone converts these to the
   same-site GEO.DAT using the existing selected MAKEGEO physics. No fake
   50x50 resampling or nominal reinterpretation of a historical GEO.
2. Independently run #55 and #56 from authentic retained NOAA archives for
   the *same* site, timestamps and selected annual stations; produce real
   UP.DAT (each real US) and SURF.DAT. PR #44/#47 scoped evidence does
   not automatically count as a generic runner.
3. Verify independent SHA256 and signed-off producer provenance of
   `geo/makegeo/geo.dat`, `met/upperair/final/up_*.dat` and
   `met/surface/final/surf.dat`, then stage the real
   `run/met/met.inp`. Verify original `NSSTA/NUSTA`, ordered
   `SSn/USn`, `IFSTN`, `IUPT`, projected station positions,
   `NX/NY/NZ/ZFACE`, categories/elevation and UTC windows.
4. Invoke the **existing** `p6_g19_handoff` source-only validator and
   independently compiled G19 input preflight **with actual producer
   bytes**, not mock streams. Require native parser station count/order
   and footprint evidence. Do **not** run P6D/E/F numerical fields
   here; that is #40.

Neither a parse-success sentinel nor an output hash alone attests
geographical authenticity. Any missing producer, reference source or
independent check leaves #42 `BLOCKED`.

## B-4 — strictly separate proof levels

- **Offline contract checks**: alternate non-Hefei UTM zone/hemisphere,
  alternate `NX/NY/DGRIDKM` and UTC interval/years, 1US/1SS and 1US/2SS
  valid fixtures if supported, plus negative cases for wrong alias,
  calendar boundary, duplicate station, wrong SHA, mismatched origin,
  old Hefei GEO and invalid source-class/NoData. Synthetic bytes only
  prove software contract and rejection behavior.
- **One real-site source gate**: Huoshan/Luogang(Xinqiao) 2022/2023
  authentic NOAA 1US Anqing + 2SS Huoshan/Luogang, plus newly produced
  independently reviewed non-Hefei GEO for its **identical** footprint.
  Real original data coverage must match retained producer reports.
- **Second real-site scientific equivalence**: separate task/evidence
  (and **NOT_RUN** until a second full genuine source set exists). Do not
  infer arbitrary N-station or multi-region science from one actual site.

Retain frozen Hefei scientific regression unchanged. Long runs including
original/native comparisons and the full scientific workflow must only
run via explicit manual `workflow_dispatch`; PR CI may run bounded
offline unit tests without external downloads or credentials.

## B-5 — acceptance matrix and handoff

| Stage | Current proven evidence | #42 status |
|---|---|---|
| P1-A/P1-B | PR #49 input adaptation only | NATIVE_PRODUCER_PENDING_#54 |
| P2-A/P2-B | PR #48/#52 original source adapters only | NATIVE_PRODUCER_PENDING_#53 |
| P3 | Hefei-scoped existing tests; no new-site same-grid GEO | NEW_SITE_PRODUCER_PENDING_#46 |
| P4 | PR #44 real NOAA UP 2022/2023 | PASS_SCOPED_SOURCE_ONLY; generic #55 pending |
| P5 | PR #47 real NOAA SURF 2022/2023 | PASS_SCOPED_SOURCE_ONLY; generic #56 pending |
| Same-site GEO+UP+SURF | No verified simultaneous full new-site stack | BLOCKED |
| G19 combined native input-only | No above same-site complete stack | NOT_RUN |
| P6 45-field/hour physics and P7 | Owned by #40/#36 | NOT_RUN |

Only grant `G1B_B_P1_P5_REAL_INPUT_STACK=PASS_SCOPED` after independent
producer-backed, **same-site** original files and genuine G19 source
parser evidence are complete; include source/producer SHA256, selected
P1/P2 route, stage logs and exact Actions run IDs in `joint.json`.
Then hand this artifact to #40, where P6 physical 45-field/hour
original/native numerical validation is independently required. A
successful #42 gate **does not** close #40/#36 or assert complete CALMET,
CALPUFF, precipitation or wet-deposition reconstruction.

### Immediate implementation sequence

1. #54/#53 freeze producer output/provenance schemas without duplicating
   PR #49/#48/#52; #46 then freezes P3 GEO output.
2. #55/#56 adapt original NOAA runners to isolated case-provided
   time/footprint/paths; keep PR #44/#47 frozen-case fixtures as regressions.
3. Once the five independent output contracts exist, #42 implements
   only the scratch coordinator and multi-producer attestations; reuse
   `site_plan` and `p6_g19_handoff` directly.
4. Manually trigger the real Huoshan/Xinqiao joint-input run, review logs
   and raw SHA independently, complete matrix and hand off to #40.
