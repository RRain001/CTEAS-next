#!/usr/bin/env python3
"""Fail closed if any executable CTEAS Actions job needs a retired local runner."""
from __future__ import annotations

from pathlib import Path
import sys
import yaml

root = Path(".github/workflows")
paths = sorted((*root.glob("*.yml"), *root.glob("*.yaml")))
failures: list[str] = []
count = 0
for path in paths:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(workflow, dict):
        failures.append(f"{path}: missing YAML workflow mapping")
        continue
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        failures.append(f"{path}: missing jobs mapping")
        continue
    for name, job in jobs.items():
        count += 1
        if not isinstance(job, dict):
            failures.append(f"{path}:{name}: job must be a mapping")
            continue
        runner = job.get("runs-on")
        if runner is None and "uses" in job:  # legitimate reusable workflow
            continue
        if not isinstance(runner, str) or not runner.startswith(
            ("ubuntu-", "windows-", "macos-")
        ):
            failures.append(
                f"{path}:{name}: non-GitHub-hosted/unknown runs-on={runner!r}"
            )
if len(paths) < 70:
    failures.append(f"Expected >=70 tracked workflows, found {len(paths)}")
# P7 long-running numerical gates must remain wired to the merged target branch.
# PyYAML SafeLoader follows YAML 1.1 and can decode the literal "on" key as True.
p7_base = "codex/cteas-p7-calpuff-20261011"
for filename in (
    "p7-hefei-real-hour7-probe.yml",
    "p7-hefei-real-143h-independent-probe.yml",
):
    path = root / filename
    if not path.is_file():
        failures.append(f"{path}: required P7 scientific workflow is missing")
        continue
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(workflow, dict):
        failures.append(f"{path}: invalid workflow mapping")
        continue
    events = workflow.get("on", workflow.get(True))
    if not isinstance(events, dict):
        failures.append(f"{path}: invalid/missing GitHub event triggers")
        continue
    for event in ("pull_request", "push"):
        settings = events.get(event)
        if not isinstance(settings, dict):
            failures.append(f"{path}: missing {event} trigger")
            continue
        branches = settings.get("branches", [])
        paths_filter = settings.get("paths", [])
        if not isinstance(branches, list) or not {"main", p7_base}.issubset(set(branches)):
            failures.append(f"{path}: {event} must include main and P7 historical target {p7_base}")
        if not isinstance(paths_filter, list) or not {
            "native_cpp/modules/p7_calpuff/**", ".github/workflows/" + filename
        }.issubset(set(paths_filter)):
            failures.append(f"{path}: {event} must include P7 code and gate YAML in paths")
        if isinstance(paths_filter, list) and "docs/reconstruction_cpp/**" in paths_filter:
            failures.append(f"{path}: {event} must not rerun expensive science for docs-only edits")
    if "workflow_dispatch" not in events:
        failures.append(f"{path}: missing manual workflow_dispatch trigger")
# The coupled C2 science job must run whenever integrated P6 or P7 changes on main.
c2_name = "integration-p1-p7-143h-science.yml"
c2_path = root / c2_name
if not c2_path.is_file():
    failures.append(f"{c2_path}: required unified P6/P7 C2 scientific gate is missing")
else:
    c2_yaml = yaml.safe_load(c2_path.read_text(encoding="utf-8"))
    c2_events = c2_yaml.get("on", c2_yaml.get(True)) if isinstance(c2_yaml, dict) else None
    for event in ("pull_request", "push"):
        opts = c2_events.get(event) if isinstance(c2_events, dict) else None
        branches = opts.get("branches", []) if isinstance(opts, dict) else []
        paths = opts.get("paths", []) if isinstance(opts, dict) else []
        required_paths = {
            f".github/workflows/{c2_name}",
            "native_cpp/modules/p6_calmet/**",
            "native_cpp/modules/p7_calpuff/**",
        }
        if not isinstance(branches, list) or "main" not in branches:
            failures.append(f"{c2_path}: {event} must include main")
        if not isinstance(paths, list) or not required_paths.issubset(set(paths)):
            failures.append(f"{c2_path}: {event} must cover both P6 and P7 and gate YAML")

if failures:
    for failure in failures:
        print("HOSTED_RUNNER_POLICY_BLOCKED " + failure, file=sys.stderr)
    raise SystemExit(1)
print(
    f"CTEAS_GITHUB_HOSTED_RUNNER_POLICY=PASS WORKFLOWS={len(paths)}"
    f" JOBS={count} SELF_HOSTED=0"
)
