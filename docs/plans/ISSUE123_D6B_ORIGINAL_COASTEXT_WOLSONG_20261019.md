# Issue #123 D6-B — Real original CTGPROC COASTEXT on frozen Wolsong 2022

## Unmodified original and immutable real inputs

- `CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13` original `ctgproc.for`, SHA256 `719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281`, separately checked out in Actions at runtime. Do not vend or upload original vendor code/binary.
- GMT GSHHG v2.3.7 `gshhs_f.b` original binary, exact verified SHA `af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6`, D5 byte-level source contract.
- Official GLCC Eurasia GLAZAS `eausgs2_0la.img` original, 156000000 bytes, SHA256 `4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a`. **Not** GLC2022 mapped to illegal `GENERIC + LCOAST`.
- Frozen Wolsong: EPSG:32652, `XREFKM=533.215`, `YREFKM=3942.629`, `NX=NY=200`, `DGRIDKM=0.100`. Set `LCOAST=T`, `LBLNREAD=F`, `LMARSWAP=T`, `LMARFILL=F`, `IOCEAN=55`, `LFINAL=F`, `MESHGLAZ=10` and original legal GLAZAS.
- No Antarctica study: only Wolsong original coastal outputs are accepted. GSHHS source's far-away level 5/6 records are out of scope.

## D6-B meaning

Compiles **unmodified original** `CTGPROC` Fortran with proven existing include aliases on Ubuntu; original binary runs in isolated temp working dir and produces original `coast.bln`. Audit reads *that output*, not a shapefile imitation, verifies valid `NP,IISIDE,\"ITYPE,ISOURCE,ID\"` BLN records, vertices, closure, Wolsong UTM bounds, source/control/binary and resulting file SHA. Runner publishes **only JSON metadata**; never original code, executable, raw GLCC source, binary shoreline or raw BLN.

- PR only synthetic control and BLN file-format tests. On merged `main`, path-scoped push automatically runs genuine original, or authorized GitHub dispatch can run it directly.
- Success of authentic `COASTEXT` means only `D6B_UNMODIFIED_ORIGINAL_COASTEXT_GENERATED_BLN_SCOPED`. It is **not** C++ equality.
- If original runtime fails, has no BLN, bad format or wrong coordinates, fail closed; preserve failure reason in Actions logs and rerun after targeted correction.

## Next acceptance

1. Feed the same real original BLN (not reconstructed geometry) and matched REAL*4 sample points to original Fortran `IPTYPE` and C++ `OriginalBlnIptypeR4`. Require exact integer agreement for every original sample including shoreline edge and surrounding cases. This must have a separate actual scientific run.
2. Finally compare authentic `LFINAL=F` 200×200×38 original integer HITS and `LFINAL=T` displayed fractions against C++ identical original-source sampling; preserve 52/55/54 and marine swap/fill cases. No `EXACT_AREA_V1` rewriting, #119 remains frozen.
3. Issue #123 remains OPEN; passing software CI or even original output generation never implies full original vs C++ parity.
