# Original source and provisional controls audit

Read-only authority: `RRain001/CTEAS@66e30ffb1ff4638a97af8a060748ce30b7578350`. Git **blob** SHAs below are not whole-tree hashes; whole trees and build flags remain to be frozen with reference runs.

| Stage | Primary Fortran source (Git blob SHA) | Bundled sample control (Git blob SHA) |
|---|---|---|
| P1 TERREL | `terrel.for` `abace38a0b51deef6ed521b38c416855236af1f2` | `terrel.inp` `5dfa5994bd04cb6706d8ff90c7a66ad3c54025cc` |
| P2 CTGPROC | `ctgproc.for` `9d065735667c2ef0aa170c3e9709d4c01fb6df27` | `ctgproc.inp` `ff5d1612c69d405b0c3e4bc1952e9506d5bbcfca` |
| P3 MAKEGEO | `makegeo.for` `9dde69f22eabad04907a7ae6545d881183d8f523` | `makegeo.inp` `49fec849e965d4f717a2995975e752380fa74761` |
| P4 READ62 | `READ62.FOR` `2de05fbeb32cc3aca731a9e89b0a0889c6cafab9` | `read62.inp` `5363fad287c68d32cf7f9691ca7ff173f59b6261` |
| P5 SMERGE | `SMERGE.FOR` `a4315036dae437977d9c90ab5abbb8b8085018d5` | `smerge.inp` `01638b034174a27383ed9ec91486253a7365aabe` |
| P6 CALMET | `calmet.for` `437f43bb7f0e51a1919e56664663e1a046986ed0` | `calmet.inp` `8f0a6b6d2150c56d0e3724f3972aed67f7a00fcc` |
| P7 CALPUFF | `calpuff.for` `3ce72291d3ed143f5f59ac3b92ec2faaac5dc208` | `calpuff.inp` `84a5f0bd51df85601c3d7ea90504805eab3150fc` |

## Non-authoritative bundled settings
Bundled `.inp` controls for P1, P2, P3, P6 and P7 are **not** the requested Hefei test case: displayed placeholders include 100 x 100 cells, `DGRIDKM=1` km, and placeholder `XREFKM` or `XORIGKM`. Thus one cannot use them without producing new, provenance-checked controls. CTGPROC sample `DNZGEN=WGS-84`, whereas uploaded GEN points require `DNZGEN=ESR-S`; source control additionally describes `IGRID=1` as the SW **corner** of cell (1,1), versus `IGRID=2` as its center. P6/P7 sample ZFACE values happen to match the requested 9 layers; this is not evidence of a fully matched case.

READ62 and SMERGE sample dates are in 2000, not the 2022 source requirement. None of the seven original executable run configurations, actual met station files or numerical outputs was re-labelled as the 2022 six-day reference.

## CI evidence for first P1/P2 input scope
The initial GitHub-hosted Actions `C++ input contracts` run #2, run id `38041297946`, job `114181911937` on PR #2 commit `e90e0f2aecf2feb32c0e8cb4d7ad9e11faab3e71` **completed SUCCESS**.
- Ubuntu (GitHub hosted), GNU C++ 13.3.0, GDAL 3.8.4, CMake/C++20, warnings `-Wall -Wextra -Wpedantic -Werror`.
- CTest 2/2 PASS: strict synthetic P1 and P2 readers.
- Real committed SRTM crop: `width=90 height=77 valid=6930 missing=0 nodata=-32768`.
- Real GEN point crop: `datum=ESR-S categories=38 points=57600`; 50m point spacing is **not** output grid spacing.
- Independent SHA-256 compared against crop_info.json: SRTM `c4211914fce527d2ad41ecac1e668d7faa2904bbbfd9135868ee83ef0d32123f` PASS; GEN `bd937d99fb13b49ac6185c080359bef050afe76fc63945ac53b7d676547d43dc` PASS.
- This tests raw input identity and parsing; it does not compare 100m processed surface terrain, per-grid land fractions, or original Fortran results.
- CI did **not** invoke the private self-hosted runner and did **not** run original Fortran.

Gate classification: **PASS_SOFTWARE_INPUT_SCOPED** for P1/P2; **BLOCKED_REFERENCE_AND_FULL_PROGRAM** for each of P1–P7; no physics equivalence claim.
