# P7 WROUT1 header reconstruction and AVET audit — updated 2026-10-13

Selected frozen case: `hefei5km_2022_reference_case_20261011`, METFM=1, MWET=0, 143 hours, 50×50 receptor sampling grid. This document distinguishes **complete header byte parity** from **unaccepted concentration-value parity**.

## Confirmed native-header acceptance

Frozen original `puff.con`: 1,896,056 bytes, SHA256 `0d51bdb68ff1a5798048bc41067107d3ffe10dc6222f25336df856bcbf48ba10`, **3,655** sequential-unformatted Fortran records.

The original record sequence is now classified and entirely source-reconstructed up to the first data record:

| Section | Records | Native source of record bodies | Acceptance |
|---|---:|---|---|
| CONC.DAT version and embedded-comment count | 2 | CALPUFF WROUT1 v7.0 header + computed comment count | BITWISE PASS |
| Embedded 132-byte comments | 3,218 | 2 CALPUFF/COORDLIB provenance lines + all 2,098 raw `puff.inp` lines + 3 separator lines + source `MET.DAT` 96-byte identity + 1,114 original MET header comments | BITWISE PASS |
| General run parameters | 1 × 300 B | Typed C++ serialization in original `WROUT1` L57177–57183 order, selected deck and metre-precision MET grid origin | BITWISE PASS |
| Source-type counts | 1 × 52 B | Original 13 `INTEGER*4` source-type counts; 1 point source | BITWISE PASS |
| Run title / H-3 / Bq/m3 / HTO_STACK | 4 (240/15/16/20 B) | Selected deck titles and native typed metadata | BITWISE PASS |
| 143 hourly period/TOTAL/H-3 fields | 429 | Independently computed native receptor fields **still required** | **NOT ACCEPTED** |

Thus the **first 3,226 records are byte-for-byte equivalent** to the pinned original, as checked by [GitHub-hosted Ubuntu Actions #38383774781](https://github.com/RRain001/CTEAS/actions/runs/38383774781), test `cteas_p7e_original_wrout1_full_native_header` PASS. All headers are reconstituted from input/source metadata. The C++ output path does **not** copy the original `puff.con` header.

The 1,118 lines beyond the direct `puff.inp` echo were isolated and their provenance confirmed: 4 MET separators/identity lines and **1,114** contiguous 132-byte comment records read directly from pinned original `MET.DAT`. The CALMET source SHA256 is `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30`. Binary audits also confirm `WROUT1` L57127–57275 ordering. The historical estimate that **3,224 independent header records were missing** was incorrect and has been withdrawn.

**Important scope:** This is an exact header test for the **selected frozen 2022 configuration** and its specified CALPUFF version, COORDLIB version, WGS-84 datum epoch, original station count and metre-precision MET origin. Other CALPUFF configurations require parameter/source-deck audit before claiming compatibility. The native writer still needs to be plugged into the genuine source-ordered full-case driver to produce the final 429 original numerical records.

## AVET and physical completeness

Here `AVET=PGTIME=60 min`, so the PG sigma-y averaging factor is exactly 1. This does **not** eliminate hourly CALCPF receptor accumulation or justify zero/nonphysical output. Complete P7 acceptance still requires native persistent `POINTS1→COMP→PUFRECS/VCBAR/CALCPF` behavior, dry-case mass bookkeeping, and true 1h, 6h and 143h original concentration-value equivalence.

**Status: WROUT1 HEADER = PASS; FULL REAL 143h puff.con AND P7 FINAL = OPEN.**
