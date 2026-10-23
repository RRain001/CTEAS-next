# CTEAS-next Actions policy — Ubuntu-first, manual cloud dispatch (2026-10-23)

The owner's 2026-10-23 decision supersedes the 2026-10-19 event-triggered
science execution policy. **GitHub Actions workflows must only declare
`workflow_dispatch`**. No automatic `push`, `pull_request`, scheduled or
`issue_comment` workflow launches. The separate, formerly supported
Issue-comment brokerage workflows have been retired; posting a
`/cteas run ...` Issue comment no longer launches CI.

## Default development and testing

- ChatGPT edits source and tests directly in isolated Ubuntu Git worktrees.
- Ubuntu `/home/lhy/dev/bin/local-ci` supplies local Docker smoke/full and
  scoped scientific readiness checks. Use exact source SHA, environment,
  input checksums and actual exit codes; never relabel `PARTIAL` as PASS.
- Pushing a branch or opening/updating a PR records changes **without**
  automatically launching cloud tests. GitHub CI is optional to dispatch,
  but all existing *scientific acceptance requirements* remain mandatory
  before making a claim of scientific equivalence or merging any change
  for which a project-level strict gate applies.
- Use GitHub UI Actions > select workflow > Run workflow, or the authenticated
  CLI: `gh workflow run <workflow-file>.yml --repo RRain001/CTEAS-next --ref <branch>`.
  Agents may run this with explicit task authority. Distinguish submission
  from successful completion by checking run ID, job exit and evidence.
- `workflow_dispatch` is an actual manual API/UI trigger and **does not**
  mean a test runs automatically after a PR is opened.

## Guardrails and history

- The previously deployed comment-to-workflow dispatcher and five
  issue-specific Issue-comment bridges are removed. For science runs,
  trigger the underlying reviewed workflow directly with any allowed
  inputs; do not recreate owner-comment launch hooks.
- Workflows previously reading an immutable pull-request event SHA need a
  genuine manually-selected `github.sha` reference. Use a fixed branch/SHA
  and record it. Do not treat an arbitrary manual run on `main` as proof
  that an unrelated PR head was verified.
- Existing same-input scientific comparisons, original Fortran provenance,
  model-specific tolerances, review, licenses, and data access controls
  are unchanged. Do not use synthetic data to claim external verification.
- Sensitive original-model science workflows should normally run on
  trusted `main`, subject to their existing in-job admissions. Historical
  published test/PR/Issue evidence and numerical outcomes are unaffected.
- GitHub workflow changes take effect on the default branch **only after
  the reviewed PR is merged**. Prior open PRs and already queued/running
  jobs are not retroactively changed.
- Release, asset publication and branch-maintenance workflows retain
  their existing job-level safeguards; manual dispatch is not permission
  to bypass release approval or restrictions.

This policy changes execution scheduling only; it neither disables nor
weakens any numerical, conservation or independent-science gate.
