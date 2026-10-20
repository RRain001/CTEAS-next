# Issue #40: S4-B4 opt-in single-station selected COMP numerical probe

Date: 2026-10-20. This PR **is not** a C1 science acceptance. Previously, [PR #204](https://github.com/RRain001/CTEAS-next/pull/204) established authentic C1 1SS+1US source admission and identified the hard-coded `G18A` **test-only** cardinality guard as the first blocked physical stage (not an intrinsic original CALMET station minimum).

The original C1 2022 CALMET run itself used 1 SS and 1 US, while C2's controlled 2SS+2US was already original-CALMET benchmarked. The inspected selected G18A MIXHT grid and station loops are cardinality-driven: input sizes are checked against `frame.stations.upper.size()`, and each genuine STHEOR station is mapped to its original upper ordinal and unique cell. There is no 2-station formula in G18A: only the entry-guard `size()<2`. This evidence permits an **experiment**, not a blanket science acceptance.

- A new `allow_one_one_source_audit` boolean on G18A controls defaults false.
- Only genuine source-backed selected `G26B` COMP, with **exactly 1 SS + 1 US**, sets the opt-in. Existing C2 2SS+2US path is unchanged; 0 station, 1/2 and 2/1 retain previous controls/validation (those asymmetries remain S4-C).
- No physical formula, REAL4 arithmetic, PREPDI, station mapping, original source records, K-dimension, output serializer, G26 production `Unknown,false` or other stage-control is changed.
- Live CI compiles the same G14 actor, uses original frozen 143h C1 source with its full real 00/12 upper archive, executes **only first causal selected hour**, and requires actual original-format P6F candidate. The candidate is `PRODUCED_UNVERIFIED` until compared with the original independently.
- Rejects production without `--selected-experimental` and extra duplicate UP file. The old C2 vs same-shared-actor 6h 270-field SHA comparison is a separate mandatory PR regression.

If runtime rejects a different original physical assumption, stop and report it; do not bypass blindly. If first-hour physics computes, next require field-by-field C1 frozen original 45-field first-hour comparisons and initial COMP `ZI/ZICONV/DPTT` history parity **before** longer runs, and C2 unchanged regression. Status remains `S4_P6_NEW_SITE_SCIENCE=NOT_ACCEPTED`, `S4_C1_C2_SHARED_143H=NOT_RUN`. P7, rainfall and S5 excluded.
