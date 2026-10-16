# CTEAS-next

Clean-history successor workspace for the CTEAS P1–P7 C++20 reconstruction.

This repository is **private** and initially contains only this bootstrap note. The original research repository remains at [RRain001/CTEAS](https://github.com/RRain001/CTEAS), with its full Git history, pull requests, original scientific evidence, and archival branches preserved.

## Source provenance

- Source repository: `RRain001/CTEAS`
- Starting reviewed integration commit: `dfad99a78ed84d655e21411c9d25eb0d2583bf13` (merged PR [#75](https://github.com/RRain001/CTEAS/pull/75)).
- The Ubuntu implementer must fetch `origin/main`, record the actual upstream SHA, and explicitly report any difference from the above reference before migration.
- The first code migration must use a **tracked-file export of the exact source revision**, not a copy of the old `.git` history or a local working tree containing untracked files.

## Scientific scope

A clean Git history **does not** recertify physics. Existing reference-case P6/P7 143-hour acceptance and its limitations must remain explicit. Generic P6/P7 runs, arbitrary sites and periods, and full G5 P1–P7 native execution are not automatically accepted. No silent fallback to old Fortran in a new claimed-native execution path.

## Working agreement

- ChatGPT: plan, independently review code/evidence, report decisions in pull requests.
- Ubuntu Codex: implement, run real builds/tests, push branches, post logs and blockers on its PR.
- Initial migration: use a feature branch and **Draft PR** against `main`; do not directly overwrite this bootstrap baseline.
- Do not copy secrets, temporary outputs, caches, virtual environments, compiled binaries, or `.git`.
- Review font redistribution rights, third-party vendor licensing, and test data provenance before copying bundled assets into the new repository; retain required verification dependencies with explicit notices, and report any exclusion that breaks a test.
- Do not modify accepted physics or numerical thresholds as part of history cleanup. Preserve the old CTEAS repository intact.

See the initial migration issue for the staged execution contract.
