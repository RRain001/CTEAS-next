# Remote Migration Runbook

## Target

- SSH host: `lhy-desktop`
- Remote root: `/home/lhy/CTEAS`
- Remote role: primary development and compute host
- Local role: backup copy only

## Scope

- Keep GUI code and GUI assets in the repo sync.
- Reuse `bin/linux-x86_64/*.x` on the first migration.
- Do not copy local `.venv`.
- Do not install or validate Docker for this migration.

## Local Dirty State Handling

Current migration flow assumes:

- tracked deletions such as `WEBGUI_USAGE.md` and `建议.md` are mirrored only on the final cutover sync
- untracked local `plan.md` stays local and is excluded from sync

If new untracked scratch files appear, add them to the sync exclude set before cutover.

## Commands

Run these commands from the repository root. `REMOTE_HOST` and `REMOTE_DIR`
remain configurable through environment variables.

Pre-sync remote bootstrap:

```bash
./scripts/bootstrap_remote_host.sh pre-sync
```

Warmup sync:

```bash
./scripts/sync_to_lhy_desktop.sh warmup
```

Warmup uploads files without enabling `rsync --delete`.

Remote venv bootstrap:

```bash
./scripts/bootstrap_remote_host.sh post-sync
```

Remote verification:

```bash
./scripts/bootstrap_remote_host.sh verify
```

Final cutover sync:

```bash
CONFIRM_CUTOVER_DELETE=1 ./scripts/sync_to_lhy_desktop.sh cutover
```

Cutover enables `rsync --delete` and may remove remote files that are not
present locally. Use it only when the local working tree is the intended source
of truth for the remote destination.

`bootstrap_remote_host.sh` may run `sudo apt-get`, `uv python install`, and
`.venv` setup on the remote host depending on the selected mode.

## Expected Verification

- `/home/lhy/CTEAS/.venv/bin/python -V` reports `3.11.x`
- `scripts/check_current_case.py` passes
- `scripts/check_native_binaries.py --platform linux-x86_64` passes
- `scripts/check_native_runner_mapping.py --platform linux-x86_64` passes
- `python -m engine.run_met.prepare_met --case smoke5d_docker_test` passes
- `python -m engine.run_puff.prepare_puff --case smoke5d_docker_test` passes
- `import engine.gui.workbench, engine.ui.desktop.main` passes

## Notes

- In this migration, the old `/home/lhy/project/tutorial` path is not
  recreated.
- Docker scripts remain in the repository as historical build assets only.
