# CTEAS-next science execution: project-wide 2026-10-19 owner decision

This supersedes every historical project rule requiring the repository owner
to personally click "Run workflow" for full/original/scientific validation.
The manual-only execution restriction is REVOKED PROJECT-WIDE. Agents,
authorized CI and GitHub Actions may dispatch science runs as needed.

Older comments and names containing "manual only" are historical labels,
not a prohibition on authorized software dispatch. Keep scientific
acceptance criteria unchanged.

## Authorized ways to launch
1. An authenticated repository-owner Issue comment on any OPEN non-PR Issue:
   /cteas run issue123-original-binary-full-manual.yml
   /cteas run issue119-wolsong-p2b-real-coast.yml validation_scope=full_p2b
   /cteas run issue84-noaa-source-screen.yml years=2023,2024 max_nearest=6
   This fires the issue_comment Actions dispatcher, which calls GitHub's
   workflow_dispatch API on trusted main. Connected agents posting as the
   authorized repository owner can use this route. No owner UI click needed.
2. Actions-write credentials, gh workflow run, CI automation and supported
   GitHub App dispatch methods can also call the target workflow_dispatch
   directly, subject to actual connector/tool write capabilities.
3. Individual workflows can use automatic event triggers where relevant
   (push, PR, workflow_run, schedule). Do not blindly fan out all
   expensive 143-hour cases on every main push.

## Safeguards preserved
- The dispatcher accepts only approved science/build workflow filenames
  registered as ACTIVE, bound to main. No user-provided branch or shell.
- Commands must be from RRain001 on an open Issue with OWNER association;
  untrusted users, PR comments, invalid command grammar and unknown
  workflows are rejected.
- Maintenance branch deletion, release publication, bootstrap, and other
  state-changing workflows are excluded from this science dispatcher,
  while still able to use separate authorized execution routes.
- The dispatcher blocks duplicate queued/running target workflows on main.
  Resource/runner limits and concurrency are still enforced. Do not
  pointlessly repeat an already validated expensive same-SHA/input case.
- Source SHA and dataset manifests, legitimate original data input,
  Fortran/C++ numeric parity, tolerances, and audit artifacts remain
  hard scientific acceptance requirements. The dispatcher succeeding is
  not the same as the scientific run passing.
- A workflow retaining the workflow_dispatch YAML event is an API
  dispatch endpoint, not a human-only execution requirement.

## Scope
Applies to P1-P7, Wolsong #119/#123, P3 #46, P5 #84, C1/C2, and
future workflows. Does not change the Wolsong GSHHG Full-only
EXACT_AREA_V1 frozen methodology, physical options, or science
NOT_RUN assessments.

Do not claim all workflows were run, or that a connector can directly
call workflow_dispatch where no such action is available; use the issue
comment broker and inspect the downstream run in that case.
