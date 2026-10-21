# Issue #40 — S4-F scoped G26/G26B normal-call production-admission trial

Date: 2026-10-21. Based on the single already original-validated G14 17-stage selected physical actor and merged #215/#219/#220/#221. **This PR does not release a production solver**.

## Motivation and change

Current native G26 DIAGNO `G26SourceFileBackedG14DiagnoBridge::run()` and G26B COMP `G26BSourceFileBackedCompBridge::run()` always return `Unknown,false`; all accepted original-model physics is invoked through `run_selected(stage,frame,true)` within the **same** G14 17-stage actor. Therefore each separate selected experiment can be scientifically correct but the normal `MultiHourPhysics::run` adapter route is still not exercised.

A narrow opt-in **trial of the normal interface**, from the existing `cteas_p6g_s4b2_unified_selected` binary only, adds `--g26-normal-entry-trial`. The pre-existing mandatory `--selected-experimental` flag, G19 source-control reader, legal source station IDs, S4B1 shape checks, G14 causal stage sequence, G26 and G26B per-stage physical kernels, clock publishing, COMP historical memory, original P6F 45-field writer and final `PRODUCTION_ADMISSION=NOT_ACCEPTED` all remain intact.

With no opt-in, `G26::run()` and `G26B::run()` **still return `Unknown,false`**. With explicit source-backed opt-in, the normal `run(stage,frame)` methods dispatch to the EXACT same already selected and vetted physical stage method, guarded by the same existing `run_selected(stage,frame,true)` source, clock, order, and selected-option preconditions. This is a controlled software interface migration trial, **not a second model**, no new physical branch and no broader CALMET option support.

## Independent regression gates

1. Same original C2 2SS/2US 6-hour input: selected G14, opt-in normal G26/G26B and accepted old C2 output must be **byte-for-byte identical**, with forbidden missing opt-in and output collision negative gates.
2. C2 143-hour 12×12×9: normal-call trial 143h MET byte-for-byte identical to single unified G14 selected MET, which independently passes *fresh unchanged original CALMET* 143×45-field P6E zero exceedance.
3. Original controlled 20SS/20US, 20SS/1US and 1SS/20US: compare opt-in normal entry 1h/6h MET with selected branch bytes, then independently fresh-run original CALMET 45 fields for the same source, no station hard cap introduced.
4. Genuine observed NOAA Huoshan 100×100×9 1SS/1US: opt-in normal 6h MET must match accepted selected G14 byte-for-byte, and same PR exact-head independently reruns unchanged original CALMET and compares all 270 field-hour groups zero exceedance.
5. Existing source/clock/record budget CTest and G26 default refusal remain PASS; no accepted science with mismatched source SHAs.

Only after the exact final PR SHA passes all gates may this **trial** be merged as `S4F_G26_NORMAL_INTERFACE_TRIAL=PASS_SOFTWARE_AND_SCOPED_PARITY`. Normal default production remains disabled and `#40` stays open pending an explicitly approved production authority and independent full true multi-observation-site CALMET original science. No P7/G5 release, no precipitation, Docker or S5.

## Precise exclusions

The `run()` trial deliberately delegates to existing selected `run_selected(...,true)`, which still carries option-specific experimental admission; this is a **migration test of interface reachability**, NOT a claim all selected kernels are production certified. Output remains `PRODUCED_UNVERIFIED` until the independent original comparison, and no `production` CLI flag exists.
