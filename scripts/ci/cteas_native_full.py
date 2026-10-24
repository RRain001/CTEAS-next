#!/usr/bin/env python3
"""CTEAS-next exact-commit native Ubuntu software full (not scientific acceptance).

S4/S5 native verification; Docker delivery full is a separate post-S5 milestone.
Do not publish statuses from targeted DEV_ONLY smoke, dirty worktrees, or old SHAs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

PROFILE = "CTEAS_NEXT_NATIVE_FULL_V2"
CONTEXT = "ubuntu-native-full"
REQUIRED = (
    "cmake-configure", "cmake-build", "ctest-all", "s4-python",
    "p1-configure", "p1-build", "p1-ctest",
    "p3-configure", "p3-build", "p3-ctest", "s2g-python",
)


def call(argv: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)


def git(worktree: Path, *args: str) -> str:
    p = call(["git", "-C", str(worktree), *args])
    if p.returncode:
        raise ValueError(f"git {args} failed: {p.stderr.strip()[:300]}")
    return p.stdout.strip()


def clean_sha(worktree: Path) -> str:
    if not (worktree / "native_cpp" / "CMakeLists.txt").is_file():
        raise ValueError("Not a CTEAS-next native_cpp worktree")
    sha = git(worktree, "rev-parse", "HEAD")
    if len(sha) != 40 or git(worktree, "status", "--porcelain=v1", "-uall"):
        raise ValueError("Native full requires a clean committed worktree")
    return sha


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def commands(worktree: Path, build: Path, jobs: int, python: str) -> list[tuple[str, list[str]]]:
    p1_build = build.parent / "build-p1"
    p3_build = build.parent / "build-p3"
    compiler = "-DCMAKE_CXX_COMPILER=/usr/bin/g++-12"
    return [
        # Ubuntu's default g++ 9 cannot compile mandatory C++20 <span>.
        # Pin the same tested GCC 12 compiler as validate_ubuntu.py.
        ("cmake-configure", ["cmake", "-S", str(worktree / "native_cpp"), "-B", str(build),
                             "-DCMAKE_BUILD_TYPE=Release",
                             "-DCMAKE_CXX_COMPILER=/usr/bin/g++-12"]),
        ("cmake-build", ["cmake", "--build", str(build), "--parallel", str(jobs)]),
        ("ctest-all", ["ctest", "--test-dir", str(build), "--output-on-failure",
                       "--parallel", str(jobs)]),
        ("s4-python", [python, "-m", "unittest", "discover", "-s", "scripts/s4",
                       "-p", "test_*.py", "-q"]),
        # S2G tests depend on three independent CMake modules. Build the
        # genuine native programs instead of silently skipping test contracts.
        ("p1-configure", ["cmake", "-S", str(worktree / "native_cpp/p1"),
                          "-B", str(p1_build), "-DCMAKE_BUILD_TYPE=Release", compiler]),
        ("p1-build", ["cmake", "--build", str(p1_build), "--parallel", str(jobs)]),
        ("p1-ctest", ["ctest", "--test-dir", str(p1_build),
                      "--output-on-failure", "--parallel", str(jobs)]),
        ("p3-configure", ["cmake", "-S", str(worktree / "native_cpp/p3"),
                          "-B", str(p3_build), "-DCMAKE_BUILD_TYPE=Release", compiler,
                          "-DPython3_EXECUTABLE=" + python]),
        ("p3-build", ["cmake", "--build", str(p3_build), "--parallel", str(jobs)]),
        ("p3-ctest", ["ctest", "--test-dir", str(p3_build),
                      "--output-on-failure", "--parallel", str(jobs)]),
        ("s2g-python", [python, "-m", "unittest", "discover", "-s", "scripts/s2g/tests",
                        "-p", "test_*.py", "-q"]),
    ]


def step_environment(name: str, build: Path) -> dict[str, str]:
    if name != "s2g-python":
        return {}
    # All executables come from this same frozen source commit and run.
    return {
        "P1_CASE_BINARY": str(build.parent / "build-p1/cteas_p1_terrain_case"),
        "P2_D3_GLCC": str(build / "cteas_p2_glcc_lu_dat"),
        "P12_OLD_ADAPTER": str(build.parent / "build-p3/cteas_p12_to_p3_dat"),
        "P2_GLCC_TEST_DRIVER": str(build / "cteas_p2_glcc_gen_test_driver"),
        "P2_GEN_CLI": str(build / "cteas_p2_gen_fraction"),
        "CXX": "/usr/bin/g++-12",
    }


def save(manifest_file: Path, data: dict) -> None:
    tmp = manifest_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(manifest_file)


def run(worktree: Path, output_root: Path, jobs: int) -> int:
    worktree = worktree.resolve(strict=True)
    if not 1 <= jobs <= 32:
        raise ValueError("jobs must be 1..32")
    sha = clean_sha(worktree)
    if sys.version_info < (3, 11):
        raise ValueError("S4/S5 native Python 3.11+ is required; use the Ubuntu acceptance venv")
    if output_root.resolve() == worktree or worktree in output_root.resolve().parents:
        raise ValueError("Reports must not be inside the source worktree")
    now = dt.datetime.now(dt.timezone.utc)
    run_id = "native-" + now.strftime("%Y%m%dT%H%M%SZ") + "-" + sha[:10]
    report = (output_root.resolve() / run_id)
    report.mkdir(mode=0o700, parents=True, exist_ok=False)
    build = report / "build"
    manifest = report / "manifest.json"
    record = {
        "profile": PROFILE,
        "context": CONTEXT,
        "source_sha": sha,
        "worktree": str(worktree),
        "run_id": run_id,
        "jobs": jobs,
        "python_executable": sys.executable,
        "started_utc": now.isoformat(),
        "status": "RUNNING",
        "exit_code": None,
        "scientific_acceptance": "NOT_RUN",
        "docker_delivery": "DEFERRED_UNTIL_POST_S5",
        "steps": [],
    }
    save(manifest, record)
    for name, command in commands(worktree, build, jobs, sys.executable):
        if clean_sha(worktree) != sha:
            raise ValueError("Worktree changed during native full run")
        print("RUN", name, flush=True)
        log = report / (name + ".log")
        configured = step_environment(name, build)
        env = dict(os.environ)
        if configured:
            env.update(configured)
            # This dedicated S2G acceptance suite is required to test the
            # binaries compiled in the same exact-SHA full build.
            if any(not Path(path).is_file() for key, path in configured.items()
                   if key != "CXX"):
                raise ValueError("Missing native S2G test binary from frozen build")
        with log.open("w", encoding="utf-8") as output:
            output.write("$ " + " ".join(command) + "\n")
            output.flush()
            p = subprocess.run(command, cwd=worktree, env=env, stdout=output,
                               stderr=subprocess.STDOUT, check=False)
        record["steps"].append({
            "name": name, "command": command, "exit_code": p.returncode,
            "environment": configured, "log_sha256": digest(log),
        })
        save(manifest, record)
        if p.returncode:
            record.update(status="FAIL", exit_code=p.returncode,
                          finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
            save(manifest, record)
            print("FAIL", name, "log:", log, flush=True)
            return 1
    if clean_sha(worktree) != sha:
        raise ValueError("Worktree changed during native full run")
    record.update(status="PASS_SOFTWARE_SCOPED", exit_code=0,
                  finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    save(manifest, record)
    print("PASS_SOFTWARE_SCOPED", sha, "manifest:", manifest, flush=True)
    return 0


def verify(manifest: Path, expected_sha: str | None = None) -> dict:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("profile") != PROFILE or data.get("context") != CONTEXT:
        raise ValueError("Wrong evidence profile/context")
    sha = data.get("source_sha")
    if (not isinstance(sha, str) or len(sha) != 40
            or not all(c in "0123456789abcdef" for c in sha)):
        raise ValueError("Invalid full Git source SHA")
    if expected_sha is not None and sha != expected_sha:
        raise ValueError("Manifest and requested PR HEAD differ")
    if data.get("status") != "PASS_SOFTWARE_SCOPED" or data.get("exit_code") != 0:
        raise ValueError("Native full not successful")
    if data.get("scientific_acceptance") != "NOT_RUN":
        raise ValueError("Software-only evidence cannot assert independent science")
    if data.get("docker_delivery") != "DEFERRED_UNTIL_POST_S5":
        raise ValueError("Native evidence is not Docker delivery evidence")
    worktree = Path(data["worktree"])
    if clean_sha(worktree) != sha:
        raise ValueError("Worktree no longer matches evidenced Git SHA")
    jobs = data.get("jobs")
    python = data.get("python_executable")
    if type(jobs) is not int or not 1 <= jobs <= 32 or not isinstance(python, str):
        raise ValueError("Invalid native full toolchain selection")
    steps = data.get("steps", [])
    if len(steps) != len(REQUIRED) or tuple(s.get("name") for s in steps) != REQUIRED:
        raise ValueError("Native full required steps are incomplete")
    expected = commands(worktree, manifest.parent / "build", jobs, python)
    for step, (_, expected_cmd) in zip(steps, expected, strict=True):
        if step.get("command") != expected_cmd:
            raise ValueError("Native full command list was modified")
        if step.get("environment") != step_environment(step["name"], manifest.parent / "build"):
            raise ValueError("Native full source-built S2G environment drift")
        if step.get("exit_code") != 0:
            raise ValueError("Failed test step")
        logfile = manifest.parent / (step["name"] + ".log")
        if not logfile.is_file() or digest(logfile) != step.get("log_sha256"):
            raise ValueError("Missing or modified native full log")
        if not isinstance(step.get("command"), list) or not step["command"]:
            raise ValueError("Missing command evidence")
    return data


def pr_head(pr: int) -> str:
    p = call(["gh", "pr", "view", str(pr), "-R", "RRain001/CTEAS-next",
              "--json", "headRefOid", "--jq", ".headRefOid"])
    if p.returncode or len(p.stdout.strip()) != 40:
        raise ValueError("Cannot verify GitHub PR HEAD")
    return p.stdout.strip()


def publish(manifest: Path, pr: int, dry_run: bool) -> None:
    head = pr_head(pr)
    data = verify(manifest, head)
    print(f"VERIFIED {CONTEXT} at exact PR #{pr} HEAD {head}; no science claim.")
    if dry_run:
        return
    if pr_head(pr) != head:
        raise ValueError("PR HEAD changed before status publication")
    status = call(["gh", "api", "--method", "POST",
                   f"repos/RRain001/CTEAS-next/statuses/{head}",
                   "-f", "state=success", "-f", "context=" + CONTEXT,
                   "-f", "description=Ubuntu native full PASS_SCOPED " + data["run_id"]])
    if status.returncode:
        raise ValueError("Status publish failed: " + status.stderr[-400:])
    print("PUBLISHED", CONTEXT, head)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)
    run_arg = sub.add_parser("run")
    run_arg.add_argument("--worktree", type=Path, required=True)
    run_arg.add_argument("--output-root", type=Path, default=Path("/home/lhy/dev/reports/cteas-native-full"))
    run_arg.add_argument("--jobs", type=int, default=8)
    check_arg = sub.add_parser("verify")
    check_arg.add_argument("manifest", type=Path)
    check_arg.add_argument("--expect-sha")
    send_arg = sub.add_parser("publish")
    send_arg.add_argument("manifest", type=Path)
    send_arg.add_argument("--pr", type=int, required=True)
    send_arg.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    try:
        if args.mode == "run":
            return run(args.worktree, args.output_root, args.jobs)
        if args.mode == "verify":
            d = verify(args.manifest, args.expect_sha)
            print("VERIFIED", d["source_sha"], d["run_id"])
            return 0
        publish(args.manifest, args.pr, args.dry_run)
        return 0
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print("REJECT:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
