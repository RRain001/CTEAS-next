# #54 original TERREL independence, same-source D2/D3 manual parity

The owner correctly identified the complete original
`TERREL_v7.0.0_L141010` Fortran source and input deck in the **separate
public** `RRain001/CTEAS` repo, immutable revision
`dfad99a78ed84d655e21411c9d25eb0d2583bf13`. It includes
`terrel.for`, `terrel.inp`, and historical supporting FORTRAN include
files. Do **not** commit any additional vendor source into
`CTEAS-next`, or upload original vendor executable/source/raw TIFF.

A new manual-only [Actions] workflow
`.github/workflows/issue54-original-terrel-manual.yml`:

1. Checks out `CTEAS-next` at main and **separately**, pinned to exact
   commit, checks out `RRain001/CTEAS`. Existing CTEAS source is
   unmodified; only scratch alias INCLUDE symlinks are created.
2. Replays **the same** non-Hefei 50×50@100m UTM50N/115E seam case
   with genuine original 90m twin LFS TIFFs, or actual SRTMGL1 30m
   OpenTopography API/official S3 bulk route; source SHA and C++ 2500-cell
   output manifest are newly verified.
3. Compiles untouched TERREL using previously scoped genuine frozen
   reference compile flags. Copies the exact CTEAS template to scratch
   and invokes the **original CTEAS**
   `engine.preprocess.terrel.auto_select_srtm_to_terrel.update_terrel`
   to synchronize the authoritative case UTM/nx/ny/xref/yref/dgridkm
   and exactly **one identical selected TIFF**.
4. Executes the independent Fortran program in a distinct work
   directory, preserving stdout/stderr and original control/dat/sav
   *SHA hashes* locally. Runs the existing #67/#71 independent
   generic original DAT/SAV vs native CSV comparator on these
   **same byte-identical** inputs, without changing sample selection,
   output F8.1 tolerance or REAL4 mean tolerance.
5. Uploads **only** compact JSON of hashed input identity, numeric
   comparison summary and blocked reason categories; no vendor
   source/binary, raw DEM, control file, science field or detailed
   original log ever becomes an Actions artifact.

Triggers are restricted to `workflow_dispatch` on `main`, or
the existing GitHub owner `RRain001` commenting on **Issue #54**
exactly `/cteas-p1-original-90m` or
`/cteas-p1-original-30m`. Normal PR CI only exercises no-data,
no-original-source negative contracts.

**Scientific gate:** A passing execution may produce
`NUMERIC_PASS_PROVISIONAL`. It does **not** by itself verify
source-product versions, original distribution licensing, arbitrary
UTM domains or independently accept P1 physics for every model
option. Contradictions, differing CSV/Fortran hit counts or failure
to decode the selected TIFF remain explicit **BLOCKED/FAIL**; the
test must not silently re-encode TIFF, change datasets or relax
the original benchmark tolerance. #54 D4 independent scientific
audit is still required before closing.
