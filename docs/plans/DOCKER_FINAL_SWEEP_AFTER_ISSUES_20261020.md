# Final Docker consolidation — deferred by user (2026-10-20)

**Trigger:** start **only after all remaining CTEAS-next development Issues are closed**. Docker is not a condition for closing Issue #168, for merging PR #170, nor for moving on to S2–S5. This file is a documented final-stage backlog, **not** a scheduled background task or current scientific PASS.

## Existing evidence and blocker

- [Issue #168](https://github.com/RRain001/CTEAS-next/issues/168), [PR #170](https://github.com/RRain001/CTEAS-next/pull/170) retired the P2-B exact-area CLI/core and repointed static Dockerfile copy list to P2-C original-style 30 m source-pixel 10x10 point producer. **No multi-architecture runtime PASS is claimed**.
- [AMD64/ARM64 Docker attempts #39373264635](https://github.com/RRain001/CTEAS-next/actions/runs/39373264635) failed in the **existing P7 configure source-provenance gate**. P7 CMake requires `git rev-parse HEAD`; `.dockerignore` intentionally excludes `/.git`. Do not satisfy this using guessed strings, weakened P7 admission, or unintentionally copying repository secrets into a final image.
- [Diagnostic check #39373745832](https://github.com/RRain001/CTEAS-next/actions/runs/39373745832) verified standalone P7 configuration works with .git present, but the normal full Docker runtime stage still fails. This is packaging provenance, not P2 numerical parity evidence.
- The independent authentic P2-A Hefei / P2-C Hefei and Wolsong 40,000 × 38 scientific regressions remained PASS on PR #170 before Docker deferral; artifacts in the S1 audit.

## Final-stage acceptance checklist

- [ ] Design auditable **gitless** build provenance: authenticated 40-character Git SHA from source checkout, strongly bound to copied source tree and image metadata. No unverified user-provided commit substitute; keep CALPUFF physical options / current code unchanged.
- [ ] Keep original third-party vendor assets and legally restricted datasets **outside** distributed images. Inspect build context and image layers, not only `.dockerignore`.
- [ ] AMD64 runtime image builds and includes retained P2-A GLCC and P2-C point-sampling CLIs; retired B CLIs/kernels are absent.
- [ ] ARM64 same checks; check dynamic library linkage, GDAL/PROJ, entrypoint and minimal P2-A/C controlled smoke.
- [ ] Re-run verification target / portable regression and source-SHA policy, and confirm other active P1–P7 standalone CLI tools are not broken by image changes.
- [ ] Record actual run URL, exact source commit, image digest, architectures, logs and artifacts. Document which numerical science gates were **not** rerun.
- [ ] Handle all other Docker build/test/deployment issues **together** in this final pass. Do not reactivate automatic Docker PR checks prematurely.

This backlog intentionally creates no new open Issue that would circularly prevent the requested "after all Issues are closed" trigger.
