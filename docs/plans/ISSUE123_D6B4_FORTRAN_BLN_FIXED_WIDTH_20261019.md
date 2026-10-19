# Issue #123 D6-B4 — Original Fortran BLN fixed-width header admission

## Genuine result after D6-B3 split I/O

[Run #39283528976](https://github.com/RRain001/CTEAS-next/actions/runs/39283528976), `main@b865e867`, verified the exact original Full GSHHG and GLCC SHA, original CTGPROC source SHA, unchanged DIRECT/RECL=1 for GLCC, and audited GSHHG-only GNU STREAM plus prior BREADH EOF derivative. The previous `READ(IOINP,REC=KCNT)` invalid argument did not recur. The source program completed its execution step with an extant nonempty `coast.bln`, but the independent audit failed **at polygon header zero**:

```text
D6B_FAIL_CLOSED:ValueError:D6B_ORIGINAL_BLN_BAD_HEADER:0
```

No `original_coastext_report.json` was produced and [artifact #12200939972](https://github.com/RRain001/CTEAS-next/actions/runs/39283528976/artifacts/12200939972) contains only original-source and runtime-adapter provenance. Thus D6-B3 removed the preceding I/O failure, but **genuine BLN scientific admission is not yet accepted**.

## Exact source formatting root

The original pinned CTGPROC v7.0.0 `COASTEXT` at `ctgproc.for:6789` has:

```fortran
87      format(i7,',',i1,',"',i1,',',i1,',',i6,'"')
```

The last `I6` produces leading blanks *inside the quoted BLN polygon identifier*, e.g. `      5,0,"1,2,    72"`. The prior Python `BLN_HEADER` regex required the identifier's digits to follow its comma immediately, and therefore **rejected the valid fixed-width original Fortran output**. The original `COASTRD` reads `CPTYPE` using list-directed parsing and permits that padding.

## Bounded change and gate

Only broaden the BLN header regex whitespace acceptance **inside the quoted original fixed-width fields**; retain strict polygon count budget, 0–4 type, 0/1 side flag, integer identifiers, polygon closure, 20km Wolsong UTM52N coordinate envelope, source checks and SHA audit. Add tests for authentic Fortran-style I7/I6 positive/zero/negative identifiers; retain malformed-header rejection. The C++ D4 BLN parser already allows such space before the polygon ID.

The change is **strictly an audit-parser compatibility correction**. It does not mutate original Fortran source, GSHHG Full binary, GLCC, BLN bytes, P2-A, D7, #119 EXACT_AREA_V1 or physics, and does not relax any geometry acceptance threshold.

After focused offline CI and merge, a one-time authentic main-push D6B run should either create an audited `original_coastext_report.json` containing a true original nonempty BLN SHA, polygon counts, class types and bounds, or fail closed on the next real discrepancy. Do **not** count previous nonempty BLN existence alone as original scientific PASS. Full original-vs-C++ same real BLN `IPTYPE` and all 38-class HITS/LU.DAT gates remain independently NOT_RUN; #123 remains OPEN.
