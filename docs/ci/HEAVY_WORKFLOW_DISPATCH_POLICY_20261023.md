# Heavy scientific workflow dispatch policy (2026-10-23)

This is an **execution-trigger** optimization, not a scientific acceptance or physics change. For the 23 workflows listed in the accompanying change, `pull_request` and/or `push` triggers were removed while preserving `workflow_dispatch`, their existing jobs, commands, checks, constraints, permissions, and numerical thresholds. Scientific evidence and option-specific acceptance remain mandatory for science-related PRs. The normal GitHub PR `repository-admission` and `scientific-admission` checks still run automatically.

## Selection and safety

- Selected only current-main workflows with a configured maximum job timeout of at least 60 minutes, or a frozen C1/C2 143h trigger, and an automatic PR/push trigger.
- Workflows referring directly to `github.event.pull_request`, `github.head_ref`, `pull_request.number` or PR-only `event_name` conditions were **left unchanged**. Eleven such long-timeout workflows require a separate safe migration with explicit PR/SHA inputs; changing their trigger alone would break their event contexts.
- Job definitions were compared structurally before/after migration. No test, threshold, model source, job, or artifact was deleted.
- The timeout is a *maximum configured duration*, not measured runtime. It is used only to identify workflows suitable for explicit dispatch.

## Execution and merging

The agent, not the user, may call GitHub's `workflow_dispatch` API on the reviewed candidate PR branch/ref, or use the project-approved owner/agent science dispatcher. Record exact resolved commit SHA, workflow ID, input hashes, completion and the true PASS/FAIL/NOT_RUN verdict. Dispatching a branch name is not evidence of an immutable run unless the resulting run head SHA is independently verified. For missing sources or scientific review, keep the PR Draft and fail closed. The independent science review condition and local Ubuntu Docker exact-HEAD status remain mandatory. Never interpret a skipped heavy Action as scientific acceptance.

The 23 modified workflow filenames and original event types are recorded outside Git in `/home/lhy/dev/reports/ci-gates-20261023/heavy-dispatch-migration.tsv` for local operator traceability.
