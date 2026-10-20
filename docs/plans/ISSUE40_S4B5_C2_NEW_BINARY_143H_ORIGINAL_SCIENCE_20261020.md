# Issue #40 S4-B5 — one new binary C2 original CALMET 143h numerical reacceptance

Prerequisite: S4-B4 new shared G14 1SS/1US C1 1h/6h frozen-original 45-field parity via PR #205, already merged. Before P6 production admission, **the same** `cteas_p6g_s4b2_unified_selected` binary must also pass actual C2 2SS/2US original-vs-native 143h science. The accepted original C2 result is an independently freshly run unchanged CALMET 6.5.0 from controlled-synthetic original-format source, **not** external field observations.

## Scope and unchanged code

The existing purpose-triggered `.github/workflows/science-c2-143h.yml` already:
1. authenticates the exact `main` checkout SHA via `workflow_dispatch` or a single-file agent request, restores unchanged original vendor source at pinned original CTEAS SHA, compiles CALMET and CALPUFF, exports **same** 143h C2 2SS+2US original-format source;
2. freshly executes unchanged original CALMET and the old accepted G34B C2 binary, comparing their original-format 143×45 field outputs;
3. executes P7 four-arm tests independently.

B5 adds **no new physical source**: it builds the newer shared G14 C++ binary in the existing C2 build dir, runs it using the EXACT same five source files, requires byte-exact comparison against the old C2 binary and independent scientific 6435-field comparison against that **fresh** original Fortran `CALMET.DAT`. Captures SHA and JSON verdict as an extra artifact. This specifically verifies **one new binary** for the C2 143h path rather than assuming the B2 6h old-vs-new equality generalizes to 143h.

No automatic 143h on broad PR CI, no changes to P1–P7 formulas, no release of G26 `Unknown,false`, no Huoshan real-new-site claim. B5 should be treated `PASS_C2_UNIFIED_ORIGINAL_FRESH_SCOPED` only if the user/agent-triggered specific science workflow passes *and* exact original/new code SHA and 143×45 JSON are present. The original C1 fresh Fortran run remains not performed (C1 uses the SHA-pinned frozen original). S4-C/D non-Hefei real original parity, asymmetrical sites and dynamic grid, P7 later #36, S5 capacity, Docker, wet deposition remain separate.

## Manual/agent science trigger after merge

Reuse `.github/workflows/science-c2-143h.yml` on `main`. Supported precise agent request branch `automation/science/c2/<unique-run-id>` must contain exactly one changed `.github/science-triggers/c2.request` file whose `SOURCE_SHA=` equals its parent, which must equal current main HEAD. This permits user-authorized agent triggering while preserving strict genuine input SHA and never silently launching full 143h in PR CI.
