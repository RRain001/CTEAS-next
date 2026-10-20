# P2 #123 D11 — opt-in C++ ORIGINAL_SAMPLING standalone LU.DAT producer

Date: 2026-10-20. Source-level physics reference: CTGPROC v7.0.0 `ctgproc.for`, pinned original CTEAS commit `dfad99a78ed84d655e21411c9d25eb0d2583bf13`, source SHA256 `719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281`.

## Previously authentic science-verified

[Run #39344388008](https://github.com/RRain001/CTEAS-next/actions/runs/39344388008), [Artifact #12229939690](https://github.com/RRain001/CTEAS-next/actions/runs/39344388008/artifacts/12229939690), repository `main@909ff3ad`: D6 original Full shoreline BLN original SHA `67da93d441e7defe3eb46627ed9ce896c0a91ffd89fd5e4363d834d8108e11f9`; D8 42,863 original Fortran vs C++ IPTYPE points zero mismatch; D9 1,520,000 integer hits zero mismatch, total 40,025, nonempty 37,035; D10 second independent original LFINAL=T program output 1,520,000 F6.3 fractions and 40,000 missing flags zero mismatch, same regenerated BLN SHA. Original GNU STREAM/EOF I/O adaptations remain disclosed.

## D11 output interface and exact scope

Dedicated standalone executable `cteas_p2_original_sampling_wolsong`:

```bash
cteas_p2_original_sampling_wolsong \
  /path/to/eausgs2_0la.img \
  /path/to/GENUINE_ORIGINAL_COASTRD/coast.bln \
  /path/to/NEW_OUTPUT_DIRECTORY
```

- Independent C++ GLCC direct-LAEA historical 38-USGS-class source-mesh reading plus original BLN/REAL*4 original IPTYPE, original LUGRID marine category swap, SVGRID real4 divisions, 38-category F6.3 LU.DAT version 2.1 rows, exact per-cell `Missing` flags.
- **Fail-closed Wolsong-only** UTM52N 200×200 100m, xref 533.215 km yref 3942.629 km, MESHGLAZ=10; historical GLCC source `4f2a1977c6a70d74f7a0e136bdd4aa1777dc9cbab15c184e7f483f772cd266c6`, exact genuine original BLN `67da93d441e7defe3eb46627ed9ce896c0a91ffd89fd5e4363d834d8108e11f9`, Full only, LCOAST=T LMARSWAP=T LMARFILL=F, IOCEAN55. No source or BLN bytes bundled; caller must obtain legitimate inputs independently. Explicit new output directory, no in-place overwrite.
- Output `lu.dat` plus `p2_original_sampling_manifest.json` with dataset and file SHAs, method discriminator, original vendor reference, Wolsong scope, all 40,000 grid cells, 40,025 total sample HITS, 37,035 nonempty and 2,965 missing cells. Writer never changes P2-A or P2-B `EXACT_AREA_V1`.
- Standalone `lu.dat` header has independent producer comments and is **not expected to be byte-identical** to original CTGPROC header. The 38 F6.3 fields, indices, missing flags, physical grid metadata and 38 category IDs **must be independently identical**.
- Production-created status alone is `PRODUCED_VERIFIED_SOURCE_NOT_EXTERNAL_SCIENCE`, never scientific PASS by assertion. D11 authentic science gate recomputes C++ output from exact GLCC/BLN and compares every printed field/flag directly against the **separately executed** source-pinned original `LFINAL=T` LU.DAT; D6-D10 report + actual output SHAs required. Only actual SHA-audited Run and result artifact can establish D11 PASS.

## Deliberate non-goals

No Antarctica, no GSHHG High alternative, no untested L2-L4 nesting, `LMARFILL=T`, generic GLC_FCS30D input or other controls. Nothing in this D11 PR declares generic original CTGPROC full reimplementation, automatic P3 success or P6/P7 original-option parity. Close #123 only after real D11 production-run result, launchable CLI docs and independent scientific acceptance are reviewed; future geographic/input extension needs a different explicit scope and authentic original comparison.
