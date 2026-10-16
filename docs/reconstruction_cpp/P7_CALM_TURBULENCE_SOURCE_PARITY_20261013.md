# P7 CALPUFF calm dispersion and turbulence inputs — 2026-10-13

## Scope and original authority

This addition preserves the Draft PR #41 physical-acceptance boundary. It does not change P6, vendor Fortran, the frozen Hefei controls, or the 143 h reference outputs. Original CALPUFF 7.2.1 `calpuff.for` is pinned by `sigma_source_anchor.json` (full original source SHA256 `da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568`).

| Original source | Original semantics | Port / gate |
|---|---|---|
| COMP L10516–10528 | Post-RISEWIND `WSCALM=0.5`, `UCALM=0.001`; not CALMET station-calm processing | `original_comp_calm.hpp`; atomic no-partial-commit test |
| SETPUF L48390–48399 | `LCALM` forces `IDOPTY=IDOPTZ=1`; cancels wake/downwash and XFINAL | `step.cpp` bookkeeping source gate |
| SIGTY L50962–51022 | IDOPTYS=1 lateral Draxler/Irwin with `SIGV/TYIDR` | `original_calm_sigma.hpp` |
| SIGTZ L51458–51573 | IDOPTZS=1 vertical Draxler/Irwin; neutral/unstable closed form and stable iterative log-secant inverse | `original_calm_sigma.hpp` |
| BLOCK DATA L2140, L2144 | `TYIDR=0.001`, `TZIDR=0.002`, `TZISDR=0.01` (s⁻¹), `AYT=0.5` (m/s) | Explicit original defaults, not fitted |
| SETCSIG L52504–52619 | With `MTAULY=0`, no TAULY override; receives upstream TSIGV/W and sets Heffter Y transition | Source inspection workflow |
| TURBSET L52039–52190 | For selected `MDISP=MDISP2=3`, neither SIGWV calculation nor turbulence profile override is active; fallback `SVMIN/SWMIN` by class and land/water | `original_turbset_mdisp3.hpp`, frozen `puff.inp` input gate |
| COMP L10839–10842 | `ILW=2` when current grid `ILANDU` in original `IWAT1..IWAT2`; else 1 | Native current-MET 2,500-cell adapter, fail closed for missing geometry |
| Original MAKEGEO `makegeo.inp` | Frozen 2022 water range `IWAT1=50, IWAT2=55` | Original case control input, not inferred from latitude |

## Independent accepted results

- [Original IDOPT=1 SIGTY/SIGTZ vendor parity #38407647908](https://github.com/RRain001/CTEAS/actions/runs/38407647908): 48 separate controlled cases, 288 output numbers, reported MAX_REL 0 at probe printing precision; both CTests pass. This is kernel-level parity, **not a full CALPUFF run**.
- [Native locked-Hefei SVMIN/SWMIN source gate #38409235549](https://github.com/RRain001/CTEAS/actions/runs/38409235549): all 12 original class × land/water combinations, direct parser input, source time scales; 3/3 CTests pass.
- [Original CALPUFF COMP ILW source inspection #38409431034](https://github.com/RRain001/CTEAS/actions/runs/38409431034): source-proven cell-choice ordering.
- [Full real MET land-use bridge #38410307840](https://github.com/RRain001/CTEAS/actions/runs/38410307840): **SUCCESS, 3/3 CTests PASS**. All 143 original meteorological hours read; across the fixed 50×50 static ILANDU grid the original MAKEGEO water range 50–55 classifies **2,500 LAND cells and 0 WATER cells**. The 2,500 original cells × 6 stability classes yielded **15,000 exact native SVMIN/SWMIN mapping checks**. This proves the selected frozen static domain uses only the original land column, **not** that water physics can be deleted from the general implementation.

## Strict remaining limits

The independently tested IDOPT=1 kernel is **not yet connected into the source-ordered rising COMP solver**. Existing production COMP explicitly rejects `LCALM` before SIGTY/SIGTZ; do **not** remove fail-closed guards simply because the independent kernel passes. Before linking, source-specific JDSTAB, chosen current MET cell and per-substep `TURBSET`, SETCSIG/Heffter initial virtual time, calm `XFINAL`/downwash conversion, `LCALM` minima on stored sigma, and receptor-specific per-step `PUFRECS` state must be transacted together. CALMET static `ILANDU` and MAKEGEO bounds alone are not enough for complete dynamics.

**The original 989 calm puff substeps, real 1h/6h/143h concentration fields, and exact full 3,655-record `puff.con` remain NOT ACCEPTED.** The DGM forensic trace is a comparison oracle only, never native physics input. PR #41 remains Draft and unmerged. GitHub-hosted Ubuntu only.
