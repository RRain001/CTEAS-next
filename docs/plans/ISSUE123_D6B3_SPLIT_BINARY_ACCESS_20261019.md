# Issue #123 D6-B3 — original binary I/O split by source algorithm

## Genuine failure; not an absent source or a polygon algorithm discrepancy

Original science workflow [#39280129505](https://github.com/RRain001/CTEAS-next/actions/runs/39280129505) ran on `main@f2f5c5c7`. It verified exact original CTGPROC source, official GSHHG v2.3.7 Full `gshhs_f.b`, and original GLCC Eurasia `eausgs2_0la.img` source SHA; staged GNU STREAM+EOF derivatives compiled. Original `COASTEXT` then reported **one shoreline polygon**. The next original `COMP` step reached the legal GLAZAS `glcc.img` and terminated:

```text
At line 2453 of file ctgproc.for (unit = 2, file = 'glcc.img')
Fortran runtime error: Invalid argument
Processing coastline data
Note: # shoreline polygons found: 1
Processing: 6 2 1 glcc.img
```

The fail-closed provenance artifact [#12200911020](https://github.com/RRain001/CTEAS-next/actions/runs/39280129505/artifacts/12200911020) had three source/adapter JSON files, **no original_coastext_report.json**. Therefore `ORIGINAL_COASTEXT_BLN` and real Fortran/C++ point parity remain **NOT_ACCEPTED**.

### Root cause from exact original Fortran source

The previous GNU adapter (#148) patched shared `params.ctg` from `caccess='direct'` to `caccess='stream'` for the original binary GSHHG sequential reader. But the **same parameter** also configures the original `COMP` GLAZAS input OPEN:

- `ctgproc.for:2167-2168`: `OPEN(IOINP, ..., FORM=CFORM, ACCESS=CACCESS, RECL=IRECL)`.
- `ctgproc.for:2453`: `READ(IOINP,REC=KCNT)KBUF`, which **requires DIRECT indexed-record access** (RECL=1 for original one-byte GLCC pixels).
- `ctgproc.for:6273-6274`: `OPEN(IOGSHHS, ..., ACCESS=CACCESS, FORM=CFORM, RECL=IRECL)`, while `BREADH/BREADP` use sequential `READ(IOGSHHS)` on raw GSHHG Full binary, requiring GNU STREAM.

The global access change fixed GSHHG but broke GLAZAS, not the physical classification algorithm.

### D6-B3 auditable, scratch-only remedy

1. Retain SHA-pinned original `params.ctg` **byte-identically** (SHA256 `28dc5877c6a70d74f7a0e136bdd4aa1777dc9cbab15c184e7f483f772cd266c6`): `CACCESS='direct', RECL=1`. Do **not** modify the original GLCC `OPEN` or random `READ(REC=)`.
2. On a SHA-pinned original `ctgproc.for` copy only (original SHA256 `719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281`), retain the separately audited D6-B2 eight `BREADH ERR=99 -> END=99` conversions; verify that EOF-derived scratch source hash before any further changes.
3. Replace exactly **one** `COASTEXT` binary GSHHG `OPEN` with `ACCESS='stream'` and **omit RECL**. No other source OPEN, data parser, transformation, `COASTRD`, `IPTYPE`, `PNPOLY`, `LUGRID`, `SVGRID`, `GLAZAS`, or scientific algorithm modification is authorized. Any source/patch count/SHA drift fails closed.
4. Upload only split-I/O and EOF derivative provenance JSON, original input hashes, and if it is actually generated an audited `original_coastext_report.json`, never vendor source/raw BLN/raw GLCC.

This is an explicitly declared **GNU I/O-adapted derivative**, not a byte-identical original Fortran execution. Original scientific equivalence is not inferred from compiled output.

### Real acceptance after merging and one justified retry

The current PR CI is **synthetic/offline only**. After review and merge, an independent main-push `issue123-d6b-real-original-coastext.yml` run is justified because the historical run failed for a concrete I/O reason and the new source SHA changes. Require:
- Genuine GSHHG Full and legal GLCC SHA admission;
- Original `COASTEXT` generated nonempty BLN, with valid polygon closure, 0–4 category, coordinate bounds and audit manifest;
- No glcc.img `READ(REC=)` runtime failures;
- Only then original-vs-C++ same-BLN REAL*4 `IPTYPE` zero differences, and later per-cell 200×200×38 original integer HITS and formatted LU.DAT exact scoped comparison.

The 200×200 Wolsong UTM52N 100m, Full-only original boundary and [#119](https://github.com/RRain001/CTEAS-next/issues/119) frozen `EXACT_AREA_V1` are unchanged. Keep #123 OPEN.
