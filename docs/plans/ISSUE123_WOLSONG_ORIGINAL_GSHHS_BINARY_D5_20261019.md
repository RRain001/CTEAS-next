# Issue #123 D5 — Wolsong original GSHHS binary admission (2026-10-19)

## Use the accepted Wolsong geometry
Reuse Wolsong 20 km x 20 km, EPSG:32652, XREFKM=533.215,
YREFKM=3942.629, DGRIDKM=0.100, NX=200 and NY=200.
The plant coordinate is representative, not a verified stack position.

The frozen #119 EXACT_AREA_V1 used GLC_FCS30D 2022 with a
GSHHG Full **shapefile** (L1), and produced a 40,000-cell LU.DAT.
Its data, SHA pins, mapping and acceptance remain unchanged.
That output cannot be labeled ORIGINAL_SAMPLING.

## Why an additional data source is required
Unmodified CTGPROC v7.0.0 COASTEXT calls BREADH/BREADP to read
**GSHHS binary** polygons, projects/clips them and sometimes constructs
surrounding polygons before writing BLN (six-decimal km vertices).
A Full Shapefile alone is NOT proof of identical original extracted
BLN geometry. The original binary and Shapefile are related products,
but original data and transformation provenance must be checked.

## D5 scope: authentic binary input source admission ONLY
- Use the official GSHHG v2.3.7 gshhg-bin-2.3.7.zip from GMT.
- Official archive SHA256:
  28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc
- Extract exactly one gshhs_f.b Full member, refusing missing,
  duplicate, unsupported header or size, symlinks and SHA drift.
- Independently SHA the extracted source and pin archive-member path,
  original header, binary size, archive SHA and extracted binary SHA
  in an audit manifest. The verify step compares extracted bytes to
  the SHA-pinned archive, not just a trusted manifest.
- Neither the original archive nor the binary is committed or
  uploaded. Only source provenance JSON is uploaded as an artifact.
- PR CI uses only synthetic ZIP/header tests. Authentic download and
  extraction occur through authorized owner/agent/CI workflow_dispatch,
  including the project-wide issue-comment dispatcher; an owner UI click
  is no longer required.

Upstream: https://github.com/GenericMappingTools/gshhg-gmt/releases/tag/2.3.7
Unmodified CTGPROC: https://github.com/RRain001/CTEAS/blob/dfad99a78ed84d655e21411c9d25eb0d2583bf13/engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for

## Subsequent real-original acceptance: NOT_RUN
1. Run the **unmodified** original COASTEXT on the authenticated
   gshhs_f.b, with the Wolsong grid and original legal controls.
   Record full original source SHA/compiler flags, input/datum controls,
   BLN SHA, polygon count, ordered type/id/source/vertices, closing
   and artificial surrounding polygon evidence. Do not substitute
   shapefile clipping or synthetic BLN for this original oracle.
2. Use the authentic original BLN and identical original sample-point
   records to compare unmodified original IPTYPE and the C++
   OriginalBlnIptypeR4. Require zero integer point-category differences.
   D4's earlier 568/568 **synthetic** PNPOLY result cannot replace this.
3. A real original LCOAST=T validation also requires an admissible
   historical CTGPROC land-use input such as GLCC/GLAZAS. The frozen
   Wolsong GLC2022 alone is NOT a legal original GENERIC+LCOAST source.
   Pin the original GLCC input and establish real coverage separately.
4. Finally test original-vs-native USGS 38-class integer HITS under
   LFINAL=F and printed LU.DAT fractions under LFINAL=T for the
   same real legal input. Preserve 52/55 mixing, 54 estuary,
   LMARSWAP/LMARFILL and 0-sample behavior.
5. Retain separate GLC2022 EXACT_AREA_V1 and GLCC ORIGINAL_SAMPLING
   methodology and provenance; their fractions are not required to
   match each other.

## Status and separation
Successful D5 source verification means only
D5_AUTHENTIC_GSHHS_FULL_BINARY_SOURCE_VERIFIED.
Real COASTEXT / BLN, IPTYPE, 38-class HITS and LU.DAT original
numerical equivalence remain NOT_RUN. No change to P2-A/P2-B
production, P3 #46 or P6/P7. GSHHG Full only; no High threshold.
All further original science workflows may be dispatched by authorized
agents or guarded CI without the owner clicking Run workflow; see
`docs/ci/SCIENCE_TRIGGER_POLICY.md`. Scientific acceptance gates remain.
Keep Issue #123 OPEN.
